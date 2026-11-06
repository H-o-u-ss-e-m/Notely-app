"""
Filtres qualité et anti-poison pour les corrections OCR (ML-5 / ML-6 / §8.6.b & Plan v2 §1.5).
Empêche l'empoisonnement du dictionnaire et des jeux d'entraînement
par des corrections abusives, du spam ou des réécritures complètes,
tout en acceptant les corrections légitimes lorsque le moteur ne supporte pas
encore nativement la langue (ex: arabe) ou a une confiance faible (< 0.5).
"""
import re
from typing import Optional, Tuple, Union

# Langues supportées nativement par les moteurs locaux configurés dans models.yaml
SUPPORTED_ENGINE_LANGUAGES = {"fr", "en", "de"}


def char_error_rate(reference: str, hypothesis: str) -> float:
    """
    Calcule le taux d'erreur caractère (CER) entre deux chaînes via Levenshtein.
    """
    if not reference:
        return 1.0 if hypothesis else 0.0
    if not hypothesis:
        return 1.0

    r_len = len(reference)
    h_len = len(hypothesis)

    dp = [[0] * (h_len + 1) for _ in range(r_len + 1)]
    for i in range(r_len + 1):
        dp[i][0] = i
    for j in range(h_len + 1):
        dp[0][j] = j

    for i in range(1, r_len + 1):
        for j in range(1, h_len + 1):
            cost = 0 if reference[i - 1] == hypothesis[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,       # suppression
                dp[i][j - 1] + 1,       # insertion
                dp[i - 1][j - 1] + cost  # substitution
            )

    dist = dp[r_len][h_len]
    return float(dist) / float(r_len)


def looks_like_spam(text: str) -> bool:
    """
    Détecte les motifs de spam ou de dégradation délibérée :
    - Répétition excessive (> 8 fois le même caractère d'affilée)
    - Caractères de contrôle non imprimables
    - Chaîne vide ou uniquement des espaces
    """
    s = text.strip()
    if not s:
        return True

    # Répétitions excessives d'un même caractère (ex: 'aaaaaaaaa' ou '!!!!!!!')
    if re.search(r"(.)\1{7,}", s):
        return True

    # Caractères de contrôle dangereux (hors retours à la ligne standard \n, \r, \t)
    for ch in s:
        code = ord(ch)
        if (code < 32 and ch not in "\n\r\t") or (127 <= code <= 159):
            return True

    return False


def should_reject(
    predicted: str,
    corrected: str,
    lang: str = "fr",
    engine_supports_lang: Optional[bool] = None,
    confidence: Optional[float] = None,
    max_cer: float = 0.60,
) -> bool:
    """
    Détermine si une correction doit être rejetée pour écart excessif (CER > max_cer).
    Si le moteur ne supporte pas la langue (ex: arabe sur TrOCR latin) ou si la confiance
    du modèle est faible (< 0.5), la prédiction initiale n'est pas fiable : on accepte la correction.
    """
    lang_norm = (lang or "fr").lower().strip()
    if engine_supports_lang is None:
        engine_supports_lang = lang_norm in SUPPORTED_ENGINE_LANGUAGES

    if not engine_supports_lang or (confidence is not None and confidence < 0.5):
        return False

    c = corrected.strip()
    p = predicted.strip()
    if len(c) <= 3 or len(p) <= 3:
        return False

    return char_error_rate(p, c) > max_cer


def validate_correction(
    predicted_text: str,
    corrected_text: str,
    max_cer: float = 0.6,
    max_len: int = 300,
    lang: str = "fr",
    engine_supports_lang: Optional[bool] = None,
    confidence: Optional[float] = None,
    return_code: bool = False,
) -> Union[Tuple[bool, str], Tuple[bool, str, str]]:
    """
    Valide une correction OCR avant enregistrement :
    - Longueur entre 1 et max_len
    - Anti-spam (pas de motifs destructeurs)
    - CER <= max_cer (sauf moteur non supporté pour la langue, confiance < 0.5 ou mot <= 3 caracs)
    Codes lisibles : OK, EMPTY_CORRECTION, CORRECTION_TOO_LONG, SPAM, CORRECTION_TOO_FAR.
    """
    c = corrected_text.strip()
    if not c:
        msg = "Le texte corrigé ne peut pas être vide."
        return (False, msg, "EMPTY_CORRECTION") if return_code else (False, msg)

    if len(c) > max_len:
        msg = f"La correction dépasse la taille maximale autorisée ({max_len} caractères)."
        return (False, msg, "CORRECTION_TOO_LONG") if return_code else (False, msg)

    if looks_like_spam(c):
        msg = "La correction a été rejetée par le filtre anti-spam."
        return (False, msg, "SPAM") if return_code else (False, msg)

    p = predicted_text.strip()
    if should_reject(
        predicted=p,
        corrected=c,
        lang=lang,
        engine_supports_lang=engine_supports_lang,
        confidence=confidence,
        max_cer=max_cer,
    ):
        cer = char_error_rate(p, c)
        msg = f"CER trop élevé ({cer:.2f} > {max_cer:.2f}) : réécriture excessive rejetée."
        return (False, msg, "CORRECTION_TOO_FAR") if return_code else (False, msg)

    return (True, "OK", "OK") if return_code else (True, "OK")
