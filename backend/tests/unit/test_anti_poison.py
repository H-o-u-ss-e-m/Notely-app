import pytest
from app.domain.anti_poison import char_error_rate, looks_like_spam, validate_correction


def test_char_error_rate():
    assert char_error_rate("bonjour", "bonjour") == 0.0
    assert char_error_rate("", "") == 0.0
    assert char_error_rate("bonjour", "") == 1.0
    assert char_error_rate("", "bonjour") == 1.0
    # 1 substitution sur 4 lettres = 0.25
    assert char_error_rate("chat", "char") == 0.25


def test_looks_like_spam():
    assert looks_like_spam("") is True
    assert looks_like_spam("   ") is True
    assert looks_like_spam("aaaaaaaaaa") is True  # > 7 répétitions
    assert looks_like_spam("bonjour!!!!!!") is False  # 6 répétitions
    assert looks_like_spam("bonjour!!!!!!!!") is True  # 8 répétitions
    assert looks_like_spam("bonjour \x00 monde") is True  # caractère de contrôle non printable
    assert looks_like_spam("dérivable continue") is False


def test_validate_correction():
    # Correction valide
    ok, msg = validate_correction("derivable", "dérivable")
    assert ok is True

    # Correction vide
    ok, msg = validate_correction("mot", "")
    assert ok is False

    # Correction trop longue
    ok, msg = validate_correction("a", "a" * 350)
    assert ok is False

    # Spam
    ok, msg = validate_correction("mot", "zzzzzzzzzz")
    assert ok is False

    # Réécriture complète (CER > 0.6)
    ok, msg = validate_correction("dérivable continue", "intégrale de Riemann divergente")
    assert ok is False
    assert "CER trop élevé" in msg
