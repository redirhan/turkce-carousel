"""Türkçe metin yardımcıları: büyük/küçük harf (İ/ı), sade karşılaştırma, satır bölme kuralları.

Python'un str.upper() / str.lower() fonksiyonları Türkçe değildir:
    "istanbul".upper()  -> "ISTANBUL"   (yanlış, doğrusu İSTANBUL)
    "IŞIK".lower()      -> "işik"       (yanlış, doğrusu ışık)
    "İ".lower()         -> "i̇"          (i + birleşik nokta, görünmez hata)
"""
from __future__ import annotations

import re
import unicodedata

LETTERS = "A-Za-zÇĞİÖŞÜçğıöşüÂâÎîÛû"


def tr_upper(s: str) -> str:
    """tr_upper("istanbul'da ışık") == "İSTANBUL'DA IŞIK"."""
    return s.replace("i", "İ").replace("ı", "I").upper()


def tr_lower(s: str) -> str:
    """tr_lower("IŞIK İLK") == "ışık ilk" (birleşik nokta bırakmaz)."""
    return s.replace("I", "ı").replace("İ", "i").lower().replace("i̇", "i")


def fold(s: str) -> str:
    """Karşılaştırma için sade biçim: "Açık-Editoryal" -> "acik-editoryal"."""
    s = tr_lower(s).replace("ı", "i")
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).strip()


def slug(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", fold(s)).strip("-")
    return s[:60] or "carousel"


def plain(s: str) -> str:
    """Vurgu işaretlerini (*...*) ve satır sonlarını temizler."""
    return re.sub(r"\s+", " ", str(s or "").replace("*", "")).strip()


def words(s: str) -> list:
    return [w for w in re.split(r"\s+", plain(s)) if w]


# Satır sonunda kalmaması gerekenler (bir sonraki kelimeye bağlı).
BAD_END = {"ve", "ile", "veya", "ya", "ama", "fakat", "ancak", "çünkü", "bir", "en", "çok", "daha", "yüzde", "her",
           "bu", "şu", "o", "hem", "ne"}
# Satır başına düşmemesi gerekenler (önceki kelimeye bağlı).
CLITIC = {"de", "da", "ki", "mi", "mı", "mu", "mü", "gibi", "kadar", "için", "diye", "dek", "değil"}
# Sayıdan ayrılmaması gereken birimler.
UNITS = {"tl", "₺", "lira", "dolar", "euro", "dakika", "dk", "saniye", "sn", "saat", "gün", "hafta", "ay", "yıl",
         "kg", "gr", "km", "m", "cm", "mm", "adım", "kat", "%"}


def bare(w: str) -> str:
    return re.sub(rf"[^{LETTERS}0-9₺%]", "", tr_lower(w))


def bad_break(prev_word: str, next_word: str) -> bool:
    """prev_word ile next_word arasında satır bölmek Türkçede kötü mü?"""
    p, n = bare(prev_word), bare(next_word)
    if p in BAD_END and not re.search(r"[,.;:!?]$", prev_word):
        return True
    if n in CLITIC:
        return True
    if re.fullmatch(r"[0-9.,%]+", p) and n in UNITS:
        return True
    return False


def smart_quotes(s: str) -> str:
    """Düz tırnakları dizgi tırnağına çevirir: "DM" -> “DM”, DM'den -> DM’den."""
    out, open_q = [], True
    for i, ch in enumerate(s):
        if ch == '"':
            out.append("“" if open_q else "”")
            open_q = not open_q
        elif ch == "'":
            prev = s[i - 1] if i else " "
            out.append("’" if prev.strip() else "‘")
        else:
            out.append(ch)
    return "".join(out)


def has_combining_dot(s: str) -> bool:
    """Python lower() kalıntısı 'i̇' (i + U+0307) var mı?"""
    return "̇" in str(s or "")


def looks_all_caps(s: str) -> bool:
    """En az iki 'gerçek' kelime (3+ harf) var ve hepsi büyük harf mi? (Formüller, kısaltmalar sayılmaz.)"""
    ws = [w for w in re.findall(rf"[{LETTERS}]{{3,}}", plain(s))]
    return len(ws) >= 2 and all(w.isupper() for w in ws)
