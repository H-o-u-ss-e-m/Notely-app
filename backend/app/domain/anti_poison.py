"""
Filtres qualité et anti-poison pour les corrections OCR (ML-5 / ML-6 / §8.6.b).
Empêche l'empoisonnement du dictionnaire et des jeux d'entraînement
par des corrections abusives, du spam ou des réécritures complètes.
"""
import re
from typing import Tuple


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


def validate_correction(
    predicted_text: str,
    corrected_text: str,
    max_cer: float = 0.6,
    max_len: int = 300,
) -> Tuple[bool, str]:
    """
    Valide une correction OCR avant enregistrement :
    - Longueur entre 1 et max_len
    - Anti-spam (pas de motifs destructeurs)
    - CER <= max_cer sauf si le texte prédit est très court (<= 3 caractères)
    """
    c = corrected_text.strip()
    if not c:
        return False, "Le texte corrigé ne peut pas être vide."

    if len(c) > max_len:
        return False, f"La correction dépasse la taille maximale autorisée ({max_len} caractères)."

    if looks_like_spam(c):
        return False, "La correction a été rejetée par le filtre anti-spam."

    p = predicted_text.strip()
    # Si le texte prédit a au moins 4 caractères, vérifier que ce n'est pas une réécriture totale
    if len(p) >= 4:
        cer = char_error_rate(p, c)
        if cer > max_cer:
            return False, f"CER trop élevé ({cer:.2f} > {max_cer:.2f}) : réécriture excessive rejetée."

    return True, "OK"
