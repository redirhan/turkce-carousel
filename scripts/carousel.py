#!/usr/bin/env python3
"""Türkçe Carousel Üretici — slayt planı (YAML/JSON) -> 1080x1350 PNG serisi + LinkedIn PDF + caption.

Kullanım:
    python3 carousel.py doctor
    python3 carousel.py sablonlar
    python3 carousel.py yeni "Vize haftası için 5 dakikalık plan" --sablon koyu-mercan --kalip adim > plan.yaml
    python3 carousel.py kontrol plan.yaml           # yalnız metin kuralları (hızlı)
    python3 carousel.py render plan.yaml --cikti carousel_cikti/
    python3 carousel.py caption plan.yaml           # yalnız açıklama metni
Hepsi yerel çalışır: yayın yok, hesap yok, ücretli API yok, tarayıcı yok.
Çıkış kodu: 0 = temiz, 1 = plan hatası, 2 = çizimde taşma/çakışma (metni kısalt, yeniden çiz).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

ROOT = HERE.parent
VERSION = (ROOT / "VERSION").read_text().strip() if (ROOT / "VERSION").is_file() else "dev"


def _deps():
    try:
        import PIL  # noqa: F401
        import numpy  # noqa: F401
    except ImportError as e:
        raise SystemExit(f"Eksik paket: {e.name}. Kur: pip install -r {ROOT / 'requirements.txt'}")


# ---------------------------------------------------------------- çıktılar
def write_pdf(pngs, out: Path) -> str:
    try:
        import img2pdf
        layout = img2pdf.get_fixed_dpi_layout_fun((72, 72))   # 1 px = 1 pt -> 1080x1350 pt sayfa
        out.write_bytes(img2pdf.convert([str(p) for p in pngs], layout_fun=layout))
        return "img2pdf (kayıpsız)"
    except ImportError:
        pass
    try:
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(str(out), pagesize=(1080, 1350))
        for p in pngs:
            c.drawImage(str(p), 0, 0, 1080, 1350)
            c.showPage()
        c.save()
        return "reportlab"
    except ImportError:
        pass
    from PIL import Image
    ims = [Image.open(p).convert("RGB") for p in pngs]
    ims[0].save(out, save_all=True, append_images=ims[1:], resolution=72, quality=95)
    return "Pillow (JPEG sıkıştırmalı; kayıpsız PDF için: pip install img2pdf)"


def contact_sheet(pngs, out: Path, cols=5):
    from PIL import Image
    tw, th, g = 324, 405, 18
    rows = (len(pngs) + cols - 1) // cols
    cols = min(cols, len(pngs))
    sh = Image.new("RGB", (cols * tw + (cols + 1) * g, rows * th + (rows + 1) * g), (120, 120, 120))
    for i, p in enumerate(pngs):
        im = Image.open(p).resize((tw, th), Image.LANCZOS)
        sh.paste(im, (g + (i % cols) * (tw + g), g + (i // cols) * (th + g)))
    sh.save(out, quality=88)


def render_plan(plan_path: str, out_dir: str, sablon: str | None = None, quiet=False, pdf=True) -> int:
    _deps()
    import caption as C
    import layouts
    import spec as SP
    d = SP.load(plan_path)
    if sablon:
        d["sablon"] = SP.trtext.slug(sablon)
    err, warn = SP.lint(d)
    if err:
        print("PLAN HATALARI (çizilmedi):")
        for e in err:
            print("  ✗", e)
        for w in warn:
            print("  !", w)
        return 1
    tpl = SP.template(d["sablon"])
    pals = SP.palettes_for(d, tpl)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("[0-9][0-9].png"):
        old.unlink()
    meta = {"hesap": d.get("hesap"), "seri": d.get("seri"), "reklam": d.get("reklam"),
            "madde_etiketi": d.get("madde_etiketi")}
    total = len(d["slaytlar"])
    pngs, problems = [], []
    for i, (s, pal) in enumerate(zip(d["slaytlar"], pals), 1):
        sl, issues = layouts.render(s, i, total, tpl, pal, meta)
        p = out / f"{i:02d}.png"
        sl.save(p)
        pngs.append(p)
        for m in issues:
            problems.append(f"Slayt {i:02d}: {m}")
    name = SP.trtext.slug(d.get("konu") or Path(plan_path).stem)
    pdf_note = write_pdf(pngs, out / f"{name}.pdf") if pdf else "atlandı"
    contact_sheet(pngs, out / "onizleme.jpg")
    cap, cwarn = C.build(d)
    (out / "caption.txt").write_text(cap, encoding="utf-8")
    (out / "alt_metin.txt").write_text(C.alt_texts(d), encoding="utf-8")
    if d.get("reklam"):
        (out / "reklam_kontrol.yaml").write_text(C.reklam_yaml(d, cap), encoding="utf-8")
    notes = [p for p in problems if p.split(": ", 1)[1].startswith("NOT")]
    hard = [p for p in problems if p not in notes]
    lines = [f"Türkçe Carousel Üretici {VERSION}", f"plan: {plan_path}", f"şablon: {tpl['ad']}",
             f"slayt: {total} x 1080x1350 PNG", f"PDF: {pdf_note}", ""]
    lines += ["UYARILAR:"] + [f"  ! {w}" for w in warn + cwarn] if (warn or cwarn) else ["UYARI YOK"]
    lines += [""] + (["ÇİZİM SORUNLARI (metni kısalt ya da böl, yeniden çiz):"] + [f"  ✗ {p}" for p in hard]
                     if hard else ["ÇİZİM KONTROLÜ: taşma yok, çakışma yok, kenar payları tamam."])
    if notes:
        lines += ["", "NOTLAR:"] + [f"  · {p.replace('NOT: ', '')}" for p in notes]
    lines += ["", "Şimdi slaytlara tek tek gözle bak (onizleme.jpg + her PNG)."]
    (out / "rapor.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if not quiet:
        print("\n".join(lines))
        print(f"\nçıktı: {out}/  (01..{total:02d}.png, {name}.pdf, caption.txt, alt_metin.txt, onizleme.jpg, rapor.txt"
              + (", reklam_kontrol.yaml" if d.get("reklam") else "") + ")")
    return 2 if hard else 0


# ---------------------------------------------------------------- komutlar
def cmd_doctor(a) -> int:
    ok = True
    print(f"Türkçe Carousel Üretici {VERSION}")
    print(f"python {sys.version.split()[0]}")
    for mod, need in (("PIL", True), ("numpy", True), ("yaml", False), ("img2pdf", False), ("reportlab", False)):
        try:
            m = __import__(mod)
            print(f"  ✓ {mod} {getattr(m, '__version__', '')}")
        except ImportError:
            print(f"  {'✗' if need else '·'} {mod} yok" + ("" if need else " (isteğe bağlı)"))
            ok = ok and not need
    if not ok:
        print(f"Kur: pip install -r {ROOT / 'requirements.txt'}")
        return 1
    import engine
    import spec as SP
    import trtext
    assert trtext.tr_upper("istanbul'da ışık ilk iğne") == "İSTANBUL'DA IŞIK İLK İĞNE"
    assert trtext.tr_lower("IŞIK İLK") == "ışık ilk"
    print("  ✓ tr_upper / tr_lower (istanbul -> İSTANBUL, IŞIK -> ışık)")
    probe = "ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZ abcçdefgğhıijklmnoöprsştuüvyz ÂâÎîÛû 0123456789 %₺.,:;!?'’“”—–·→"
    for name, tpl in SP.templates().items():
        for role, fd in tpl["fontlar"].items():
            fs = engine.FontSpec.of(fd)
            p = engine.FONTS / fs.file
            if not p.is_file():
                print(f"  ✗ {name}: {fd['dosya']} yok")
                ok = False
                continue
            miss = engine.missing_glyphs(fs, probe)
            if miss and role != "yedek":
                print(f"  ! {name}/{role}: {fs.file} içinde {''.join(miss)} yok (yedek font devreye girer)")
        print(f"  ✓ şablon {name}")
    lic = sorted(x.name for x in engine.FONTS.glob("OFL-*.txt"))
    print(f"  ✓ font lisansları: {', '.join(lic)}")
    print("Hazır." if ok else "Eksikler var.")
    return 0 if ok else 1


def cmd_sablonlar(a) -> int:
    import spec as SP
    for name, t in SP.templates().items():
        print(f"{name:16s} {t['gorunen_ad']}: {t['aciklama']}")
    print("\nPro şablon paketi (20 şablon: eğitim, ürün, ajans vaka, önce/sonra, alıntı...): yakında.")
    return 0


def cmd_yeni(a) -> int:
    import spec as SP
    sys.stdout.write(SP.skeleton(a.konu, SP.trtext.slug(a.sablon), a.slayt, a.kalip, a.cta, a.hesap))
    return 0


def cmd_kontrol(a) -> int:
    import caption as C
    import spec as SP
    d = SP.load(a.plan)
    err, warn = SP.lint(d)
    _, cw = C.build(d)
    for e in err:
        print("  ✗", e)
    for w in warn + cw:
        print("  !", w)
    if not err and not warn and not cw:
        print("Plan kurallara uygun.")
    return 1 if err else 0


def cmd_caption(a) -> int:
    import caption as C
    import spec as SP
    d = SP.load(a.plan)
    text, warn = C.build(d)
    sys.stdout.write(text)
    for w in warn:
        print("!", w, file=sys.stderr)
    return 0


def cmd_render(a) -> int:
    return render_plan(a.plan, a.cikti, a.sablon, pdf=not a.pdf_yok)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="carousel.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", action="version", version=VERSION)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor", help="kurulum, font ve Türkçe harf testi").set_defaults(fn=cmd_doctor)
    sub.add_parser("sablonlar", help="şablonları listele").set_defaults(fn=cmd_sablonlar)
    p = sub.add_parser("yeni", help="konudan boş slayt planı (iskelet) yaz")
    p.add_argument("konu")
    p.add_argument("--sablon", default="koyu-mercan")
    p.add_argument("--slayt", type=int, default=7)
    p.add_argument("--kalip", choices=["liste", "adim", "hata"], default="liste")
    p.add_argument("--cta", choices=["kaydet", "paylas", "yorum", "takip"], default="kaydet")
    p.add_argument("--hesap", default="@hesabin")
    p.set_defaults(fn=cmd_yeni)
    p = sub.add_parser("kontrol", help="planı kurallara göre denetle (çizmeden)")
    p.add_argument("plan")
    p.set_defaults(fn=cmd_kontrol)
    p = sub.add_parser("caption", help="yalnız gönderi açıklamasını yaz")
    p.add_argument("plan")
    p.set_defaults(fn=cmd_caption)
    p = sub.add_parser("render", help="PNG + PDF + caption + rapor")
    p.add_argument("plan")
    p.add_argument("--cikti", default="carousel_cikti")
    p.add_argument("--sablon", default=None, help="plandaki şablonu geçersiz kıl")
    p.add_argument("--pdf-yok", action="store_true")
    p.set_defaults(fn=cmd_render)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
