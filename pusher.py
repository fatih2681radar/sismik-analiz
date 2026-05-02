import os
import time
import subprocess
import shutil

# --- AYARLAR ---
BEKLEME_SURESI = 10  # 30 saniyede bir internete veri fırlatır

def git_yolu_bul():
    # Sistemde 'git' komutu kayıtlı mı?
    yol = shutil.which("git")
    if yol: return yol
    
    # Yaygın Windows yollarını kontrol et
    muhtemel_yollar = [
        r"C:\Program Files\Git\bin\git.exe",
        r"C:\Program Files\Git\cmd\git.exe",
        os.path.expanduser(r"~\AppData\Local\GitHubDesktop\app-3.3.13\resources\app\git\cmd\git.exe"),
        os.path.expanduser(r"~\AppData\Local\GitHubDesktop\bin\git.exe")
    ]
    
    for p in muhtemel_yollar:
        if os.path.exists(p): return p
    return None

def github_gonder():
    git_exe = git_yolu_bul()
    
    if not git_exe:
        print("❌ HATA: Git bulunamadı! Lütfen Git'in kurulu olduğundan emin olun.")
        return

    try:
        print(f"[{time.strftime('%H:%M:%S')}] Veriler internete (GitHub) fırlatılıyor...")
        
        # Değişiklikleri tara
        subprocess.run([git_exe, "add", "."], check=True)
        
        # Paketle
        subprocess.run([git_exe, "commit", "-m", "Oto-Guncelleme"], capture_output=True)
        
        # Gönder
        subprocess.run([git_exe, "push", "origin", "main"], check=True)
        
        print("✅ Başarılı: Veriler seismicradar.streamlit.app adresine uçtu!")
    except subprocess.CalledProcessError as e:
        if e.returncode == 1:
            print("ℹ️ Değişiklik yok, bekleniyor...")
        else:
            print(f"⚠️ Gönderim hatası (İnternet veya Yetki): {e}")

print("🚀 Sismik Otomatik Yükleyici (v2.0) Başlatıldı!")
print("Sistemi durdurmak için bu pencereyi kapatabilir veya Ctrl+C yapabilirsiniz.")

while True:
    github_gonder()
    time.sleep(BEKLEME_SURESI)