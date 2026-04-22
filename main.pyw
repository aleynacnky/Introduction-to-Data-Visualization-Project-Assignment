import pyperclip
from pynput import keyboard
import pyautogui
import tkinter as tk
from tkinter import messagebox
import time
import threading
import requests
import queue
import sys
import os
import ast
from pygments.lexers import guess_lexer
from pygments.util import ClassNotFound

os.system("chcp 65001 > nul")
sys.stdout.reconfigure(encoding="utf-8")

# --- AYARLAR ---
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_ADI = "gemma3:4b"
TEXT_MODEL_CANDIDATES = [
    MODEL_ADI,
]

KISAYOL_METIN = keyboard.Key.f8  # Metin secimi icin kisayol


# Global değişkenler
root = None
gui_queue = queue.Queue()
kisayol_basildi = False


# --- MENÜ SEÇENEKLERİ VE PROMPT'LAR ---
ISLEMLER = {
    "📝 Gramer Düzelt": "Bu metni Türkçe yazım ve dil bilgisi kurallarına göre düzelt, resmi ve akıcı olsun. Sadece sonucu ver.",
    "🇬🇧 İngilizceye Çevir": "Bu metni İngilizceye çevir. Sadece çeviriyi ver.",
    "🇹🇷 Türkçeye Çevir": "Bu metni Türkçeye çevir. Sadece çeviriyi ver.",
    "📑 Özetle (Madde Madde)": "Bu metni analiz et ve en önemli noktaları madde madde özetle.",
    "💼 Daha Resmi Yap": "Bu metni kurumsal bir e-posta diline çevir, çok resmi olsun.",
    "🐍 Python Koduna Çevir": "Bu metindeki isteği yerine getiren bir Python kodu yaz. Sadece kodu ver.",
    "📧 Cevap Yaz (Mail)": "Bu gelen bir e-posta, buna kibar ve profesyonel bir cevap metni taslağı yaz.",
    "🎮 PS5 Oyun Skor + Acımasız Yorum": (
        "Seçili metni bir PS5 oyunu adı olarak ele al. Aşağıdaki formatta Türkçe cevap ver:\n"
        "1) Oyun: <ad>\n"
        "2) Topluluk Beğeni Skorları:\n"
        "- Metacritic User Score: <değer veya 'bilgi yok'>\n"
        "- OpenCritic / benzer eleştirmen ortalaması: <değer veya 'bilgi yok'>\n"
        "- Oyuncu yorumu ortalaması (PS Store vb.): <değer veya 'bilgi yok'>\n"
        "3) Hüküm: sadece 'IYI' veya 'KOTU'\n"
        "4) Acımasız Yorum: 2-4 cümle, net ve sert.\n"
        "Kurallar: Kesin bilmediğin puanı uydurma, onun yerine 'bilgi yok' yaz. "
        "Yorumu skorlarla tutarlı kur."
    ),
}

KOD_ISLEMLERI = {
    "🧪 Kodu Test Et": "kodu_test_et",
    "🛠️ Hata Düzelt": "hata_duzelt",
    "🔎 Hangi Dil": "hangi_dil",
}

def get_available_text_model():
    """Metin işlemede kullanılabilir modeli seçer."""
    preferred_models = []
    for model in TEXT_MODEL_CANDIDATES:
        if model and model not in preferred_models:
            preferred_models.append(model)

    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code != 200:
            return MODEL_ADI

        models = response.json().get("models", [])
        installed_lower = {m.get("name", "").lower(): m.get("name", "") for m in models}

        for candidate in preferred_models:
            candidate_lower = candidate.lower()
            if candidate_lower in installed_lower:
                return installed_lower[candidate_lower]

            candidate_base = candidate_lower.split(":")[0]
            for installed_name_lower, installed_name in installed_lower.items():
                if installed_name_lower.startswith(candidate_base + ":"):
                    return installed_name
    except Exception:
        pass

    return MODEL_ADI


def ollama_cevap_al(prompt):
    """Ollama API'den cevap al."""
    try:
        aktif_model = get_available_text_model()
        payload = {
            "model": aktif_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
            },
        }

        response = requests.post(OLLAMA_URL, json=payload, timeout=60)

        if response.status_code == 200:
            result = response.json()
            return result.get("response", "").strip()

        err_msg = (
            f"Ollama API Hatası: {response.status_code}\n"
            f"Model: {aktif_model}\n"
            f"Cevap: {response.text}"
        )
        print(f"❌ {err_msg}")
        gui_queue.put((messagebox.showerror, ("API Hatası", err_msg)))
        return None

    except requests.exceptions.ConnectionError:
        err_msg = (
            "Ollama'ya bağlanılamadı.\n"
            "Programın çalıştığından emin olun!\n"
            "(http://localhost:11434)"
        )
        print(f"❌ {err_msg}")
        gui_queue.put((messagebox.showerror, ("Bağlantı Hatası", err_msg)))
        return None
    except Exception as e:
        err_msg = f"Beklenmeyen Hata: {e}"
        print(f"❌ {err_msg}")
        gui_queue.put((messagebox.showerror, ("Hata", err_msg)))
        return None


def strip_code_fence(text):
    if not text:
        return text
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        lines = lines[1:] if lines else []
        while lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


def secili_metni_kopyala(max_deneme=4):
    sentinel = f"__AI_ASISTAN__{time.time_ns()}__"
    try:
        pyperclip.copy(sentinel)
    except Exception:
        pass

    for _ in range(max_deneme):
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.2)
        metin = pyperclip.paste()
        if metin and metin.strip() and metin != sentinel:
            return metin
    return ""


def pencere_modunda_gosterilsin_mi(komut_adi):
    return (
        "PS5 Oyun Skor" in komut_adi
        or komut_adi in ["🧪 Kodu Test Et", "🛠️ Hata Düzelt", "🔎 Hangi Dil"]
    )


def sonuc_penceresi_goster(baslik, icerik):
    pencere = tk.Toplevel(root)
    pencere.title(baslik)
    pencere.geometry("780x520")
    pencere.minsize(520, 320)
    pencere.attributes("-topmost", True)

    frame = tk.Frame(pencere, bg="#1f1f1f")
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    text_alani = tk.Text(
        frame,
        wrap="word",
        bg="#2b2b2b",
        fg="white",
        insertbackground="white",
        font=("Segoe UI", 10),
        padx=10,
        pady=10,
    )
    kaydirma = tk.Scrollbar(frame, command=text_alani.yview)
    text_alani.configure(yscrollcommand=kaydirma.set)

    text_alani.pack(side="left", fill="both", expand=True)
    kaydirma.pack(side="right", fill="y")

    text_alani.insert("1.0", icerik)
    text_alani.config(state="disabled")

    alt_frame = tk.Frame(pencere, bg="#1f1f1f")
    alt_frame.pack(fill="x", padx=10, pady=(0, 10))

    def panoya_kopyala():
        pyperclip.copy(icerik)

    tk.Button(
        alt_frame,
        text="Panoya Kopyala",
        command=panoya_kopyala,
        bg="#3d3d3d",
        fg="white",
        activebackground="#4d4d4d",
        activeforeground="white",
        relief="flat",
        padx=12,
        pady=6,
    ).pack(side="left")

    tk.Button(
        alt_frame,
        text="Kapat",
        command=pencere.destroy,
        bg="#3d3d3d",
        fg="white",
        activebackground="#4d4d4d",
        activeforeground="white",
        relief="flat",
        padx=12,
        pady=6,
    ).pack(side="right")

    pencere.focus_force()
    pencere.lift()


def islemi_yap(komut_adi, secili_metin):
    prompt_emri = ISLEMLER[komut_adi]
    full_prompt = f"{prompt_emri}:\n\n'{secili_metin}'"

    print(f"🤖 İşlem: {komut_adi}")
    print("⏳ Ollama ile işleniyor...")

    sonuc = ollama_cevap_al(full_prompt)
    if not sonuc:
        print("❌ Sonuç alınamadı.")
        return

    sonuc = strip_code_fence(sonuc)
    if sonuc.startswith("'") and sonuc.endswith("'"):
        sonuc = sonuc[1:-1]

    if pencere_modunda_gosterilsin_mi(komut_adi):
        gui_queue.put((sonuc_penceresi_goster, (komut_adi, sonuc)))
        print("âœ… SonuÃ§ ayrÄ± pencerede gÃ¶sterildi.")
        return

    time.sleep(0.2)
    pyperclip.copy(sonuc)
    time.sleep(0.1)
    pyautogui.hotkey("ctrl", "v")
    print("✅ İşlem tamamlandı!")


def process_queue():
    """Kuyruktaki GUI işlemlerini ana thread'de çalıştırır."""
    try:
        while True:
            try:
                task = gui_queue.get_nowait()
            except queue.Empty:
                break
            func, args = task
            func(*args)
    finally:
        if root:
            root.after(100, process_queue)


def menu_goster():
    """Metni kopyalar ve menüyü gösterir (ana thread)."""
    secili_metin = secili_metni_kopyala()
    if not secili_metin.strip():
        gui_queue.put(
            (
                messagebox.showwarning,
                (
                    "Secim Bulunamadi",
                    "Lutfen once metin secin, sonra F8 ile menuyu acin.",
                ),
            )
        )
        return

    menu = tk.Menu(
        root,
        tearoff=0,
        bg="#2b2b2b",
        fg="white",
        activebackground="#4a4a4a",
        activeforeground="white",
        font=("Segoe UI", 10),
    )

    def komut_olustur(k_adi, s_metin):
        def komut_calistir():
            threading.Thread(
                target=islemi_yap,
                args=(k_adi, s_metin),
                daemon=True
            ).start()
        return komut_calistir

    def kod_komutu_olustur(k_adi, s_metin):
        def komut_calistir():
            threading.Thread(
                target=kod_islemi_yap,
                args=(k_adi, s_metin),
                daemon=True
            ).start()
        return komut_calistir

    for baslik in ISLEMLER.keys():
        menu.add_command(label=baslik, command=komut_olustur(baslik, secili_metin))

    menu.add_separator()

    for baslik in KOD_ISLEMLERI.keys():
        menu.add_command(label=baslik, command=kod_komutu_olustur(baslik, secili_metin))

    menu.add_separator()
    menu.add_command(label="❌ İptal", command=lambda: None)

    try:
        x, y = pyautogui.position()
        menu.tk_popup(x, y)
    finally:
        menu.grab_release()


def kod_dilini_tespit_et(kod):
    kod_strip = kod.strip()
    kod_lower = kod_strip.lower()

    # HTML
    if any(x in kod_lower for x in [
        "<!doctype html", "<html", "<head", "<body", "<div", "<span",
        "<p>", "<h1", "<script", "<title"
    ]):
        return "HTML"

    # CSS
    if (
        "{" in kod_strip and "}" in kod_strip
        and any(x in kod_lower for x in [
            "color:", "background:", "font-size:", "margin:", "padding:",
            "display:", "border:", "justify-content:", "align-items:"
        ])
    ):
        return "CSS"

    # JavaScript
    if any(x in kod_lower for x in [
        "console.log(", "function ", "let ", "const ", "var ",
        "document.getelementbyid", "document.queryselector",
        "addeventlistener", "window.", "=>"
    ]):
        return "JavaScript"

    # Python
    if any(x in kod_lower for x in [
        "def ", "print(", "import ", "from ", "elif ", "except ",
        "lambda ", "if __name__ == '__main__':", 'if __name__ == "__main__":'
    ]):
        return "Python"

    # C++
    if any(x in kod_lower for x in [
        "#include <iostream>", "std::cout", "std::cin",
        "using namespace std", "cout <<", "cin >>"
    ]):
        return "C++"

    # C
    if any(x in kod_lower for x in [
        "#include <stdio.h>", "printf(", "scanf(", "int main(void)"
    ]):
        return "C"

    # Java
    if (
        ("public class " in kod_lower and "public static void main" in kod_lower)
        or "system.out.println(" in kod_lower
        or "import java." in kod_lower
        or "scanner " in kod_lower
    ):
        return "Java"

    # C#
    if any(x in kod_lower for x in [
        "using system",
        "console.writeline(",
        "namespace ",
        "class ",
        "static void main(",
        "string[] args",
        "get; set;",
        "public ",
        "private ",
        "new ",
        "list<",
        "var "
    ]):
        return "C#"

    # Ortak main kontrolü
    if "int main(" in kod_lower:
        if "#include <iostream>" in kod_lower or "cout" in kod_lower or "std::" in kod_lower:
            return "C++"
        if "#include <stdio.h>" in kod_lower or "printf(" in kod_lower or "scanf(" in kod_lower:
            return "C"

    # Son çare: pygments
    try:
        lexer = guess_lexer(kod_strip)
        if lexer and hasattr(lexer, "name"):
            ad = lexer.name.lower()

            if "python" in ad:
                return "Python"
            if "javascript" in ad:
                return "JavaScript"
            if "html" in ad:
                return "HTML"
            if "css" in ad:
                return "CSS"
            if "c++" in ad or "cpp" in ad:
                return "C++"
            if ad == "c":
                return "C"
            if "java" in ad and "javascript" not in ad:
                return "Java"
            if "c#" in ad or "csharp" in ad:
                return "C#"

            return lexer.name
    except ClassNotFound:
        pass
    except Exception:
        pass

    return "Bilinmiyor"


def python_syntax_kontrolu(kod):
    try:
        ast.parse(kod)
        return True, "Python kodunda sözdizimi hatası bulunamadı."
    except SyntaxError as e:
        hatali_satir = ""
        satirlar = kod.splitlines()
        if e.lineno and 1 <= e.lineno <= len(satirlar):
            hatali_satir = satirlar[e.lineno - 1]

        mesaj = (
            f"Python sözdizimi hatası bulundu.\n\n"
            f"Satır: {e.lineno}\n"
            f"Sütun: {e.offset}\n"
            f"Hata: {e.msg}\n\n"
            f"Hatalı satır:\n{hatali_satir}"
        )
        return False, mesaj
    except Exception as e:
        return False, f"Python kodu analiz edilirken beklenmeyen hata oluştu:\n{e}"


def ai_ile_kod_test_et(kod, dil):
    dil_tag = dil.lower() if isinstance(dil, str) else ""

    prompt = f"""
Aşağıdaki kodu bir derleyici / yorumlayıcı titizliğiyle analiz et.

Kurallar:
- Kod dili: {dil}
- Sözdizimi hataları, yanlış fonksiyon/metot adları, eksik parantez, eksik noktalı virgül, yanlış anahtar kelime, yanlış sınıf/metot kullanımı gibi hataları kontrol et.
- Özellikle derlenmeyecek / çalışmayacak yerleri bul.
- Eğer herhangi bir hata veya güçlü şüpheli bug varsa mutlaka "HATA VAR" yaz.
- Eğer hata yoksa sadece şu formatta cevap ver:

HATA YOK
Açıklama: Kodda belirgin bir hata görünmüyor.

- Eğer hata varsa şu formatta cevap ver:

HATA VAR
Hatalı Blok:
```{dil_tag}
[yalnızca hatalı kod bloğu]

Açıklama:
[kısa ve net açıklama]

Kod:

{kod}

"""
    return ollama_cevap_al(prompt)

def ai_ile_hata_duzelt(kod, dil):
    dil_tag = dil.lower() if isinstance(dil, str) else ""

    prompt = f"""
Aşağıdaki kodda hata olabilir. Kodu dikkatlice analiz et ve hataları düzelt.

Kurallar:
- Kod dili: {dil}
- Çıktıda SADECE düzeltilmiş kodun tam halini ver.
- Açıklama yazma.
- Hatalı kısmı aynen tekrar etme; gerçekten düzelt.
- Özellikle yanlış metot adlarını, eksik karakterleri, eksik noktalı virgülleri, sözdizimi hatalarını ve yanlış anahtar kelimeleri düzelt.
- Kod çalışabilir / derlenebilir halde olsun.

Kod:
```{dil_tag}
{kod}

"""
    return ollama_cevap_al(prompt)

def kod_islemi_yap(komut_adi, secili_metin):
    dil = kod_dilini_tespit_et(secili_metin)

    if komut_adi == "🔎 Hangi Dil":
        sonuc = f"Tespit edilen dil: {dil}"
        gui_queue.put((sonuc_penceresi_goster, (komut_adi, sonuc)))
        return

    if komut_adi == "🧪 Kodu Test Et":
        basarili, mesaj = kodu_kural_tabanli_test_et(secili_metin, dil)
        gui_queue.put((sonuc_penceresi_goster, (komut_adi, mesaj)))
        return

    if komut_adi == "🛠️ Hata Düzelt":
        duzeltilmis_kod = kodu_kural_tabanli_duzelt(secili_metin, dil)
        gui_queue.put((sonuc_penceresi_goster, (komut_adi, duzeltilmis_kod)))
        return
    
def hata_mesaji_olustur(dil, hata_turu, aciklama, satir_no=None, hatali_satir=None):
    mesaj = f"{dil} HATASI\n\n"
    mesaj += f"Hata Türü: {hata_turu}\n"

    if satir_no is not None:
        mesaj += f"Satır: {satir_no}\n"

    mesaj += f"Açıklama: {aciklama}\n"

    if hatali_satir:
        mesaj += f"\nHatalı Satır:\n{hatali_satir}"

    return mesaj

def hata_mesaji_olustur(dil, hata_turu, aciklama, satir_no=None, hatali_satir=None):
    mesaj = f"{dil} HATASI\n\n"
    mesaj += f"Hata Türü: {hata_turu}\n"

    if satir_no is not None:
        mesaj += f"Satır: {satir_no}\n"

    mesaj += f"Açıklama: {aciklama}\n"

    if hatali_satir:
        mesaj += f"\nHatalı Satır:\n{hatali_satir}"

    return mesaj


def python_kontrol(kod):
    try:
        ast.parse(kod)
        return True, "Python kodunda belirgin hata bulunamadı."
    except SyntaxError as e:
        satirlar = kod.splitlines()
        hatali_satir = ""
        if e.lineno and 1 <= e.lineno <= len(satirlar):
            hatali_satir = satirlar[e.lineno - 1]

        return False, hata_mesaji_olustur(
            "Python",
            "Syntax Hatası",
            e.msg,
            e.lineno,
            hatali_satir
        )


def c_kontrol(kod):
    satirlar = kod.splitlines()
    kod_lower = kod.lower()

    if "#include <stdio.h>" not in kod_lower:
        return False, hata_mesaji_olustur("C", "Eksik Kütüphane Hatası", "#include <stdio.h> bulunamadı.")

    if "int main(" not in kod_lower:
        return False, hata_mesaji_olustur("C", "Eksik Ana Fonksiyon Hatası", "int main(...) bulunamadı.")

    for i, satir in enumerate(satirlar, start=1):
        s = satir.strip()
        if ("printf(" in s or "scanf(" in s) and not s.endswith(";"):
            return False, hata_mesaji_olustur("C", "Noktalı Virgül Hatası", "Satır ';' ile bitmeli.", i, s)

    return True, "C kodunda belirgin hata bulunamadı."


def cpp_kontrol(kod):
    satirlar = kod.splitlines()
    kod_lower = kod.lower()

    if "#include <iostream>" not in kod_lower:
        return False, hata_mesaji_olustur("C++", "Eksik Kütüphane Hatası", "#include <iostream> bulunamadı.")

    if "int main(" not in kod_lower:
        return False, hata_mesaji_olustur("C++", "Eksik Ana Fonksiyon Hatası", "int main(...) bulunamadı.")

    if "cout <<" not in kod and "std::cout" not in kod:
        return False, hata_mesaji_olustur("C++", "Çıkış Komutu Hatası", "cout << veya std::cout bulunamadı.")

    for i, satir in enumerate(satirlar, start=1):
        s = satir.strip()
        if "cout <<" in s and not s.endswith(";"):
            return False, hata_mesaji_olustur("C++", "Noktalı Virgül Hatası", "Satır ';' ile bitmeli.", i, s)

    return True, "C++ kodunda belirgin hata bulunamadı."


def csharp_kontrol(kod):
    satirlar = kod.splitlines()
    kod_lower = kod.lower()

    if "class " not in kod_lower:
        return False, hata_mesaji_olustur("C#", "Sınıf Tanımı Hatası", "class tanımı bulunamadı.")

    if "static void main(" not in kod_lower:
        return False, hata_mesaji_olustur("C#", "Ana Metot Hatası", "static void Main(...) bulunamadı.")

    for i, satir in enumerate(satirlar, start=1):
        s = satir.strip()

        if "Console.WriteLi(" in s:
            return False, hata_mesaji_olustur("C#", "Metot Adı Hatası", "Console.WriteLi geçersiz. Doğrusu Console.WriteLine olmalı.", i, s)

        if "Console.Writeline(" in s:
            return False, hata_mesaji_olustur("C#", "Büyük/Küçük Harf Hatası", "Console.Writeline yerine Console.WriteLine kullanılmalı.", i, s)

        if "System.out.println(" in s:
            return False, hata_mesaji_olustur("C#", "Yanlış Dil Komutu Hatası", "Bu ifade Java'ya aittir. C# için Console.WriteLine kullanılmalı.", i, s)

        if "Console.WriteLine(" in s and not s.endswith(";"):
            return False, hata_mesaji_olustur("C#", "Noktalı Virgül Hatası", "Satır ';' ile bitmeli.", i, s)

    return True, "C# kodunda belirgin hata bulunamadı."


def java_kontrol(kod):
    satirlar = kod.splitlines()
    kod_lower = kod.lower()

    if "public class " not in kod_lower:
        return False, hata_mesaji_olustur("Java", "Sınıf Tanımı Hatası", "public class tanımı bulunamadı.")

    if "public static void main" not in kod_lower:
        return False, hata_mesaji_olustur("Java", "Ana Metot Hatası", "public static void main(...) bulunamadı.")

    for i, satir in enumerate(satirlar, start=1):
        s = satir.strip()

        if "System.out.printLn(" in s:
            return False, hata_mesaji_olustur("Java", "Büyük/Küçük Harf Hatası", "printLn yerine println kullanılmalı.", i, s)

        if "Console.WriteLine(" in s:
            return False, hata_mesaji_olustur("Java", "Yanlış Dil Komutu Hatası", "Bu ifade C# diline aittir. Java için System.out.println kullanılmalı.", i, s)

        if "System.out.println(" in s and not s.endswith(";"):
            return False, hata_mesaji_olustur("Java", "Noktalı Virgül Hatası", "Satır ';' ile bitmeli.", i, s)

    return True, "Java kodunda belirgin hata bulunamadı."


def js_kontrol(kod):
    satirlar = kod.splitlines()
    kod_lower = kod.lower()

    if not any(x in kod_lower for x in ["function ", "console.log(", "let ", "const ", "var "]):
        return False, hata_mesaji_olustur("JavaScript", "Temel Yapı Hatası", "function, console.log, let, const veya var yapılarından hiçbiri bulunamadı.")

    for i, satir in enumerate(satirlar, start=1):
        s = satir.strip()

        if "console.WriteLine(" in s:
            return False, hata_mesaji_olustur("JavaScript", "Yanlış Dil Komutu Hatası", "Bu ifade C# diline aittir. JavaScript için console.log kullanılmalı.", i, s)

    return True, "JavaScript kodunda belirgin hata bulunamadı."


def html_kontrol(kod):
    kod_lower = kod.lower()

    if "<html" not in kod_lower:
        return False, hata_mesaji_olustur("HTML", "Eksik Etiket Hatası", "<html> etiketi bulunamadı.")

    if "<body" not in kod_lower:
        return False, hata_mesaji_olustur("HTML", "Eksik Etiket Hatası", "<body> etiketi bulunamadı.")

    if "</html>" not in kod_lower:
        return False, hata_mesaji_olustur("HTML", "Kapanış Etiketi Hatası", "</html> etiketi bulunamadı.")

    if "</body>" not in kod_lower:
        return False, hata_mesaji_olustur("HTML", "Kapanış Etiketi Hatası", "</body> etiketi bulunamadı.")

    return True, "HTML kodunda belirgin hata bulunamadı."


def css_kontrol(kod):
    kod_lower = kod.lower()

    if "{" not in kod or "}" not in kod:
        return False, hata_mesaji_olustur("CSS", "Blok Hatası", "CSS içinde { } blokları bulunamadı.")

    if ":" not in kod:
        return False, hata_mesaji_olustur("CSS", "Property Hatası", "CSS özellik tanımı bulunamadı.")

    if ";" not in kod:
        return False, hata_mesaji_olustur("CSS", "Noktalı Virgül Hatası", "CSS özellikleri ';' ile bitmeli.")

    return True, "CSS kodunda belirgin hata bulunamadı."

def kodu_kural_tabanli_test_et(kod, dil):
    dil_lower = dil.lower()

    if dil_lower == "python":
        return python_kontrol(kod)
    elif dil_lower == "c":
        return c_kontrol(kod)
    elif dil_lower == "c++":
        return cpp_kontrol(kod)
    elif dil_lower == "c#":
        return csharp_kontrol(kod)
    elif dil_lower == "java":
        return java_kontrol(kod)
    elif dil_lower == "javascript":
        return js_kontrol(kod)
    elif dil_lower == "html":
        return html_kontrol(kod)
    elif dil_lower == "css":
        return css_kontrol(kod)

    return False, f"{dil} için henüz özel kontrol tanımlanmadı."
    
def python_duzelt(kod):
    return kod


def c_duzelt(kod):
    return kod


def cpp_duzelt(kod):
    return kod


def csharp_duzelt(kod):
    yeni_satirlar = []
    for satir in kod.splitlines():
        yeni_satir = satir

        yeni_satir = yeni_satir.replace("Console.WriteLi(", "Console.WriteLine(")
        yeni_satir = yeni_satir.replace("Console.Writeline(", "Console.WriteLine(")
        yeni_satir = yeni_satir.replace("Console.writeLine(", "Console.WriteLine(")
        yeni_satir = yeni_satir.replace("System.out.println(", "Console.WriteLine(")

        yeni_satirlar.append(yeni_satir)

    return "\n".join(yeni_satirlar)


def java_duzelt(kod):
    yeni_satirlar = []
    for satir in kod.splitlines():
        yeni_satir = satir

        yeni_satir = yeni_satir.replace("System.out.printLn(", "System.out.println(")
        yeni_satir = yeni_satir.replace("Console.WriteLine(", "System.out.println(")

        yeni_satirlar.append(yeni_satir)

    return "\n".join(yeni_satirlar)


def js_duzelt(kod):
    yeni_satirlar = []
    for satir in kod.splitlines():
        yeni_satir = satir.replace("Console.WriteLine(", "console.log(")
        yeni_satirlar.append(yeni_satir)

    return "\n".join(yeni_satirlar)


def html_duzelt(kod):
    kod_lower = kod.lower()
    yeni_kod = kod.strip()

    if "<html" not in kod_lower:
        yeni_kod = "<html>\n" + yeni_kod
    if "<body" not in kod_lower:
        yeni_kod = yeni_kod.replace("<html>", "<html>\n<body>")
    if "</body>" not in yeni_kod.lower():
        yeni_kod += "\n</body>"
    if "</html>" not in yeni_kod.lower():
        yeni_kod += "\n</html>"

    return yeni_kod


def css_duzelt(kod):
    satirlar = kod.splitlines()
    yeni_satirlar = []

    for satir in satirlar:
        s = satir.rstrip()

        if ":" in s and "{" not in s and "}" not in s and not s.strip().endswith(";"):
            s += ";"

        yeni_satirlar.append(s)

    return "\n".join(yeni_satirlar)


def kodu_kural_tabanli_duzelt(kod, dil):
    dil_lower = dil.lower()

    if dil_lower == "python":
        return python_duzelt(kod)
    elif dil_lower == "c":
        return c_duzelt(kod)
    elif dil_lower == "c++":
        return cpp_duzelt(kod)
    elif dil_lower == "c#":
        return csharp_duzelt(kod)
    elif dil_lower == "java":
        return java_duzelt(kod)
    elif dil_lower == "javascript":
        return js_duzelt(kod)
    elif dil_lower == "html":
        return html_duzelt(kod)
    elif dil_lower == "css":
        return css_duzelt(kod)

    return kod
    
    
def on_press(key):
    global kisayol_basildi
    try:
        if key == KISAYOL_METIN and not kisayol_basildi:
            kisayol_basildi = True
            gui_queue.put((menu_goster, ()))
    except AttributeError:
        pass


def on_release(key):
    global kisayol_basildi
    try:
        if key == KISAYOL_METIN:
            kisayol_basildi = False
    except AttributeError:
        pass


if __name__ == "__main__":
    print("=" * 60)
    print("🤖 AI Asistan - Metin İşleme")
    print("=" * 60)
    aktif_text_model = get_available_text_model()
    print(f"📦 Metin İşleme (F8): {aktif_text_model}")
    print()
    print("🔧 Kullanım:")
    print("   F8 - Metin sec ve AI islemleri yap")
    print()
    print("⚠️ Programı kapatmak için bu pencereyi kapatın veya Ctrl+C yapın.")
    print("=" * 60)

    try:
        test_response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if test_response.status_code == 200:
            print("✅ Ollama bağlantısı başarılı!")
        else:
            print("⚠️ Ollama'ya bağlanılamadı, servisi kontrol edin!")
    except Exception:
        print("⚠️ Ollama çalışmıyor olabilir! 'ollama serve' ile başlatın.")

    print()

    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()

    root = tk.Tk()
    root.withdraw()
    root.after(100, process_queue)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("Kapatılıyor...")
