"""
Gestionnaire de cycle de vie des modèles HTR : Registre, Canary et Rollback (ML-7 / §8.7).
- Évaluation des critères stricts de promotion (qualité, non-régression, latence, calibration).
- Routage Canary déterministe (10% des utilisateurs : hash(user_id) % 100 < 10).
- Rollback immédiat en une commande.
"""
import hashlib
import logging
from typing import Dict, Any, Tuple, Optional
from datetime import datetime

logger = logging.getLogger("model_lifecycle")


def decide_promotion(candidate_metrics: Dict[str, Any], active_metrics: Dict[str, Any]) -> Tuple[bool, Dict[str, bool]]:
    """
    Règles strictes de décision (§8.7) :
    - Gain CER FR >= 5 % relatif
    - Erreurs d'accents réduites ou stables
    - Tolérance de régression anglaise max 2 %
    - Latence p95 maîtrisée (<= 1.25 x actif)
    - Calibration ECE < 0.08
    """
    c = candidate_metrics
    a = active_metrics

    cer_fr_target = a.get("cer_fr", 0.15) * 0.95
    accent_target = a.get("accent_err", 0.60)
    en_regression_limit = a.get("cer_en", 0.12) * 1.02
    latency_limit = a.get("p95_ms_per_line", 2200.0) * 1.25

    checks = {
        "cer_fr_improved": c.get("cer_fr", 1.0) <= cer_fr_target,
        "accents_improved": c.get("accent_err", 1.0) <= accent_target,
        "no_en_regression": c.get("cer_en", 1.0) <= en_regression_limit,
        "latency_ok": c.get("p95_ms_per_line", 9999.0) <= latency_limit,
        "calibration_ok": c.get("ece", 1.0) < 0.08,
    }
    return all(checks.values()), checks


def is_user_in_canary(user_id: str, canary_percentage: int = 10) -> bool:
    """
    Routage Canary déterministe par utilisateur (§8.7 #2) :
    hash(user_id) % 100 < 10
    Garantit qu'un même utilisateur est toujours sur la même version.
    """
    if not user_id or user_id in ("anon", "usr-guest"):
        return False
    h = int(hashlib.sha256(str(user_id).encode("utf-8")).hexdigest(), 16) % 100
    return h < canary_percentage


class ModelRegistryService:
    """Service de pilotage du registre `model_versions` en base de données."""

    @staticmethod
    def resolve_model_version(
        db,
        model_name: str,
        user_id: str,
    ) -> str:
        """
        Détermine la version de modèle à utiliser pour une requête OCR :
        - Si l'utilisateur est dans le cohort Canary 10% et qu'un modèle canary existe -> canary.
        - Sinon -> modèle actif en production.
        """
        from app.db.models.model_version import ModelVersion

        # 1. Vérifier si un modèle canary existe
        if is_user_in_canary(user_id, canary_percentage=10):
            canary_model = (
                db.query(ModelVersion)
                .filter(ModelVersion.name == model_name, ModelVersion.status == "canary")
                .first()
            )
            if canary_model:
                return canary_model.version

        # 2. Modèle actif standard
        active_model = (
            db.query(ModelVersion)
            .filter(ModelVersion.name == model_name, ModelVersion.status == "active")
            .order_by(ModelVersion.created_at.desc())
            .first()
        )
        if active_model:
            return active_model.version

        return "v3"  # Version par défaut si aucune entrée en base

    @staticmethod
    def promote_candidate_to_canary(db, model_version_id, human_approved: bool = False) -> Dict[str, Any]:
        """
        Promeut un candidat vers le statut 'canary' après validation des règles et accord humain.
        """
        if not human_approved:
            raise ValueError("Validation humaine obligatoire pour promouvoir un modèle en canary (§8.7).")

        from app.db.models.model_version import ModelVersion

        candidate = db.query(ModelVersion).filter(ModelVersion.id == model_version_id).first()
        if not candidate:
            raise ValueError(f"Modèle introuvable : {model_version_id}")

        active = (
            db.query(ModelVersion)
            .filter(ModelVersion.name == candidate.name, ModelVersion.status == "active")
            .first()
        )

        active_metrics = active.metrics if (active and active.metrics) else {
            "cer_fr": 0.1386,
            "accent_err": 0.5455,
            "cer_en": 0.1166,
            "p95_ms_per_line": 2213.0,
            "ece": 0.64,
        }

        passed, checks = decide_promotion(candidate.metrics or {}, active_metrics)
        if not passed:
            raise ValueError(f"Échec des critères de promotion automatique : {checks}")

        # Retirer d'anciens canaries s'il y en a
        db.query(ModelVersion).filter(
            ModelVersion.name == candidate.name, ModelVersion.status == "canary"
        ).update({"status": "retired"})

        candidate.status = "canary"
        db.commit()
        return {"status": "canary", "version": candidate.version, "checks": checks}

    @staticmethod
    def promote_canary_to_active(db, model_name: str) -> Dict[str, Any]:
        """Bascule le modèle canary validé en statut 'active', l'ancien passe 'retired'."""
        from app.db.models.model_version import ModelVersion

        canary = (
            db.query(ModelVersion)
            .filter(ModelVersion.name == model_name, ModelVersion.status == "canary")
            .first()
        )
        if not canary:
            raise ValueError(f"Aucun modèle canary en cours pour {model_name}")

        # Passer l'actuel en retired
        db.query(ModelVersion).filter(
            ModelVersion.name == model_name, ModelVersion.status == "active"
        ).update({"status": "retired"})

        canary.status = "active"
        db.commit()
        logger.info(f"Modèle {model_name} promu en 'active' : version {canary.version}")
        return {"status": "active", "version": canary.version}

    @staticmethod
    def rollback_active(db, model_name: str) -> Dict[str, Any]:
        """
        Rollback immédiat (§8.7 #4) :
        Désactive la version active courante et réactive la version précédente 'retired'.
        """
        from app.db.models.model_version import ModelVersion

        current_active = (
            db.query(ModelVersion)
            .filter(ModelVersion.name == model_name, ModelVersion.status == "active")
            .first()
        )

        previous_model = (
            db.query(ModelVersion)
            .filter(ModelVersion.name == model_name, ModelVersion.status == "retired")
            .order_by(ModelVersion.created_at.desc())
            .first()
        )

        if not previous_model:
            raise ValueError(f"Aucune version précédente trouvée pour le rollback de {model_name}")

        if current_active:
            current_active.status = "retired"

        previous_model.status = "active"
        db.commit()

        logger.warning(
            f"ROLLBACK EXÉCUTÉ pour {model_name} : "
            f"version {previous_model.version} réactivée."
        )
        return {"rollback": True, "active_version": previous_model.version}
