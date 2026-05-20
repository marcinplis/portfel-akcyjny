import json
import os
import yfinance as yf
from datetime import datetime

# --- OCHRONA PRZED WEEKENDAMI ---
today = datetime.now()
# 5 = Sobota, 6 = Niedziela
if today.weekday() in [5, 6]:
    print(f"[{today.strftime('%Y-%m-%d')}] Weekend! Rynki są zamknięte. Pomijam zapisywanie historii.")
    exit() # Kończymy działanie skryptu tutaj
# --------------------------------

db_file = "portfel_db.json"

if not os.path.exists(db_file):
    print("Błąd: Plik bazy danych nie istnieje!")
    exit()

with open(db_file, "r") as f:
    db = json.load(f)

# 1. Pobranie kursu USD/PLN
try:
    usd_pln_ticker = yf.Ticker("PLN=X")
    usd_pln_hist = usd_pln_ticker.history(period="1d")
    usd_pln_rate = usd_pln_hist["Close"].iloc[-1] if not usd_pln_hist.empty else 4.00
except Exception:
    usd_pln_rate = 4.00

# 2. Przeliczenie aktualnej wartości wszystkich akcji
total_portfolio_value_pln = 0.0

for ticker, info in db["portfolio"].items():
    qty = info["qty"] if isinstance(info, dict) else info
    
    try:
        ticker_data = yf.Ticker(ticker)
        hist = ticker_data.history(period="1d")
        if not hist.empty:
            last_price = hist["Close"].iloc[-1]
        else:
            last_price = ticker_data.history(period="5d")["Close"].iloc[-1]
            
        currency = ticker_data.info.get("currency", "PLN")
        rate = usd_pln_rate if currency == "USD" else 1.0
        total_portfolio_value_pln += qty * last_price * rate
    except Exception as e:
        print(f"Błąd pobierania danych dla {ticker}: {e}")

# 3. Pobranie aktualnej bazy
if db["history"]:
    current_baza = db["history"][-1].get("baza", 0.0)
else:
    current_baza = 0.0

# 4. Dodanie punktu do historii
now_str = today.strftime("%Y-%m-%d")
nowy_wpis = {
    "data": now_str,
    "baza": current_baza,
    "wartosc": round(total_portfolio_value_pln, 2)
}

db["history"].append(nowy_wpis)

with open(db_file, "w") as f:
    json.dump(db, f, indent=4)

print(f"[{now_str}] Sukces! Zapisano wycenę po sesji: {total_portfolio_value_pln:,.2f} PLN")