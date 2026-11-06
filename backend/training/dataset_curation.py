"""
Curation et préparation du jeu d'entraînement HTR (ML-6 / §8.6).
- Filtres qualité stricts (consentement, anti-poison, plafond 5% par utilisateur).
- Rendu vectoriel identique à la production (RenderConfig).
- Split par page déterministe (jamais par ligne).
- Déclenchement conditionnel (≥ 500 corrections validées).
"""
import hashlib
from typing import List, Dict, Any, Tuple
from collections import Counter

from app.domain.anti_poison import char_error_rate, looks_like_spam


def split_of(page_id: str) -> str:
    """
    Règle d'or (§8.6.c) : split par page ou par utilisateur, jamais par ligne.
    Empêche toute fuite de données entre train, val et test.
    """
    h = int(hashlib.sha256(str(page_id).encode("utf-8")).hexdigest(), 16) % 100
    if h < 10:
        return "test"
    elif h < 20:
        return "val"
    return "train"


def filter_and_curate_corrections(
    corrections: List[Dict[str, Any]],
    max_user_share: float = 0.05,
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """
    Filtre les corrections brutes pour constituer le dataset d'entraînement (§8.6.b) :
    1. Consentement actif (consent_train=True, consent_withdrawn_at IS NULL).
    2. Présence obligatoire des tracés vectoriels (strokes_json).
    3. Longueur raisonnable (1 <= len <= 300).
    4. CER <= 0.60 (sauf mots courts <= 3 caractères).
    5. Absence de spam / répétition abusive.
    6. Plafonnement de l'influence par utilisateur (user_contribution_share <= 5%).
    7. Dédoublonnage par empreinte de tracés.
    """
    stats = {
        "total_in": len(corrections),
        "rejected_no_consent": 0,
        "rejected_no_strokes": 0,
        "rejected_length": 0,
        "rejected_cer": 0,
        "rejected_spam": 0,
        "rejected_duplicate": 0,
        "rejected_user_cap": 0,
        "accepted": 0,
    }

    # 1. Pré-filtrage qualitatif individuel
    preliminary: List[Dict[str, Any]] = []
    seen_fingerprints = set()

    for c in corrections:
        if not c.get("consent_train") or c.get("consent_withdrawn_at") is not None:
            stats["rejected_no_consent"] += 1
            continue

        strokes = c.get("strokes_json") or c.get("strokes")
        if not strokes:
            stats["rejected_no_strokes"] += 1
            continue

        text_corr = (c.get("corrected_text") or c.get("line_corrected") or "").strip()
        if not (1 <= len(text_corr) <= 300):
            stats["rejected_length"] += 1
            continue

        text_pred = (c.get("predicted_text") or c.get("line_predicted") or "").strip()
        # Règle CER avec exemption des mots <= 3 caracs
        if len(text_pred) > 3:
            err = char_error_rate(text_pred, text_corr)
            if err > 0.60:
                stats["rejected_cer"] += 1
                continue

        if looks_like_spam(text_corr):
            stats["rejected_spam"] += 1
            continue

        fp = c.get("stroke_fingerprint") or ""
        if fp:
            if fp in seen_fingerprints:
                stats["rejected_duplicate"] += 1
                continue
            seen_fingerprints.add(fp)

        preliminary.append(c)

    # 2. Application du filtre anti-poison de contribution par utilisateur (user_contribution_share <= 5 %)
    total_valid = len(preliminary)
    if total_valid == 0:
        return [], stats

    user_counts = Counter(c.get("user_id") for c in preliminary)
    max_allowed = max(1, int(total_valid * max_user_share))

    accepted: List[Dict[str, Any]] = []
    user_accepted = Counter()

    for c in preliminary:
        uid = c.get("user_id")
        if user_accepted[uid] < max_allowed:
            accepted.append(c)
            user_accepted[uid] += 1
        else:
            stats["rejected_user_cap"] += 1

    stats["accepted"] = len(accepted)
    return accepted, stats


def partition_dataset_by_page(
    curated_corrections: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Partitionne les données nettoyées en train / val / test selon le page_id.
    """
    splits: Dict[str, List[Dict[str, Any]]] = {"train": [], "val": [], "test": []}
    for c in curated_corrections:
        page_id = str(c.get("page_id") or c.get("id") or "anonymous_page")
        s = split_of(page_id)
        splits[s].append(c)
    return splits


def check_training_trigger(
    new_corrections_count: int,
    threshold: int = 500,
) -> Tuple[bool, str]:
    """
    Règle de déclenchement MLOps (§8.6.a) :
    Lancer le ré-entraînement seulement si ≥ 500 nouvelles corrections validées.
    """
    if new_corrections_count >= threshold:
        return True, f"Seuil de ré-entraînement atteint ({new_corrections_count} >= {threshold})."
    return False, f"Seuil non atteint ({new_corrections_count} < {threshold}). Attente de corrections supplémentaires."
