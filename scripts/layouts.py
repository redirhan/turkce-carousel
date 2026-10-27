"""Slayt düzenleri: kanca, madde, liste, sayi, karsilastirma, cta — üç stil (mercan, editoryal, egitim).

Her düzen öğe listesi kurar (metin, boşluk, panel, çizim). Öğeler önce ölçülür; sığmazsa her şey birlikte
küçültülür (ölçek 1,0 → 0,6). En küçük ölçekte de sığmayan slayt TAŞMA olarak raporlanır.
"""
from __future__ import annotations

import math
from typing import Callable, Dict, List, Optional, Tuple

import trtext
from engine import H, S, W, Block, FontSpec, Slide, fit, rgb

M = 88                 # yan boşluk
TOP = 160              # içerik başlangıcı (üst bilgi satırının altı)
BOT = H - 150          # içerik sonu (alt bilgi satırının üstü)
CW = W - 2 * M


class Ctx:
    def __init__(self, tpl: Dict, pal: Dict, idx: int, total: int, meta: Dict, sl: Dict):
        self.tpl, self.pal, self.idx, self.total, self.meta, self.sl = tpl, pal, idx, total, meta, sl
        self.st = tpl["stil"]
        self.fonts = {k: FontSpec.of(v) for k, v in tpl["fontlar"].items()}
        self.o = tpl["olcu"]
        self.upper = bool(tpl.get("baslik_buyuk_harf"))
        self.lead = float(tpl.get("baslik_satir", 0.95))
        self.notes: List[str] = []

    def f(self, role: str) -> FontSpec:
        return self.fonts[role]

    def c(self, key: str):
        return rgb(self.pal[key])


# ---------------------------------------------------------------- öğeler
class Item:
    """measure(scale, w) -> (yükseklik, draw(slide, x, y))"""

    def measure(self, cx: Ctx, scale: float, w: float):
        raise NotImplementedError


class Gap(Item):
    def __init__(self, h: float):
        self.h = h

    def measure(self, cx, scale, w):
        return self.h * (0.6 + 0.4 * scale), (lambda sl, x, y: None)


class Text(Item):
    def __init__(self, text, role="govde", size=40, min_size=28, color="metin", accent="vurgu", upper=None,
                 balance=False, lead=None, max_lines=None, align="left", name="metin", maxh=None, pref_lines=None):
        self.__dict__.update(locals())
        del self.__dict__["self"]

    def measure(self, cx, scale, w):
        up = cx.upper if (self.upper is None and self.role == "baslik") else bool(self.upper)
        lead = self.lead or (cx.lead if self.role in ("baslik", "sayi") else 1.34)
        b = fit(self.text, cx.f(self.role), w, self.maxh, max(self.min_size, self.size * scale), self.min_size,
                lead=lead, upper=up, balance=self.balance, max_lines=self.max_lines, fallback=cx.f("yedek"),
                pref_lines=self.pref_lines)

        def draw(sl, x, y, b=b):
            sl.draw_block(b, x, y, cx.c(self.color), cx.c(self.accent), align=self.align, width=w, name=self.name)
        return b.h, draw


class Custom(Item):
    def __init__(self, h: float, fn: Callable, scale_h: bool = True):
        self.h, self.fn, self.scale_h = h, fn, scale_h

    def measure(self, cx, scale, w):
        hh = self.h * (scale if self.scale_h else 1.0)
        return hh, (lambda sl, x, y: self.fn(sl, x, y, w, hh))


class Label(Item):
    """Küçük, harf aralıklı BÜYÜK HARF etiket (kicker)."""

    def __init__(self, text, color="vurgu", size=None, name="ust etiket"):
        self.text, self.color, self.size, self.name = text, color, size, name

    def measure(self, cx, scale, w):
        size = self.size or cx.o["etiket"] + 3
        b = fit(trtext.tr_upper(self.text), cx.f("etiket"), w, None, size, 18, lead=1.2, max_lines=2,
                fallback=cx.f("yedek"), gap_em=0.12)

        def draw(sl, x, y):
            sl.draw_block(b, x, y, cx.c(self.color), name=self.name)
        return b.h, draw


class Panel(Item):
    """Kutu: üstte küçük etiket (+ isteğe bağlı ✓/✕ işareti), altında metin."""

    def __init__(self, label, text, bg="panel", fg="panel_metin", label_color="vurgu", icon=None, style="box",
                 name="panel"):
        self.__dict__.update(locals())
        del self.__dict__["self"]

    def measure(self, cx, scale, w):
        pad = 34 if self.style == "box" else 0
        bar = 10 if self.style == "bar" else 0
        indent = pad + (bar + 30 if bar else 0)
        inner = w - indent - pad
        lab_size = cx.o["etiket"] + 1
        lab = fit(trtext.tr_upper(self.label), cx.f("etiket"), inner - (44 if self.icon else 0), None, lab_size, 16,
                  lead=1.2, max_lines=1, fallback=cx.f("yedek"), gap_em=0.12) if self.label else None
        body = fit(self.text, cx.f("govde"), inner, None, max(cx.o["govde_min"], cx.o["govde"] * 0.95 * scale),
                   cx.o["govde_min"], lead=1.32, fallback=cx.f("yedek"))
        lab_h = max(lab.h if lab else 0, 30 if self.icon else 0)
        top_pad = pad if self.style == "box" else 4
        hh = top_pad + (lab_h + 20 if (lab or self.icon) else 0) + body.h + (pad if self.style == "box" else 4)

        def draw(sl, x, y):
            if self.style == "box":
                sl.rect((x, y, x + w, y + hh), fill=cx.c(self.bg), r=22 if cx.st == "egitim" else 14)
            else:
                sl.rect((x, y, x + bar, y + hh), fill=cx.c("vurgu"))
            yy = y + top_pad
            lx = x + indent
            if self.icon:
                icon(sl, self.icon, lx, yy + lab_h / 2 - 13, 26, cx.c(self.label_color))
                lx += 44
            if lab:
                sl.draw_block(lab, lx, yy + (lab_h - lab.h) / 2, cx.c(self.label_color), name=self.name + " etiketi")
            if lab or self.icon:
                yy += lab_h + 20
            sl.draw_block(body, x + indent, yy, cx.c(self.fg), cx.c(self.label_color), name=self.name)
        return hh, draw


class Bullets(Item):
    def __init__(self, items: List[str], mark="tik", color="metin", name="liste"):
        self.items, self.mark, self.color, self.name = items, mark, color, name

    def measure(self, cx, scale, w):
        ind = 70
        size = max(cx.o["govde_min"], cx.o["govde"] * 1.2 * scale)
        blocks = [fit(t, cx.f("govde_kalin" if self.mark != "nokta" else "govde"), w - ind, None, size,
                      cx.o["govde_min"], lead=1.28, fallback=cx.f("yedek")) for t in self.items]
        g = 30 * scale + 10
        hh = sum(max(b.h, 34) for b in blocks) + g * (len(blocks) - 1)

        def draw(sl, x, y):
            yy = y
            for i, b in enumerate(blocks):
                bh = max(b.h, 34)
                cy = yy + min(b.h, size * 0.75) / 2
                if self.mark == "tik":
                    icon(sl, "tik", x, cy - 16, 32, cx.c("vurgu"))
                elif self.mark == "sayi":
                    nb = fit(str(i + 1), cx.f("sayi"), 44, None, size * 0.9, 16, lead=1.0, max_lines=1)
                    sl.draw_block(nb, x, cy - nb.h / 2, cx.c("vurgu"), name=f"{self.name} no {i + 1}")
                else:
                    sl.ellipse((x + 6, cy - 9, x + 24, cy + 9), fill=cx.c("vurgu"))
                sl.draw_block(b, x + ind, yy, cx.c(self.color), cx.c("vurgu"), name=f"{self.name} {i + 1}")
                yy += bh + g
        return hh, draw


# ---------------------------------------------------------------- çizimler
def icon(sl: Slide, kind: str, x: float, y: float, s: float, color):
    if kind == "tik":
        sl.line([(x + s * 0.06, y + s * 0.55), (x + s * 0.38, y + s * 0.86), (x + s * 0.96, y + s * 0.16)],
                color, width=max(3, s * 0.16))
    elif kind == "carpi":
        wd = max(3, s * 0.15)
        sl.line([(x + s * 0.12, y + s * 0.12), (x + s * 0.88, y + s * 0.88)], color, width=wd)
        sl.line([(x + s * 0.88, y + s * 0.12), (x + s * 0.12, y + s * 0.88)], color, width=wd)
    elif kind == "kaydet":
        w = s * 0.74
        x0 = x + (s - w) / 2
        sl.poly([(x0, y), (x0 + w, y), (x0 + w, y + s), (x0 + w / 2, y + s * 0.72), (x0, y + s)], fill=color)
    elif kind == "yorum":
        sl.rect((x, y, x + s, y + s * 0.74), fill=color, r=s * 0.2)
        sl.poly([(x + s * 0.2, y + s * 0.6), (x + s * 0.48, y + s * 0.6), (x + s * 0.16, y + s * 0.98)], fill=color)
    elif kind == "paylas":
        sl.poly([(x, y + s * 0.42), (x + s, y), (x + s * 0.6, y + s), (x + s * 0.44, y + s * 0.58)], fill=color)
    elif kind == "takip":
        sl.ellipse((x + s * 0.28, y, x + s * 0.72, y + s * 0.44), fill=color)
        sl.rect((x + s * 0.08, y + s * 0.52, x + s * 0.92, y + s), fill=color, r=s * 0.22)


def circle_number(cx: Ctx, txt: str, d: float, bg="vurgu", fg="vurgu_metin", name="numara"):
    def fn(sl, x, y, w, hh):
        dd = hh
        sl.ellipse((x, y, x + dd, y + dd), fill=cx.c(bg))
        b = fit(txt, cx.f("sayi"), dd * 0.64, dd * 0.5, dd * 0.5, 14, lead=1.0, max_lines=1, fallback=cx.f("yedek"))
        sl.draw_block(b, x + (dd - b.w) / 2, y + (dd - b.h) / 2, cx.c(fg), name=name)
    return Custom(d, fn)


def rule_label(cx: Ctx, txt: str, name="numara"):
    """Editoryal: 'ADIM 01 ————' etiketi."""
    def fn(sl, x, y, w, hh):
        f = cx.f("etiket").get(cx.o["etiket"] + 2)
        bb = sl.text((x, y + hh / 2), trtext.tr_upper(txt), f, cx.c("vurgu"), anchor="lm", tracking=0.14, name=name)
        sl.rect((bb[2] + 22, y + hh / 2 - 1, x + w, y + hh / 2 + 1), fill=cx.c("cizgi"))
    return Custom(36, fn, scale_h=False)


def keyword_pill(cx: Ctx, key: str):
    def fn(sl, x, y, w, hh):
        b = fit(trtext.tr_upper(key), cx.f("sayi"), w - 120, hh * 0.62, hh * 0.62, 30, lead=1.0, max_lines=1,
                fallback=cx.f("yedek"))
        pw = b.w + 110
        px = x + (w - pw) / 2 if cx.st == "egitim" else x
        sl.rect((px, y, px + pw, y + hh), fill=cx.c("vurgu"), r=hh / 2 if cx.st == "egitim" else 18)
        sl.draw_block(b, px + 55, y + (hh - b.h) / 2, cx.c("vurgu_metin"), name="anahtar kelime")
    return Custom(150, fn)


# ---------------------------------------------------------------- üst / alt bilgi
def chrome(sl: Slide, cx: Ctx, last: bool):
    st, meta = cx.st, cx.meta
    fe = cx.f("etiket").get(cx.o["etiket"])
    fb = cx.f("govde").get(cx.o["etiket"] + 2)
    fbb = cx.f("govde_kalin").get(cx.o["etiket"] + 2)
    yt, yb = 80, H - 78
    counter = f"{cx.idx:02d} / {cx.total:02d}" if st != "egitim" else f"{cx.idx} / {cx.total}"
    reklam = meta.get("reklam")
    # sol üst: reklam etiketi (varsa her slaytta) ya da seri adı
    if reklam:
        txt = f"{trtext.tr_upper(reklam.get('tur') or 'Reklam')} · {reklam.get('veren', '')}".strip(" ·")
        f = cx.f("etiket").get(cx.o["etiket"] + 3)
        tw = sl.tracked_width(txt, f, 0.06)
        sl.rect((M - 4, yt - 26, M + tw + 40, yt + 26), fill=cx.c("metin"), r=26)
        sl.text((M + 18, yt), txt, f, cx.c("zemin"), anchor="lm", tracking=0.06, name="reklam etiketi")
    elif meta.get("seri"):
        seri = trtext.tr_upper(meta["seri"])
        if st == "egitim":
            tw = sl.tracked_width(seri, fe, 0.1)
            sl.rect((M - 4, yt - 24, M + tw + 36, yt + 24), fill=cx.c("panel"), r=24)
            sl.text((M + 16, yt), seri, fe, cx.c("panel_metin"), anchor="lm", tracking=0.1, name="seri")
        else:
            sl.text((M, yt), seri, fe, cx.c("vurgu" if st == "editoryal" else "soluk"), anchor="lm", tracking=0.12,
                    name="seri")
    # sağ üst: sayfa
    if st == "egitim":
        tw = sl.tracked_width(counter, fe, 0.04)
        sl.rect((W - M - tw - 36, yt - 24, W - M + 4, yt + 24), fill=cx.c("panel"), r=24)
        sl.text((W - M - 16, yt), counter, fe, cx.c("panel_metin"), anchor="rm", tracking=0.04, name="sayfa")
    else:
        sl.text((W - M, yt), counter, fe, cx.c("soluk"), anchor="rm", tracking=0.08, name="sayfa")
    if st == "editoryal":
        sl.rect((M, 118, W - M, 120), fill=cx.c("cizgi"))
        sl.rect((M, H - 116, W - M, H - 113), fill=cx.c("cizgi"))
        sl.rect((M, H - 117, M + CW * cx.idx / cx.total, H - 112), fill=cx.c("vurgu"))
    # alt: hesap + kaydır
    cta_has_handle = last and trtext.fold(cx.sl.get("tip", "")) == "cta" and cx.sl.get("takip_metni") is not False
    if meta.get("hesap") and not cta_has_handle:
        sl.text((M, yb), meta["hesap"], fbb if st == "egitim" else fb, cx.c("metin" if st == "egitim" else "soluk"),
                anchor="lm", name="hesap")
    if not last:
        hook = cx.idx == 1
        txt = "Kaydır  →"
        if st == "egitim":
            tw = fbb.getlength(txt) / S
            sl.rect((W - M - tw - 40, yb - 26, W - M + 4, yb + 26), fill=cx.c("metin"), r=26)
            sl.text((W - M - 18, yb), txt, fbb, cx.c("zemin"), anchor="rm", name="kaydır")
        else:
            sl.text((W - M, yb), txt, fbb if hook else fb, cx.c("vurgu" if hook else "soluk"), anchor="rm",
                    name="kaydır")


# ---------------------------------------------------------------- yerleşim
def place(sl: Slide, cx: Ctx, top: List[Item], bottom: List[Item], valign="top") -> None:
    avail = BOT - TOP
    chosen = None
    for k in range(9):
        scale = 1.0 - 0.05 * k
        mt = [it.measure(cx, scale, CW) for it in top]
        mb = [it.measure(cx, scale, CW) for it in bottom]
        ht = sum(h for h, _ in mt)
        hb = sum(h for h, _ in mb) + (44 if bottom else 0)
        chosen = (mt, mb, ht, hb)
        if ht + hb <= avail:
            break
    mt, mb, ht, hb = chosen
    if ht + hb > avail:
        cx.notes.append(f"TAŞMA: slayt içeriği alana sığmadı ({int(ht + hb)} px > {avail} px); metni kısalt.")
    if valign == "center":
        y = TOP + max(0, (avail - hb - ht) * 0.44)
    else:
        y = TOP + (12 if cx.st != "editoryal" else 20)
    for h, draw in mt:
        draw(sl, M, y)
        y += h
    if mb:
        y = BOT - (hb - 44)
        for h, draw in mb:
            draw(sl, M, y)
            y += h


def number_badge(cx: Ctx, no, big=False) -> List[Item]:
    if no in (None, "", False):
        return []
    txt = f"{int(no):02d}" if str(no).isdigit() else str(no)
    if cx.st == "mercan":
        return [Text(txt, "sayi", cx.o["sayi_madde"], 90, color="vurgu", max_lines=1, name="numara"), Gap(34)]
    if cx.st == "editoryal":
        lab = cx.sl.get("no_etiket") or cx.meta.get("madde_etiketi") or ""
        return [rule_label(cx, f"{lab} {txt}".strip()), Gap(46)]
    return [circle_number(cx, str(int(no)) if str(no).isdigit() else str(no), 128), Gap(40)]


def big_number(cx: Ctx, txt: str) -> List[Item]:
    if cx.st == "egitim":
        return [circle_number(cx, txt, cx.o["sayi_kanca"] * 1.3, name="büyük sayı"), Gap(40)]
    color = "vurgu" if cx.st == "mercan" else "metin"
    items: List[Item] = [Text(txt, "sayi", cx.o["sayi_kanca"], 120, color=color, max_lines=1, lead=0.9,
                              name="büyük sayı")]
    if cx.st == "editoryal":
        items += [Gap(18), Custom(8, lambda sl, x, y, w, hh: sl.rect((x, y, x + 120, y + 8), fill=cx.c("vurgu")))]
    return items + [Gap(34)]


def headline(cx: Ctx, text: str, kanca=False, scale=1.0, name="başlık") -> Text:
    mx = (cx.o["kanca_max"] if kanca else cx.o["baslik_max"]) * scale
    return Text(text, "baslik", mx, cx.o["baslik_min"], balance=True, name=name, pref_lines=3)


def body(cx: Ctx, text: str, color="metin", k=1.0, name="metin") -> Text:
    return Text(text, "govde", cx.o["govde"] * k, cx.o["govde_min"], color=color, name=name)


# ---------------------------------------------------------------- düzenler
def lay_kanca(sl, cx):
    s = cx.sl
    top: List[Item] = []
    if s.get("ust"):
        top += [Label(s["ust"]), Gap(30)]
    if s.get("sayi"):
        top += big_number(cx, str(s["sayi"]))
    top.append(headline(cx, s.get("baslik", ""), kanca=True))
    if s.get("alt"):
        top += [Gap(46), body(cx, s["alt"], color="soluk", k=1.08, name="alt metin")]
    place(sl, cx, top, [], valign="center")


def lay_madde(sl, cx):
    s = cx.sl
    top: List[Item] = number_badge(cx, s.get("no"))
    top.append(headline(cx, s.get("baslik", "")))
    if s.get("metin"):
        top += [Gap(48), body(cx, s["metin"])]
    bottom: List[Item] = []
    if s.get("ipucu"):
        bottom.append(Panel(s.get("ipucu_etiket") or "İpucu", s["ipucu"], style="bar" if cx.st == "editoryal" else "box",
                            name="ipucu"))
    place(sl, cx, top, bottom, valign="center")


def lay_liste(sl, cx):
    s = cx.sl
    top: List[Item] = []
    if s.get("ust"):
        top += [Label(s["ust"]), Gap(26)]
    top += [headline(cx, s.get("baslik", ""), scale=0.86), Gap(62),
            Bullets([str(m) for m in s.get("maddeler") or []], mark=s.get("isaret", "tik"))]
    bottom: List[Item] = []
    if s.get("not"):
        bottom.append(body(cx, s["not"], color="soluk", k=0.82, name="not"))
    place(sl, cx, top, bottom, valign="center")


def lay_sayi(sl, cx):
    s = cx.sl
    top: List[Item] = []
    if s.get("ust"):
        top += [Label(s["ust"]), Gap(28)]
    top += big_number(cx, str(s.get("sayi", "")))
    top.append(headline(cx, s.get("baslik", ""), scale=0.9))
    if s.get("metin"):
        top += [Gap(30), body(cx, s["metin"])]
    bottom: List[Item] = []
    if s.get("kaynak"):
        bottom.append(Text("Kaynak: " + str(s["kaynak"]), "govde", 24, 20, color="soluk", name="kaynak"))
    place(sl, cx, top, bottom, valign="center")


def lay_karsilastirma(sl, cx):
    s = cx.sl
    top: List[Item] = number_badge(cx, s.get("no"))
    top += [headline(cx, s.get("baslik", ""), scale=0.88), Gap(40)]
    top.append(Panel(s.get("yanlis_etiket") or "Yanlış", s.get("yanlis", ""), bg="panel", fg="panel_metin",
                     label_color="soluk", icon="carpi", name="yanlış"))
    top.append(Gap(22))
    top.append(Panel(s.get("dogru_etiket") or "Doğru", s.get("dogru", ""), bg="vurgu", fg="vurgu_metin",
                     label_color="vurgu_metin", icon="tik", name="doğru"))
    place(sl, cx, top, [], valign="center")


CTA_DEFAULT = {
    "kaydet": ("Kaydet, *lazım olunca* aç.", "İşine yarayacak birine de gönder."),
    "paylas": ("Bunu *bilmesi gereken* birine gönder.", "Kaydetmeyi unutma."),
    "takip": ("Daha fazlası için *takip et.*", "Her hafta yeni bir liste."),
    "yorum": ("Yoruma yaz, *göndereyim.*", ""),
}


def lay_cta(sl, cx):
    s = cx.sl
    tur = trtext.fold(s.get("tur") or "kaydet").replace("ş", "s")
    tur = {"paylas": "paylas", "kaydet": "kaydet", "yorum": "yorum", "takip": "takip"}.get(tur, "kaydet")
    t0, m0 = CTA_DEFAULT[tur]
    top: List[Item] = []
    al = "center" if cx.st == "egitim" else "left"

    def ic(sl_, x, y, w, hh):
        xx = x + (w - hh) / 2 if al == "center" else x
        icon(sl_, tur, xx, y, hh, cx.c("vurgu"))
    top += [Custom(132, ic), Gap(48)]
    if tur == "yorum":
        key = str(s.get("anahtar") or "").strip()
        top.append(Text(s.get("baslik") or "Yoruma şunu yaz:", "baslik", cx.o["kanca_max"] * 0.7, cx.o["baslik_min"],
                        balance=True, align=al, name="başlık"))
        top += [Gap(46), keyword_pill(cx, key or "?"), Gap(42)]
        metin = s.get("metin") or (f"{s['vaat']} DM'den göndereyim." if s.get("vaat") else "")
    else:
        top.append(Text(s.get("baslik") or t0, "baslik", cx.o["kanca_max"] * 0.82, cx.o["baslik_min"], balance=True,
                        align=al, name="başlık"))
        top.append(Gap(36))
        metin = s.get("metin") or m0
    if metin:
        top.append(Text(metin, "govde", cx.o["govde"] * 1.1, cx.o["govde_min"], color="soluk", align=al,
                        name="metin"))
    bottom: List[Item] = []
    hesap = s.get("hesap") or cx.meta.get("hesap")
    if hesap and s.get("takip_metni") is not False:
        bottom.append(Text(f"{hesap}" + (f"  ·  {s['takip_metni']}" if s.get("takip_metni") else ""), "govde_kalin",
                           34, 24, color="metin", align=al, name="hesap (cta)"))
    place(sl, cx, top, bottom, valign="center")


LAYOUTS = {"kanca": lay_kanca, "madde": lay_madde, "liste": lay_liste, "sayi": lay_sayi,
           "karsilastirma": lay_karsilastirma, "cta": lay_cta}


def render(sl_spec: Dict, idx: int, total: int, tpl: Dict, pal: Dict, meta: Dict) -> Tuple[Slide, List[str]]:
    cx = Ctx(tpl, pal, idx, total, meta, sl_spec)
    sl = Slide(pal["zemin"])
    tip = trtext.fold(sl_spec.get("tip", "madde"))
    LAYOUTS.get(tip, lay_madde)(sl, cx)
    chrome(sl, cx, last=(idx == total))
    issues = cx.notes + sl.check()
    return sl, issues
