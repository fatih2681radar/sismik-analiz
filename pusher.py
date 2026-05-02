import os
import time
import subprocess
import shutil
import sqlite3
import pandas as pd

# --- AYARLAR ---
BEKLEME_SURESI = 30 
DB_ADI = "radar_gecmisi.db"

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
    """Klasördeki CSV verilerini okur ve SQLite veritabanına işler."""
    csv_dosyalari = [f for f in os.listdir('.') if f.endswith('.csv')]
    if not csv_dosyalari: return

    try:
        conn = sqlite3.connect(DB_ADI)
        # Tablo yoksa oluştur (Streamlit kodunla tam uyumlu kolonlar)
        conn.execute('''CREATE TABLE IF NOT EXISTS sinyaller 
                        (Z_Obj TEXT, Zaman TEXT, Deger REAL)''')
        
        for dosya in csv_dosyalari:
            # CSV dosyasını oku (senin dosya_oku fonksiyonundaki mantıkla)
            df = pd.read_csv(dosya, sep=';', header=None, names=['A', 'B', 'Deger', 'Zaman'], on_bad_lines='skip')
            # Sayısal dönüşüm ve temizlik
            df['Deger'] = pd.to_numeric(df['Deger'].astype(str).str.replace(',', '.'), errors='coerce')
            df['Zaman'] = df['Zaman'].astype(str).str.split(' ').str[-1]
            df['Z_Obj'] = pd.to_datetime(df['Zaman'], format='%H:%M:%S', errors='coerce').astype(str)
            
            # Veriyi DB'ye ekle (Mükerrer kaydı önlemek için basitçe ekliyoruz, 
            # ileride 'to_sql' ile daha gelişmiş hale getirilebilir)
            df[['Z_Obj', 'Zaman', 'Deger']].dropna().to_sql('sinyaller', conn, if_exists='append', index=False)
            
        conn.commit()
        conn.close()
        print(f"✅ Arşiv: Veriler {DB_ADI} dosyasına işlendi.")
    except Exception as e:
        print(f"⚠️ DB Hatası: {e}")

def github_gonder():
    git_exe = git_yolu_bul()
    if not git_exe:
        print("❌ HATA: Git bulunamadı!")
        return

    try:
        # Önce veriyi yerel arşive işle
        db_arsivle()

        # Git işlemleri
        subprocess.run([git_exe, "add", "."], check=True)
        
        status = subprocess.run([git_exe, "diff", "--cached", "--quiet"])
        if status.returncode == 0:
            print(f"[{time.strftime('%H:%M:%S')}] Değişiklik yok, bekleniyor...")
            return

        print(f"[{time.strftime('%H:%M:%S')}] Yeni veri algılandı, gönderiliyor...")
        subprocess.run([git_exe, "commit", "-m", "Oto-Veri-Guncelleme"], capture_output=True)
        subprocess.run([git_exe, "pull", "origin", "main", "--rebase"], capture_output=True)
        subprocess.run([git_exe, "push", "origin", "main"], check=True)
        
        print("✅ Başarılı: GitHub ve Streamlit güncellendi!")

    except Exception as e:
        print(f"🚨 Hata: {e}")

print("🚀 Sismik Pusher + Arşivleyici v4.0")
print("-" * 40)

while True:
    github_gonder()
    time.sleep(BEKLEME_SURESI)