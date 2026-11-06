"""
Métriques HTR — CER, WER, accent_error_rate et métriques de calibration.
Calcul en Python pur (sans dépendance obligatoire externe).
"""
import difflib
import unicodedata
from typing import List


def _edit_distance_chars(a: str, b: str) -> int:
    """Distance de Levenshtein entre deux chaînes de caractères."""
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if la == 0:
        return lb
    if lb == 0:
        return la
    prev = list(range(lb + 1))
    for i, ca in enumerate(a, 1):
        curr = [i] + [0] * lb
        for j, cb in enumerate(b, 1):
            curr[j] = min(
                prev[j] + 1,                           # suppression
                curr[j - 1] + 1,                       # insertion
                prev[j - 1] + (0 if ca == cb else 1),  # substitution
            )
        prev = curr
    return prev[lb]


def _edit_distance_words(r_words: List[str], h_words: List[str]) -> int:
    """Distance de Levenshtein au niveau des mots."""
    lr, lh = len(r_words), len(h_words)
    if lr == 0:
        return lh
    if lh == 0:
        return lr
    prev = list(range(lh + 1))
    for rw in r_words:
        curr = [prev[0] + 1] + [0] * lh
        for j, hw in enumerate(h_words, 1):
            curr[j] = min(
                prev[j] + 1,
                curr[j - 1] + 1,
                prev[j - 1] + (0 if rw == hw else 1),
            )
        prev = curr
    return prev[lh]


def cer(references: List[str], hypotheses: List[str]) -> float:
    """
    Character Error Rate moyen sur une liste d'exemples.
    Retourne 0.0 si la liste est vide.
    """
    if not references:
        return 0.0
    total_dist = sum(
        _edit_distance_chars(r, h) for r, h in zip(references, hypotheses)
    )
    total_chars = sum(len(r) for r in references)
    return total_dist / total_chars if total_chars > 0 else 0.0


def wer(references: List[str], hypotheses: List[str]) -> float:
    """
    Word Error Rate moyen sur une liste d'exemples.
    Retourne 0.0 si la liste est vide.
    """
    if not references:
        return 0.0
    total_dist = 0
    total_words = 0
    for r, h in zip(references, hypotheses):
        rw = r.split()
        hw = h.split()
        total_dist += _edit_distance_words(rw, hw)
        total_words += len(rw)
    return total_dist / total_words if total_words > 0 else 0.0


def empty_rate(hypotheses: List[str]) -> float:
    """Taux de lignes vides (modèle n'a rien reconnu)."""
    if not hypotheses:
        return 0.0
    return sum(1 for h in hypotheses if not h.strip()) / len(hypotheses)


def accent_error_rate(hypotheses: List[str], references: List[str]) -> float:
    """
    Proportion de caractères accentués de la référence mal transcrits (plan §8.9).
    """
    def accented(c: str) -> bool:
        return unicodedata.normalize("NFD", c)[1:] != ""

    total = 0
    bad = 0
    for p, r in zip(hypotheses, references):
        sm = difflib.SequenceMatcher(None, p, r)
        ok = {j for blk in sm.get_matching_blocks() for j in range(blk.b, blk.b + blk.size)}
        for j, ch in enumerate(r):
            if accented(ch):
                total += 1
                if j not in ok:
                    bad += 1
    return bad / total if total > 0 else 0.0
