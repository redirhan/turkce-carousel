"""Gönderi açıklaması (caption) yazarı.

Düzen (çalışan carousel/reel açıklamalarından):
    [Reklam | @marka tarafından sağlandı.]       <- yalnız iş birliğinde, İLK satır
    Kanca satırı (ilk ~125 karakter "devamı"ndan önce görünür)

    1. Madde başlığı
    2. ...

    CTA satırı (kaydet/paylaş ya da yoruma ANAHTAR yaz)

    anahtar kelime · anahtar kelime · ...        <- hashtag yerine düz arama satırı
    #en #fazla #dört #etiket
"""
from __future__ import annotations

import re
from typing import Dict, List, Tuple

import trtext

IG_LIMIT = 2200
FOLD = 125


def _tag(t: str) -> str:
    t = re.sub(r"[^\wÇĞİÖŞÜçğıöşü]", "", str(t).lstrip("#").replace(" ", ""))
    return "#" + trtext.tr_lower(t) if t else ""


def ad_line(r: Dict) -> str:
    if r.get("metin"):
        return str(r["metin"]).strip()
    tur = str(r.get("tur") or "Reklam").strip()
    tur = trtext.tr_upper(tur[:1]) + trtext.tr_lower(tur[1:])
    veren = str(r.get("veren") or "").strip()
    return f"{tur} | {veren} tarafından sağlandı."


def build(d: Dict) -> Tuple[str, List[str]]:
    cap = d.get("caption") or {}
    slides = d["slaytlar"]
    warn: List[str] = []
    out: List[str] = []
    r = d.get("reklam")
    if r:
        out.append(ad_line(r))
        if r.get("yapay_zeka"):
            out.append(str(r["yapay_zeka"]).strip())
    hook = trtext.plain(cap.get("kanca") or "")
    if not hook and slides:
        h = slides[0]
        hook = trtext.plain(h.get("baslik", ""))
        if h.get("sayi") and str(h["sayi"]) not in hook:
            hook = f"{h['sayi']}: {hook}" if not re.search(r"\d", hook) else hook
        if hook and not re.search(r"[.!?…:]$", hook):
            hook += "."
    if len(hook) > FOLD:
        warn.append(f"Kanca satırı {len(hook)} karakter; ilk {FOLD} karakter 'devamı'ndan önce görünür.")
    out.append(hook)
    items = cap.get("maddeler")
    if items is None:
        items = [trtext.plain(s.get("baslik", "")) for s in slides if s["tip"] in ("madde", "karsilastirma", "sayi")]
        if not items:
            for s in slides:
                if s["tip"] == "liste":
                    items = [trtext.plain(m) for m in s.get("maddeler") or []]
                    break
    if items:
        out.append("")
        out += [f"{i}. {t}" for i, t in enumerate(items, 1)]
    cta = cap.get("cta")
    if not cta:
        last = slides[-1] if slides else {}
        tur = trtext.fold(last.get("tur") or "kaydet") if last.get("tip") == "cta" else "kaydet"
        if tur != "yorum" and last.get("baslik"):
            parts = [trtext.plain(x) for x in (last.get("baslik"), last.get("metin")) if x]
            cta = " ".join(p if re.search(r"[.!?…]$", p) else p + "." for p in parts)
        elif tur == "yorum":
            key = trtext.tr_upper(str(last.get("anahtar") or "").strip())
            vaat = str(last.get("vaat") or "listeyi").strip()
            cta = f"Yoruma \"{key}\" yaz, {vaat} DM'den göndereyim."
        elif tur.startswith("paylas"):
            cta = "Bunu bilmesi gereken birine gönder, sonra lazım olursa diye kaydet."
        elif tur == "takip":
            cta = f"Daha fazlası için {d.get('hesap') or 'hesabı'} takip et."
        else:
            cta = "Kaydet, lazım olunca aç. İşine yarayacak birine de gönder."
    out += ["", trtext.plain(cta)]
    kws = [trtext.tr_lower(trtext.plain(k)) for k in (cap.get("anahtar_kelimeler") or []) if str(k).strip()]
    if kws:
        out += ["", " · ".join(kws)]
    tags = [t for t in (_tag(x) for x in (cap.get("hashtagler") or [])) if t]
    if len(tags) > 4:
        warn.append(f"{len(tags)} hashtag verildi, ilk 4'ü kullanıldı.")
        tags = tags[:4]
    if tags:
        out.append(" ".join(tags))
    text = "\n".join(out).strip() + "\n"
    if len(text) > IG_LIMIT:
        warn.append(f"Açıklama {len(text)} karakter; Instagram sınırı {IG_LIMIT}.")
    return text, warn


def alt_texts(d: Dict) -> str:
    """Her slayt için erişilebilirlik (alt) metni: Instagram'da 'Gelişmiş ayarlar > Alternatif metin'."""
    rows = []
    for i, s in enumerate(d["slaytlar"], 1):
        parts = [s.get("ust"), s.get("sayi"), s.get("baslik"), s.get("metin"), s.get("alt"), s.get("ipucu")]
        if s["tip"] == "karsilastirma":
            parts += [f"Yanlış: {s.get('yanlis', '')}", f"Doğru: {s.get('dogru', '')}"]
        if s["tip"] == "liste":
            parts += list(s.get("maddeler") or [])
        if s["tip"] == "cta" and s.get("anahtar"):
            parts.append(f"Yoruma {s['anahtar']} yaz.")
        txt = " ".join(trtext.plain(p) for p in parts if p)
        rows.append(f"{i:02d}: {txt}")
    return "\n".join(rows) + "\n"


def reklam_yaml(d: Dict, caption_text: str) -> str:
    """Reklam Etiketi Kontrolü skill'i (github.com/redirhan/reklam-etiketi) için gönderi girdisi."""
    r = d["reklam"]
    veren = str(r.get("veren") or "")
    label = f"{trtext.tr_upper(r.get('tur') or 'Reklam')} · {veren}"
    n = len(d["slaytlar"])
    ai = bool(r.get("yapay_zeka"))
    cap = "\n".join("  " + ln for ln in caption_text.rstrip("\n").split("\n"))
    return (
        "# Reklam Etiketi Kontrolü girdisi — Türkçe Carousel Üretici tarafından yazıldı.\n"
        "# Eksik alanları doldur, sonra: python3 <reklam-etiketi>/scripts/kontrol.py reklam_kontrol.yaml\n"
        "# Bu bir hukuki görüş değildir; bilgilendirme amaçlıdır.\n"
        "platform: instagram\n"
        "bicim: carousel\n"
        "hesap_turu: icerik_uretici   # icerik_uretici | marka_kendi | ajans_musteri\n"
        "ticari_iliski: evet\n"
        "iliski_turu: [ucret]         # ucret | hediye_urun | indirimli_urun | yonlendirme | cekilis | etkinlik\n"
        f"reklam_veren: \"{veren.lstrip('@')}\"\n"
        f"reklam_veren_hesap: \"{veren if veren.startswith('@') else ''}\"\n"
        "urun_kategorisi: diger\n"
        "platform_ortaklik_etiketi: hayir\n"
        "filtre: hayir\n"
        "aciklama: |\n" + cap + "\n"
        "ekran_yazilari:\n"
        f"  - metin: \"{label}\"\n"
        "    baslangic: 0\n"
        "    bitis: 0\n"
        "    konum: ust\n"
        f"parca_sayisi: {n}\n"
        "her_parcada_etiket: evet     # etiket her slaytın sol üstünde\n"
        "yapay_zeka:\n"
        f"  kullanildi: {'evet' if ai else 'hayir'}\n"
        "  neler: []\n"
        "  gercek_kisi_kopyasi: hayir\n"
    )
