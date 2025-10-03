# settings.py
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
import requests

# Load .env for local runs (Render uses Env Vars)
load_dotenv(override=False)

# ---------- Helpers ----------
def _env_list(key: str, default: str = ""):
    raw = os.getenv(key, default)
    return [s.strip() for s in raw.split(",") if s.strip()]

def _env_promos(key: str, default: str = ""):
    raw = os.getenv(key, default)
    promos = {}
    for chunk in raw.split(";"):
        if ":" in chunk:
            code, desc = chunk.split(":", 1)
            promos[code.strip()] = desc.strip()
    return promos

# ---------- Identity ----------
HOTEL_NAME = os.getenv("HOTEL_NAME", "Hotel Quinto")
OFFICIAL_EMAIL = os.getenv("OFFICIAL_EMAIL", "info@hotelquinto.com")
WHATSAPP_E164 = os.getenv("WHATSAPP_E164", "")

# ---------- Booking ----------
USD_RATE = float(os.getenv("USD_RATE", "26"))
CHECKIN = os.getenv("CHECKIN", "15:00")
CHECKOUT = os.getenv("CHECKOUT", "11:00")

# ---------- Payments & Promos ----------
ACCEPTED_PAYMENTS = _env_list(
    "ACCEPTED_PAYMENTS",
    "Cash (COP), Nequi, Bancolombia Transfer",
)
PROMOS = _env_promos(
    "PROMOS",
    "WEEKLY10:10% off stays of 7+ nights;STAY3PAY2:Stay 3 nights, pay 2",
)

# ---------- FX ----------
USD_TO_COP_FALLBACK = float(os.getenv("USD_TO_COP_FALLBACK", "3900"))
FX_PROVIDER = os.getenv("FX_PROVIDER", "exchangerate_host").lower()
OXR_APP_ID = os.getenv("OXR_APP_ID", "")
FX_TIMEOUT_SECONDS = int(os.getenv("FX_TIMEOUT_SECONDS", "4"))

def fetch_usd_to_cop():
    """
    Returns (rate, timestamp).
    Uses live API if possible, otherwise falls back to USD_TO_COP_FALLBACK.
    """
    try:
        if FX_PROVIDER == "openexchangerates":
            if not OXR_APP_ID:
                raise ValueError("OXR_APP_ID missing")
            url = (
                f"https://openexchangerates.org/api/latest.json?app_id={OXR_APP_ID}&symbols=COP"
            )
            r = requests.get(url, timeout=FX_TIMEOUT_SECONDS)
            r.raise_for_status()
            data = r.json()
            rate = float(data["rates"]["COP"])
        elif FX_PROVIDER in ("exchangerate_host", "exchangeratehost"):
            url = "https://api.exchangerate.host/latest?base=USD&symbols=COP"
            r = requests.get(url, timeout=FX_TIMEOUT_SECONDS)
            r.raise_for_status()
            data = r.json()
            rate = float(data["rates"]["COP"])
        else:
            raise ValueError("Unknown FX_PROVIDER")

        ts = datetime.now(timezone.utc).isoformat()
        return rate, ts
    except Exception:
        return float(USD_TO_COP_FALLBACK), datetime.now(timezone.utc).isoformat()
