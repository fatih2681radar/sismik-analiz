import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from scipy.signal import find_peaks
import os, glob, time as time_lib
import sqlite3
import requests
from datetime import datetime, timedelta, time, date

# --- 1. EKRAN AYARLARI ---
st.set_page_config(page_title="Radar Pro v2.5", layout="wide")
st.markdown("""
    <style>
    .block-container {padding-top: 3.5rem;}
    [data-testid='stMetric'] {background-color: #1e1e1e; padding: 5px; border-radius: 8px; border: 1px solid #333;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. ANALİZ PARAMETRELERİ (SABİT) ---
P_HASSASIYET = 0.010
RITIM_RISK = 1.6

# --- 3. FONKSİYONLAR ---
@st.cache_data(ttl=600)
def depremleri_getir():
    try:
        # Büyüklük sınırı 3.0 yapıldı (Küçük depremleri yakalamak için)
        url = "https://seismicportal.eu"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        events = []
        for f in data['features']:
            p = f['properties']
            utc_dt = datetime.strptime(p['time'][:19], "%Y-%m-%dT%H:%M:%S")
            tsi_dt = utc_dt + timedelta(hours=3) # Türkiye Saati
            events.append({"Zaman": tsi_dt.strftime("%H:%M:%S"), "Buyukluk": p['mag']})
        return pd.DataFrame(events)
    except: return pd.DataFrame()

def dosya_oku(dosya_yolu):
    if not dosya_yolu or not os.path.exists(dosya_yolu): return pd.DataFrame()
    data_list = []
    try:
        with open(dosya_yolu, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                clean = line.strip()
                if not clean or any(x in clean for x in ["Elapsed", "["]): continue
                parts = [p.strip() for p in clean.split(';')]
                if len(parts) >= 3:
                    try:
                        v = float(parts[2].replace(',', '.'))
                        t_s = parts[-1].split(' ')[-1]
                        t_o = pd.to_datetime(t_s, format='%H:%M:%S', errors='coerce')
                        data_list.append({'Z_Obj': t_o, 'Zaman': t_s, 'Deger': v})
                    except: continue
        df_res = pd.DataFrame(data_list)
        if not df_res.empty:
            return df_res.groupby('Zaman').agg({'Z_Obj': 'first', 'Deger': 'mean'}).reset_index()
    except: pass
    return pd.DataFrame()

def db_arsiv_cek(secili_tarih, bas_saat, bit_saat):
    try:
        conn = sqlite3.connect("radar_gecmisi.db")
        df_db = pd.read_sql("SELECT * FROM sinyaller", conn)
        conn.close()
        if not df_db.empty:
            df_db['Z_Obj'] = pd.to_datetime(df_db['Z_Obj'])
            df_db['Saat_Obj'] = df_db['Z_Obj'].dt.time
            mask = (df_db['Z_Obj'].dt.date == secili_tarih) & \
                   (df_db['Saat_Obj'] >= bas_saat) & \
                   (df_db['Saat_Obj'] <= bit_saat)
            return df_db.loc[mask]
    except: pass
    return pd.DataFrame()

# --- 4. YAN PANEL ---
st.sidebar.markdown("### 📡 Radar Kontrol")
menu = st.sidebar.radio("Sayfa Seçimi:", ["🔴 Canlı Akış", "⏱️ Ritim Geçmişi", "📂 Arşiv"])

if menu == "📂 Arşiv":
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔍 Arşiv Filtresi")
    arsiv_gun = st.sidebar.date_input("Tarih Seçin:", date.today())
    bas_s = st.sidebar.time_input("Başlangıç Saati:", time(0, 0))
    bit_s = st.sidebar.time_input("Bitiş Saati:", time(23, 59))
else:
    hiz = st.sidebar.slider("Akış Hızı (Sn)", 1, 10, 3)
    secili_dosya = st.sidebar.selectbox("Dosya Seç:", sorted(glob.glob("*.csv"), reverse=True)) if glob.glob("*.csv") else None

# --- 5. ANA İŞLEM DÖNGÜSÜ ---
if menu == "📂 Arşiv":
    st.subheader(f"📂 {arsiv_gun} Tarihli Arşiv Kayıtları")
    df_arsiv = db_arsiv_cek(arsiv_gun, bas_s, bit_s)
    if not df_arsiv.empty:
        fig_arsiv = go.Figure()
        fig_arsiv.add_trace(go.Scatter(x=df_arsiv['Zaman'], y=df_arsiv['Deger'], mode='lines', line=dict(color='#00ff00', width=1)))
        fig_arsiv.update_layout(template='plotly_dark', height=500, xaxis=dict(nticks=15, tickangle=0))
        st.plotly_chart(fig_arsiv, use_container_width=True)
        st.dataframe(df_arsiv[::-1], use_container_width=True, hide_index=True)
    else:
        st.info(f"{arsiv_gun} tarihinde bu saatlerde kayıt bulunamadı.")

elif (menu == "🔴 Canlı Akış" or menu == "⏱️ Ritim Geçmişi") and secili_dosya:
    df = dosya_oku(secili_dosya)
    if not df.empty:
        df_deprem = depremleri_getir()
        p_idx, _ = find_peaks(df['Deger'], prominence=P_HASSASIYET, distance=10)
        
        son_r, r_say, l_rit = 0, 0, 0
        res = []
        for i in range(len(p_idx)):
            curr = df.iloc[p_idx[i]]
            f = int((curr['Z_Obj'] - df.iloc[p_idx[i-1]]['Z_Obj']).total_seconds()) if i > 0 else 0
            if i > 0: son_r = f
            if i == 1: l_rit = f
            durum = "Normal"
            if l_rit > 0:
                if f >= l_rit * RITIM_RISK: r_say += 1; durum = "⚠️ RİSKLİ"
                else: l_rit = f
            res.append({"Zaman": curr['Zaman'], "sn": f, "mV": round(curr['Deger'], 2), "D": durum})
        
        st.session_state['tablo'] = res

        if menu == "🔴 Canlı Akış":
            m = st.columns(5)
            m[0].metric("Anlık", f"{df['Deger'].iloc[-1]:.2f} mV")
            m[1].metric("Maksimum", f"{df['Deger'].max():.2f} mV")
            m[2].metric("Sismik Ritim", f"{son_r} sn")
            m[3].metric("Peak Sayısı", len(p_idx))
            m[4].metric("Riskli Atım", r_say)

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['Zaman'], y=df['Deger'], mode='lines', line=dict(color='#00ff00', width=1), name="Sinyal"))
            if len(p_idx) > 0:
                fig.add_trace(go.Scatter(x=df.iloc[p_idx]['Zaman'], y=df.iloc[p_idx]['Deger'], mode='markers', marker=dict(color='red', size=6), name="Peak"))
            
            # --- DEPREM ÇİZGİSİ (DAKİKA BAZLI KESİN ÇÖZÜM) ---
            if not df_deprem.empty:
                for _, dep in df_deprem.iterrows():
                    dep_dk = dep['Zaman'][:5] # Saniyeyi at, dakika al
                    for z in df['Zaman'].unique():
                        if z[:5] == dep_dk:
                            fig.add_vline(x=z, line_width=3, line_dash="dash", line_color="orange")
                            fig.add_annotation(x=z, y=df['Deger'].max(), text=f"M{dep['Buyukluk']}", showarrow=True, bgcolor="orange", font=dict(color="black"))
                            break

            fig.update_layout(template='plotly_dark', height=450, margin=dict(l=10, r=10, t=10, b=10), xaxis=dict(nticks=10, tickangle=0))
            st.plotly_chart(fig, use_container_width=True)
        
        else:
            st.subheader("⏱️ Detaylı Ritim Geçmişi")
            df_final = pd.DataFrame(st.session_state.get('tablo', []))
            st.dataframe(df_final[::-1], use_container_width=True, hide_index=True)
            
            fig_rit = go.Figure()
            fig_rit.add_trace(go.Scatter(x=df_final["Zaman"], y=df_final["sn"], mode='lines+markers', name="Ritim"))
            
            riskler = df_final[df_final["D"] == "⚠️ RİSKLİ"]
            if not riskler.empty:
                fig_rit.add_trace(go.Scatter(x=riskler["Zaman"], y=riskler["sn"], mode='markers', marker=dict(color='red', size=10, symbol='x')))

            fig_rit.update_layout(template='plotly_dark', height=350, xaxis=dict(nticks=10, tickangle=0))
            st.plotly_chart(fig_rit, use_container_width=True)

        time_lib.sleep(hiz); st.rerun()
else:
    st.info("Lütfen bir CSV dosyası seçin veya Arşiv'e gidin.")
