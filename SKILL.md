---
name: turkce-carousel
description: Bir konudan ya da metinden 5-10 slaytlık Türkçe Instagram/LinkedIn carousel'i üretir - 1080x1350 PNG serisi + LinkedIn için PDF + gönderi açıklaması (kanca satırı, madde listesi, kaydet/yorum çağrısı, anahtar kelime satırı, en fazla 4 hashtag). Doğru Türkçe büyük harf (İSTANBUL, ISTANBUL değil), Ş/Ç/Ğ/İ işaretleri satırlar arasında çakışmaz, taşma ve çakışma her slaytta ölçülür. Çalışan slayt kalıpları (sayılı kanca, slayt başına tek fikir, yanlış/doğru, özet, kaydet ya da yorum-anahtar kelime CTA'sı). 3 ücretsiz şablon (koyu-mercan, açık-editoryal, renkli-eğitim) ve OFL lisanslı fontlar dahil. İş birliği gönderilerinde her slayta "REKLAM · @marka" etiketi ve açıklamaya etiket satırı ekler. Kullanıcı "carousel yap", "kaydırmalı gönderi", "slayt gönderi", "LinkedIn PDF gönderisi", "bu yazıyı carousel'e çevir", "Instagram için 7 slayt" dediğinde ya da bir konu verip Instagram/LinkedIn görsel serisi istediğinde kullan. Tamamen yerel çalışır - yayın, hesap, ücretli API ve tarayıcı yok.
---

# Türkçe Carousel Üretici

Konu ya da metin girer → **slayt planı** (YAML) → `carousel.py render` → `01.png … NN.png` (1080x1350),
`<konu>.pdf` (LinkedIn belge gönderisi), `caption.txt`, `alt_metin.txt`, `onizleme.jpg`, `rapor.txt`.
Planı sen (Claude) yazarsın; çizimi, Türkçe dizgiyi ve kontrolleri script yapar.

## Kurallar (değişmez)

- **Yerel kal.** Hiçbir şeyi yayınlama, yükleme, hesaba girme; ücretli API çağırma. Paylaşmayı kullanıcı yapar.
- **Tarayıcı açma.** Chrome/Chromium hiç başlatma; çizim PIL ile yapılır, HTML yok.
- **Uydurma yok.** Sayı, istatistik, alıntı yalnız kullanıcının verdiği ya da doğrulanabilir kaynaktan.
  `sayi` slaytına `kaynak` yaz; kaynağı yoksa sayıyı çıkar. Ders/bilim içeriğinde bilinen gerçeklerle sınırlı kal.
- **Başkasının carousel'ini kopyalama.** Stil referansı olur, metin ve görsel birebir olmaz.
- **Büyük harfe kendin çevirme.** Planı normal yaz; şablon gerekiyorsa `tr_upper` ile çevirir.
  Python `upper()`, JS `toUpperCase()`, CSS `uppercase` (lang="tr" olmadan) "istanbul"u ISTANBUL yapar.
- **Yorum-anahtar kelime CTA'sı bir söz.** "Yoruma LİSTE yaz, göndereyim" yazdırıyorsan kullanıcı bunu elle
  (ya da kendi aracıyla) gerçekten gönderecek mi, sor. Bu skill DM göndermez, otomasyon vaat etme.

## Akış

`S=~/.claude/skills/turkce-carousel/scripts`, `PY` = Pillow + numpy kurulu Python (README'deki venv).

1. **Kontrol:** `$PY $S/carousel.py doctor` (eksik paket/font varsa tek satırla söyle).
2. **Netleştir (kısa):** konu, hedef kitle, platform (Instagram / LinkedIn / ikisi), şablon, hesap adı,
   CTA türü (kaydet / paylaş / yorum + anahtar kelime / takip), iş birliği mi (reklam veren kim?).
   Kullanıcı metin verdiyse içerik ondan gelir; sen yalnız böl ve kısalt.
3. **Planı yaz.** İskelet için: `$PY $S/carousel.py yeni "KONU" --sablon renkli-egitim --kalip adim --slayt 8 > plan.yaml`
   (`--kalip liste | adim | hata`, `--cta kaydet | paylas | yorum | takip`). Sonra aşağıdaki kalıplara göre doldur.
   Hazır örnekler: `examples/*/plan.yaml`.
4. **Denetle:** `$PY $S/carousel.py kontrol plan.yaml` → hataları düzelt, uyarıları değerlendir.
5. **Çiz:** `$PY $S/carousel.py render plan.yaml --cikti carousel_cikti/`
   Çıkış kodu 2 = TAŞMA / ÇAKIŞMA / KENAR: metni kısalt ya da ikiye böl, yeniden çiz.
6. **Gözle bak (zorunlu).** Önce `onizleme.jpg`, sonra **her** `NN.png`'yi Read ile aç. Bak: Türkçe harfler doğru mu
   (İ noktası, Ş/Ç çengeli), satırlar birbirine değiyor mu, yazı kenara/alt bilgiye yaslanıyor mu, tek kelimelik
   dul satır var mı, vurgu doğru kelimede mi, iki slayt aynı şeyi mi söylüyor. Gördüğünü kısaca yaz; sorun varsa
   planı düzelt, yeniden çiz, yeniden bak.
7. **Sun:** slayt sayısı + dosyalar + `caption.txt` içeriği + rapordaki uyarılar. LinkedIn için PDF'i,
   Instagram için PNG'leri sırayla yüklemesini söyle; `alt_metin.txt` erişilebilirlik metinleridir.

## Slayt kalıpları (çalışanlar)

- **1. slayt = kanca.** Somut sayı + fayda: "5 Instagram hatası", "Fotosentez 6 adımda", "5 dakikada plan".
  `sayi` alanı büyük yazılır; başlık ≤ 10 kelime; `alt` tek cümle (ne kazanacak). Kaydırma kararı burada verilir.
- **Slayt başına tek fikir.** Başlık = fikrin kendisi (≤ 10 kelime), metin = 1-2 cümle (≤ 35 kelime).
  Ayrıntı fazlaysa ikinci slayta böl; küçük yazıyla sığdırma.
- **Vurgu tek yerde:** başlıkta 1-3 kelimeyi `*yıldız*` içine al (vurgu rengine boyanır). Her şey vurguluysa hiçbiri değil.
- **Somut örnek** için `ipucu` paneli (madde slaytının altında): "Örnek: …", "Dikkat: …" (`ipucu_etiket`).
- **Yanlış → doğru** (`karsilastirma`): hata/efsane içeriklerinde en net kalıp.
- **Özet** (`liste`, sondan bir önceki slayt): 3-5 kısa madde; kaydetme sebebi olur.
- **Son slayt = CTA.** `kaydet` (bilgi/ders içeriği), `paylas` ("sınavı olan arkadaşına gönder"),
  `yorum` + `anahtar` (tek kelime, ör. LİSTE) + `vaat` (ne gönderilecek), `takip`.
- 5-10 slayt. 7-9 çoğu konu için yeter; 10'u geçme.

## Plan alanları

```yaml
konu: "Fotosentez 6 adımda"         # PDF adı ve kayıt için
sablon: renkli-egitim                # koyu-mercan | acik-editoryal | renkli-egitim
hesap: "@hesabin"                    # alt bilgi + CTA (isteğe bağlı)
seri: "Biyoloji notu"                # sol üst etiket (isteğe bağlı)
madde_etiketi: "Adım"                # editoryal şablonda "ADIM 01" (isteğe bağlı)
slaytlar:
  - {tip: kanca, ust: "küçük üst etiket", sayi: "6", baslik: "Fotosentez *6 adımda*", alt: "tek cümle"}
  - {tip: madde, baslik: "...", metin: "...", ipucu: "...", ipucu_etiket: "Örnek"}   # no otomatik
  - {tip: karsilastirma, baslik: "...", yanlis: "...", dogru: "...", yanlis_etiket: "Efsane", dogru_etiket: "Gerçek"}
  - {tip: sayi, sayi: "%40", baslik: "...", metin: "...", kaynak: "Kurum, yıl"}
  - {tip: liste, ust: "Özet", baslik: "...", maddeler: ["...", "..."], isaret: tik}   # tik | nokta | sayi
  - {tip: cta, tur: yorum, anahtar: "LİSTE", vaat: "kontrol listesini", baslik: "...", metin: "..."}
caption:
  kanca: ""                          # boşsa kanca slaytından; ilk ~125 karakter "devamı"ndan önce görünür
  maddeler: null                     # boşsa madde başlıklarından
  cta: ""                            # boşsa CTA slaytından
  anahtar_kelimeler: ["...", "..."]  # hashtag yerine düz arama satırı
  hashtagler: ["#...", "#..."]       # en fazla 4 (fazlası atılır)
reklam: null                         # iş birliği: {tur: Reklam, veren: "@marka", yapay_zeka: "Görseller yapay zekâ ile üretildi."}
```

Slayt `palet:` alanıyla şablonun başka bir rengini zorlayabilir (ör. `palet: koyu`). `\n` zorunlu satır sonu.

## Reklam / iş birliği

`reklam` doluysa: her slaytın sol üstüne yüksek kontrastlı **"REKLAM · @marka"** etiketi (çok parçalı içerikte her
parçada olmalı), açıklamanın **ilk satırına** "Reklam | @marka tarafından sağlandı." eklenir ve
`reklam_kontrol.yaml` yazılır. Ayrıntılı denetim için ücretsiz **Reklam Etiketi Kontrolü** skill'i:
github.com/redirhan/reklam-etiketi (`kontrol.py reklam_kontrol.yaml`). Bu bir hukuki görüş değildir.

## Alt komutlar

| Komut | İş |
|---|---|
| `doctor` | paketler, fontlar, Türkçe glif ve `tr_upper` testi |
| `sablonlar` | şablon listesi |
| `yeni KONU` | boş plan iskeleti (`--kalip`, `--cta`, `--slayt`, `--sablon`, `--hesap`) |
| `kontrol PLAN` | kurallar: slayt sayısı, kancada sayı, tek fikir, kaynak, CTA, hashtag, büyük harf |
| `render PLAN` | PNG + PDF + caption + alt metin + önizleme + rapor (`--sablon` ile şablon değiştir, `--pdf-yok`) |
| `caption PLAN` | yalnız açıklama metni |

## Şablonlar

- `koyu-mercan`: siyah / kırık beyaz sırayla, mercan vurgu, dar BÜYÜK HARF başlık (Archivo). Liste, ipucu, kişisel marka.
- `acik-editoryal`: krem kâğıt, ince çizgiler, ilerleme çubuğu, cümle düzeni başlık (Bricolage Grotesque + Manrope). Ajans, B2B, LinkedIn.
- `renkli-egitim`: her slayt ayrı canlı renk, numara rozetleri (Unbounded + Manrope). Ders notu, adım adım anlatım.

Pro şablon paketi (20 şablon: eğitim, ürün, ajans vaka, önce/sonra, alıntı, kendi marka renklerin): **yakında**.
