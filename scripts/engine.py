"""Çizim motoru: font yükleme, Türkçe satır bölme, çakışmasız satır aralığı, slayt tuvali ve son kontrol.

Çakışmasız başlık fikri: Türkçe büyük harflerin işaretleri (İ noktası, Ş/Ç çengeli, Ğ kıvrığı, Ö/Ü noktaları)
dar satır aralığında üst satırın inen harflerine (ş, ç, g, y, p) değer. Her satırın mürekkebi (gerçek piksel)
çıkarılır, sütun sütun "üst satırın en alt pikseli" ile "alt satırın en üst pikseli" arasındaki boşluk ölçülür
ve satır aralığı, her yerde en az `gap` piksel boşluk kalacak kadar açılır. Bütün satırlar aynı aralığı alır
(ritim bozulmaz).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import trtext

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / "fonts"
W, H = 1080, 1350
S = 2                       # süper örnekleme: her şey 2x çizilir, sonda küçültülür
AXIS_NAMES = {"wght": b"Weight", "wdth": b"Width", "opsz": b"Optical size", "ital": b"Italic", "slnt": b"Slant"}


def rgb(c) -> Tuple[int, int, int]:
    if isinstance(c, (list, tuple)):
        return tuple(int(v) for v in c[:3])
    c = str(c).lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


# ---------------------------------------------------------------- fontlar
@lru_cache(maxsize=512)
def _font(path: str, px: int, axes: Tuple[Tuple[str, float], ...]) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(path, px)
    if axes:
        try:
            info = f.get_variation_axes()
        except Exception:
            info = []
        if info:
            want = dict(axes)
            vals = []
            for a in info:
                name = a.get("name")
                tag = next((t for t, n in AXIS_NAMES.items() if n == name), None)
                v = want.get(tag, a.get("default", a["minimum"]))
                vals.append(max(a["minimum"], min(a["maximum"], v)))
            f.set_variation_by_axes(vals)
    return f


@dataclass(frozen=True)
class FontSpec:
    file: str
    axes: Tuple[Tuple[str, float], ...] = ()

    @staticmethod
    def of(d: Dict) -> "FontSpec":
        return FontSpec(d["dosya"], tuple(sorted((d.get("eksen") or {}).items())))

    def get(self, size: float) -> ImageFont.FreeTypeFont:
        return _font(str(FONTS / self.file), max(4, int(round(size * S))), self.axes)


@lru_cache(maxsize=64)
def _notdef(path: str, axes) -> bytes:
    return bytes(_font(path, 40, axes).getmask("￿"))


def missing_glyphs(fs: FontSpec, text: str) -> List[str]:
    f = _font(str(FONTS / fs.file), 40, fs.axes)
    nd = _notdef(str(FONTS / fs.file), fs.axes)
    out = []
    for ch in sorted(set(text)):
        if ch.isspace() or ch == "*":
            continue
        if bytes(f.getmask(ch)) == nd:
            out.append(ch)
    return out


# ---------------------------------------------------------------- zengin metin
@dataclass
class Tok:
    text: str
    accent: bool = False
    brk: bool = False          # bu kelimeden ÖNCE zorunlu satır sonu


def tokens(text: str, upper: bool = False) -> List[Tok]:
    """'Kaydet, *sonra* aç' -> [Kaydet,][sonra*][aç]. '\\n' zorunlu satır sonu. *...* birden çok kelimeyi sarabilir."""
    out: List[Tok] = []
    acc = False
    text = trtext.smart_quotes(str(text or ""))
    for li, line in enumerate(text.replace("\r", "").split("\n")):
        first = True
        for raw in line.split():
            w = raw
            starts = w.startswith("*")
            if starts:
                acc = True
                w = w[1:]
            ends = w.endswith("*") or re.search(r"\*[.,;:!?…'’)]*$", w) is not None
            if ends:
                w = re.sub(r"\*(?=[.,;:!?…'’)]*$)", "", w, count=1)
            this_acc = acc
            if ends:
                acc = False
            w = w.replace("*", "")
            if not w:
                continue
            if upper:
                w = trtext.tr_upper(w)
            out.append(Tok(w, this_acc, brk=(first and li > 0)))
            first = False
    return out


def wrap(toks: List[Tok], font: ImageFont.FreeTypeFont, maxw: float) -> List[List[Tok]]:
    """Açgözlü satır bölme + Türkçe kurallar (ve/ile satır sonunda kalmaz, de/da/ki/mi satır başına düşmez)."""
    sp = font.getlength(" ")
    lines: List[List[Tok]] = []
    cur: List[Tok] = []
    cw = 0.0
    for t in toks:
        w = font.getlength(t.text)
        if cur and (t.brk or cw + sp + w > maxw):
            if not t.brk and len(cur) >= 2 and trtext.bad_break(cur[-1].text, t.text):
                carry = [cur.pop()]
                lines.append(cur)
                cur = carry
                cw = font.getlength(carry[0].text)
                if cw + sp + w <= maxw:
                    cur.append(t)
                    cw += sp + w
                    continue
                lines.append(cur)
                cur, cw = [t], w
                continue
            lines.append(cur)
            cur, cw = [t], w
        else:
            cw = (cw + sp + w) if cur else w
            cur.append(t)
    if cur:
        lines.append(cur)
    # dul satır: son satırda tek kelime kaldıysa önceki satırdan bir kelime indir
    if len(lines) >= 2 and len(lines[-1]) == 1 and not lines[-1][0].brk:
        for k in (1, 2, 3):
            prev = lines[-2]
            if len(prev) < k + 2:
                break
            if trtext.bad_break(prev[-k - 1].text, prev[-k].text):
                continue
            trial = prev[-k:] + lines[-1]
            if line_width(trial, font) <= maxw:
                lines[-2] = prev[:-k]
                lines[-1] = trial
            break
    return lines


def line_width(line: List[Tok], font) -> float:
    return sum(font.getlength(t.text) for t in line) + font.getlength(" ") * max(0, len(line) - 1)


def balanced_wrap(toks: List[Tok], font, maxw: float) -> List[List[Tok]]:
    """Aynı satır sayısını koruyan en dar genişliği bulur: başlıkta tek kelimelik dul satır kalmaz."""
    base = wrap(toks, font, maxw)
    if len(base) <= 1 or any(t.brk for t in toks):
        return base
    lo, hi = maxw * 0.5, maxw
    best = base
    for _ in range(14):
        mid = (lo + hi) / 2
        trial = wrap(toks, font, mid)
        if len(trial) == len(base) and max(line_width(l, font) for l in trial) <= mid + 0.5:
            best, hi = trial, mid
        else:
            lo = mid
    return best


# ---------------------------------------------------------------- blok yerleşimi
@dataclass
class Block:
    """Ölçülmüş, çizilmeye hazır metin bloğu. Koordinatlar S ölçeğinde (piksel*2)."""
    lines: List[List[Tok]]
    font: ImageFont.FreeTypeFont
    size: float
    step: int                     # taban çizgileri arası (S)
    tops: List[int]               # her satırın taban çizgisine göre en üst mürekkep (negatif)
    bottoms: List[int]            # ... en alt mürekkep
    widths: List[float]
    overflow: bool = False
    fallback: Optional[str] = None

    @property
    def ink_h(self) -> int:       # S ölçeğinde
        if not self.lines:
            return 0
        return (len(self.lines) - 1) * self.step + self.bottoms[-1] - self.tops[0]

    @property
    def h(self) -> float:         # final piksel
        return self.ink_h / S

    @property
    def w(self) -> float:
        return (max(self.widths) if self.widths else 0) / S


def _line_mask(line: List[Tok], font, pad_up: int, height: int, width: int) -> np.ndarray:
    im = Image.new("L", (width, height), 0)
    d = ImageDraw.Draw(im)
    x = 0.0
    sp = font.getlength(" ")
    for t in line:
        d.text((x, pad_up), t.text, font=font, fill=255, anchor="ls")
        x += font.getlength(t.text) + sp
    return np.asarray(im) > 60


def _profiles(mask: np.ndarray, pad_up: int):
    has = mask.any(axis=0)
    top = np.where(has, mask.argmax(axis=0), 10 ** 6) - pad_up
    bot = np.where(has, mask.shape[0] - 1 - mask[::-1].argmax(axis=0), -10 ** 6) - pad_up
    return top, bot


def _sliding_max(a: np.ndarray, r: int) -> np.ndarray:
    out = a.copy()
    for s in range(1, r + 1):
        out[:-s] = np.maximum(out[:-s], a[s:])
        out[s:] = np.maximum(out[s:], a[:-s])
    return out


def measure(text: str, fs: FontSpec, size: float, maxw: float, lead: float = 1.0, upper: bool = False,
            balance: bool = False, gap_em: float = 0.07, min_gap: float = 6,
            quick_lines: Optional[int] = None) -> Block:
    """Metni ölçer: satırlara böler ve mürekkebe göre çakışmasız satır aralığını hesaplar."""
    font = fs.get(size)
    toks = tokens(text, upper)
    mw = maxw * S
    lines = balanced_wrap(toks, font, mw) if balance else wrap(toks, font, mw)
    widths = [line_width(l, font) for l in lines]
    overflow = any(w > mw + 1 for w in widths)
    asc, desc = font.getmetrics()
    if overflow or (quick_lines is not None and len(lines) > quick_lines):
        # sığmıyor: maske hesaplamadan kaba ölçü döndür (fit bir küçük boyu deneyecek)
        n = len(lines)
        return Block(lines, font, size, int(size * S * lead), [-asc] * n, [desc] * n, widths, True)
    pad_up = int(asc * 1.45) + 4
    hh = pad_up + int(desc * 1.6) + 8
    width = int(max(widths + [1])) + 8
    tops, bots, profs = [], [], []
    for l in lines:
        m = _line_mask(l, font, pad_up, hh, width)
        t, b = _profiles(m, pad_up)
        profs.append((t, b))
        tops.append(int(t.min()) if (t < 10 ** 5).any() else -asc)
        bots.append(int(b.max()) if (b > -10 ** 5).any() else desc)
    step = int(round(size * S * lead))
    gap = int(max(min_gap * S, size * S * gap_em))
    for i in range(len(lines) - 1):
        _, b = profs[i]
        t, _ = profs[i + 1]
        n = max(len(b), len(t))
        bb = np.full(n, -10 ** 6)
        tt = np.full(n, 10 ** 6)
        bb[:len(b)] = b
        tt[:len(t)] = t
        bd = _sliding_max(bb, gap * 3)   # yatayda da pay: yan yana duran işaretler (Ş çengeli + İ noktası) sıkışmasın
        ok = (bd > -10 ** 5) & (tt < 10 ** 5)
        if ok.any():
            need = int((bd[ok] + gap - tt[ok]).max())
            step = max(step, need)
    return Block(lines, font, size, step, tops, bots, widths, overflow)


def fit(text: str, fs: FontSpec, maxw: float, maxh: Optional[float], size_max: float, size_min: float,
        lead: float = 1.0, upper: bool = False, balance: bool = False, max_lines: Optional[int] = None,
        fallback: Optional[FontSpec] = None, pref_lines: Optional[int] = None, **kw) -> Block:
    """En büyük yazı boyunu bulur: her kelime genişliğe sığar, blok yüksekliği maxh'i geçmez.
    pref_lines: tercih edilen en fazla satır (yumuşak): önce bu sınırla denenir, olmazsa sınırsız."""
    if pref_lines and (max_lines is None or pref_lines < max_lines):
        b = fit(text, fs, maxw, maxh, size_max, max(size_min, size_max * 0.62), lead, upper, balance, pref_lines,
                fallback, None, **kw)
        if not b.overflow:
            return b
    note = None
    probe = trtext.tr_upper(text) if upper else text
    if fallback is not None and missing_glyphs(fs, probe):
        note = f"{fs.file} içinde {''.join(missing_glyphs(fs, probe))} yok, {fallback.file} kullanıldı"
        fs = fallback
    size = size_max
    last = None
    while size >= size_min:
        b = measure(text, fs, size, maxw, lead, upper, balance, quick_lines=max_lines, **kw)
        last = b
        fits = not b.overflow and (maxh is None or b.h <= maxh) and (max_lines is None or len(b.lines) <= max_lines)
        if fits:
            b.fallback = note
            return b
        size -= 2 if size > 40 else 1
    last = measure(text, fs, size_min, maxw, lead, upper, balance, **kw)
    last.overflow = True
    last.fallback = note
    return last


# ---------------------------------------------------------------- slayt
@dataclass
class Element:
    name: str
    mask: np.ndarray              # final ölçekte, tuval boyutunda bool (yalnız bbox bölgesi dolu)
    box: Tuple[int, int, int, int]
    kind: str = "text"            # text | shape
    overflow: bool = False
    note: Optional[str] = None


class Slide:
    def __init__(self, bg):
        self.bg = rgb(bg)
        self.im = Image.new("RGB", (W * S, H * S), self.bg)
        self.d = ImageDraw.Draw(self.im)
        self.elements: List[Element] = []

    # ---- ilkel şekiller (final piksel koordinatı)
    def rect(self, box, fill=None, outline=None, width=1, r=0):
        b = [v * S for v in box]
        if r:
            self.d.rounded_rectangle(b, radius=r * S, fill=fill and rgb(fill), outline=outline and rgb(outline),
                                     width=int(width * S))
        else:
            self.d.rectangle(b, fill=fill and rgb(fill), outline=outline and rgb(outline), width=int(width * S))

    def ellipse(self, box, fill=None, outline=None, width=1):
        self.d.ellipse([v * S for v in box], fill=fill and rgb(fill), outline=outline and rgb(outline),
                       width=int(width * S))

    def poly(self, pts, fill=None, outline=None, width=1):
        self.d.polygon([(x * S, y * S) for x, y in pts], fill=fill and rgb(fill), outline=outline and rgb(outline),
                       width=int(width * S))

    def line(self, pts, fill, width=2):
        self.d.line([(x * S, y * S) for x, y in pts], fill=rgb(fill), width=int(width * S), joint="curve")

    # ---- metin
    def draw_block(self, b: Block, x: float, y_top: float, color, accent=None, align: str = "left",
                   width: Optional[float] = None, name: str = "metin") -> float:
        """Bloğu mürekkep üstü y_top olacak şekilde çizer; mürekkep altını (final px) döndürür."""
        color = rgb(color)
        accent = rgb(accent) if accent else color
        base = y_top * S - b.tops[0] if b.lines else y_top * S
        sp = b.font.getlength(" ")
        layer = Image.new("L", self.im.size, 0)
        ld = ImageDraw.Draw(layer)
        for i, (l, lw) in enumerate(zip(b.lines, b.widths)):
            bx = x * S
            if align == "center" and width:
                bx = x * S + (width * S - lw) / 2
            elif align == "right" and width:
                bx = x * S + width * S - lw
            by = base + i * b.step
            for t in l:
                self.d.text((bx, by), t.text, font=b.font, fill=accent if t.accent else color, anchor="ls")
                ld.text((bx, by), t.text, font=b.font, fill=255, anchor="ls")
                bx += b.font.getlength(t.text) + sp
        self._register(name, layer, "text", b.overflow, b.fallback)
        return (base + (len(b.lines) - 1) * b.step + b.bottoms[-1]) / S if b.lines else y_top

    def text(self, xy, s, font: ImageFont.FreeTypeFont, color, anchor="la", tracking: float = 0.0,
             name: str = "etiket") -> Tuple[float, float, float, float]:
        """Tek satır küçük metin (etiket, sayfa no). tracking: harf arası (em). bbox (final px) döndürür."""
        layer = Image.new("L", self.im.size, 0)
        ld = ImageDraw.Draw(layer)
        x, y = xy[0] * S, xy[1] * S
        if tracking:
            tw = self.tracked_width(s, font, tracking) * S
            if anchor[0] == "r":
                x -= tw
            elif anchor[0] == "m":
                x -= tw / 2
            a = "l" + anchor[1]
            for ch in s:
                self.d.text((x, y), ch, font=font, fill=rgb(color), anchor=a)
                ld.text((x, y), ch, font=font, fill=255, anchor=a)
                x += font.getlength(ch) + tracking * font.size
        else:
            self.d.text((x, y), s, font=font, fill=rgb(color), anchor=anchor)
            ld.text((x, y), s, font=font, fill=255, anchor=anchor)
        bb = layer.getbbox() or (0, 0, 0, 0)
        self._register(name, layer, "text")
        return tuple(v / S for v in bb)

    @staticmethod
    def tracked_width(s: str, font, tracking: float) -> float:
        return (sum(font.getlength(ch) for ch in s) + tracking * font.size * max(0, len(s) - 1)) / S

    def _register(self, name, layer: Image.Image, kind, overflow=False, note=None):
        small = layer.resize((W, H), Image.BILINEAR)
        m = np.asarray(small) > 70
        bb = small.getbbox() or (0, 0, 0, 0)
        self.elements.append(Element(name, m, bb, kind, overflow, note))

    def save(self, path: Path):
        self.im.resize((W, H), Image.LANCZOS).save(path, optimize=True)

    # ---- son kontrol
    def check(self, safe: int = 40, gap: int = 4) -> List[str]:
        """Taşma, kenara fazla yaklaşma ve iki yazının mürekkebinin değmesi."""
        out = []
        for e in self.elements:
            if e.overflow:
                out.append(f"TAŞMA: '{e.name}' en küçük boyda bile alana sığmadı; metni kısalt.")
            if e.note:
                out.append(f"NOT: {e.name}: {e.note}")
            x0, y0, x1, y1 = e.box
            if x1 > x0 and (x0 < safe or y0 < safe or x1 > W - safe or y1 > H - safe):
                out.append(f"KENAR: '{e.name}' kenara {min(x0, y0, W - x1, H - y1)} px (en az {safe}).")
        texts = [e for e in self.elements if e.kind == "text" and e.box[2] > e.box[0]]
        for i in range(len(texts)):
            a = texts[i]
            ax0, ay0, ax1, ay1 = a.box
            for j in range(i + 1, len(texts)):
                b = texts[j]
                bx0, by0, bx1, by1 = b.box
                if ax1 + gap < bx0 or bx1 + gap < ax0 or ay1 + gap < by0 or by1 + gap < ay0:
                    continue
                x0, y0 = max(0, min(ax0, bx0) - gap), max(0, min(ay0, by0) - gap)
                x1, y1 = min(W, max(ax1, bx1) + gap), min(H, max(ay1, by1) + gap)
                ma = a.mask[y0:y1, x0:x1]
                mb = b.mask[y0:y1, x0:x1]
                dil = ma.copy()
                for s in range(1, gap + 1):
                    dil[:-s] |= ma[s:]
                    dil[s:] |= ma[:-s]
                d2 = dil.copy()
                for s in range(1, gap + 1):
                    d2[:, :-s] |= dil[:, s:]
                    d2[:, s:] |= dil[:, :-s]
                if (d2 & mb).any():
                    out.append(f"ÇAKIŞMA: '{a.name}' ile '{b.name}' birbirine değiyor (<{gap} px).")
        return out
