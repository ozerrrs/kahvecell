"""Türkçe dostu metin normalleştirme (arama için)."""

_TR_LOWER = str.maketrans({"I": "ı", "İ": "i"})
_ASCII_FOLD = str.maketrans({"ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u", "â": "a", "î": "i", "û": "u"})


def fold_text(value: str | None) -> str:
    """'KIZILAY Meydanı' → 'kizilay meydani'.

    Türkçe büyük/küçük harf kuralları uygulanır ve Türkçe karakterler sadeleştirilir;
    böylece 'kizilay', 'Kızılay' ve 'KIZILAY' aynı sonucu bulur.
    """
    if not value:
        return ""
    lowered = value.translate(_TR_LOWER).lower()
    return " ".join(lowered.translate(_ASCII_FOLD).split())
