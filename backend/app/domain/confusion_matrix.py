"""
Analyseur de matrice de confusion de caractères (ML-5 / §8.5.d).
Identifie les 30 confusions les plus fréquentes (ex. e -> é, c -> ç, u -> n)
à partir des corrections enregistrées pour orienter les améliorations futures.
"""
import difflib
from collections import Counter
from typing import List, Tuple, Dict, Any


def compute_char_confusions(pairs: List[Tuple[str, str]], top_k: int = 30) -> List[Dict[str, Any]]:
    """
    Extrait les substitutions de caractères les plus fréquentes entre prédictions et corrections.
    """
    counter: Counter = Counter()
    for pred, true in pairs:
        if not pred or not true:
            continue
        sm = difflib.SequenceMatcher(None, pred, true)
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == "replace" and (i2 - i1) == (j2 - j1):
                for a, b in zip(pred[i1:i2], true[j1:j2]):
                    if a != b:
                        counter[(a, b)] += 1

    return [
        {"predicted": pair[0], "corrected": pair[1], "count": count}
        for pair, count in counter.most_common(top_k)
    ]
