import streamlit as st
import yfinance as yf
import pandas as pd
import json
import os
import altair as alt
import random
from datetime import datetime, timedelta

# konfiguracja strony mobilnej
st.set_page_config(page_title="portfel", layout="centered")
st.title("notowania portfela")

db_file = "portfel_db.json"
logos_dir = "logos"

if not os.path.exists(logos_dir):
    os.makedirs(logos_dir)

if not os.path.exists(db_file):
    default_data = {"portfolio": {}, "history": []}
    with open(db_file, "w") as f:
        json.dump(default_data, f)

with open(db_file, "r") as f:
    db = json.load(f)

# Paleta ładnych, żywych kolorów startowych do wylosowania przy dodawaniu
VIVID_COLORS = ["#FF5E5B", "#00D2D3", "#FFED66", "#845EC2", "#FF9671", "#26DE81", "#EB4D4B", "#4A90E2", "#F7B731", "#A55EEA"]

# --- OKIENKA DIALOGOWE (MODALE) ---

@st.dialog("Dodaj nową akcję")
def modal_add_ticker():
    ticker_input = st.text_input("Ticker spółki (np. AAPL, PKO.WA)").upper().strip()
    amount_input = st.number_input("Ilość akcji", min_value=0.0, step=1.0, value=0.0)
    price_input = st.number_input("Średnia cena zakupu (za szt.)", min_value=0.0, step=0.01, value=0.0)
    
    # Wybór koloru na wykresie (RGB) z losowym kolorem startowym
    chosen_color = st.color_picker("Kolor spółki na wykresie struktury", value=random.choice(VIVID_COLORS))
    
    if st.button("Zapisz i dodaj", use_container_width=True):
        if ticker_input and amount_input > 0:
            db["portfolio"][ticker_input] = {
                "qty": amount_input,
                "buy_price": price_input,
                "color": chosen_color
            }
            with open(db_file, "w") as f:
                json.dump(db, f)
            st.success(f"Dodano {ticker_input} do portfela!")
            st.rerun()
        else:
            st.error("Podaj poprawny ticker i ilość większą od 0!")

@st.dialog("Edycja pozycji i logo")
def modal_edit_ticker(ticker, current_qty, current_price, current_color):
    st.markdown(f"Edytujesz spółkę: **{ticker}**")
    
    new_qty = st.number_input("Ilość akcji", min_value=0.0, step=1.0, value=float(current_qty))
    new_price = st.number_input("Średnia cena zakupu", min_value=0.0, step=0.01, value=float(current_price))
    
    # Edycja zapisanego koloru
    new_color = st.color_picker("Zmień kolor na wykresie struktury", value=current_color)
    
    st.write("---")
    uploaded_file = st.file_uploader("Wybierz plik graficzny (PNG, JPG)", type=["png", "jpg", "jpeg"], key=f"logo_{ticker}")
    
    if st.button("Zapisz zmiany", use_container_width=True):
        if new_qty > 0:
            db["portfolio"][ticker] = {
                "qty": new_qty, 
                "buy_price": new_price,
                "color": new_color
            }
        else:
            del db["portfolio"][ticker]
            
        if uploaded_file is not None:
            ext = uploaded_file.name.split(".")[-1]
            for e in ["png", "jpg", "jpeg"]:
                old_path = os.path.join(logos_dir, f"{ticker}.{e}")
                if os.path.exists(old_path): os.remove(old_path)
            
            file_path = os.path.join(logos_dir, f"{ticker}.{ext}")
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
                
        with open(db_file, "w") as f:
            json.dump(db, f)
        st.success("Zmiany zostały zapisane!")
        st.rerun()

@st.dialog("Zarządzaj wpłaconym kapitałem (Baza)")
def modal_manage_base():
    # Pobieramy aktualną bazę z ostatniego wpisu w historii
    if db["history"]:
        df_h = pd.DataFrame(db["history"])
        current_baza = float(df_h["baza"].iloc[-1]) if "baza" in df_h.columns else 0.0
        current_wartosc = float(df_h["wartosc"].iloc[-1]) if "wartosc" in df_h.columns else 0.0
    else:
        current_baza = 0.0
        current_wartosc = 0.0
        
    st.markdown(f"Aktualny wpłacony kapitał: **{current_baza:,.2f} PLN**")
    
    amount = st.number_input(
        "Kwota zmiany (np. 5000 dla dopłaty, -2000 dla wypłaty)", 
        value=0.0, 
        step=100.0
    )
    
    st.caption("Operacja zmieni aktualną bazę portfela i doda punkt w historii wyceny.")
    
    if st.button("Zatwierdź operację", use_container_width=True):
        if amount == 0:
            st.error("Wpisz kwotę inną niż 0!")
        else:
            new_baza = current_baza + amount
            # Nową wartość portfela w tym ułamku sekundy szacujemy na starą wartość + dopłata
            new_wartosc = current_wartosc + amount 
            
            # Dodajemy nowy punkt do historii z dzisiejszym timestampem
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            db["history"].append({
                "data": now_str,
                "baza": new_baza,
                "wartosc": new_wartosc
            })
            
            with open(db_file, "w") as f:
                json.dump(db, f)
                
            st.success(f"Pomyślnie zmodyfikowano kapitał o {amount:+,.2f} PLN!")
            st.rerun()

# --- ZAKŁADKI ---
tab1, tab2 = st.tabs(["na zywo", "zarzadzanie"])

with tab2:
    # Górna sekcja: Tytuł i dwa przyciski obok siebie
    col_title, col_btn_add, col_btn_cash = st.columns([1.5, 1, 1])
    with col_title:
        st.header("Zarządzanie")
    with col_btn_add:
        st.markdown("<div style='padding-top: 25px;'></div>", unsafe_allow_html=True)
        if st.button("➕ Dodaj akcję", use_container_width=True):
            modal_add_ticker()
    with col_btn_cash:
        st.markdown("<div style='padding-top: 25px;'></div>", unsafe_allow_html=True)
        if st.button("💰 Dopłata / Wypłata", use_container_width=True):
            modal_manage_base()
            
    st.write("---")
    
    # Lista posiadanych akcji (czyste dane zakupu)
    if not db["portfolio"]:
        st.info("Twój portfel jest pusty. Kliknij 'Dodaj akcję', aby rozpocząć.")
    else:
        for t, info in list(db["portfolio"].items()):
            qty = info["qty"] if isinstance(info, dict) else info
            buy_price = info["buy_price"] if isinstance(info, dict) else 0.0
            color = info.get("color", "#4A90E2") if isinstance(info, dict) else "#4A90E2"
            
            col_logo, col_details, col_edit, col_delete = st.columns([0.6, 3.4, 1.0, 1.0])
            
            with col_logo:
                local_png = os.path.join(logos_dir, f"{t}.png")
                local_jpg = os.path.join(logos_dir, f"{t}.jpg")
                local_jpeg = os.path.join(logos_dir, f"{t}.jpeg")
                
                if os.path.exists(local_png): st.image(local_png, width=40)
                elif os.path.exists(local_jpg): st.image(local_jpg, width=40)
                elif os.path.exists(local_jpeg): st.image(local_jpeg, width=40)
                else: st.markdown("<h3 style='margin:0; padding-top:5px;'>🏢</h3>", unsafe_allow_html=True)
                    
            with col_details:
                st.markdown(f"**{t}** <span style='color:{color};'>■</span>", unsafe_allow_html=True)
                st.markdown(f"<span style='color:#7f8c8d; font-size:14px;'>Ilość: <b>{qty:.0f} szt.</b> | Średnia cena: <b>{buy_price:,.2f}</b></span>", unsafe_allow_html=True)
                
            with col_edit:
                st.markdown("<div style='padding-top: 5px;'></div>", unsafe_allow_html=True)
                if st.button("✏️ Edytuj", key=f"edit_btn_{t}", use_container_width=True):
                    modal_edit_ticker(t, qty, buy_price, color)
                    
            with col_delete:
                st.markdown("<div style='padding-top: 5px;'></div>", unsafe_allow_html=True)
                if st.button("🗑️ Usuń", key=f"del_btn_{t}", use_container_width=True):
                    del db["portfolio"][t]
                    with open(db_file, "w") as f:
                        json.dump(db, f)
                    st.rerun()
                    
            st.markdown("<div style='margin: 5px 0px 10px 0px; border-bottom: 1px solid #f0f2f6;'></div>", unsafe_allow_html=True)


@st.fragment(run_every=60)
def show_live_portfolio(portfolio_data, history_data):
    try:
        usd_pln_ticker = yf.Ticker("PLN=X")
        usd_pln_hist = usd_pln_ticker.history(period="1d")
        if not usd_pln_hist.empty:
            usd_pln_rate = usd_pln_hist["Close"].iloc[-1]
        else:
            usd_pln_rate = usd_pln_ticker.history(period="5d")["Close"].iloc[-1]
    except Exception:
        usd_pln_rate = 4.00

    items = []
    total_portfolio_value_pln = 0.0
    total_prev_day_value_pln = 0.0
    
    for ticker, info in portfolio_data.items():
        qty = info["qty"] if isinstance(info, dict) else info
        buy_price = info["buy_price"] if isinstance(info, dict) else 0.0
        custom_color = info.get("color", "#4A90E2") if isinstance(info, dict) else "#4A90E2"

        try:
            ticker_data = yf.Ticker(ticker)
            hist = ticker_data.history(period="5d")
                
            if not hist.empty and len(hist) >= 1:
                last_price = hist["Close"].iloc[-1]
                prev_price = hist["Close"].iloc[-2] if len(hist) > 1 else last_price
            else:
                raise Exception("Brak danych")
                
            t_info = ticker_data.info
            full_name = t_info.get("longName", ticker)
            currency = t_info.get("currency", "PLN")
            
            rate = usd_pln_rate if currency == "USD" else 1.0
            value_pln = qty * last_price * rate
            prev_day_value_pln = qty * prev_price * rate
            invested_pln = qty * buy_price * rate
            
            daily_change_pct = ((last_price - prev_price) / prev_price * 100) if prev_price > 0 else 0.0
            total_profit_pln = value_pln - invested_pln
            total_roi_pct = (total_profit_pln / invested_pln * 100) if invested_pln > 0 else 0.0
            
            price_str = f"{last_price:.2f} USD" if currency == "USD" else f"{last_price:.2f} PLN"
            
            items.append({
                "ticker": ticker, "name": full_name, "qty": qty, "price_str": price_str,
                "val": value_pln, "daily_change_pct": daily_change_pct,
                "total_profit_pln": total_profit_pln, "total_roi_pct": total_roi_pct,
                "color": custom_color
            })
            
            total_portfolio_value_pln += value_pln
            total_prev_day_value_pln += prev_day_value_pln
            
        except Exception:
            st.error(f"błąd pobierania danych dla {ticker}")
            
    items.sort(key=lambda x: x["val"], reverse=True)
    
    # Kalkulacja kwotowej i procentowej zmiany dziennej portfela
    daily_change_portfolio_pln = total_portfolio_value_pln - total_prev_day_value_pln
    daily_change_portfolio_pct = ((total_portfolio_value_pln - total_prev_day_value_pln) / total_prev_day_value_pln * 100) if total_prev_day_value_pln > 0 else 0.0
    
    if history_data:
        df_h = pd.DataFrame(history_data)
        current_baza_pln = df_h["baza"].iloc[-1] if "baza" in df_h.columns and not df_h.empty else 0.0
    else:
        current_baza_pln = 0.0

    global_profit_from_baza_pln = total_portfolio_value_pln - current_baza_pln
    global_roi_from_baza_pct = (global_profit_from_baza_pln / current_baza_pln * 100) if current_baza_pln > 0 else 0.0

    # --- UKŁAD METRYK NA SAMEJ GÓRZE ---
    col_main_val, col_main_profit = st.columns([1, 1])
    with col_main_val:
        st.metric(label="Aktualna wartość portfela", value=f"{total_portfolio_value_pln:,.2f} PLN")
    with col_main_profit:
        profit_color = "#2ec4b6" if global_profit_from_baza_pln >= 0 else "#e76f51"
        # Tytuł sekcji zmieniony na czystą biel (#FFF)
        st.markdown(f"""
            <div style="line-height: 1.2;">
                <span style="color: #FFF; font-size: 14px; font-weight: 500;">Zysk całkowity od bazy</span><br>
                <span style="color: {profit_color}; font-size: 28px; font-weight: bold;">{global_profit_from_baza_pln:+,.2f} PLN</span><br>
                <span style="color: {profit_color}; font-size: 16px; font-weight: 500;">{global_roi_from_baza_pct:+.2f}%</span>
            </div>
        """, unsafe_allow_html=True)
        
    st.markdown(f"<div style='margin-top: 10px; color:#7f8c8d; font-size:14px;'>Wpłacony kapitał (Baza): <b>{current_baza_pln:,.2f} PLN</b></div>", unsafe_allow_html=True)
    
    # Dodana kwota do zmiany dziennej
    daily_color = "#2ec4b6" if daily_change_portfolio_pct >= 0 else "#e76f51"
    daily_sign = "+" if daily_change_portfolio_pln >= 0 else ""
    st.markdown(f"<div style='margin-top: 5px; font-size:14px;'>Zmiana dzienna portfela: <span style='color:{daily_color}; font-weight:bold;'>{daily_sign}{daily_change_portfolio_pln:,.2f} PLN ({daily_change_portfolio_pct:+.2f}%)</span></div>", unsafe_allow_html=True)
    st.write("---")
    
    st.markdown("### Twoje akcje")
    
    for item in items:
        if item["daily_change_pct"] > 0:
            daily_html = f'<span style="color:#2ec4b6; font-size:13px;">+{item["daily_change_pct"]:.2f}%</span>'
        elif item["daily_change_pct"] < 0:
            daily_html = f'<span style="color:#e76f51; font-size:13px;">{item["daily_change_pct"]:.2f}%</span>'
        else:
            daily_html = f'<span style="color:#7f8c8d; font-size:13px;">0.00%</span>'

        profit_sign = "+" if item["total_profit_pln"] >= 0 else ""
        profit_color = "#2ec4b6" if item["total_profit_pln"] >= 0 else "#e76f51"
        # Procent powiększony z font-size:12px do 14px (zrównanie z resztą)
        total_profit_html = f'''
        <div style="text-align: right;">
            <span style="color:{profit_color}; font-weight:500;">{profit_sign}{item["total_profit_pln"]:,.2f} PLN</span><br>
            <span style="color:{profit_color}; font-size:14px; font-weight:500;">{item["total_roi_pct"]:+.2f}%</span>
        </div>
        '''

        col_icon, col_name, col_qty, col_price, col_total = st.columns([0.5, 2.0, 0.7, 1.8, 2.0])
        
        with col_icon:
            local_png = os.path.join(logos_dir, f"{item['ticker']}.png")
            local_jpg = os.path.join(logos_dir, f"{item['ticker']}.jpg")
            local_jpeg = os.path.join(logos_dir, f"{item['ticker']}.jpeg")
            
            if os.path.exists(local_png): st.image(local_png, width=35)
            elif os.path.exists(local_jpg): st.image(local_jpg, width=35)
            elif os.path.exists(local_jpeg): st.image(local_jpeg, width=35)
            else: st.markdown("<h3 style='margin:0; padding-top:2px;'>🏢</h3>", unsafe_allow_html=True)
                
        with col_name: st.markdown(f"**{item['name']}** \n`{item['ticker']}`")
        with col_qty: st.markdown(f"{item['qty']:.0f} szt.")
        with col_price:
            st.markdown(f"{item['price_str']}")
            st.markdown(daily_html, unsafe_allow_html=True)
        with col_total:
            st.markdown(f"<div style='text-align:right;'><b>{item['val']:,.2f} PLN</b></div>", unsafe_allow_html=True)
            st.markdown(total_profit_html, unsafe_allow_html=True)
            
        st.markdown("<div style='margin: -5px 0px 10px 0px; border-bottom: 1px solid #f0f2f6;'></div>", unsafe_allow_html=True)
        
    # Kurs USD/PLN zmieniony na czystą biel (#FFF)
    st.markdown(f"<div style='text-align: center; color:#FFF; font-size: 13px; margin-top:15px;'>Aktualny kurs USD/PLN: <b>{usd_pln_rate:.4f}</b></div>", unsafe_allow_html=True)

# --- WYKRES STRUKTURY PORTFELA (Z POPRAWIONYM SORTOWANIEM LEGENDY) ---
    if items:
        st.write("---")
        st.subheader("Struktura portfela")
        
        df_chart = pd.DataFrame(items)
        df_chart["y"] = "Skład"
        
        # Wyciągamy przypisane kolory zachowując kolejność malejącą (jak na liście)
        custom_palette = df_chart["color"].tolist()
        order_tickers = df_chart["ticker"].tolist()
        
        chart = alt.Chart(df_chart).mark_bar(size=20).encode(
            x=alt.X("val:Q", stack="normalize", title=None, axis=alt.Axis(format='%', orient='top', title=None)),
            y=alt.Y("y:N", title=None, axis=None),
            color=alt.Color(
                "ticker:N", 
                scale=alt.Scale(domain=order_tickers, range=custom_palette), # Domena i paleta zsynchronizowane z listą
                title="Akcje", 
                sort=order_tickers, # POPRAWKA: sortowanie przeniesione tutaj!
                legend=alt.Legend(orient='bottom', direction='horizontal', columns=5) 
            ),
            order=alt.Order("val:Q", sort="descending"),
            tooltip=[
                alt.Tooltip("ticker:N", title="Ticker"),
                alt.Tooltip("name:N", title="Nazwa"),
                alt.Tooltip("val:Q", format=",.2f", title="Wartość (PLN)")
            ]
        ).properties(width='container', height=120).configure_view(strokeOpacity=0)
        
        st.altair_chart(chart, use_container_width=True)


def render_history_chart(history_data):
    st.write("---")
    if history_data:
        df_hist = pd.DataFrame(history_data)
        df_hist["data"] = pd.to_datetime(df_hist["data"], errors='coerce')
        df_hist = df_hist.dropna(subset=["data"])
        df_hist = df_hist.sort_values("data")
        
        df_hist["zysk_pln"] = df_hist["wartosc"] - df_hist["baza"]
        df_hist["zwrot_proc"] = (df_hist["zysk_pln"] / df_hist["baza"].replace(0, 1)) * 100
        
        period_choice = st.radio("Wybierz okres dla analizy historii:", ["1M", "3M", "6M", "1Y", "Wszystko"], index=4, horizontal=True)
        
        # --- POPRAWKA FILTROWANIA DAT (BEZ UWZGLĘDNIANIA GODZIN) ---
        # Zamieniamy kolumnę z datą na czysty format YYYY-MM-DD do celów filtrowania zakresu
        df_hist["data_czysta"] = pd.to_datetime(df_hist["data"]).dt.date
        
        max_date = df_hist["data_czysta"].max()
        
        if period_choice == "1M": start_date = max_date - timedelta(days=30)
        elif period_choice == "3M": start_date = max_date - timedelta(days=90)
        elif period_choice == "6M": start_date = max_date - timedelta(days=180)
        elif period_choice == "1Y": start_date = max_date - timedelta(days=365)
        else: start_date = df_hist["data_czysta"].min()
            
        # Filtrujemy po czystej dacie (porównanie dzień do dnia, ignorując godziny sesji)
        df_filtered = df_hist[(df_hist["data_czysta"] >= start_date) & (df_hist["data_czysta"] <= max_date)]
        # -----------------------------------------------------------
    
        
        if not df_filtered.empty:
            scale_choice = st.checkbox("Skala od zera (0) dla wartości portfela", value=False)
            
            # Konfiguracja wielopoziomowej osi czasu (Miesiące wyżej, Rok niżej)
           # POPRAWIONA: Bezpieczna konfiguracja osi X z polskimi miesiącami i rokiem
            # POPRAWIONA: Bezpieczna konfiguracja osi X z polskimi miesiącami i rokiem
            x_axis_config = alt.Axis(
                title=None,
                format='%b %Y', # Format: "Mon YYYY" (np. Jan 2026)
                labelExpr=(
                    "substring(datum.label, 0, 3) == 'Jan' ? 'Sty' + substring(datum.label, 3) : "
                    "substring(datum.label, 0, 3) == 'Feb' ? 'Lut' + substring(datum.label, 3) : "
                    "substring(datum.label, 0, 3) == 'Mar' ? 'Mar' + substring(datum.label, 3) : "
                    "substring(datum.label, 0, 3) == 'Apr' ? 'Kwi' + substring(datum.label, 3) : "
                    "substring(datum.label, 0, 3) == 'May' ? 'Maj' + substring(datum.label, 3) : "
                    "substring(datum.label, 0, 3) == 'Jun' ? 'Cze' + substring(datum.label, 3) : "
                    "substring(datum.label, 0, 3) == 'Jul' ? 'Lip' + substring(datum.label, 3) : "
                    "substring(datum.label, 0, 3) == 'Aug' ? 'Sie' + substring(datum.label, 3) : "
                    "substring(datum.label, 0, 3) == 'Sep' ? 'Wrz' + substring(datum.label, 3) : "
                    "substring(datum.label, 0, 3) == 'Oct' ? 'Paź' + substring(datum.label, 3) : "
                    "substring(datum.label, 0, 3) == 'Nov' ? 'Lis' + substring(datum.label, 3) : "
                    "substring(datum.label, 0, 3) == 'Dec' ? 'Gru' + substring(datum.label, 3) : datum.label"
                ),
                grid=False,
                tickCount='month'
            )

           # 1. NAJPIERW DEFINIUJEMY DYNAMICZNE FORMATY TOOLTIPU
            if period_choice in ["1M", "3M"]:
                tooltip_date_format = "%d %b %Y" # Dzień Miesiąc Rok, np. 19 Maj 2026
            else:
                tooltip_date_format = "%b %Y"    # Sam Miesiąc i Rok, np. Maj 2026

            # 2. TUTAJ WYCIĄGAMY OSTATNI ZYSK I DEFINIUJEMY KOLORY (Brak błędu NameError!)
            last_profit = df_filtered["zysk_pln"].iloc[-1] if not df_filtered.empty else 0
            last_return = df_filtered["zwrot_proc"].iloc[-1] if not df_filtered.empty else 0
            
            live_portfolio_color = '#2ec4b6' if last_profit >= 0 else '#e76f51' # turkus / koral
            line_color_profit = '#2ec4b6' if last_profit >= 0 else '#e76f51'
            line_color_return = '#2ec4b6' if last_return >= 0 else '#e76f51'

            # --- WYKRES 1: WARTOŚĆ PORTFELA VS BAZA ---
            st.markdown("#### 1. Wycena portfela na tle wpłat")
            df_melted = df_filtered.melt(id_vars=["data"], value_vars=["baza", "wartosc"], var_name="Typ", value_name="Kwota")
            df_melted["Typ"] = df_melted["Typ"].map({"baza": "Wpłacone środki (Baza)", "wartosc": "Wartość portfela"})
            
            y_scale = alt.Scale(zero=True) if scale_choice else alt.Scale(zero=False)
            color_scale_hist = alt.Scale(domain=["Wpłacone środki (Baza)", "Wartość portfela"], range=["#4F5D75", live_portfolio_color])
            
            chart_val = alt.Chart(df_melted).mark_line(interpolate='linear', strokeWidth=2.5).encode(
                x=alt.X('data:T', axis=x_axis_config),
                y=alt.Y('Kwota:Q', title=None, scale=y_scale),
                color=alt.Color('Typ:N', scale=color_scale_hist, legend=None),
                tooltip=[
                    alt.Tooltip('data:T', title='Data', format=tooltip_date_format),
                    alt.Tooltip('Typ:N', title='Typ'),
                    alt.Tooltip('Kwota:Q', format=',.2f', title='Wartość (PLN)')
                ]
            ).properties(width='container', height=320)
            st.altair_chart(chart_val, use_container_width=True)
            
            # --- WYKRES 2: ZYSK / STRATA KWOTOWO ---
            st.markdown("#### 2. Zysk / Strata kwotowo")
            
            chart_profit = alt.Chart(df_filtered).mark_line(interpolate='linear', strokeWidth=2.5, color=line_color_profit).encode(
                x=alt.X('data:T', axis=x_axis_config),
                y=alt.Y('zysk_pln:Q', title=None, scale=alt.Scale(zero=False)),
                tooltip=[
                    alt.Tooltip('data:T', title='Data', format=tooltip_date_format),
                    alt.Tooltip('zysk_pln:Q', format=',.2f', title='Zysk/Strata (PLN)')
                ]
            ).properties(width='container', height=220)
            
            rule_zero_pln = alt.Chart(pd.DataFrame({'y': [0]})).mark_rule(color='grey', strokeDash=[4, 4]).encode(y='y')
            st.altair_chart(chart_profit + rule_zero_pln, use_container_width=True)
            
            # --- WYKRES 3: STOPA ZWROTU ---
            st.markdown("#### 3. Stopa zwrotu")
            
            chart_perc = alt.Chart(df_filtered).mark_line(interpolate='linear', strokeWidth=2.5, color=line_color_return).encode(
                x=alt.X('data:T', axis=x_axis_config),
                y=alt.Y('zwrot_proc:Q', title=None, scale=alt.Scale(zero=False)),
                tooltip=[
                    alt.Tooltip('data:T', title='Data', format=tooltip_date_format),
                    alt.Tooltip('zwrot_proc:Q', format='+.2f', title='Zwrot (%)')
                ]
            ).properties(width='container', height=220)
            
            rule_zero_pct = alt.Chart(pd.DataFrame({'y': [0]})).mark_rule(color='grey', strokeDash=[4, 4]).encode(y='y')
            st.altair_chart(chart_perc + rule_zero_pct, use_container_width=True)
        else:
            st.warning("Brak danych dla wybranego okresu.")
    else:
        st.info("brak danych historycznych. pierwsze dane pojawia sie po zamknieciu sesji.")


with tab1:
    st.header("stan portfela na zywo")
    if not db["portfolio"]:
        st.info("dodaj pierwsze akcje w zakladce zarzadzanie")
    else:
        show_live_portfolio(db["portfolio"], db["history"])
        render_history_chart(db["history"])