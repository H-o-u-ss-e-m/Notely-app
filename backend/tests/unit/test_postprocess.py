import pytest
from app.ml.engines.base import LineOut, WordOut
from app.domain.text_postprocess import (
    postprocess_line,
    normalize_unicode,
    apply_french_typography,
)


def test_normalize_unicode():
    text = "Bonjour   le   monde "
    assert normalize_unicode(text) == "Bonjour le monde"


def test_apply_french_typography():
    # Espace avant deux-points et point d'interrogation
    text = "Attention: vrai?"
    assert apply_french_typography(text) == "Attention : vrai ?"

    # Ligature coeur -> cœur
    assert apply_french_typography("mon coeur") == "mon cœur"


def test_postprocess_line_french_accents():
    words = [
        WordOut(index=0, text="Les", confidence=0.9),
        WordOut(index=1, text="fonctions", confidence=0.9),
        WordOut(index=2, text="derivables", confidence=0.7),
        WordOut(index=3, text="sont", confidence=0.9),
        WordOut(index=4, text="continues", confidence=0.9),
    ]
    line = LineOut(
        text="Les fonctions derivables sont continues",
        confidence=0.86,
        min_word_confidence=0.7,
        words=words,
    )

    out = postprocess_line(line, lang="fr", auto_correct_accents=True)
    assert "dérivables" in out.text
    assert out.words[2].text == "dérivables"
    assert out.words[2].corrected is True
    assert "dérivables" in out.words[2].alternatives
