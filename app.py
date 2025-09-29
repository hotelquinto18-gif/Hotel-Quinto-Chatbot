# Booking summary card renderer for Streamlit
def render_booking_card(
    usd_per_person,
    guests,
    nights,
    fx_rate_usd_to_cop,
    rate_timestamp,
    total_usd,
    total_cop,
    cop_per_person,
    asof_str=None,
):
    """
    Render a styled booking summary card in Streamlit.
    """
    import streamlit as st
    from datetime import datetime
    try:
        from app import USD_RATE
    except ImportError:
        USD_RATE = 26.0
    try:
        usd_per_person = float(USD_RATE)  # Always use current USD_RATE
        guests = int(guests)
        nights = int(nights)
        fx_rate = float(fx_rate_usd_to_cop)
        total_usd = float(usd_per_person * guests * nights)
        total_cop = int(round(usd_per_person * fx_rate * guests * nights))
        cop_per_person = int(round(usd_per_person * fx_rate))
    except Exception:
        st.error("Invalid booking data.")
        return

    # Format timestamp
    if asof_str:
        asof = asof_str
    elif isinstance(rate_timestamp, str):
        try:
            asof = datetime.fromisoformat(rate_timestamp).strftime("%a, %d %b %Y %H:%M UTC")
        except Exception:
            asof = str(rate_timestamp)
    elif isinstance(rate_timestamp, datetime):
        asof = rate_timestamp.strftime("%a, %d %b %Y %H:%M UTC")
    else:
        asof = "unknown"

    # Format COP with dot as thousands separator, no decimals
    def cop_fmt(val):
        return f"{int(val):,}".replace(",", ".")

    # Couples rate
    couples_rate = usd_per_person * 2
    couples_cop = cop_per_person * 2
    couples_line = ""
    if guests == 2:
        couples_line = f'<div style="margin-bottom:0.7em; color:#1a5678;">Couples Rate: <b>USD ${couples_rate:,.2f}</b> (≈ <b>{cop_fmt(couples_cop)} COP</b>)</div>'

    card = f'''
<div style="background: #eaf6fb; border-radius: 14px; padding: 1.2em 1.5em 1.2em 1.5em; margin-bottom: 1em; border: 1px solid #b6e0fe;">
  <div style="font-size:1.1em; font-weight:600; margin-bottom:0.7em;">
    Base Rate: USD ${usd_per_person:,.2f} / person / night (≈ {cop_fmt(cop_per_person)} COP)
  </div>
  {couples_line}
  <div style="margin-bottom:0.7em;">
    Estimated Total: <b>USD ${total_usd:,.2f}</b> (≈ <b>{cop_fmt(total_cop)} COP</b>)<br/>
    for {guests} guest{'s' if guests != 1 else ''}, {nights} night{'s' if nights != 1 else ''}
  </div>
  <div style="color:#2a4d69; font-size:0.98em;">
    Exchange Rate: 1 USD ≈ {cop_fmt(fx_rate)} COP (as of {asof})
  </div>
</div>
'''
    st.markdown(card, unsafe_allow_html=True)
# Clean booking price text formatter
from datetime import datetime

def format_booking_price_text(
    usd_per_person, guests, nights, fx_rate_usd_to_cop, rate_timestamp
):
    try:
        usd_per_person = float(usd_per_person)
        guests = int(guests)
        nights = int(nights)
        fx_rate = float(fx_rate_usd_to_cop)
    except Exception:
        return "Invalid input."

    cop_per_person = round(usd_per_person * fx_rate)
    total_usd = round(usd_per_person * guests * nights, 2)
    total_cop = round(cop_per_person * guests * nights)

    if isinstance(rate_timestamp, str):
        try:
            rate_timestamp = datetime.fromisoformat(rate_timestamp)
        except Exception:
            rate_timestamp = None

    timestamp_local = (
        rate_timestamp.strftime("%Y-%m-%d %H:%M") if isinstance(rate_timestamp, datetime) else "unknown"
    )

    return (
        f"Base: USD ${usd_per_person:.2f}/person/night (≈ {cop_per_person:,.0f} COP)\n"
        f"Estimated total: USD ${total_usd:.2f} (≈ {total_cop:,.0f} COP) for {guests} guest(s), {nights} night(s)\n"
        f"Rate source: 1 USD ≈ {fx_rate:,.2f} COP (as of {timestamp_local})"
    )

"""
Streamlit Chatbot for Hotel Quinto (refactored)
Run:
    streamlit run app.py
"""


import os
import sys
from datetime import date, timedelta
from urllib.parse import quote_plus
from pathlib import Path
import requests
from dotenv import load_dotenv

# Streamlit import
try:
    import streamlit as st
    ST_AVAILABLE = True
except ModuleNotFoundError:
    st = None
    ST_AVAILABLE = False

# OpenAI import (optional)
try:
    from openai import OpenAI
except Exception:
    OpenAI = None


# ──────────────────────────────────────────────────────────────────────────
# Config & constants
# ──────────────────────────────────────────────────────────────────────────
load_dotenv()

BASE_DIR = Path(__file__).parent
ASSETS = BASE_DIR / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

HOTEL_LAT, HOTEL_LON = 4.57898411319599, -75.73419087522693
WHATSAPP_E164 = "573202190476"  # +57 320 219 0476
CHECKIN, CHECKOUT = "4:00 PM", "12:00 PM"
ACCEPTED_PAYMENTS = "Cash (COP) or bank transfer only — no card payments."
USD_RATE = float(os.getenv("USD_RATE_PER_PERSON", "26"))  # per-person base (USD)
PROMOS = {"CASHFLOW10": 10, "QUINTO15": 15}



# Room data (all paths as lists for consistency)
ROOMS_DATA = [
    {
        "key": "standard",
        "keywords": ["standard", "estandar", "estándar", "single"],
        "paths": [str(ASSETS / "standard.jpg"), str(ASSETS / "standard2.jpg")],
        "caption_en": "Standard — 1 double bed, bamboo style, bathroom across the hall",
        "caption_es": "Estándar — 1 cama doble, estilo bambú, baño al frente",
        "capacity": 2,
    },
    {
        "key": "downstairs",
        "keywords": ["downstairs", "abajo"],
        "paths": [str(ASSETS / "stairs-bedroom-downstairs.jpg")],
        "caption_en": "Downstairs Bedroom — Cozy room on the lower floor",
        "caption_es": "Habitación de abajo — Habitación acogedora en la planta baja",
        "capacity": 3,
    },
    {
        "key": "upstairs",
        "keywords": ["upstairs", "arriba"],
        "paths": [str(ASSETS / "upstairs-bedroom.jpg")],
        "caption_en": "Upstairs Room — Bright with views",
        "caption_es": "Habitación de arriba — Luminosa con vistas",
        "capacity": 3,
    },
    {
        "key": "threebed",
        "keywords": ["three", "triple", "tres"],
        "paths": [str(ASSETS / "three-bed-room.jpg")],
        "caption_en": "Three-Bedroom — Spacious with multiple beds",
        "caption_es": "Habitación triple — Amplia con varias camas",
        "capacity": 4,
    },
    {
        "key": "fourbed",
        "keywords": ["four", "cuatro", "quad"],
        "paths": [str(ASSETS / "four-bed.jpg")],
        "caption_en": "Four-Bedroom — Large with room for groups",
        "caption_es": "Habitación de cuatro camas — Grande para grupos",
        "capacity": 5,
    },
]

ROOM_GENERIC_TRIGGERS = ["room", "rooms", "habitacion", "habitaciones"]

T = {
    "English": {
        "title": "Hotel Quinto • Guest Assistant",
        "welcome": "Hi! I’m the Hotel Quinto assistant. Ask me about rooms, check-in, tips for Colombia, or currency.",
        "placeholder": "Type your question…",
        "faq_title": "Quick Prompts",
        "faqs": [
            "What’s check-in and check-out time?",
            "How do I contact you on WhatsApp?",
            "Where exactly is the hotel on the map?",
            "Tips to avoid currency conversion traps in Colombia",
            "What payment methods do you accept?",
            "What rooms do you offer?",
        ],
        "map_title": "Exact Location (Google Maps)",
        "contact_title": "Contact",
        "whatsapp": "Chat on WhatsApp",
        "hotel_blurb": "Boutique stays in Quindío’s Coffee Triangle. Payments: Cash (COP) or Bank Transfers only.",
        "missing_key": "⚠️ Add your OpenAI API key to .env as OPENAI_API_KEY=... then restart.",
        "booking_title": "Booking Request",
        "booking_button": "Send my dates via WhatsApp",
        "view_photos_title": "View Photos",
        "ask_room_btn": "Ask about this room on WhatsApp",
        "min_capacity": "Minimum capacity",
        "rate_source": "Rate source: 1 USD ≈ {cop:,} COP (as of {asof}).",
        "price_info": "Base: USD ${usd} (~{cop_ppn:,} COP) per person/night. Estimated total: USD ${total_usd:.2f} (~{total_cop:,} COP) for {guests} guest(s), {nights} night(s). ",
        "discount_applied": "Discount applied: {disc}%",
    },
    "Español": {
        "title": "Hotel Quinto • Asistente de Huéspedes",
        "welcome": "¡Hola! Soy el asistente de Hotel Quinto. Pregunta por habitaciones, horarios o consejos para Colombia.",
        "placeholder": "Escribe tu pregunta…",
        "faq_title": "Atajos",
        "faqs": [
            "¿Cuál es el horario de check-in y check-out?",
            "¿Cómo los contacto por WhatsApp?",
            "¿Dónde está exactamente el hotel en el mapa?",
            "Trucos para evitar perder dinero con el cambio en Colombia",
            "¿Qué métodos de pago aceptan?",
            "¿Qué habitaciones ofrecen?",
        ],
        "map_title": "Ubicación exacta (Google Maps)",
        "contact_title": "Contacto",
        "whatsapp": "Chatear por WhatsApp",
        "hotel_blurb": "Estadías boutique en el Eje Cafetero de Quindío. Pagos: solo efectivo (COP) o transferencias bancarias.",
        "missing_key": "⚠️ Agrega tu clave de OpenAI al .env como OPENAI_API_KEY=... y reinicia.",
        "booking_title": "Solicitud de Reserva",
        "booking_button": "Enviar mis fechas por WhatsApp",
        "view_photos_title": "Ver Fotos",
        "ask_room_btn": "Consultar esta habitación por WhatsApp",
        "min_capacity": "Capacidad mínima",
        "rate_source": "Fuente: 1 USD ≈ {cop:,} COP (al {asof}).",
        "price_info": "Tarifa base: USD ${usd} (~{cop_ppn:,} COP) por persona/noche. Total estimado: USD ${total_usd:.2f} (~{total_cop:,} COP) para {guests} huésped(es), {nights} noche(s). ",
        "discount_applied": "Descuento aplicado: {disc}%",
    },
}

# ──────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────

def match_rooms_from_text(text: str):
    t = (text or "").lower()
    matched = [r for r in ROOMS_DATA if any(k in t for k in r["keywords"])]
    if matched:
        return matched
    if any(k in t for k in ROOM_GENERIC_TRIGGERS):
        return ROOMS_DATA
    return []


def room_caption(r, lang: str) -> str:
    return r["caption_es"] if lang == "Español" else r["caption_en"]


def fetch_usd_to_cop():
    """Fetch today's USD->COP rate. Returns (rate_float, as_of_text). Fallback if offline."""
    try:
        r = requests.get("https://open.er-api.com/v6/latest/USD", timeout=6)
        if r.ok:
            data = r.json()
            rate = float(data["rates"]["COP"])
            as_of = data.get("time_last_update_utc", "today")
            return rate, as_of
    except Exception:
        pass
    return 3894.0, "approx (fallback)"

# New: USD to COP conversion using exchangerate.host
def usd_to_cop(amount_usd: float, default_rate: float = 4000.0):
    """
    Convert USD to COP using the latest exchange rate from exchangerate.host.
    Returns (converted_amount, rate_used).
    If the API fails, uses default_rate.
    """
    url = "https://api.exchangerate.host/latest?base=USD&symbols=COP"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        rate = data["rates"]["COP"]
    except Exception:
        rate = default_rate
    converted = amount_usd * rate
    return converted, rate

# New: COP to USD conversion using the same rate
def cop_to_usd(amount_cop: float, default_rate: float = 4000.0):
    """
    Convert COP to USD using the latest exchange rate from exchangerate.host.
    Returns (converted_amount, rate_used).
    If the API fails, uses default_rate.
    """
    url = "https://api.exchangerate.host/latest?base=USD&symbols=COP"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        rate = data["rates"]["COP"]
    except Exception:
        rate = default_rate
    converted = amount_cop / rate
    return converted, rate

def build_whatsapp_url(name, ci, co, guests, room_label, lang):
    if lang == "Español":
        pay = "Confirmo que el pago es en efectivo (COP) o transferencia bancaria (sin tarjetas)."
        prefix = "Hola Hotel Quinto! Quisiera consultar disponibilidad para:"
        msg = f"{prefix} {room_label}. Nombre: {name}. Llegada: {ci} Salida: {co}. Huéspedes: {guests}. {pay}"
    else:
        pay = "I acknowledge payments are Cash (COP) or bank transfer only (no cards)."
        prefix = "Hello Hotel Quinto! I'd like to check availability for:"
        msg = f"{prefix} {room_label}. Name: {name}. Check-in: {ci} Check-out: {co}. Guests: {guests}. {pay}"
    return f"https://wa.me/{WHATSAPP_E164}?text={quote_plus(msg)}"

SYSTEM_PROMPT = (
    "You are the Hotel Quinto assistant. Be concise, friendly, bilingual when needed, "
    "and respect policies: payments are cash (COP) or bank transfer only. "
    "If asked for the address or location, reply with: 'Hotel Quinto is located at Vereda La Frontera, Circasia, Quindío, Colombia. "
    "You can find us on Google Maps here: https://www.google.com/maps/search/?api=1&query=Hotel+Quinto,+Montenegro+-+Circasia+Vereda+La+Frontera,+Montenegro,+Quindío,+Colombia "
    "Always provide helpful tips and a welcoming tone."
)

# ──────────────────────────────────────────────────────────────────────────
# UI
# ──────────────────────────────────────────────────────────────────────────

def show_room_images(room, lang):
    """Show all images for a room, handling errors gracefully."""
    from PIL import Image, ExifTags
    for path in room.get("paths", []):
        if not path:
            continue
        p = Path(path)
        if p.exists():
            try:
                img = Image.open(str(p))
                # Auto-orient using EXIF
                try:
                    for orientation in ExifTags.TAGS.keys():
                        if ExifTags.TAGS[orientation] == 'Orientation':
                            break
                    exif = img._getexif()
                    if exif is not None:
                        orientation_value = exif.get(orientation, None)
                        if orientation_value == 3:
                            img = img.rotate(180, expand=True)
                        elif orientation_value == 6:
                            img = img.rotate(270, expand=True)
                        elif orientation_value == 8:
                            img = img.rotate(90, expand=True)
                except Exception:
                    pass
                st.image(img, caption=room_caption(room, lang), use_container_width=True)
            except Exception:
                st.warning(f"⚠️ Could not load image: {p.name}")
        else:
            st.warning(f"⚠️ Image not found: {p.name}")

def run_streamlit_app():
    # Booking Price Formatter UI
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Booking Price Summary")
    if st.sidebar.button("Show Booking Price Text"):
        # Use sidebar values and current FX rate
        fx_rate = st.session_state.get("fx_rate", 4000.0)
        now = datetime.now()
        summary = format_booking_price_text(
            usd_per_person=USD_RATE,
            guests=guests,
            nights=(co - ci).days if isinstance(co, date) and isinstance(ci, date) else 1,
            fx_rate_usd_to_cop=fx_rate,
            rate_timestamp=now,
        )
        st.sidebar.text(summary)
    st.set_page_config(page_title="Hotel Quinto • Assistant", page_icon="🏨", layout="wide")

    # Sidebar controls
    st.sidebar.markdown("### Settings / Ajustes")
    LANG = st.sidebar.radio("Language / Idioma", ["English", "Español"], index=0)
    TXT = T[LANG]

    st.sidebar.markdown("---")

    st.sidebar.markdown("### Booking Inputs / Datos de Reserva")
    name_in = st.sidebar.text_input("Name / Nombre", value="")
    today = date.today()
    ci = st.sidebar.date_input("Check-in", value=today)
    co = st.sidebar.date_input("Check-out", value=today + timedelta(days=2))
    try:
        guests = st.sidebar.number_input("Guests / Huéspedes", min_value=1, max_value=30, value=2, step=1)
        if guests is None:
            guests = 1
    except Exception:
        guests = 1
    promo_code = st.sidebar.text_input("Promo code (optional)", value="").strip().upper()

    # Currency Converter UI with refresh and warning
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Currency Converter / Convertidor de Moneda")

    # Session state for rate
    if "fx_rate" not in st.session_state or "fx_rate_time" not in st.session_state:
        # Try to fetch on first load
        _, live_rate = usd_to_cop(1.0)
        st.session_state["fx_rate"] = live_rate
        st.session_state["fx_rate_time"] = None

    if st.sidebar.button("🔄 Refresh Rate"):
        _, live_rate = usd_to_cop(1.0)
        st.session_state["fx_rate"] = live_rate
        st.session_state["fx_rate_time"] = None

    conversion_type = st.sidebar.radio("Direction / Dirección", ["USD → COP", "COP → USD"], index=0)
    fx_rate = st.session_state["fx_rate"]
    default_rate = 4000.0
    api_failed = fx_rate == default_rate

    if conversion_type == "USD → COP":
        usd_amount = st.sidebar.number_input("USD", min_value=0.0, value=1.0, step=1.0, format="%.2f")
        cop_value = usd_amount * fx_rate
        st.sidebar.write(f"{usd_amount:.2f} USD ≈ {cop_value:,.0f} COP")
        st.sidebar.caption(f"Rate: 1 USD = {fx_rate:,.2f} COP")
    else:
        cop_amount = st.sidebar.number_input("COP", min_value=0.0, value=4000.0, step=1000.0, format="%.0f")
        usd_value = cop_amount / fx_rate if fx_rate else 0
        st.sidebar.write(f"{cop_amount:,.0f} COP ≈ {usd_value:.2f} USD")
        st.sidebar.caption(f"Rate: 1 USD = {fx_rate:,.2f} COP")

    if api_failed:
        st.sidebar.warning("Live rate unavailable. Using default rate. Please check your internet connection or try again later.")

    st.title(TXT.get("title", "Hotel Quinto • Assistant"))
    st.caption(TXT.get("hotel_blurb", ""))

    # Layout
    col_chat, col_info = st.columns([0.6, 0.4])

    # Right column (info)
    with col_info:
        st.subheader(TXT.get("map_title", "Location"))
        embed_url = f"https://www.google.com/maps?q={HOTEL_LAT},{HOTEL_LON}&z=17&output=embed"
        st.components.v1.iframe(embed_url, height=260, scrolling=False)
        business_url = "https://maps.app.goo.gl/YmUyB3t5bcksvCri6?g_st=ipc"
        st.markdown(f"[🌍 Open Hotel Quinto on Google Maps]({business_url})")

        st.subheader(TXT.get("contact_title", "Contact"))
        contact_md = (
            f"**WhatsApp:** [{TXT.get('whatsapp', 'WhatsApp')}]"
            f"(https://wa.me/{WHATSAPP_E164})\n\n"
            f"**Check-in:** {CHECKIN}  \n"
            f"**Check-out:** {CHECKOUT}  \n"
            f"**Payments:** {ACCEPTED_PAYMENTS}"
        )
        st.markdown(contact_md)
        st.markdown("---")

        # Pricing & discounts block
        def group_discount(n: int) -> int:
            if n >= 8:
                return 10
            if n >= 6:
                return 8
            if n >= 4:
                return 5
            return 0

        disc_group = group_discount(int(guests))
        disc_promo = PROMOS.get(promo_code, 0)
        applied_disc = max(disc_group, disc_promo)

        if applied_disc > 0:
            if LANG == "Español":
                origen = "código" if disc_promo >= disc_group else "grupo"
                st.success(f"Descuento aplicado: {applied_disc}% ({origen})")
            else:
                origin = "promo" if disc_promo >= disc_group else "group"
                st.success(f"Discount applied: {applied_disc}% ({origin})")

        nights = (co - ci).days if isinstance(co, date) and isinstance(ci, date) else 0
        if nights <= 0:
            st.error(
                "La fecha de salida debe ser posterior a la fecha de llegada."
                if LANG == "Español"
                else "Check-out must be after check-in."
            )
        else:
            CURRENT_CONV, AS_OF = fetch_usd_to_cop()
            cop_ppn = int(USD_RATE * CURRENT_CONV)
            total_usd = USD_RATE * guests * nights
            total_cop = cop_ppn * guests * nights
            if applied_disc > 0:
                total_usd *= (1 - applied_disc / 100)
                total_cop = int(total_cop * (1 - applied_disc / 100))

            info_text = TXT.get("price_info", "").format(
                usd=int(USD_RATE),
                cop_ppn=cop_ppn,
                total_usd=total_usd,
                total_cop=total_cop,
                guests=int(guests),
                nights=nights,
            )
            if applied_disc > 0:
                info_text += TXT.get("discount_applied", "").format(disc=applied_disc) + " • "
            info_text += TXT.get("rate_source", "").format(cop=int(CURRENT_CONV), asof=AS_OF)
            st.info(info_text)

            # WhatsApp CTA
            if LANG == "Español":
                pre = "¡Hola Hotel Quinto! Quiero consultar disponibilidad."
                pay = "Confirmo pago en efectivo (COP) o transferencia bancaria (sin tarjetas)."
                disc_txt = f" Descuento aplicado: {applied_disc}%" if applied_disc > 0 else ""
                nights_txt = f" Estancia: {nights} noche(s)."
                msg = f"{pre} Nombre: {name_in}. Llegada: {ci} Salida: {co}. Huéspedes: {int(guests)}.{nights_txt}.{disc_txt}"
            else:
                pre = "Hello Hotel Quinto! I'd like to check availability."
                pay = "I acknowledge payments are Cash (COP) or bank transfer only (no cards)."
                disc_txt = f" Discount applied: {applied_disc}%" if applied_disc > 0 else ""
                nights_txt = f" Stay: {nights} night(s)."
                msg = f"{pre} Name: {name_in}. Check-in: {ci} Check-out: {co}. Guests: {int(guests)}.{nights_txt}.{disc_txt}"

            wa_url = f"https://wa.me/{WHATSAPP_E164}?text={quote_plus(msg + ' ' + pay)}"
            try:
                st.link_button(TXT.get("booking_button", "Send on WhatsApp"), wa_url, use_container_width=True)
            except Exception:
                st.markdown(f"[**{TXT.get('booking_button', 'Send on WhatsApp')}**]({wa_url})")


        # Rooms & Photos
        st.markdown("---")
        st.subheader("Rooms & Photos / Habitaciones & Fotos")
        min_cap = st.slider(TXT.get("min_capacity", "Minimum capacity"), min_value=1, max_value=8, value=1)
        filtered_rooms = [r for r in ROOMS_DATA if r.get("capacity", 1) >= min_cap]
        for r in filtered_rooms:
            show_room_images(r, LANG)
        # WhatsApp CTA (always show, for last room)
        if filtered_rooms:
            last_caption = room_caption(filtered_rooms[-1], LANG)
            room_url = build_whatsapp_url(name_in, ci, co, int(guests), last_caption, LANG)
            try:
                st.link_button(TXT.get("ask_room_btn", "Ask on WhatsApp"), room_url, use_container_width=True)
            except Exception:
                st.markdown(f"[**{TXT.get('ask_room_btn', 'Ask on WhatsApp')}**]({room_url})")


        # Quick canned content -> appends to chat
        st.markdown(f"**{TXT.get('view_photos_title', 'View Photos')}**")
        buttons = (
            [
                ("Ver Habitación Estándar", "Aquí tienes la Habitación Estándar: 1 cama doble, estilo bambú, baño al frente."),
                ("Ver Habitación Familiar", "Aquí tienes la Habitación Familiar: 2–3 camas dobles, baño privado, vista a montañas."),
                ("Ver Habitación Grupal", "Aquí tienes la Habitación Grupal: camas + camarotes, baño privado."),
                ("Ver Habitación Grande", "Aquí tienes la Habitación Grande: 3–4 camas, luminosa, baño privado."),
                ("Ver Casa Anexa en Circasia", "Casa Anexa en Circasia: 3 habitaciones, todas con baño privado; dos con vistas asombrosas."),
                ("Ver todas las habitaciones", "Tenemos Estándar, Familiar, Grupal, Grande y Casa Anexa en Circasia."),
            ]
            if LANG == "Español"
            else [
                ("View Standard Room", "Standard Room: 1 double bed, bamboo style, bathroom across the hall."),
                ("View Family Room", "Family Room: 2–3 double beds, private bath, mountain views."),
                ("View Group Bunk", "Group Bunk: beds + bunks, private bathroom."),
                ("View Large Room", "Large Room: 3–4 beds, bright, private bath."),
                ("View Annex House in Circasia", "Annex House (Circasia): 3 rooms, all private bath; two with astonishing viewpoints."),
                ("View all rooms", "Rooms available: Standard, Family, Group Bunk, Large, Annex House in Circasia."),
            ]
        )
        for label, content in buttons:
            if st.button(label, use_container_width=True):
                if "messages" not in st.session_state:
                    st.session_state["messages"] = []
                st.session_state["messages"].append({"role": "assistant", "content": content})

        # FAQ prompt buttons
        st.markdown("---")
        st.subheader(TXT.get("faq_title", "Quick Prompts"))
        for q in TXT.get("faqs", []):
            if st.button(q, use_container_width=True):
                if "messages" not in st.session_state:
                    st.session_state["messages"] = []
                st.session_state["messages"].append({"role": "user", "content": q})


    # Left column (chat)
    with col_chat:
        if "messages" not in st.session_state:
            st.session_state["messages"] = []

        if not st.session_state["messages"]:
            st.info(TXT.get("welcome", "Welcome!"))
        else:
            for m in st.session_state["messages"]:
                role = "user" if m.get("role") == "user" else "assistant"
                st.chat_message(role).markdown(m.get("content", ""))
                if role == "assistant":
                    for r in match_rooms_from_text(m.get("content", "")):
                        show_room_images(r, LANG)

        # Chat input (optional OpenAI)
        user_msg = st.chat_input(TXT.get("placeholder", "Type your question…"))
        if user_msg:
            st.session_state["messages"].append({"role": "user", "content": user_msg})
            api_key = os.getenv("OPENAI_API_KEY", "").strip()
            if not api_key or OpenAI is None:
                reply = "Thanks! Share dates via WhatsApp or click a room to ask about availability."
                st.chat_message("assistant").markdown(reply)
                st.session_state["messages"].append({"role": "assistant", "content": reply})
            else:
                client = OpenAI()
                convo = [{"role": "system", "content": SYSTEM_PROMPT}] + st.session_state["messages"]
                with st.chat_message("assistant"):
                    with st.spinner("Thinking…"):
                        resp = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=convo,
                            temperature=0.4,
                            max_tokens=700,
                        )
                        answer = resp.choices[0].message.content
                        st.markdown(answer)
                        st.session_state["messages"].append({"role": "assistant", "content": answer})
                        for r in match_rooms_from_text(answer):
                            show_room_images(r, LANG)

    # Footer
    st.markdown(
        """
        <div style='text-align:center; color:gray; font-size:0.9em; margin-top:1rem;'>
            Built with Streamlit • Hotel Quinto
        </div>
        """,
        unsafe_allow_html=True,
    )

# ──────────────────────────────────────────────────────────────────────────
# Self-tests for non-UI parts
# ──────────────────────────────────────────────────────────────────────────
def _self_tests():
    rate, asof = fetch_usd_to_cop()
    assert isinstance(rate, float) and rate > 0, "Rate must be positive float"
    assert isinstance(asof, str), "As-of text must be str"

    res = match_rooms_from_text("Tell me about the family room")
    keys = {r["key"] for r in res}
    assert "family" in keys, "Family room should match"

    res_all = match_rooms_from_text("Do you have rooms?")
    assert len(res_all) == len(ROOMS_DATA), "Generic 'rooms' should return all"

    url = build_whatsapp_url("Alice", "2025-09-10", "2025-09-12", 2, "Family Room", "English")
    assert "wa.me" in url and "Alice" in requests.utils.unquote(url), "WA URL must include name"
    print("Self-tests passed ✅")
from pathlib import Path


def check_assets():
    """Verify that all image files referenced in ROOMS_DATA exist."""
    missing = []
    for r in ROOMS_DATA:
        for path in r.get("paths", []):
            if not path:
                continue
            p = Path(path)
            if not p.exists():
                missing.append(str(p))
    if missing:
        msg = "Missing image files:\n" + "\n".join(f"• {m}" for m in missing)
        if ST_AVAILABLE:
            st.warning(msg)
        else:
            print(msg)
check_assets()

if __name__ == "__main__":
    if ST_AVAILABLE:
        try:
            run_streamlit_app()
        except Exception as e:
            st.error(f"UI rendering error: {e}")
    else:
        print("\nModuleNotFoundError: No module named 'streamlit'\n")
        print("This file includes a Streamlit app. To run the UI, install and launch Streamlit:")
        print("  pip install streamlit python-dotenv requests openai")
        print("  streamlit run app.py")
        print("Running quick self-tests for helper functions instead…")
        try:
            _self_tests()
        except AssertionError as e:
            print(f"Self-test failed: {e}")
            sys.exit(1)
        sys.exit(0)
