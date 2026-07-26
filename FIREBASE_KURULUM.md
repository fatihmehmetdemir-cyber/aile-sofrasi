# Aile Sofrası v0.3.0 — Ortak Aile Hesabı

Bu sürüm, mevcut v0.2.3 özelliklerini korur ve Firebase Authentication + Cloud Firestore üzerinden **iki telefonda ortak aile hesabı** ekler.

## Çalışan yeni özellikler

- E-posta/şifre ile hesap oluşturma ve giriş
- Yeni aile oluşturma
- 6 haneli davet kodu
- Davet linkini Android paylaşım menüsüyle eşe gönderme
- Davet koduyla aileye katılma
- Ortak senkron:
  - aile bireyleri
  - 30 günlük menü değişiklikleri
  - günlük kiler işaretleri
  - haftalık kiler işaretleri
  - ekonomik hafta / geri alma durumu
  - aylık bütçe hedefi alanı
- Yerel depolama korunur; internet yokken mevcut cihaz verisi kullanılmaya devam eder
- Son aile hareketleri
- Aile yöneticisi / üye rolü

## Firebase kurulumu

1. Firebase Console'da yeni proje oluştur.
2. Web App ekle.
3. Authentication > Sign-in method bölümünde Email/Password aç.
4. Firestore Database oluştur.
5. Firestore > Rules bölümüne bu paketteki `firestore.rules` içeriğini yapıştırıp Publish et.
6. Project settings > Your apps > Web app altındaki `firebaseConfig` değerlerini `firebase-config.js` dosyasına koy.
7. Bu paketteki dosyaları GitHub `aile-sofrasi` reposunun köküne yükle.

## Önemli

`firebase-config.js` içindeki Firebase Web API anahtarı bir kullanıcı parolası değildir. Firebase'in resmi dokümantasyonuna göre Firebase servis anahtarları istemci uygulamalarında public-by-design'dır. Veri erişimini **Firestore Security Rules** kontrol eder.

Bu sürüm ilk gerçek ortak-hesap alfa sürümüdür. Canlıya çıkmadan önce:
- App Check
- e-posta doğrulama
- şifre sıfırlama
- hesap silme
- daha ayrıntılı rol/yetki
- activity log temizleme politikası
eklenmelidir.
