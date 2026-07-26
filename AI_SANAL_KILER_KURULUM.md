# Aile Sofrası v0.3.4 — AI Sanal Kiler

## Neler eklendi?
- Yeni **Kiler** sekmesi.
- Kamerayla tek ürün, paket etiketi, buzdolabı rafı veya kiler rafı tarama.
- Paketsiz gıdaları da görüntüden tanıma: sebze, meyve, ekmek, yumurta vb.
- Paketliyse görünür olduğunda marka, barkod, parti/lot no ve SKT/TETT okuma denemesi.
- Birden fazla fotoğrafı tek taramada birleştirme (örneğin paketin ön + arka yüzü).
- AI sonucu kaydetmeden önce düzenlenebilir doğrulama ekranı.
- Kiler / Buzdolabı / Dondurucu konumu.
- Son kullanma tarihi uyarıları: 7 gün içinde, kritik, geçmiş, tarihsiz.
- Ortak aile hesabında sanal kiler Firebase ile eş zamanlanır.
- Alışveriş listesinde eşleşen ürün varsa **“Sanal kilerde”** bilgi rozeti görünür.
- Fotoğraflar bu sürümde Firestore veya Cloud Storage'a kaydedilmez; yalnızca tanıma isteğinde kullanılır.
- AI çalışmazsa destekleyen tarayıcılarda yerel BarcodeDetector barkod ipucu sağlayabilir; elle ekleme her zaman çalışır.

## AI taramayı açmak için Firebase tarafında iki adım gerekir

### 1. Firebase AI Logic
Firebase Console'da Firebase AI Logic bölümünü açın ve **Get started** akışını tamamlayın.
Gemini API sağlayıcısı olarak Gemini Developer API seçilebilir.
Kod `gemini-3.6-flash` modelini kullanır ve görüntüden yapılandırılmış JSON döndürür.

### 2. App Check — Web
Güncel Firebase AI Logic kurulumunda App Check koruması gereklidir.

- Google Cloud Console > reCAPTCHA Enterprise
- Website türünde bir anahtar oluşturun.
- Alan adı olarak GitHub Pages host'unuzu ekleyin:
  `fatihmehmetdemir-cyber.github.io`
- Firebase Console > Security > App Check
- **Aile Sofrası Web** uygulamasını reCAPTCHA Enterprise ile kaydedin.
- Verilen **site key** değerini `appcheck-config.js` içine yazın:

```js
export const appCheckSiteKey = "SITE_KEY_BURAYA";
```

Sonra `index.html`, `sw.js` ve `appcheck-config.js` dosyalarını GitHub deposuna yükleyin.

## Gıda güvenliği notu
AI'nin okuduğu lot ve tarih alanları kesin veri kabul edilmez. Kullanıcıya kaydetmeden önce düzenleme ekranı gösterilir.
Tarih belirsizse modelden tahmin etmemesi istenir. Son tüketim kararında fiziksel ambalaj üzerindeki bilgi esastır.
