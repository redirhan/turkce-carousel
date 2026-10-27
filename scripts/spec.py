"""Slayt planı (YAML/JSON): yükleme, şablon seçimi, numaralama, kurallar (lint) ve boş iskelet."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

import trtext

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
TIPLER = ("kanca", "madde", "liste", "sayi", "karsilastirma", "cta")
TODO = re.compile(r"\bTODO\b|<<|>>")


# ---------------------------------------------------------------- şablonlar
def templates() -> Dict[str, Dict]:
    out = {}
    for p in sorted(TEMPLATES.glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        out[d["ad"]] = d
    return out


def template(name: str) -> Dict:
    tpls = templates()
    key = trtext.slug(name or "koyu-mercan")
    if key not in tpls:
        raise SystemExit(f"Şablon bulunamadı: {name}. Var olanlar: {', '.join(tpls)} "
                         "(Pro şablon paketi — 20 şablon — yakında).")
    return tpls[key]


# ---------------------------------------------------------------- yükleme
def load(path: str) -> Dict:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError:
            raise SystemExit("YAML okumak için PyYAML gerekli: pip install PyYAML (ya da planı .json yaz).")
        d = yaml.safe_load(text)
    else:
        d = json.loads(text)
    if not isinstance(d, dict) or not isinstance(d.get("slaytlar"), list):
        raise SystemExit("Plan dosyasında 'slaytlar' listesi yok. Örnek: examples/*/plan.yaml")
    return normalize(d)


def normalize(d: Dict) -> Dict:
    d = dict(d)
    d["sablon"] = trtext.slug(d.get("sablon") or "koyu-mercan")
    slides = []
    n = 0
    for s in d["slaytlar"]:
        s = dict(s or {})
        s["tip"] = trtext.fold(str(s.get("tip") or "madde")).replace("ş", "s")
        if s["tip"] in ("madde", "karsilastirma") and "no" not in s:
            n += 1
            s["no"] = n
        elif s["tip"] in ("madde", "karsilastirma") and str(s.get("no", "")).isdigit():
            n = int(s["no"])
        slides.append(s)
    d["slaytlar"] = slides
    if d.get("hesap") and not str(d["hesap"]).startswith("@"):
        d["hesap"] = "@" + str(d["hesap"])
    if d.get("reklam") in (None, False, "", {}):
        d["reklam"] = None
    elif isinstance(d["reklam"], str):
        d["reklam"] = {"veren": d["reklam"]}
    return d


def palettes_for(d: Dict, tpl: Dict) -> List[Dict]:
    """Her slaytın paleti: kanca/cta şablondaki sabit palet, aradakiler palet_sirasi ile döner,
    art arda aynı renk gelmez (şablonda tek palet varsa hepsi aynı). Slayt 'palet' alanıyla zorlayabilir."""
    pals = tpl["paletler"]
    order = tpl.get("palet_sirasi") or list(pals)
    slides = d["slaytlar"]
    last = len(slides) - 1
    names: List = []
    for i, s in enumerate(slides):
        if s.get("palet") in pals:
            names.append(s["palet"])
        elif i == 0 and s["tip"] == "kanca":
            names.append(tpl.get("kanca_palet") or order[0])
        elif i == last and s["tip"] == "cta":
            names.append(tpl.get("cta_palet") or order[0])
        else:
            names.append(None)
    k = 0
    for i in range(len(names)):
        if names[i] is not None:
            continue
        nxt = names[i + 1] if i + 1 < len(names) else None
        prev = names[i - 1] if i else None
        for _ in range(len(order)):
            cand = order[k % len(order)]
            k += 1
            if len(order) == 1 or (cand != prev and cand != nxt):
                break
        names[i] = cand
    return [pals[n] for n in names]


# ---------------------------------------------------------------- kurallar
def _all_text(s: Dict) -> List[Tuple[str, str]]:
    out = []
    for k, v in s.items():
        if isinstance(v, str):
            out.append((k, v))
        elif isinstance(v, list):
            out += [(k, str(x)) for x in v if isinstance(x, (str, int, float))]
    return out


def lint(d: Dict) -> Tuple[List[str], List[str]]:
    """(hatalar, uyarılar). Hata varsa render durur."""
    err, warn = [], []
    slides = d["slaytlar"]
    n = len(slides)
    if n < 5 or n > 10:
        (err if n < 2 or n > 20 else warn).append(f"{n} slayt var; işe yarayan aralık 5-10 (Instagram üst sınırı 20).")
    for i, s in enumerate(slides, 1):
        if s["tip"] not in TIPLER:
            err.append(f"Slayt {i}: bilinmeyen tip '{s['tip']}'. Tipler: {', '.join(TIPLER)}")
        for k, v in _all_text(s):
            if TODO.search(v):
                err.append(f"Slayt {i}: '{k}' hâlâ doldurulmamış (TODO).")
            if trtext.has_combining_dot(v):
                err.append(f"Slayt {i}: '{k}' içinde birleşik nokta (i̇) var: Python lower() kalıntısı. tr_lower kullan.")
            if trtext.looks_all_caps(v) and k in ("baslik", "metin", "alt", "ipucu"):
                warn.append(f"Slayt {i}: '{k}' tamamen BÜYÜK HARF yazılmış. Normal yaz; şablon gerekiyorsa Türkçe "
                            "kurala göre büyütür (ISTANBUL değil İSTANBUL).")
            if v.count("*") % 2:
                warn.append(f"Slayt {i}: '{k}' içinde kapanmamış vurgu yıldızı (*).")
        if not str(s.get("baslik") or "").strip() and s["tip"] not in ("cta",):
            err.append(f"Slayt {i}: başlık yok.")
        bw = len(trtext.words(s.get("baslik", "")))
        if bw > 12:
            warn.append(f"Slayt {i}: başlık {bw} kelime (en fazla ~10-12; kısalt, ayrıntıyı metne taşı).")
        mw = len(trtext.words(s.get("metin", "")))
        if mw > 40:
            warn.append(f"Slayt {i}: metin {mw} kelime. Slayt başına tek fikir: ~35 kelimeyi geçme.")
        if s["tip"] == "liste":
            k = len(s.get("maddeler") or [])
            if not 2 <= k <= 6:
                warn.append(f"Slayt {i}: listede {k} madde (2-6 arası okunur).")
        if s["tip"] == "sayi" and not s.get("kaynak"):
            warn.append(f"Slayt {i}: sayı/istatistik slaytında kaynak yok. Doğrulanmış kaynak yaz ya da sayıyı çıkar.")
        if s["tip"] == "karsilastirma" and not (s.get("yanlis") and s.get("dogru")):
            err.append(f"Slayt {i}: karşılaştırmada 'yanlis' ve 'dogru' alanları gerekli.")
        if s["tip"] == "cta" and trtext.fold(s.get("tur") or "kaydet") == "yorum":
            key = str(s.get("anahtar") or "").strip()
            if not key:
                err.append(f"Slayt {i}: yorum CTA'sında 'anahtar' kelime yok (ör. PLAN).")
            elif " " in key or len(key) > 12:
                warn.append(f"Slayt {i}: anahtar kelime tek ve kısa olmalı (≤12 harf): '{key}'.")
            if not (s.get("vaat") or s.get("metin")):
                warn.append(f"Slayt {i}: yorum yazana ne gönderileceği ('vaat') yazılmamış.")
    if slides:
        h = slides[0]
        if h["tip"] != "kanca":
            warn.append("İlk slayt 'kanca' değil. Kaydırma kararı ilk slaytta verilir.")
        hook = f"{h.get('sayi', '')} {trtext.plain(h.get('baslik', ''))}"
        if not re.search(r"\d", hook):
            warn.append("Kancada sayı yok. Somut sayı ('5 hata', '6 adımda') kaydırma oranını artırır.")
        if len(trtext.words(h.get("baslik", ""))) > 10:
            warn.append("Kanca başlığı 10 kelimeden uzun; tek bakışta okunmaz.")
        if slides[-1]["tip"] != "cta":
            warn.append("Son slayt 'cta' değil. Kaydet/paylaş ya da yorum-anahtar kelime çağrısı ekle.")
    heads = [trtext.fold(trtext.plain(s.get("baslik", ""))) for s in slides if s.get("baslik")]
    if len(heads) != len(set(heads)):
        warn.append("Aynı başlık iki slaytta var.")
    r = d.get("reklam")
    if r is not None and not str(r.get("veren") or "").strip():
        err.append("reklam: 'veren' (marka adı ya da @hesap) yok. Etiket 'Reklam · @marka' biçiminde olmalı.")
    tags = (d.get("caption") or {}).get("hashtagler") or []
    if len(tags) > 4:
        warn.append(f"{len(tags)} hashtag var; en fazla 4 kullanılır (fazlası atılacak).")
    return err, warn


# ---------------------------------------------------------------- iskelet
KALIPLAR = {
    "liste": "N madde: her slayt tek fikir (madde)",
    "adim": "adım adım anlatım (madde + no_etiket ADIM)",
    "hata": "yaygın hatalar: yanlış → doğru (karsilastirma)",
}


def skeleton(konu: str, sablon: str, n: int, kalip: str, cta: str, hesap: str) -> str:
    n = max(5, min(10, n))
    mid = n - 2
    lines = [
        "# Türkçe Carousel — slayt planı. Doldur, sonra: carousel.py render bu_dosya.yaml",
        "# Kurallar: kanca sayı içerir; slayt başına tek fikir; başlık ≤ 10 kelime; metin ≤ 35 kelime;",
        "# vurgu için *kelime*; büyük harfe kendin çevirme (şablon Türkçe kurala göre çevirir).",
        f'konu: "{konu}"',
        f"sablon: {sablon}            # koyu-mercan | acik-editoryal | renkli-egitim",
        f'hesap: "{hesap}"',
        'seri: "TODO kısa seri adı"     # üst etiket, ör. VİZE HAFTASI',
    ]
    if kalip == "adim":
        lines.append('madde_etiketi: "Adım"')
    elif kalip == "hata":
        lines.append('madde_etiketi: "Hata"')
    lines += [
        "slaytlar:",
        "  - tip: kanca",
        '    ust: "TODO"',
        f'    sayi: "{mid}"',
        '    baslik: "TODO sayı içeren kanca, *vurgu* tek yerde"',
        '    alt: "TODO ne kazanacak (tek cümle)"',
    ]
    for i in range(1, mid + 1):
        if kalip == "hata":
            lines += ["  - tip: karsilastirma", '    baslik: "TODO hatanın adı"',
                      '    yanlis: "TODO yaygın yanlış"', '    dogru: "TODO ne yapmalı"']
        else:
            lines += ["  - tip: madde", '    baslik: "TODO tek fikir"', '    metin: "TODO 1-2 cümle açıklama"']
            if i == 1:
                lines.append('    ipucu: "TODO (isteğe bağlı) somut örnek"')
    if cta == "yorum":
        lines += ["  - tip: cta", "    tur: yorum", '    anahtar: "TODO"', '    vaat: "TODO (ör. PDF listesini)"']
    else:
        lines += ["  - tip: cta", f"    tur: {cta}"]
    lines += [
        "caption:",
        '  kanca: ""                  # boşsa kanca slaytından',
        "  anahtar_kelimeler: [TODO]  # hashtag yerine düz anahtar kelime satırı",
        "  hashtagler: []             # en fazla 4",
        "reklam: null                 # iş birliğiyse: {tur: Reklam, veren: \"@marka\"}",
    ]
    return "\n".join(lines) + "\n"
