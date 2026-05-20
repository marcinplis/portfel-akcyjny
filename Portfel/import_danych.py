import streamlit as st
import yfinance as yf
import pandas as pd
import json
import os
from datetime import datetime, timedelta

# konfiguracja strony mobilnej
st.set_page_config(page_title="portfel", layout="centered")
st.title("notowania portfela")

db_file = "portfel_db.json"

# ladowanie danych z bazy
if not os.path.exists(db_file):
    default_data = {"portfolio": {}, "history": []}
    with open(db_file, "w") as f:
        json.dump(default_data, f)

with open(db_file, "r") as f:
    db = json.load(f)

# zakladki w aplikacji webowej
tab1, tab2 = st.tabs(["na zywo", "zarzadzanie"])

with tab2:
    st.header("zarzadzanie akcjami")
    
    # formularz dodawania i edycji akcji
    with st.form("add_ticker"):
        ticker_input = st.text_input("ticker spolki (np. aapl, pko.wa)").upper().strip()
        amount_input = st.number_input("ilosc akcji", min_value=0.0, step=1.0)
        submit = st.form_submit_button("zapisz zmiany")
        
        if submit and ticker_input:
            if amount_input > 0:
                db["portfolio"][ticker_input] = amount_input
            elif ticker_input in db["portfolio"]:
                del db["portfolio"][ticker_input]
                
            with open(db_file, "w") as f:
                json.dump(db, f)
            st.success(f"zaktualizowano: {ticker_input}")
            st.rerun()

    if db["portfolio"]:
        st.subheader("twoje pozycje")
        for t, q in db["portfolio"].items():
            st.write(f"**{t}**: {q} szt.")


# fragment kodu ktory odswieża sie automatycznie bez przeladowania calej strony
@st.fragment(run_every=60)
def show_live_portfolio(portfolio_data):
    tickers_list = list(portfolio_data.keys())
    total_portfolio_value_pln = 0.0
    
    # pobranie aktualnego kursu usd/pln na zywo
    try:
        usd_pln_ticker = yf.Ticker("PLN=X")
        usd_pln_hist = usd_pln_ticker.history(period="1d")
        if not usd_pln_hist.empty:
            usd_pln_rate = usd_pln_hist["Close"].iloc[-1]
        else:
            usd_pln_rate = usd_pln_ticker.history(period="5d")["Close"].iloc[-1]
    except Exception:
        usd_pln_rate = 4.00
        st.warning("nie udalo sie pobrac biezacego kursu usd/pln, uzyto kursu szacunkowego 4.00")

    st.write(f"aktualny kurs USD/PLN: **{usd_pln_rate:.4f}** (auto-odświeżanie co 60s)")
    st.write("---")
    
    # pobieranie danych dla kazdej spolki
    for ticker in tickers_list:
        qty = portfolio_data[ticker]
        try:
            ticker_data = yf.Ticker(ticker)
            todays_data = ticker_data.history(period="1d", interval="1m")
            
            if not todays_data.empty:
                last_price = todays_data["Close"].iloc[-1]
            else:
                last_price = ticker_data.history(period="5d")["Close"].iloc[-1]
            
            currency = ticker_data.info.get("currency", "PLN")
            
            if currency == "USD":
                value_usd = qty * last_price
                value_pln = value_usd * usd_pln_rate
                st.write(f"{ticker}: {qty} szt. x {last_price:.2f} USD = {value_pln:,.2f} PLN")
            else:
                value_pln = qty * last_price
                st.write(f"{ticker}: {qty} szt. x {last_price:.2f} PLN = {value_pln:,.2f} PLN")
            
            total_portfolio_value_pln += value_pln
            
        except Exception:
            st.error(f"blad pobierania danych dla {ticker}")
    
    st.write("---")
    st.metric(label="calkowita wartosc portfela (PLN)", value=f"{total_portfolio_value_pln:,.2f} PLN")


with tab1:
    st.header("stan portfela na zywo")
    
    if not db["portfolio"]:
        st.info("dodaj pierwsze akcje w zakladce zarzadzanie")
    else:
        # wywolanie automatycznie odswiezanego fragmentu
        show_live_portfolio(db["portfolio"])

    st.write("---")
    st.subheader("historia wartosci portfela")
    
    if db["history"]:
        # Przygotowanie danych historycznych i wymuszenie poprawnego formatu daty
        df_hist = pd.DataFrame(db["history"])
        df_hist["data"] = pd.to_datetime(df_hist["data"], errors='coerce')
        
        # Usunięcie ewentualnych wierszy, które nie mają poprawnej daty
        df_hist = df_hist.dropna(subset=["data"])
        df_hist.set_index("data", inplace=True)
        df_hist = df_hist.sort_index()
        
        # Filtry okresu wyświetlania (ZMIANA: wyciągnięte poza logiczne warunki, żeby zawsze były widoczne)
        period_choice = st.radio(
            "Wybierz okres:",
            ["1M", "3M", "6M", "1Y", "Wszystko"],
            index=4, # Domyślnie "Wszystko"
            horizontal=True,
            key="chart_period_selector"
        )
        
        # Obliczanie daty granicznej
        max_date = df_hist.index.max()
        if period_choice == "1M":
            start_date = max_date - timedelta(days=30)
        elif period_choice == "3M":
            start_date = max_date - timedelta(days=90)
        elif period_choice == "6M":
            start_date = max_date - timedelta(days=180)
        elif period_choice == "1Y":
            start_date = max_date - timedelta(days=365)
        else:
            start_date = df_hist.index.min()
            
        # Bezpieczne filtrowanie danych
        df_filtered = df_hist.loc[start_date:max_date]
        
        if not df_filtered.empty:
            # Zmiana nazw kolumn na czytelne dla wykresu
            df_chart = df_filtered[["baza", "wartosc"]].rename(columns={
                "baza": "Wpłacone środki (Baza)",
                "wartosc": "Wartość portfela"
            })
            # Wyświetlenie interaktywnego wykresu liniowego
            st.line_chart(df_chart)
        else:
            st.warning("Brak danych dla wybranego okresu.")
    else:
        st.info("brak danych historycznych. pierwsze dane pojawia sie po zamknieciu sesji.")