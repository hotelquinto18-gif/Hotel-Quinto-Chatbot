import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Centralized settings/constants for Hotel Quinto Streamlit app
USD_RATE = float(os.getenv("USD_RATE_PER_PERSON", 26))  # fallback to 26

WHATSAPP_E164 = "573202190476"  # +57 320 219 0476
CHECKIN, CHECKOUT = "4:00 PM", "12:00 PM"
ACCEPTED_PAYMENTS = "Cash (COP) or bank transfer only — no card payments."
PROMOS = {"CASHFLOW10": 10, "QUINTO15": 15}
