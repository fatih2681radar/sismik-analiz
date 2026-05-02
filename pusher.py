import os
import time
import subprocess
import shutil
import sqlite3
import pandas as pd

# --- AYARLAR ---
BEKLEME_SURESI = 30 
DB_ADI = "radar_gecmisi.db"
ARSIV_KLASORU = "islenen_csvler"

# Arşiv klasörü yoksa oluştur
if not os.path.exists(ARSIV_KLASORU):
    os.makedirs(ARSIV_KLASORU)

def git_yolu_bul():
    yol = shutil.which("git")
    if yol: return yol
    muhtemel_yollar = [
        r"C:\Program Files\Git\bin\git.exe",
        r"C:\Program Files\Git\cmd\git.exe",
        os.path.expanduser(r"~\AppData\Local\GitHubDesktop\bin\git.exe")
    ]
    for p in muhtemel_yollar:
        if os.path.exists(p): return p
    return None

def db_arsivle():
    """CSV'leri okur, DB'ye yazar ve dosyayı arşiv klasörüne taşır."""
    csv_dosyalari = [f for f in os.listdir('.') if f.endswith('.csv')]
    if not csv_dosyalari: return

    try:
        conn = sqlite3.connect(DB_ADI)
        conn.execute('''CREATE TABLE IF NOT EXISTS sinyaller 
                        (Z_Obj TEXT, Zaman TEXT, Deger REAL)''')
        
        for dosya in csv_dosyalari:
            # CSV Oku
            df = pd.read_csv(dosya, sep=';', header=None, names=['A', 'B', 'Deger', 'Zaman'], on_bad_lines='skip')
            
            # Veri Temizleme ve Formatlama
            df['Zaman'] = df['Zaman'].astype(str).replace('nan', '')
            df['Deger'] = pd.to_numeric(df['Deger'].astype(str).str.replace(',', '.'), errors='coerce')
            df['Zaman'] = df['Zaman'].apply(lambda x: x.split(' ')[-1] if ' ' in x else x)
            df['Z_Obj'] = pd.to_datetime(df['Zaman'], format='%H:%M:%S', errors='coerce').astype(str)
            
            df_yaz = df[['Z_Obj', 'Zaman', 'Deger']].dropna(subset=['Zaman', 'Deger'])
            
            if not df_yaz.empty:
                df_yaz.to_sql('sinyaller', conn, if_exists='append', index=False)
                print(f"✅ {dosya} veritabanına işlendi.")
            
            # İşlenen dosyayı taşı (Mükerrer kaydı önlemek için en güvenli yol)
            conn.commit() 
            shutil.move(dosya, os.path.join(ARSIV_KLASORU, dosya))
        
        conn.close()
    except Exception as e:
        print(f"⚠️ DB Hatası: {e}")

def github_gonder():
    git_exe = git_yolu_bul()
    if not git_exe:
        print("❌ HATA: Git bulunamadı!")
        return

    try:
        # 1. Önce yerel arşivi güncelle
        db_arsivle()

        # 2. Git işlemlerini başlat
        subprocess.run([git_exe, "add", "."], check=True)
        
        # Değişiklik var mı kontrolü
        status = subprocess.run([git_exe, "diff", "--cached", "--quiet"])
        if status.returncode == 0:
            print(f"[{time.strftime('%H:%M:%S')}] Yeni veri yok, bekleniyor...")
            return

        print(f"[{time.strftime('%H:%M:%S')}] Veriler GitHub'a fırlatılıyor...")
        subprocess.run([git_exe, "commit", "-m", "Oto-Veri-Guncelleme"], capture_output=True)
        subprocess.run([git_exe, "pull", "origin", "main", "--rebase"], capture_output=True)
        subprocess.run([git_exe, "push", "origin", "main"], check=True)
        
        print("🚀 Başarılı: seismicradar.streamlit.app güncellendi!")

    except Exception as e:
        print(f"🚨 Hata: {e}")

print("🚀 Sismik Otomatik Pusher v5.0 (Full Otomatik)")
print(f"Döngü Süresi: {BEKLEME_SURESI} Saniye")
print("-" * 45)

while True:
    github_gonder()
    time.sleep(BEKLEME_SURESI)