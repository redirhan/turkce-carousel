# Değişiklik günlüğü

## 1.0 — 2026-10-27
İlk sürüm.
- Slayt planı (YAML/JSON) → 1080x1350 PNG serisi + LinkedIn PDF (img2pdf, kayıpsız; yoksa reportlab ya da Pillow).
- Slayt tipleri: kanca, madde, liste, sayi, karsilastirma (yanlış/doğru), cta (kaydet, paylaş, yorum + anahtar kelime, takip).
- Türkçe dizgi: `tr_upper` / `tr_lower`, mürekkebe göre çakışmasız satır aralığı (İ noktası, Ş/Ç çengeli, Ğ),
  Türkçe satır bölme (ve/ile satır sonunda kalmaz; de/da/ki/mi/için satır başına düşmez; sayı ile birimi ayrılmaz),
  dengeli başlık satırları, dizgi tırnakları (“ ” ’), eksik glifte yedek font.
- Çizim kontrolü: taşma, kenar payı, iki yazı öğesinin değmesi; çıkış kodu 2.
- Plan kuralları (`kontrol`): 5-10 slayt, kancada sayı, tek fikir/kelime sınırları, sayı slaytında kaynak, CTA, hashtag ≤ 4,
  büyük harf ve birleşik nokta (i̇) hataları, doldurulmamış TODO.
- Caption yazarı: kanca satırı + madde listesi + CTA + anahtar kelime satırı + en fazla 4 hashtag; alt metinler.
- Reklam etiketi: her slaytta "REKLAM · @marka", açıklamada ilk satır, Reklam Etiketi Kontrolü için `reklam_kontrol.yaml`.
- 3 ücretsiz şablon: koyu-mercan, acik-editoryal, renkli-egitim. OFL fontlar: Archivo, Bricolage Grotesque, Manrope, Unbounded.
- `doctor`, `yeni` (iskelet: liste / adım / hata kalıpları), `sablonlar`, `caption`; 3 örnek carousel.
