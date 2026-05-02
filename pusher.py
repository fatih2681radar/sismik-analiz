import os
import time
import subprocess
import shutil

# --- AYARLAR ---
BEKLEME_SURESI = 30  # 30 saniyede bir kontrol eder ve gönderir

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

def github_gonder():
    git_exe = git_yolu_bul()
    
    if not git_exe:
        print("❌ HATA: Git bulunamadı!")
        return

    try:
        # 1. Değişiklikleri tara
        subprocess.run([git_exe, "add", "."], check=True)
        
        # 2. Değişiklik var mı kontrol et (Boş commit atmamak için)
        status = subprocess.run([git_exe, "diff", "--cached", "--quiet"])
        if status.returncode == 0:
            print(f"[{time.strftime('%H:%M:%S')}] Değişiklik yok, bekleniyor...")
            return

        print(f"[{time.strftime('%H:%M:%S')}] Değişiklik algılandı, gönderiliyor...")

        # 3. Paketle
        subprocess.run([git_exe, "commit", "-m", "Oto-Veri-Guncelleme"], capture_output=True)
        
        # 4. Önce Uzaktaki Değişiklikleri Al (Çakışma Önleyici)
        subprocess.run([git_exe, "pull", "origin", "main", "--rebase"], capture_output=True)
        
        # 5. Gönder
        subprocess.run([git_exe, "push", "origin", "main"], check=True)
        
        print("✅ Başarılı: Veriler seismicradar.streamlit.app adresine uçtu!")

    except subprocess.CalledProcessError as e:
        print(f"⚠️ Bir sorun oluştu (İnternet veya Yetki hatası olabilir): {e}")
    except Exception as e:
        print(f"🚨 Beklenmedik hata: {e}")

print("🚀 Sismik Otomatik Yükleyici v3.0 - SAĞLAM MOD")
print(f"Gecikme: {BEKLEME_SURESI} saniye.")
print("-" * 40)

while True:
    github_gonder()
    time.sleep(BEKLEME_SURESI)