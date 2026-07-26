# v0.3.1 Dinamik Takvim

- Uygulama açıldığında cihazın yerel tarihini kullanır.
- Bugün otomatik seçilir.
- Gün başlığı gerçek tarih ve haftanın gününü gösterir.
- Ay 28, 29, 30 veya 31 günse plan otomatik o uzunluğa gelir.
- 31. gün gerektiğinde sağlıklı 30 günlük tarif şablonu döngüsel olarak devam eder.
- Haftalık alışveriş Pazartesi–Pazar takvim haftasına göre hesaplanır.
- Ayın başı/sonunda hafta aralığı mevcut ayın sınırlarında kırpılır.
- Yeni aya geçildiğinde günlük/haftalık kiler işaretleri sıfırlanır; eski ayın işaretleri yeni aya taşınmaz.
- Menü değişiklikleri mevcut ay içinde korunur.
- Firebase ortak aile durumu `calendarMonth` bilgisiyle senkronize edilir.
