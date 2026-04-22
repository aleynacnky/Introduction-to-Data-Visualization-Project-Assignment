# 🚀 AI Destekli Metin ve Kod Analiz Asistanı

Bu proje, kullanıcıların seçtikleri metin veya kod parçaları üzerinde **tek tuş (F8)** ile hızlı ve akıllı işlemler yapabilmesini sağlayan bir masaüstü uygulamasıdır.  

Proje, temel olarak hocanın sağladığı veri görselleştirme projesi altyapısı üzerine geliştirilmiş olup, özellikle **yazılımcılar için genişletilmiş kod analiz ve düzeltme özellikleri** içermektedir.

---

## 🎯 Projenin Amacı

Bu uygulama ile kullanıcı:

- Metinleri analiz edebilir, çevirebilir ve düzenleyebilir
- Kod parçalarının **hangi dilde olduğunu tespit edebilir**
- Kodlarda **hata olup olmadığını kontrol edebilir**
- Hatalı kodları **otomatik olarak düzeltebilir**

Tüm bu işlemler, sadece metni seçip **F8 tuşuna basarak** gerçekleştirilebilir.

---

## ⚙️ Özellikler

### 📝 Metin İşleme Özellikleri (Orijinal Proje)
- Gramer düzeltme
- İngilizce ↔ Türkçe çeviri
- Metin özetleme
- Metni daha resmi hale getirme
- Mail cevap önerisi oluşturma
- Python kodu üretme
- Oyun yorumlama sistemi

---

### 💻 Kod Analiz Özellikleri (Eklenen)

#### 🔎 Hangi Dil
Seçilen kodun hangi programlama diline ait olduğunu tespit eder.

Desteklenen diller:
- Python
- C
- C++
- C#
- Java
- JavaScript
- HTML
- CSS

---

#### 🧪 Kodu Test Et
Kodun yapısını analiz eder ve:

- Hata varsa:
  - Hata türünü belirtir (örnek: **Syntax Hatası**, **Metot Adı Hatası**)
  - Hatalı satırı gösterir
- Hata yoksa:
  - Kodun doğru olduğunu bildirir

---

#### 🛠️ Hata Düzelt
Kod içindeki hataları otomatik olarak düzeltir ve:

- Kullanıcıya **tam ve çalışır kodu**
- Açıklama olmadan, direkt sonuç olarak verir

---

## 🧠 Kullanım Mantığı

1. Herhangi bir metni veya kodu seç
2. **F8 tuşuna bas**
3. Açılan menüden istediğin işlemi seç
4. Sonucu:
   - Ya doğrudan metin içine yazdır
   - Ya da ayrı pencerede görüntüle

---

## ⚙️ Gereksinimler & Kurulum

### 🧩 Gereksinimler

Bu projenin çalışabilmesi için aşağıdaki yazılımların yüklü olması gerekmektedir:

- Python 3.8+
- Ollama (yerel AI modeli için)
- İnternet bağlantısı (model erişimi için)

---

### 📦 Gerekli Python Kütüphaneleri

```bash
pip install -r requirements.txt

## 📊 Proje Akış Diyagramı

```mermaid
flowchart TD

A[Kullanıcı metin veya kod seçer] --> B[F8 tuşuna basar]
B --> C[Seçili içerik panoya kopyalanır]
C --> D[Uygulama menüsü açılır]

D --> E{İşlem türü seçilir}

E --> F[Metin İşleme Özellikleri]
E --> G[Kod Analiz Özellikleri]

F --> F1[Gramer Düzelt]
F --> F2[İngilizceye Çevir]
F --> F3[Türkçeye Çevir]
F --> F4[Özetle]
F --> F5[Daha Resmi Yap]
F --> F6[Python Koduna Çevir]
F --> F7[Mail Cevabı Yaz]
F --> F8[PS5 Oyun Skor ve Yorum]

F1 --> H[AI modeli ile işlem yapılır]
F2 --> H
F3 --> H
F4 --> H
F5 --> H
F6 --> H
F7 --> H
F8 --> H

G --> G1[Hangi Dil]
G --> G2[Kodu Test Et]
G --> G3[Hata Düzelt]

G1 --> I[Kod dili tespit edilir]
G2 --> J[Kural tabanlı hata kontrolü yapılır]
G3 --> K[Kural tabanlı düzeltme uygulanır]

I --> L[Sonuç pencerede gösterilir]
J --> M{Hata var mı?}
M -->|Evet| N[Hata türü ve hatalı satır gösterilir]
M -->|Hayır| O[Hata olmadığı bilgisi gösterilir]

K --> P[Düzeltilmiş kodun tam hali oluşturulur]
P --> L
N --> L
O --> L
H --> Q[Sonuç metne yazılır veya pencerede gösterilir]