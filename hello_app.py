# app.py
import streamlit as st
from datetime import datetime
from urllib.parse import quote as urlquote

# ---- Try to import your project settings (optional). Fallbacks keep things working. ----
try:
    from settings import USD_RATE as SETTINGS_USD_RATE  # default nightly USD per person
except Exception:
    SETTINGS_USD_RATE = 26.0

try:
    # E.164 WhatsApp number for Hotel Quinto (e.g., +57...)
    from settings import WHATSAPP_E164 as SETTINGS_WHATSAPP
except Exception:
    SETTINGS_WHATSAPP = "+573202190476"

# If you have a live FX somewhere in your codebase, import it here.
# Otherwise we will gracefully fall back to 3900.0
def get_fx_rate_defaulted(candidate: float | None) -> float:
    """
    Use provided FX rate if valid; otherwise default to 3900.0 COP per USD.
    """
    try:
        if candidate is not None and float(candidate) > 0:
            return float(candidate)
    except Exception:
        pass
    return 3900.0


# ---------- Booking Summary Card (render) ----------
def render_booking_card(
    usd_per_person=None,
    guests=None,
    nights=None,
    fx_rate_usd_to_cop=None,
    rate_timestamp=None,
    total_usd=None,
    total_cop=None,
    cop_per_person=None,
    asof_str=None,
):
    """
    Render a styled booking summary card in Streamlit.
    Calculates values if not supplied. Uses fallback FX=3900 when missing.
    """
    # Safety defaults
    try:
        usd_per_person = float(usd_per_person) if usd_per_person is not None else float(SETTINGS_USD_RATE)
    except Exception:
        usd_per_person = float(SETTINGS_USD_RATE)

    try:
        guests = int(guests) if guests is not None else 2
        nights = int(nights) if nights is not None else 1
    except Exception:
        guests, nights = 2, 1

    fx_rate = get_fx_rate_defaulted(fx_rate_usd_to_cop)

    # Compute derived values (if not given)
    couples_rate_usd = usd_per_person * 2
    total_usd = float(total_usd) if total_usd is not None else float(usd_per_person * guests * nights)
    total_cop = int(total_cop) if total_cop is not None else int(round(total_usd * fx_rate))
    cop_per_person = int(cop_per_person) if cop_per_person is not None else int(round(usd_per_person * fx_rate))

    # Timestamp label
    if not asof_str:
        if rate_timestamp:
            # if you pass an ISO string, show a friendlier label
            try:
                dt = datetime.fromisoformat(str(rate_timestamp))
                asof_str = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                asof_str = "Today"
        else:
            asof_str = "Today"

    # Formatting helpers (COP with dots for thousands, to match your screenshots)
    def fmt_cop(n: int) -> str:
        return f"{n:,.0f}".replace(",", ".")

    def fmt_usd(n: float) -> str:
        return f"{n:,.2f}"

    # HTML card
    card_html = f"""
    <div style="
        background:#eaf6ff;
        border:1px solid #cfe8ff;
        padding:18px 22px;
        border-radius:16px;
        max-width:980px;">
      <div style="font-size:18px; font-weight:700; color:#0f2a3d;">
        Base Rate: USD ${fmt_usd(usd_per_person)} / person / night (≈ {fmt_cop(cop_per_person)} COP)
      </div>
      <div style="margin-top:8px; color:#2a4b5f;">
        Couples Rate: <b>USD ${fmt_usd(couples_rate_usd)}</b> (≈ {fmt_cop(int(round(couples_rate_usd*fx_rate)))} COP)
      </div>
      <div style="margin-top:12px; color:#0f2a3d;">
        Estimated Total: <b>USD ${fmt_usd(total_usd)}</b> (≈ <b>{fmt_cop(total_cop)} COP</b>)
      </div>
      <div style="margin-top:4px; color:#2a4b5f;">
        for {guests} guest{"s" if guests!=1 else ""}, {nights} night{"s" if nights!=1 else ""}
      </div>
      <div style="margin-top:12px; color:#2a4b5f;">
        Exchange Rate: 1 USD ≈ {fmt_cop(int(round(fx_rate)))} COP (as of {asof_str})
      </div>
    </div>
    """

    st.markdown(card_html, unsafe_allow_html=True)

    # Return a structured dict too (useful for buttons/exports)
    return {
        "usd_per_person": usd_per_person,
        "guests": guests,
        "nights": nights,
        "fx_rate": fx_rate,
        "total_usd": total_usd,
        "total_cop": total_cop,
        "asof_str": asof_str,
    }


# ---------- Streamlit App ----------
st.set_page_config(page_title="Hotel Quinto – Booking Calculator", page_icon="🎁", layout="centered")

def main():
    st.title("Hotel Quinto — Streamlit is working ✅")
    st.write("If you can see this, your environment and VS Code are good to go.")

    st.divider()
    st.subheader("Booking calculator (interactive)")

    with st.form("booking_form", clear_on_submit=False):
        col1, col2, col3 = st.columns(3)

        with col1:
            guests = st.number_input("Guests", min_value=1, max_value=12, value=2, step=1)
        with col2:
            nights = st.number_input("Nights", min_value=1, max_value=60, value=1, step=1)
        with col3:
            # User can type live FX; empty/zero will auto-fallback to 3900
            fx_input = st.number_input("FX: COP per USD (blank/0 → 3,900)", min_value=0.0, max_value=20000.0, value=3960.0, step=10.0)

        use_custom_usd = st.checkbox("Override base rate (USD per person per night)?", value=False)
        if use_custom_usd:
            usd_per_person = st.number_input("USD / person / night", min_value=1.0, max_value=500.0, value=float(SETTINGS_USD_RATE), step=1.0)
        else:
            usd_per_person = float(SETTINGS_USD_RATE)

        asof_str = st.text_input("Label for exchange rate timestamp", value="Today")

        submitted = st.form_submit_button("Calculate")

    if submitted:
        # Fallback to 3900 when input is missing/0/invalid
        fx_rate = get_fx_rate_defaulted(fx_input)

        # Render the card and capture computed values
        result = render_booking_card(
            usd_per_person=usd_per_person,
            guests=int(guests),
            nights=int(nights),
            fx_rate_usd_to_cop=fx_rate,
            rate_timestamp=None,
            asof_str=asof_str
        )

        # Build a human-friendly quote text
        def fmt_cop(n: int) -> str:
            return f"{n:,.0f}".replace(",", ".")
        def fmt_usd(n: float) -> str:
            return f"{n:,.2f}"

        quote_text = (
            "Booking Quote — Hotel Quinto\n"
            f"Guests: {result['guests']}, Nights: {result['nights']}\n"
            f"Base Rate: USD {fmt_usd(result['usd_per_person'])} per person per night\n"
            f"Estimated Total: USD {fmt_usd(result['total_usd'])} (≈ {fmt_cop(result['total_cop'])} COP)\n"
            f"Rate: 1 USD ≈ {fmt_cop(int(round(result['fx_rate'])))} COP (as of {result['asof_str']})\n"
        )

        st.divider()
        st.subheader("Share this quote")

        # WhatsApp deep link
        wa_msg = (
            f"Hello Hotel Quinto 👋, I’d like to book {result['guests']} guest"
            f"{'s' if result['guests']!=1 else ''} for {result['nights']} night"
            f"{'s' if result['nights']!=1 else ''}. "
            f"Estimated total: USD {fmt_usd(result['total_usd'])} "
            f"(≈ {fmt_cop(result['total_cop'])} COP). "
            f"Rate: 1 USD ≈ {fmt_cop(int(round(result['fx_rate'])))} COP ({result['asof_str']})."
        )
        wa_url = f"https://wa.me/{SETTINGS_WHATSAPP.replace('+','')}" \
                 f"?text={urlquote(wa_msg)}"

        colA, colB = st.columns(2)
        with colA:
            st.markdown(f"[📲 Send via WhatsApp]({wa_url})")
        with colB:
            st.download_button(
                "⬇️ Download Quote (.txt)",
                data=quote_text,
                file_name="Hotel_Quinto_Quote.txt",
                mime="text/plain"
            )

        # Provide an easy-to-copy box (works across OS; no extra packages needed)
        with st.expander("Preview / Copy text"):
            st.code(quote_text)


if __name__ == "__main__":
    main()
