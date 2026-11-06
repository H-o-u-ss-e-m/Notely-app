import pytest
from app.domain.text_postprocess import match_case, postprocess_line
from app.ml.engines.base import LineOut, WordOut


def test_match_case():
    assert match_case("dérivable", "derivable") == "dérivable"
    assert match_case("dérivable", "Derivable") == "Dérivable"
    assert match_case("dérivable", "DERIVABLE") == "DÉRIVABLE"


def test_apply_user_dictionary_in_postprocess():
    words = [
        WordOut(index=0, text="derivable", confidence=0.70),  # < 0.85 et récurrent
        WordOut(index=1, text="continues", confidence=0.98),  # confiance très haute (ne pas écraser)
    ]
    line = LineOut(text="derivable continues", confidence=0.84, min_word_confidence=0.70, words=words)

    # Substitution enregistrée avec count=2
    user_subs = {
        "derivable": ("dérivable", 2),
        "continues": ("continuelle", 2),
    }

    out = postprocess_line(line, lang="fr", user_subs=user_subs)
    # Le premier mot doit être corrigé
    assert out.words[0].text == "dérivable"
    assert out.words[0].corrected is True
    assert out.words[0].original == "derivable"

    # Le second mot ne doit pas être écrasé car sa confiance (0.98) >= conf_ceiling (0.85)
    assert out.words[1].text == "continues"
    assert out.words[1].corrected is False
