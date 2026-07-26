# Aile Sofrası v0.3.6 — Türk Mutfağı & Akıllı Tüketim

## Tarif ölçüleri
Tarif ekranlarında ana ölçü olarak Türk mutfağındaki ev ölçüleri kullanılır:
- adet
- paket
- su bardağı
- çay bardağı
- yemek kaşığı
- çay kaşığı
- demet
- dilim
- kase
- kepçe
- diş
- tutam

Yaklaşık gram karşılığı parantez içinde gösterilir.

## AI tarifleri
Gemini'den üç adet Türk ev mutfağına uygun öneri istenir.
AI, kilerdeki her ürünün kimliğini ve stok birimini görür.
Tarifte hem ev ölçüsü hem yaklaşık gram, ayrıca kilerden düşülecek stok miktarı ayrı alanlarda tutulur.

Paket net miktarı bilinmiyorsa kısmi paket otomatik düşülmez; kullanıcıya kontrol notu bırakılır.

## Öğün yapıldı
Planlı öğünde “Bu öğün yapıldı”, AI tarifinde “Bu yemeği yaptık” butonu vardır.
Onaylandığında:
- eşleşen kiler ürünleri son kullanma tarihi en yakın partiden başlayarak düşülür,
- tüketim kaydı aile hesabına senkronize edilir,
- aynı öğünün iki kez düşülmesi engellenir,
- yanlış işlem “geri al” ile eski stok miktarına döner.

## Geri bildirim
Yemek yapıldıktan sonra tarayıcı izin veriyorsa PWA bildirimi gönderilir.
Bildirim:
- 1–5 yıldız,
- porsiyon az/tam/fazla,
- tekrar yapalım mı,
- serbest not
geri bildirimi ister.

Bildirim izni verilmemişse geri bildirim penceresi uygulama içinde açılır.
Kaydedilen son geri bildirimler sonraki AI yemek önerilerinde kişiselleştirme sinyali olarak kullanılır.

## Not
PWA bildirimleri cihaz/tarayıcı iznine bağlıdır. Kiler düşümleri yaklaşık eşleştirme içerdiğinden
özellikle “paket” biriminde net içerik bilinmiyorsa otomatik düşüm bilinçli olarak yapılmaz.
