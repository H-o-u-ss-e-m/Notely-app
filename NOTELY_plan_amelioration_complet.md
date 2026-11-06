# NOTELY — Plan d'amélioration complet (Architecture · Code · Sécurité · Base de données · UI/UX · Modèle IA)

> **Document destiné à l'agent de développement (Antigravity).**
> Version : 3 novembre 2026 · Sources : `audit_complet_notely.md` + `evaluation_ameliorations_trocr.md`
> Langue du projet : français (+ arabe, anglais, allemand à terme)

---

## 0. Mode d'emploi pour l'agent (à lire en premier)

### 0.1 Règles de travail

1. **Vérifier avant de modifier.** Ce document a été écrit à partir de deux audits, pas à partir d'une exécution du code. Les noms de fichiers, de classes et de lignes sont ceux des audits. Si la réalité diffère, **adapte-toi à la réalité** et note l'écart dans `docs/CHANGELOG_AGENT.md`.
2. **Une tâche = une branche git = une PR** (`feat/…`, `fix/…`, `chore/…`). Jamais de gros commit fourre-tout.
3. **Chaque tâche a des critères d'acceptation.** Une tâche n'est terminée que si ces critères sont vérifiés (test automatique ou commande de vérification fournie).
4. **Ne casse pas l'existant.** Les anciennes routes (`/structural-htr`, `/recognition`…) restent fonctionnelles et sont marquées `deprecated` tant que Flutter et Angular ne sont pas migrés.
5. **Aucun secret dans le code ni dans les documents.** Le mot de passe de base de données et la clé JWT mentionnés dans les audits doivent être considérés comme **compromis** et changés.
6. **Mesurer avant d'optimiser.** Toute modification touchant le modèle ou le rendu est validée par le benchmark CER/WER (section 8.9). Pas de benchmark = pas de promotion en production.
7. **Éléments non vérifiés** : les noms de modèles Hugging Face tiers (français, arabe), les signatures exactes du plugin ML Kit Flutter et les versions de paquets sont marqués ⚠️ **À VÉRIFIER**. Ne jamais les supposer exacts.

### 0.2 Ordre d'exécution recommandé

| Phase                                 | Contenu                                                                         | Sections    |
| ------------------------------------- | ------------------------------------------------------------------------------- | ----------- |
| **P0 — Urgences sécurité**            | Secrets, JWT, CORS, IDOR, limites de payload                                    | §4          |
| **P1 — Fondations**                   | Alembic, config, qualité du code, tests, CI                                     | §2, §3, §5  |
| **P2 — UX critique**                  | Statut de sauvegarde, vraie confiance, zoom Angular, restructuration de l'UI    | §6          |
| **P3 — Modèle : mesure + quick wins** | Benchmark, post-traitement, mots + confiance, sélecteur de langue               | §7, §8      |
| **P4 — Apprentissage**                | Boucle de corrections, dictionnaire personnel, fine-tuning, registre de modèles | §8.5–8.7    |
| **P5 — Échelle**                      | File de tâches, worker, observabilité, déploiement                              | §2, §9, §10 |

### 0.3 Définition de « terminé » (Definition of Done)

- [ ] Code typé, lint propre (`ruff`, `mypy` / `flutter analyze` / `ng lint`)
- [ ] Tests ajoutés ou mis à jour et verts
- [ ] Migration Alembic fournie si le schéma change
- [ ] Aucune régression CER sur le benchmark (tâches touchant l'OCR)
- [ ] Documentation mise à jour (README, OpenAPI)
- [ ] Aucun secret, aucun `print` de debug, aucun `TODO` sans ticket

---

## 1. Synthèse du diagnostic

### 1.1 Ce qui est solide (à conserver)

- Rendu **depuis les vecteurs** (image propre, sans bruit de papier).
- Segmentation custom (gestion des points, accents, barres de t).
- Singleton du modèle + cache LRU + batch inference (moteur v2).
- Types de contenu explicites (h1–h6, `diagram`) → structure déclarée par l'utilisateur.
- Isolation par `user_id`, suppression en cascade, `consent_train` opt-in.
- Export PDF double (fidèle / structuré).

### 1.2 Ce qui manque ou est cassé (les 20 constats majeurs)

| #   | Domaine  | Constat                                                                                          | Gravité     |
| --- | -------- | ------------------------------------------------------------------------------------------------ | ----------- |
| 1   | Sécurité | `JWT_SECRET_KEY` avec valeur par défaut codée en dur                                             | 🔴 Critique |
| 2   | Sécurité | Mot de passe DB par défaut (`system`) présent dans la documentation                              | 🔴 Critique |
| 3   | Sécurité | `CORS_ORIGINS=["*"]` dans `Settings` vs regex dans `main.py` (incohérent)                        | 🟠 Haute     |
| 4   | Sécurité | Clé primaire `strokes.id` = ID client → risque d'écrasement entre utilisateurs (IDOR par upsert) | 🔴 Critique |
| 5   | Sécurité | Aucune limite de taille de payload (strokes/points) → déni de service                            | 🟠 Haute     |
| 6   | Sécurité | Refresh token via `Timer` 55 min seulement (pas de rotation, pas de révocation)                  | 🟠 Haute     |
| 7   | BDD      | Pas de migrations (`create_all`)                                                                 | 🟠 Haute     |
| 8   | BDD      | Incohérence taille page 800×1000 (DB) vs 794×1123 (Flutter A4)                                   | 🟡 Moyenne   |
| 9   | BDD      | Sauvegarde Flutter : page sans ID PostgreSQL → échec silencieux                                  | 🟠 Haute     |
| 10  | Code     | `auth.py` legacy, `preprocessing.py` vide, code mort                                             | 🟡 Moyenne   |
| 11  | Code     | Écran `notebook_screen.dart` monolithique (éditeur + OCR + export + drawer)                      | 🟠 Haute     |
| 12  | UI       | Confiance « 96 % » **codée en dur** (Angular)                                                    | 🔴 Trompeur |
| 13  | UI       | Pas de zoom/pan sur le canvas Angular                                                            | 🟠 Haute     |
| 14  | UI       | Outils de dessin cachés dans le Drawer (mobile), AppBar surchargée                               | 🟠 Haute     |
| 15  | UI       | Aucun état de sauvegarde réel (« Auto-save actif » est statique)                                 | 🟠 Haute     |
| 16  | Modèle   | `language` ignoré par le moteur ; Flutter force `'en'`                                           | 🔴 Critique |
| 17  | Modèle   | Correction mot par mot absente (fonction prête mais jamais appelée)                              | 🔴 Critique |
| 18  | Modèle   | `ocr/feedback` et `reocr-line` jamais appelés par les clients → le système n'apprend pas         | 🔴 Critique |
| 19  | Modèle   | Post-traitement = `re.sub(r'\s+',' ')` ; benchmark vide (aucun CER connu)                        | 🟠 Haute     |
| 20  | Modèle   | Arabe impossible avec TrOCR anglais ; accents français dégradés                                  | 🔴 Critique |

### 1.3 Corrections factuelles à reporter dans la documentation du projet

| Affirmation actuelle                 | Réalité à documenter                                                                                     |
| ------------------------------------ | -------------------------------------------------------------------------------------------------------- |
| Décodeur 768 dims                    | Décodeur 12 couches, **1024 dims**, initialisé depuis RoBERTa ; modèle complet ≈ **334 M** de paramètres |
| Encodeur « BEiT-base »               | Correct (12 couches, 768 dims), pré-entraîné ImageNet-21k                                                |
| Poids « ~400 MB »                    | ≈ **1,3 Go** en FP32 pour `base`                                                                         |
| « IAM + SROIE »                      | Le modèle *handwritten* est fine-tuné sur **IAM seul**                                                   |
| `max_new_tokens=64` (ancien rapport) | Le moteur v2 utilise **128** — vérifier que tous les chemins d'appel l'utilisent                         |

---

## 2. Architecture cible (niveau entreprise)

### 2.1 Principes

1. **Monolithe modulaire** côté API (pas de microservices prématurés), mais **l'inférence IA est isolée** dans un worker : l'API ne charge jamais de modèle de 1,3 Go dans le même processus que les requêtes CRUD.
2. **API stateless** : aucun état en mémoire de processus (sauf caches reconstruisables) → scalable horizontalement.
3. **12-Factor** : configuration par variables d'environnement, validée au démarrage, échec immédiat si invalide.
4. **Dégradation progressive** : chaque moteur OCR a un repli.
5. **Tout est observable** : logs structurés, métriques, traces, erreurs remontées.
6. **Tout est versionné** : schéma DB (Alembic), API (`/api/v1`, `/api/v2`), modèles IA (registre).

### 2.2 Schéma cible

```
┌──────────────┐   ┌──────────────┐
│ Flutter      │   │ Angular      │
└──────┬───────┘   └──────┬───────┘
       │      HTTPS (TLS 1.2+)     │
       └──────────────┬────────────┘
                      ▼
        ┌───────────────────────────┐
        │ Reverse proxy (Caddy /    │  TLS auto, HSTS, gzip/brotli,
        │ Traefik / Nginx)          │  limite taille corps, rate-limit L7
        └─────────────┬─────────────┘
                      ▼
        ┌───────────────────────────┐        ┌────────────────────┐
        │ API FastAPI (N réplicas)  │◄──────►│ Redis              │
        │ gunicorn + uvicorn workers│        │ cache · rate-limit │
        │ auth · cours · feedback   │        │ broker de tâches   │
        └───────┬──────────┬────────┘        └─────────┬──────────┘
                │          │ enqueue(job)               │
                ▼          └────────────────────────────┤
        ┌──────────────┐                                ▼
        │ PgBouncer    │                     ┌──────────────────────┐
        └──────┬───────┘                     │ OCR Worker(s)        │
               ▼                             │ registre de modèles  │
        ┌──────────────┐                     │ GPU/CPU · batch      │
        │ PostgreSQL   │◄────────────────────│ post-traitement      │
        └──────────────┘   résultats         └──────────┬───────────┘
                                                        ▼
                                             ┌──────────────────────┐
                                             │ Stockage objet       │
                                             │ (MinIO / S3)         │
                                             │ PDF · datasets ·     │
                                             │ artefacts de modèles │
                                             └──────────────────────┘

Hors ligne (MLOps) : export corrections → fine-tuning → évaluation → registre → promotion
Transversal : Prometheus + Grafana · Loki · Sentry · OpenTelemetry
```

### 2.3 Structure du backend cible

```
backend/
├── app/
│   ├── main.py                    # création de l'app, middlewares, routers
│   ├── core/
│   │   ├── config.py              # Settings (pydantic-settings), validation stricte
│   │   ├── security.py            # hash mdp, JWT, refresh rotation
│   │   ├── logging.py             # logs JSON structurés + request_id
│   │   ├── errors.py              # exceptions métier + handlers uniformes
│   │   └── limits.py              # constantes de limites (strokes, points, taille)
│   ├── api/
│   │   ├── deps.py                # get_db, current_user, get_owned_* (anti-IDOR)
│   │   └── v1/
│   │       ├── auth.py
│   │       ├── courses.py
│   │       ├── ocr.py             # jobs, line-words, feedback
│   │       ├── exports.py
│   │       └── health.py
│   ├── domain/                    # règles métier pures (sans FastAPI ni SQLAlchemy)
│   │   ├── segmentation.py
│   │   ├── structure.py
│   │   └── text_postprocess.py
│   ├── repositories/              # accès DB uniquement (SQLAlchemy)
│   │   ├── courses_repo.py
│   │   ├── strokes_repo.py
│   │   └── corrections_repo.py
│   ├── services/                  # orchestration (appelle repos + domain + ml)
│   │   ├── course_service.py
│   │   ├── ocr_service.py
│   │   └── export_service.py
│   ├── ml/
│   │   ├── engines/
│   │   │   ├── base.py            # interface OcrEngine
│   │   │   ├── trocr.py
│   │   │   └── vlm.py
│   │   ├── registry.py            # chargement paresseux + sélection par langue
│   │   ├── rendering.py           # (ex image_service) vecteurs → image
│   │   ├── confidence.py          # calibration
│   │   └── models.yaml            # configuration des moteurs et du routage
│   ├── workers/
│   │   ├── celery_app.py
│   │   └── ocr_tasks.py
│   ├── db/
│   │   ├── base.py
│   │   ├── session.py
│   │   └── models/
│   └── schemas/                   # Pydantic (entrées/sorties)
├── alembic/                       # migrations
├── tests/{unit,integration,e2e}
├── training/                      # scripts MLOps (export, finetune, eval, promote)
├── benchmark/
├── pyproject.toml                 # ruff, mypy, pytest
├── Dockerfile
└── docker-compose.yml
```

**Règle de dépendance** : `api → services → (repositories, domain, ml)`. Jamais l'inverse. `domain` n'importe rien d'externe.

### 2.4 TÂCHE ARCH-1 — Configuration validée au démarrage

**Problème :** secret JWT par défaut, CORS incohérent.
**Fichier :** `app/core/config.py`

```python
from functools import lru_cache
from typing import Literal
from pydantic import PostgresDsn, RedisDsn, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    env: Literal["dev", "staging", "prod"] = "dev"

    # Base de données — AUCUNE valeur par défaut
    database_url: PostgresDsn
    redis_url: RedisDsn = "redis://localhost:6379/0"

    # Sécurité — AUCUNE valeur par défaut
    jwt_secret_key: SecretStr
    jwt_algorithm: Literal["HS256", "RS256"] = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 30

    # CORS : liste explicite, jamais "*" en prod
    cors_origins: list[str] = []

    # IA
    ocr_default_language: Literal["fr", "en", "ar", "de"] = "fr"
    ocr_models_config: str = "app/ml/models.yaml"
    ocr_max_loaded_models: int = 2
    ocr_device: Literal["auto", "cpu", "cuda"] = "auto"

    # Limites
    max_request_body_mb: int = 10

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @model_validator(mode="after")
    def validate_prod(self):
        secret = self.jwt_secret_key.get_secret_value()
        if len(secret) < 32:
              # utilise sa jai genere manuelment dappret  (https://www.hexhero.com/tools/random-key-generator)
            raise ValueError("0f0b1ca76dd33216e741a7724eb00f8e3c1220b5f8f1d713a53706e0edc939a3")
        if self.env == "prod":
            if "*" in self.cors_origins:
                raise ValueError("CORS '*' interdit en production")
            if not all(o.startswith("https://") for o in self.cors_origins):
                raise ValueError("Les origines CORS de prod doivent être en https")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

**Critères d'acceptation :**

- Démarrer l'app sans `JWT_SECRET_KEY` → **erreur explicite au démarrage**.
- Une seule source de vérité CORS : `main.py` lit `settings.cors_origins`, plus de regex séparée.
- `.env.example` fourni (sans vraies valeurs), `.env` dans `.gitignore`.
- Générer un secret : `python -c "import secrets; print(secrets.token_urlsafe(64))"`.

### 2.5 TÂCHE ARCH-2 — OCR asynchrone par jobs (le changement d'architecture le plus important)

**Problème :** `POST /structural-htr` est synchrone : une page = 30 à 60 s sur CPU, ce qui bloque un worker HTTP et provoque des timeouts mobiles.

**Solution :** API de jobs.

```
POST /api/v1/ocr/jobs        → 202 { "jobId": "...", "status": "queued" }
GET  /api/v1/ocr/jobs/{id}   → { status: queued|running|done|failed, progress: 0-100, result?: {...} }
GET  /api/v1/ocr/jobs/{id}/events   (optionnel : SSE pour le temps réel)
```

**Table `ocr_jobs`** (voir §5.4) : `id, user_id, page_id, status, progress, language, engine, result_json, error, created_at, finished_at`.

**Endpoint (squelette) :**

```python
# app/api/v1/ocr.py
@router.post("/ocr/jobs", status_code=202, response_model=JobCreated)
async def create_job(
    body: OcrJobRequest,                      # strokes validés (limites §4.5)
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit("ocr", per_minute=10)),
):
    page = get_owned_page(body.page_id, user, db) if body.page_id else None
    job = jobs_repo.create(db, user_id=user.id, page_id=page.id if page else None,
                           language=body.options.language)
    ocr_task.delay(str(job.id), body.model_dump(mode="json"))
    return JobCreated(jobId=job.id, status="queued")
```

**Worker :**

```python
# app/workers/ocr_tasks.py
@celery_app.task(bind=True, name="ocr.run", soft_time_limit=120, time_limit=150)
def ocr_task(self, job_id: str, payload: dict):
    with session_scope() as db:
        jobs_repo.mark_running(db, job_id)
        try:
            result = ocr_service.run_pipeline(
                payload, on_progress=lambda p: jobs_repo.set_progress(db, job_id, p)
            )
            jobs_repo.mark_done(db, job_id, result)
        except Exception as exc:                       # noqa: BLE001
            logger.exception("ocr_failed", extra={"job_id": job_id})
            jobs_repo.mark_failed(db, job_id, str(exc)[:500])
            raise
```

**Notes d'exploitation :**

- Lancer le worker GPU avec `--concurrency=1` (un modèle par processus GPU). Sur CPU : `--concurrency=<cœurs/2>` ; `--pool=solo` ou `threads` pour éviter de dupliquer 1,3 Go par processus fils.
- **Warm-up** au démarrage du worker : charger le modèle et faire une inférence factice.
- Garder l'ancienne route synchrone, marquée `deprecated=True`, avec un garde-fou : refuser au-delà de N lignes (renvoyer `409` avec message « utilisez /ocr/jobs »).
- **Client** : poll toutes les 1 s avec backoff, afficher la progression (§6).

**Critères d'acceptation :**

- Une page de 30 lignes ne bloque plus l'API : `GET /health` répond < 100 ms pendant un OCR.
- Un job échoué renvoie `status=failed` + message lisible, jamais un 500 muet.
- Un job d'un autre utilisateur renvoie `404`.

### 2.6 TÂCHE ARCH-3 — Conteneurisation et environnements

```yaml
# docker-compose.yml (dev) — à dupliquer en docker-compose.prod.yml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: notely
      POSTGRES_USER: notely
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
    secrets: [db_password]
    volumes: [pgdata:/var/lib/postgresql/data]
    healthcheck: { test: ["CMD-SHELL", "pg_isready -U notely"], interval: 5s, retries: 10 }

  redis:
    image: redis:7-alpine
    command: ["redis-server", "--appendonly", "yes"]

  api:
    build: ./backend
    command: gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:8000 --timeout 60
    env_file: .env
    depends_on: { db: { condition: service_healthy }, redis: { condition: service_started } }
    deploy: { resources: { limits: { memory: 1g } } }

  worker:
    build: ./backend
    command: celery -A app.workers.celery_app worker -l info --concurrency=1 -Q ocr
    env_file: .env
    volumes: [hf_cache:/root/.cache/huggingface]      # évite de re-télécharger les modèles
    # GPU : décommenter pour NVIDIA
    # deploy: { resources: { reservations: { devices: [{ capabilities: [gpu] }] } } }

  proxy:
    image: caddy:2
    ports: ["80:80", "443:443"]
    volumes: [./Caddyfile:/etc/caddy/Caddyfile, caddy_data:/data]

secrets:
  db_password: { file: ./secrets/db_password.txt }
volumes: { pgdata: {}, hf_cache: {}, caddy_data: {} }
```

```
# Caddyfile — TLS automatique + en-têtes de sécurité
api.notely.example {
    request_body { max_size 10MB }
    encode zstd gzip
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "no-referrer"
    }
    reverse_proxy api:8000
}
```

**Remplace ngrok** : domaine fixe + Cloudflare Tunnel ou VPS. Plus de rebuild Flutter à chaque changement d'URL ; l'URL de base devient une variable de build (`--dart-define=API_BASE_URL=https://api.notely.example`).

**Dockerfile backend** (multi-stage, utilisateur non-root) :

```dockerfile
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock
COPY . .
RUN useradd -m app && chown -R app /app
USER app
HEALTHCHECK CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8000/api/v1/health')"
```

**Critères :** `docker compose up` démarre toute la pile ; `requirements.lock` épingle **toutes** les versions (dont `transformers<5` ou la version testée).

### 2.7 TÂCHE ARCH-4 — Observabilité

| Besoin       | Outil                               | Mise en œuvre                                                                                                                           |
| ------------ | ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| Logs         | JSON structuré + `request_id`       | middleware qui injecte un UUID par requête, renvoyé dans l'en-tête `X-Request-ID`                                                       |
| Erreurs      | Sentry (self-hosted possible)       | `sentry_sdk.init(dsn=..., traces_sample_rate=0.1)`, **sans** données personnelles ni tracés                                             |
| Métriques    | `prometheus-fastapi-instrumentator` | `/metrics` protégé (réseau interne)                                                                                                     |
| Métriques IA | métriques custom                    | `ocr_line_latency_seconds`, `ocr_confidence` (histogramme), `ocr_corrections_total{language}`, `ocr_cache_hit_ratio`, `ocr_queue_depth` |
| Traces       | OpenTelemetry                       | instrumentation FastAPI + SQLAlchemy + Celery                                                                                           |
| Alertes      | Grafana                             | p95 latence API > 1 s, taux 5xx > 1 %, file OCR > 50, CER en ligne (corrections/jour) en hausse                                         |

```python
# app/core/logging.py (extrait)
import logging, json, contextvars
request_id_var = contextvars.ContextVar("request_id", default="-")

class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "ts": self.formatTime(record), "level": record.levelname,
            "msg": record.getMessage(), "logger": record.name,
            "request_id": request_id_var.get(),
            **{k: v for k, v in record.__dict__.items() if k in ("job_id", "user_id", "latency_ms")},
        }, ensure_ascii=False)
```

> **Règle absolue :** ne jamais logger les tracés (`strokes`), le texte reconnu, les e-mails ni les tokens. Logger des identifiants, des durées et des compteurs.

---

## 3. Qualité du code

### 3.1 Backend (Python / FastAPI)

#### TÂCHE CODE-1 — Outillage obligatoire

```toml
# pyproject.toml
[tool.ruff]
line-length = 100
target-version = "py312"
[tool.ruff.lint]
select = ["E","F","I","B","UP","S","C4","SIM","PL","ASYNC"]   # S = bandit (sécurité)
ignore = ["PLR2004"]
[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy", "sqlalchemy.ext.mypy.plugin"]
[tool.pytest.ini_options]
addopts = "-q --cov=app --cov-fail-under=70"
```

- `pre-commit` : `ruff`, `ruff-format`, `mypy`, `detect-secrets`.
- Supprimer le code mort : `app/api/auth.py` (legacy), `app/ml/preprocessing.py` (vide) → **soit supprimé, soit réellement implémenté** (voir §8.8, qui y met le rendu et la normalisation).
- Aucun `print()` : utiliser `logger`.

#### TÂCHE CODE-2 — Gestion d'erreurs uniforme

Toutes les erreurs renvoient le même format, exploitable par Flutter et Angular pour afficher un message utile :

```json
{ "error": { "code": "OCR_TIMEOUT", "message": "La reconnaissance a pris trop de temps.", "requestId": "…", "details": null } }
```

```python
# app/core/errors.py
class AppError(Exception):
    status_code = 400
    code = "APP_ERROR"
    def __init__(self, message: str, *, details=None):
        self.message, self.details = message, details

class NotFound(AppError):    status_code, code = 404, "NOT_FOUND"
class Forbidden(AppError):   status_code, code = 403, "FORBIDDEN"
class PayloadTooLarge(AppError): status_code, code = 413, "PAYLOAD_TOO_LARGE"
class OcrFailed(AppError):   status_code, code = 502, "OCR_FAILED"

@app.exception_handler(AppError)
async def app_error_handler(request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"error": {
        "code": exc.code, "message": exc.message,
        "requestId": request_id_var.get(), "details": exc.details}})

@app.exception_handler(Exception)          # filet de sécurité : jamais de stacktrace au client
async def unhandled(request, exc):
    logger.exception("unhandled")
    return JSONResponse(status_code=500, content={"error": {
        "code": "INTERNAL", "message": "Erreur interne.", "requestId": request_id_var.get()}})
```

#### TÂCHE CODE-3 — Séparer routes / services / dépôts

Aujourd'hui `recognition.py`, `handwriting_service.py` etc. mélangent plusieurs responsabilités. Règle : **une route ne contient ni SQL, ni logique métier** — elle valide, appelle un service, formate la réponse.

```python
# ❌ À éviter                         # ✅ Cible
@router.put("/lessons/{id}")           @router.put("/lessons/{id}")
def save(...):                         def save(lesson: Lesson = Depends(get_owned_lesson),
    db.query(...).delete()                      body: LessonSave, svc: CourseService = Depends()):
    for s in strokes: db.add(...)          return svc.save_lesson(lesson, body)
```

#### TÂCHE CODE-4 — Segmentation : performance et fiabilité

- Remplacer `queue.pop(0)` par `collections.deque.popleft()` (O(1)).
- Trier les tracés par `y_center` et ne comparer qu'à une **fenêtre voisine** (évite le O(n²) sur 1 000+ tracés), ou vectoriser avec NumPy.
- Appliquer réellement `MAX_DESKEW_DEG` : `if abs(angle) > MAX_DESKEW_DEG: angle = 0`.
- Tests unitaires avec des fixtures de tracés (lignes simples, accents, exposants, écriture serrée).

### 3.2 Flutter

#### TÂCHE FLT-1 — Découper `notebook_screen.dart`

L'écran actuel porte : canvas, outils, zoom, drawer, sauvegarde, OCR, PDF, dialogs. **Cible :**

```
lib/
├── core/
│   ├── api/{api_client.dart, auth_interceptor.dart, api_exception.dart}
│   ├── storage/secure_token_store.dart
│   ├── config/env.dart                 # API_BASE_URL via --dart-define
│   └── i18n/                           # fr, en, ar, de (ARB)
├── features/
│   ├── auth/{data,domain,presentation}
│   ├── dashboard/{data,domain,presentation}
│   └── notebook/
│       ├── data/{notebook_repository.dart, ocr_repository.dart}
│       ├── domain/{stroke.dart, page.dart, ocr_result.dart}   # modèles immuables (freezed)
│       ├── application/                # état (Riverpod ou Bloc)
│       │   ├── notebook_controller.dart
│       │   ├── drawing_controller.dart
│       │   └── ocr_controller.dart
│       └── presentation/
│           ├── notebook_screen.dart            # assemble seulement
│           ├── widgets/{canvas_view, tool_palette, zoom_badge, page_strip,
│           │            save_status_chip, ocr_button}.dart
│           └── ocr/{ocr_result_sheet, word_chip, word_correction_sheet,
│                    language_selector}.dart
```

- **Gestion d'état :** Riverpod (recommandé) ou Bloc. Un seul choix, appliqué partout. Les widgets ne font **aucun appel réseau** directement.
- **Modèles immuables** avec `freezed` + `json_serializable` ; plus de `Map<String,dynamic>` qui circulent.
- **Performance du dessin :** isoler le tracé en cours dans un `CustomPainter` séparé (couche « live »), avec `RepaintBoundary` ; les tracés terminés vont dans une couche « statique » repeinte seulement quand elle change. Évite de repeindre 1 000 tracés à chaque point.
- Lint : `flutter_lints` + `very_good_analysis`.

#### TÂCHE FLT-2 — Client HTTP robuste (corrige le refresh par `Timer`)

```dart
// core/api/auth_interceptor.dart
class AuthInterceptor extends QueuedInterceptorsWrapper {
  AuthInterceptor(this._dio, this._store);
  final Dio _dio;
  final SecureTokenStore _store;

  @override
  void onRequest(RequestOptions o, RequestInterceptorHandler h) async {
    final t = await _store.accessToken();
    if (t != null) o.headers['Authorization'] = 'Bearer $t';
    h.next(o);
  }

  @override
  void onError(DioException e, ErrorInterceptorHandler h) async {
    if (e.response?.statusCode == 401 && e.requestOptions.extra['retried'] != true) {
      final refreshed = await _tryRefresh();            // POST /auth/refresh (rotation)
      if (refreshed) {
        final req = e.requestOptions..extra['retried'] = true;
        final newToken = await _store.accessToken();
        req.headers['Authorization'] = 'Bearer $newToken';
        return h.resolve(await _dio.fetch(req));
      }
      await _store.clear();                             // → redirection vers login
    }
    h.next(e);
  }
}
```

- Supprimer le `Timer` de 55 min : le rafraîchissement se fait **sur 401**.
- Timeouts explicites (`connectTimeout: 10s`, `receiveTimeout: 30s`), **retry avec backoff** uniquement sur requêtes idempotentes.
- Stockage des tokens : `flutter_secure_storage` (Keychain / Keystore), **jamais** `SharedPreferences`.
- Mode hors-ligne : file locale (`drift`/`isar`/`sqflite`) des modifications non synchronisées (voir §6.5).

#### TÂCHE FLT-3 — Corriger la sauvegarde silencieuse (constat #9)

```dart
// Tout objet créé localement reçoit un UUID v4 côté client (jamais « sans ID »)
final page = NotebookPage(id: const Uuid().v4(), pageNumber: n, strokes: []);

// Le repository retourne un résultat explicite, jamais un bool muet
sealed class SaveResult {}
class Saved extends SaveResult { Saved(this.serverVersion); final int serverVersion; }
class SaveConflict extends SaveResult {}          // version obsolète
class SaveFailed extends SaveResult { SaveFailed(this.error); final ApiException error; }
```

L'UI traduit chaque cas (§6 : puce d'état « Enregistré / Enregistrement… / Échec — Réessayer »).

### 3.3 Angular

#### TÂCHE NG-1 — Modernisation

- **Composants standalone** + `ChangeDetectionStrategy.OnPush` + **Signals** pour l'état local.
- **Lazy loading** des routes (`loadComponent`), l'éditeur est la partie lourde.
- Découper `notebook-editor` : `drawing-canvas`, `tool-palette`, `ocr-panel`, `export-dialog`, `page-navigator`, `save-status`.
- Un **service d'état** (`NotebookStore` avec signals) ; les composants ne se parlent pas par `@Input` en cascade.
- **Interceptor HTTP** : ajout du token + refresh sur 401 + mapping des erreurs.

```typescript
// core/auth.interceptor.ts
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const authed = auth.accessToken() ? req.clone({ setHeaders: { Authorization: `Bearer ${auth.accessToken()}` } }) : req;
  return next(authed).pipe(
    catchError((err: HttpErrorResponse) => {
      if (err.status === 401 && !req.url.includes('/auth/')) {
        return auth.refresh().pipe(
          switchMap(() => next(req.clone({ setHeaders: { Authorization: `Bearer ${auth.accessToken()}` } }))),
          catchError(e => { auth.logout(); return throwError(() => e); })
        );
      }
      return throwError(() => err);
    })
  );
};
```

- Types stricts (`strict: true` dans `tsconfig`), aucun `any`.
- Lint : `eslint` + `@angular-eslint`, tests : Jest ou Karma + Playwright pour l'e2e.

#### TÂCHE NG-2 — Canvas : Pointer Events (remplace mouse + touch séparés)

Le canvas actuel gère `mousedown/touchstart` séparément : pas de pression, pas de distinction stylet/doigt, comportement incohérent. **Cible :**

```typescript
// drawing-canvas.component.ts (extrait)
@HostListener('pointerdown', ['$event'])
onDown(e: PointerEvent) {
  if (e.pointerType === 'touch' && this.stylusOnly()) return;     // rejet de la paume
  this.canvas.setPointerCapture(e.pointerId);
  this.current = this.store.beginStroke(this.toPage(e), e.pressure || 0.5, e.timeStamp);
}
@HostListener('pointermove', ['$event'])
onMove(e: PointerEvent) {
  if (!this.current) return;
  const events = e.getCoalescedEvents?.() ?? [e];                  // tracé fluide
  for (const ev of events) this.store.addPoint(this.current, this.toPage(ev), ev.pressure || 0.5, ev.timeStamp);
}
@HostListener('pointerup',     ['$event']) onUp(e: PointerEvent)    { this.finish(); }
@HostListener('pointercancel', ['$event']) onCancel(e: PointerEvent){ this.finish(); }
```

```css
canvas { touch-action: none; }   /* indispensable : empêche le scroll navigateur pendant le dessin */
```

- **Netteté Retina** : `canvas.width = cssWidth * devicePixelRatio` puis `ctx.scale(dpr, dpr)`.
- **Zoom/pan** : matrice de transformation unique (`scale`, `tx`, `ty`) appliquée à l'affichage ; `toPage(e)` inverse la matrice pour que les coordonnées stockées restent en **repère page (794×1123)**. Molette + Ctrl = zoom centré curseur ; deux doigts = pan/pinch ; barre d'espace + glisser = pan.
- Rendu en deux couches (`<canvas>` statique + `<canvas>` du tracé courant) pour la performance.

---

## 4. Sécurité

> **Priorité P0.** Les points 4.1 à 4.5 sont à traiter avant toute nouvelle fonctionnalité.

### 4.1 TÂCHE SEC-1 — Secrets et configuration (urgence)

1. **Renouveler** : mot de passe PostgreSQL, `JWT_SECRET_KEY`. Les valeurs apparues dans la documentation ou le dépôt sont compromises.
2. Purger l'historique git si les secrets y figurent (`git filter-repo` ou `bfg`), puis **rotation** quand même.
3. `config.py` sans valeurs par défaut (voir ARCH-1). `.env` jamais committé ; `.env.example` fourni.
4. En production : secrets via Docker/Kubernetes secrets ou un coffre (Vault, AWS/GCP Secret Manager), pas de `.env` en clair sur disque partagé.
5. Ajouter `detect-secrets` en pre-commit et `gitleaks` en CI.
6. Retirer tout identifiant de la documentation (`audit`, `README`).

### 4.2 TÂCHE SEC-2 — Mots de passe

- Algorithme : **argon2id** (`argon2-cffi`) — meilleur que bcrypt pour du matériel moderne.

```python
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
ph = PasswordHasher(time_cost=3, memory_cost=64 * 1024, parallelism=2)

def hash_password(p: str) -> str: return ph.hash(p)
def verify_password(h: str, p: str) -> bool:
    try: return ph.verify(h, p)
    except VerifyMismatchError: return False
```

- Si l'existant est en bcrypt : **re-hash transparent** à la connexion réussie (`ph.check_needs_rehash`).
- Politique : minimum 10 caractères, refuser les mots de passe courants (liste `zxcvbn` ou HIBP k-anonymity), pas de règle « 1 majuscule 1 symbole » absurde.
- Message de login **identique** si l'e-mail n'existe pas ou si le mot de passe est faux (anti-énumération) ; temps de réponse constant (faire un hash factice).

### 4.3 TÂCHE SEC-3 — Jetons : access court + refresh à rotation

| Jeton                      | Durée      | Stockage serveur         | Stockage client                                                            |
| -------------------------- | ---------- | ------------------------ | -------------------------------------------------------------------------- |
| Access (JWT)               | **15 min** | aucun (stateless)        | mémoire (Angular), Keystore/Keychain (Flutter)                             |
| Refresh (opaque, 256 bits) | 30 jours   | **hash SHA-256** en base | cookie `HttpOnly; Secure; SameSite=Strict` (web) / secure storage (mobile) |

```python
# Rotation avec détection de réutilisation
def rotate_refresh(db, presented: str) -> TokenPair:
    h = sha256(presented)
    tok = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == h))
    if tok is None:
        raise Unauthorized()
    if tok.revoked_at is not None:
        # Jeton déjà utilisé → vol probable : on révoque TOUTE la famille
        db.execute(update(RefreshToken).where(RefreshToken.family_id == tok.family_id)
                   .values(revoked_at=func.now()))
        raise Unauthorized()
    if tok.expires_at < utcnow():
        raise Unauthorized()
    tok.revoked_at = func.now()
    new = issue_refresh(db, user_id=tok.user_id, family_id=tok.family_id)
    return TokenPair(access=issue_access(tok.user_id), refresh=new)
```

- Route `POST /auth/logout` (révoque la famille) et `POST /auth/logout-all`.
- Le JWT contient `sub`, `exp`, `iat`, `jti`, `role` ; vérifier `exp` et l'algorithme **explicitement** (`algorithms=["HS256"]`).
- Table `refresh_tokens` : voir §5.4.

### 4.4 TÂCHE SEC-4 — Autorisation : fin des IDOR

Toute ressource est accessible **uniquement** via des dépendances qui vérifient la propriété. Jamais `db.get(Lesson, id)` brut dans une route.

```python
# app/api/deps.py
def get_owned_subject(subject_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)) -> Subject:
    obj = db.scalar(select(Subject).where(Subject.id == subject_id, Subject.user_id == user.id))
    if obj is None:
        raise NotFound("Matière introuvable")          # 404 (et non 403) : ne révèle pas l'existence
    return obj

def get_owned_lesson(lesson_id: UUID, user=Depends(current_user), db=Depends(get_db)) -> Lesson:
    obj = db.scalar(select(Lesson).join(Subject).where(Lesson.id == lesson_id, Subject.user_id == user.id))
    if obj is None:
        raise NotFound("Cours introuvable")
    return obj

def get_owned_page(page_id: UUID, user=Depends(current_user), db=Depends(get_db)) -> NotebookPage:
    obj = db.scalar(select(NotebookPage).join(Lesson).join(Subject)
                    .where(NotebookPage.id == page_id, Subject.user_id == user.id))
    if obj is None:
        raise NotFound("Page introuvable")
    return obj
```

**Cas critique — sauvegarde des tracés (constat #4)** : la PK `strokes.id` est fournie par le client. Un utilisateur malveillant peut envoyer l'ID d'un tracé d'autrui, et un `ON CONFLICT DO UPDATE` l'écraserait. **Correction :** clé interne UUID + contrainte d'unicité `(page_id, client_id)` (voir §5.3). L'upsert cible cette contrainte, donc il ne peut jamais toucher une autre page.

**Tests obligatoires** (`tests/integration/test_authz.py`) : pour chaque route avec un identifiant, un utilisateur B reçoit `404` sur les ressources de A. Un test paramétré sur toutes les routes.

### 4.5 TÂCHE SEC-5 — Validation des entrées et limites (anti-DoS)

```python
# app/core/limits.py
MAX_STROKES_PER_REQUEST   = 5_000
MAX_POINTS_PER_STROKE     = 2_000
MAX_TOTAL_POINTS          = 200_000
MAX_PAGES_PER_LESSON      = 300
MAX_CANVAS_DIM            = 4_000
MAX_TEXT_CORRECTION_LEN   = 2_000
```

```python
# app/schemas/strokes.py
class Point(BaseModel):
    x: float = Field(ge=-10_000, le=10_000)
    y: float = Field(ge=-10_000, le=10_000)
    timestamp: float | None = Field(default=None, ge=0)
    pressure: float = Field(default=0.5, ge=0, le=1)

class Stroke(BaseModel):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_\-]+$")
    tool: Literal["pen", "diagram", "eraser"]
    content_type: Literal["normal", "h1", "h2", "h3", "h4", "h5", "h6"] = "normal"
    color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    width: float = Field(gt=0, le=50)
    points: list[Point] = Field(min_length=1, max_length=MAX_POINTS_PER_STROKE)

class RecognitionRequest(BaseModel):
    strokes: list[Stroke] = Field(max_length=MAX_STROKES_PER_REQUEST)
    canvas_width: int = Field(gt=0, le=MAX_CANVAS_DIM)
    canvas_height: int = Field(gt=0, le=MAX_CANVAS_DIM)

    @model_validator(mode="after")
    def total_points(self):
        if sum(len(s.points) for s in self.strokes) > MAX_TOTAL_POINTS:
            raise PayloadTooLarge("Trop de points dans la requête")
        return self
```

- Limite de corps HTTP au proxy (10 Mo) **et** dans l'app (middleware qui lit `Content-Length`).
- Le client Flutter **simplifie** les tracés avant envoi (Ramer-Douglas-Peucker, tolérance ≈ 0,5 px) → payload ÷ 3 à ÷ 5 sans perte visible pour l'OCR.
- Compression `gzip` des requêtes volumineuses (`Content-Encoding: gzip`, décompression bornée côté serveur pour éviter les « zip bombs »).

### 4.6 TÂCHE SEC-6 — Rate limiting et anti brute-force

```python
# slowapi + Redis
limiter = Limiter(key_func=get_remote_address, storage_uri=settings.redis_url)

@router.post("/auth/login")
@limiter.limit("5/minute")                 # par IP
async def login(...): ...
# + verrouillage progressif par compte : après 5 échecs → délai 1 min, 10 échecs → 15 min
```

| Route                           | Limite proposée              |
| ------------------------------- | ---------------------------- |
| `/auth/login`, `/auth/register` | 5/min/IP + verrou par compte |
| `/ocr/jobs`                     | 10/min/utilisateur           |
| `/ocr/feedback`                 | 60/min/utilisateur           |
| `/export-pdf*`                  | 5/min/utilisateur            |
| Autres                          | 120/min/utilisateur          |

### 4.7 TÂCHE SEC-7 — En-têtes, CORS, transport

- **CORS** : liste blanche stricte (Flutter mobile n'en a pas besoin ; seul Angular est concerné). `allow_credentials=True` uniquement avec origines explicites.
- **TLS partout** ; HSTS ; pas de HTTP en production.
- Angular : **Content-Security-Policy** (`default-src 'self'; img-src 'self' data:; script-src 'self'; connect-src 'self' https://api.notely.example`), pas de `innerHTML` non assaini (le rendu Markdown doit passer par un sanitizer).
- Flutter : builds release avec `--obfuscate --split-debug-info`, aucun `debugPrint` de données sensibles, interdiction du `badCertificateCallback` permissif ; **certificate pinning** optionnel pour la production.
- Swagger/`/docs` : désactivé ou protégé en production.

### 4.8 TÂCHE SEC-8 — Vie privée, RGPD, consentement IA

| Exigence                    | Mise en œuvre                                                                                                                                                                 |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Consentement entraînement   | `consent_train` **par défaut FALSE**, case explicite dans les paramètres, retirable à tout moment (retrait ⇒ exclusion des futurs exports et marquage `consent_withdrawn_at`) |
| Envoi cloud (VLM)           | **Second consentement distinct** (`consent_cloud_ocr`), jamais implicite. Sans consentement, pas de repli VLM cloud                                                           |
| Droit d'accès / portabilité | `GET /me/export` → archive ZIP (JSON des cours + corrections)                                                                                                                 |
| Droit à l'effacement        | `DELETE /me` : suppression utilisateur + cascade + purge des datasets d'entraînement contenant ses données (tâche asynchrone, journalisée)                                    |
| Minimisation                | Ne stocker `strokes_json` dans les corrections que si `consent_train = TRUE`                                                                                                  |
| Journal d'audit             | table `audit_logs` (connexion, export, suppression, changement de consentement) sans contenu manuscrit                                                                        |
| Rétention                   | corrections non consenties supprimées après 30 jours ; logs applicatifs 30 jours                                                                                              |

### 4.9 TÂCHE SEC-9 — Chaîne d'approvisionnement

- CI : `pip-audit`, `npm audit --omit=dev`, `flutter pub outdated`, `trivy image` sur les conteneurs.
- `requirements.lock` / `package-lock.json` / `pubspec.lock` committés.
- **Modèles Hugging Face** : épingler la **révision** (`revision="<commit sha>"`) lors de `from_pretrained`, préférer les poids `safetensors` ; ne jamais charger un modèle tiers inconnu avec `trust_remote_code=True`. Un modèle communautaire non vérifié est du code potentiellement exécutable.
- Dépendabot/Renovate activés.

### 4.10 Checklist sécurité (critères d'acceptation globaux)

- [ ] L'app refuse de démarrer sans `JWT_SECRET_KEY` valide
- [ ] Aucune route sans authentification sauf `/health`, `/auth/*`
- [ ] Test d'autorisation : B ne voit jamais les données de A (404)
- [ ] Payload de 10 000 tracés → `413`/`422`, pas de plantage
- [ ] 6 tentatives de login en 1 min → `429`
- [ ] Refresh réutilisé → toute la famille révoquée
- [ ] `trivy` / `pip-audit` / `gitleaks` verts en CI

---

## 5. Base de données

### 5.1 TÂCHE DB-1 — Alembic (bloquant pour toute évolution)

```bash
pip install alembic
alembic init alembic
# alembic/env.py : target_metadata = Base.metadata ; sqlalchemy.url lu depuis Settings (pas d'URL en dur)
```

**Mise en place sur une base existante (sans la perdre) :**

```bash
alembic revision --autogenerate -m "baseline"     # relire attentivement le script généré
alembic stamp head                                # marque la base EXISTANTE comme à jour
# Ensuite, toute modification de schéma passe par :
alembic revision --autogenerate -m "add refresh_tokens"
alembic upgrade head
```

- **Supprimer `Base.metadata.create_all()`** du démarrage de l'app en staging/prod. En dev uniquement, éventuellement derrière `if settings.env == "dev"`.
- Exécuter `alembic upgrade head` dans l'entrypoint du conteneur **avant** de lancer l'API (job d'init séparé en prod).
- Règle de migration sans interruption : **expand → migrate → contract** (ajouter, copier, retirer en 2 déploiements), jamais de `DROP COLUMN` direct.
- CI : une base vide doit atteindre `head`, et `alembic check` ne doit détecter aucune dérive.

### 5.2 TÂCHE DB-2 — Corrections du schéma existant

| Problème                                                                | Correction (migration)                                                                                                             |
| ----------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `notebook_pages.width/height` défaut 800×1000, Flutter utilise 794×1123 | `ALTER … SET DEFAULT 794 / 1123` + `UPDATE` des pages dont les dimensions sont exactement 800×1000 et jamais modifiées (à valider) |
| `DATETIME` sans fuseau                                                  | `TIMESTAMPTZ` partout, stockage en UTC                                                                                             |
| `updated_at` géré à la main                                             | trigger ou `onupdate=func.now()` SQLAlchemy                                                                                        |
| `users.role` en VARCHAR libre                                           | `CHECK (role IN ('student','teacher','admin'))` ou type ENUM                                                                       |
| `users.email` insensible à la casse ?                                   | index unique sur `lower(email)` (`citext` ou index fonctionnel)                                                                    |
| Pas d'index utiles                                                      | voir ci-dessous                                                                                                                    |
| Pas de suppression logique                                              | `deleted_at` sur `lessons` (corbeille 30 jours)                                                                                    |

```sql
CREATE UNIQUE INDEX uq_users_email_lower ON users (lower(email));
CREATE INDEX ix_subjects_user        ON subjects (user_id);
CREATE INDEX ix_lessons_subject      ON lessons (subject_id) WHERE deleted_at IS NULL;
CREATE INDEX ix_pages_lesson_number  ON notebook_pages (lesson_id, page_number);
CREATE INDEX ix_strokes_page         ON strokes (page_id);
CREATE INDEX ix_corrections_user_lang ON ocr_corrections (user_id, language, created_at DESC);
CREATE INDEX ix_corrections_train    ON ocr_corrections (language) WHERE consent_train AND is_validated;
```

### 5.3 TÂCHE DB-3 — Refonte de la table `strokes` (sécurité + performance)

**Problème :** PK = ID client (`VARCHAR`) → collision/écrasement possible (constat #4).

```python
class Stroke(Base):
    __tablename__ = "strokes"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)         # clé interne
    page_id: Mapped[UUID] = mapped_column(ForeignKey("notebook_pages.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[str] = mapped_column(String(64))                         # ID généré par le client
    tool: Mapped[str] = mapped_column(String(16))
    content_type: Mapped[str] = mapped_column(String(16), default="normal")
    color: Mapped[str] = mapped_column(String(7))
    width: Mapped[float]
    points: Mapped[list] = mapped_column(JSONB)
    bbox: Mapped[dict] = mapped_column(JSONB)
    start_time: Mapped[float | None]
    end_time: Mapped[float | None]
    seq: Mapped[int] = mapped_column(default=0)          # ordre d'écriture (indispensable à l'OCR et au rejeu)
    deleted_at: Mapped[datetime | None]                  # effacement logique (undo côté serveur)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    __table_args__ = (UniqueConstraint("page_id", "client_id", name="uq_stroke_page_client"),)
```

**Upsert sûr (corrige aussi le constat #9) :**

```python
from sqlalchemy.dialects.postgresql import insert as pg_insert

def upsert_strokes(db, page_id: UUID, strokes: list[StrokeIn]):
    rows = [dict(page_id=page_id, client_id=s.id, tool=s.tool, content_type=s.content_type,
                 color=s.color, width=s.width, points=[p.model_dump() for p in s.points],
                 bbox=s.bbox.model_dump(), seq=i) for i, s in enumerate(strokes)]
    stmt = pg_insert(Stroke).values(rows)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_stroke_page_client",
        set_={c: stmt.excluded[c] for c in ("tool", "content_type", "color", "width", "points", "bbox", "seq")},
    )
    db.execute(stmt)
```

**Sauvegarde différentielle (performance)** — au lieu de renvoyer toute la leçon à chaque autosave :

```
PATCH /api/v1/pages/{page_id}/strokes
{ "baseVersion": 12, "added": [ {...} ], "removedClientIds": ["stroke-…"] }
→ 200 { "version": 13 }     |     409 si baseVersion obsolète (conflit)
```

- **Concurrence optimiste** : `lessons.version` / `notebook_pages.version` incrémentés ; `UPDATE … WHERE version = :base` ; zéro ligne affectée ⇒ `409`.
- **Chargement paresseux** : `GET /courses/lessons/{id}` renvoie les métadonnées + pages ; `GET /pages/{id}/strokes` charge les tracés **page par page**.
- Évolution possible si le volume explose : stocker `points` en tableau binaire compact (float32, delta) dans `BYTEA`. À ne faire **que si** le monitoring montre un problème (JSONB est déjà compressé par TOAST).

### 5.4 TÂCHE DB-4 — Nouvelles tables

```python
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    family_id: Mapped[UUID] = mapped_column(index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None]
    user_agent: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

class UserSettings(Base):
    __tablename__ = "user_settings"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    ocr_language: Mapped[str] = mapped_column(String(5), default="fr")
    ui_language: Mapped[str] = mapped_column(String(5), default="fr")
    consent_train: Mapped[bool] = mapped_column(default=False)
    consent_cloud_ocr: Mapped[bool] = mapped_column(default=False)
    consent_updated_at: Mapped[datetime | None]
    stylus_only: Mapped[bool] = mapped_column(default=False)

class OcrJob(Base):
    __tablename__ = "ocr_jobs"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    page_id: Mapped[UUID | None] = mapped_column(ForeignKey("notebook_pages.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(12), default="queued")    # queued|running|done|failed
    progress: Mapped[int] = mapped_column(default=0)
    language: Mapped[str] = mapped_column(String(5))
    engine: Mapped[str | None] = mapped_column(String(64))
    model_version: Mapped[str | None] = mapped_column(String(64))
    result_json: Mapped[dict | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    finished_at: Mapped[datetime | None]

class UserDictionary(Base):                  # apprentissage immédiat à partir des corrections
    __tablename__ = "user_dictionary"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    language: Mapped[str] = mapped_column(String(5))
    wrong: Mapped[str] = mapped_column(String(100))        # forme produite par le modèle (minuscule)
    right: Mapped[str] = mapped_column(String(100))        # forme corrigée
    count: Mapped[int] = mapped_column(default=1)
    last_seen: Mapped[datetime] = mapped_column(server_default=func.now())
    __table_args__ = (UniqueConstraint("user_id", "language", "wrong", name="uq_userdict"),)

class ModelVersion(Base):                    # registre des modèles IA
    __tablename__ = "model_versions"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(64))           # ex: trocr-fr
    version: Mapped[str] = mapped_column(String(32))        # ex: 2026.11.1
    language: Mapped[str] = mapped_column(String(5))
    artifact_uri: Mapped[str]                               # s3://… ou chemin
    base_model: Mapped[str] = mapped_column(String(128))
    train_samples: Mapped[int]
    metrics: Mapped[dict] = mapped_column(JSONB)            # {"cer":0.081,"wer":0.19,"cer_accents":0.11,...}
    status: Mapped[str] = mapped_column(String(12))         # candidate|active|retired|rejected
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    __table_args__ = (UniqueConstraint("name", "version"),)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[UUID | None]
    action: Mapped[str] = mapped_column(String(64))         # login, export, delete_account, consent_change…
    ip: Mapped[str | None] = mapped_column(String(45))
    meta: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)
```

**Extension de `ocr_corrections` pour la correction mot par mot :**

```sql
ALTER TABLE ocr_corrections
  ADD COLUMN scope          VARCHAR(8)  NOT NULL DEFAULT 'line',   -- 'word' | 'line'
  ADD COLUMN word_index     INTEGER,                               -- position du mot dans la ligne
  ADD COLUMN line_predicted TEXT,                                  -- ligne complète avant correction
  ADD COLUMN line_corrected TEXT,                                  -- ligne complète après correction
  ADD COLUMN alternatives   JSONB,                                 -- hypothèses proposées au moment de la correction
  ADD COLUMN source         VARCHAR(16) NOT NULL DEFAULT 'manual', -- 'manual' | 'suggestion' | 'dictionary'
  ADD COLUMN consent_withdrawn_at TIMESTAMPTZ;
ALTER TABLE ocr_corrections ADD CONSTRAINT ck_scope CHECK (scope IN ('word','line'));
```

### 5.5 TÂCHE DB-5 — Exploitation

- **PgBouncer** en mode `transaction`, pool SQLAlchemy `pool_size=10, max_overflow=20, pool_pre_ping=True, pool_recycle=1800`.
- **Sauvegardes** : `pg_dump` quotidien + WAL archiving (PITR), rétention 14 jours, **test de restauration mensuel** documenté.
- **Utilisateur applicatif** à privilèges minimaux (pas de `SUPERUSER`, pas de `CREATE` en prod ; les migrations utilisent un rôle distinct).
- Requêtes lentes : `log_min_duration_statement = 300ms`, extension `pg_stat_statements`.
- Évolution possible : *Row Level Security* PostgreSQL en défense en profondeur (`SET app.user_id` par requête).
- Jeu de données de test et script `seed` pour les environnements de dev.

---

## 6. Interface et expérience utilisateur (Flutter + Angular)

### 6.1 Principes directeurs

1. **L'écriture est reine.** La feuille occupe un maximum d'écran ; tout le reste est discret, repliable.
2. **Toujours montrer l'état du système** : enregistré ? en cours ? erreur ? hors ligne ? Aucun libellé statique mensonger.
3. **Rien de destructif sans filet** : confirmation **ou** annulation possible (snackbar « Annuler »).
4. **Le modèle doute, l'interface le dit** : la confiance affichée est toujours réelle, et les mots douteux sont corrigeables en 2 gestes.
5. **Cohérence mobile/web** : mêmes noms, mêmes icônes, mêmes regroupements.
6. **Accessibilité** : cibles tactiles ≥ 48 dp (Flutter) / 44 px (web), contraste WCAG AA (≥ 4,5:1), étiquettes sémantiques, ne **jamais** coder une information uniquement par la couleur.
7. **Internationalisation** : textes dans des fichiers de traduction (fr, en, ar, de), support **RTL** pour l'arabe.

### 6.2 Boutons et éléments à corriger — Flutter (écran Notebook)

| #   | Élément actuel                                       | Problème                                                                       | Correction précise                                                                                                                                                                                                           |
| --- | ---------------------------------------------------- | ------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | AppBar : `[☰][Titre][−][75%][+][⊞][✏/✋]`             | 7 contrôles : surchargé, cibles trop petites, mélange navigation / zoom / mode | Garder `[← retour][Titre + puce d'état][✏/✋][⋮]`. Le zoom passe dans un **badge flottant** en bas à droite (`75 %`, tap = ajuster à l'écran, appui long = 100 %) + pincement. Le reste va dans le menu `⋮`                   |
| 2   | Outils de dessin **dans le Drawer** (mobile)         | L'outil le plus utilisé est caché derrière un menu                             | **Barre d'outils flottante** repliable (bord gauche en paysage, bas en portrait) : stylo, gomme, couleur, épaisseur, annuler, rétablir. Le Drawer ne garde que la **navigation** (matières, cours)                           |
| 3   | Bouton `💾 Sauvegarder`                              | Sauvegarde manuelle = oubli = perte                                            | **Autosave** (debounce 2 s après le dernier tracé) + **puce d'état** : `Enregistré ✓` / `Enregistrement…` / `Hors ligne — en attente` / `Échec · Réessayer`. Le bouton disparaît (ou devient « Forcer la synchro » dans `⋮`) |
| 4   | Bouton `📄 PDF`                                      | Un seul bouton, deux types d'export derrière                                   | Ouvre une **feuille** avec 2 cartes (« Fidèle (mes tracés) » / « Structuré (texte IA) »), une description d'une ligne chacune, un indicateur de progression et un message d'erreur                                           |
| 5   | Bouton `🔍 Transcription OCR`                        | Libellé technique, aucune indication de langue/progression, pas annulable      | Renommer **« Reconnaître l'écriture »**, à côté un **sélecteur de langue** (`FR ▾`). Pendant le traitement : barre de progression + bouton **Annuler** ; bouton désactivé tant que le job tourne                             |
| 6   | Icône poubelle « Effacer la page »                   | Destructive, pas de confirmation                                               | Dialogue de confirmation **ou** effacement immédiat + snackbar `Page effacée · ANNULER` (10 s). Icône distincte d'« annuler »                                                                                                |
| 7   | Annuler / Rétablir                                   | Visibilité variable                                                            | Toujours visibles dans la barre flottante, **grisés** quand inutilisables, raccourcis clavier/stylet (double tap sur le côté du stylet si supporté)                                                                          |
| 8   | Gomme                                                | Un seul mode ?                                                                 | Deux modes : **gomme trait** (supprime un tracé entier) et **gomme précise** ; aperçu du rayon pendant l'effacement                                                                                                          |
| 9   | Palette 5 couleurs                                   | Limité                                                                         | 8 couleurs prédéfinies + **couleurs récentes** + sélecteur libre ; l'**aperçu d'épaisseur** est un trait réel et non une puce                                                                                                |
| 10  | Épaisseurs 1.5 / 3.0 / 5.0                           | Valeurs techniques                                                             | 3 presets visuels (fin / moyen / épais) + curseur dans « Plus »                                                                                                                                                              |
| 11  | « Retour Dashboard » avec dialogue si non sauvegardé | À remplacer                                                                    | Avec l'autosave, plus de dialogue : le bouton retour sauvegarde puis revient ; dialogue **uniquement** si la sauvegarde a échoué (« Quitter sans enregistrer ? »)                                                            |
| 12  | Toggle ✏/✋ (dessin / pan)                            | Icône ambiguë                                                                  | Libellé accessible + infobulle ; **par défaut** : un doigt = pan, stylet = dessin (comme les apps pro) ; option « Dessiner aussi au doigt » dans les paramètres                                                              |
| 13  | Pas de navigation entre pages visible                | Perte de repère                                                                | Bande de pages (vignettes) repliable + indicateur `Page 2/5` + bouton `+ Page`                                                                                                                                               |
| 14  | Pas de rejet de la paume                             | Traits parasites                                                               | Si un stylet est détecté, ignorer les `PointerDeviceKind.touch` pendant le dessin (`stylusOnly` auto)                                                                                                                        |
| 15  | Bottom sheet OCR : texte seulement                   | Pas de confiance, pas de correction                                            | Voir §6.4 (feuille à 3 onglets)                                                                                                                                                                                              |

**Cibles tactiles — implémentation :**

```dart
IconButton(
  tooltip: 'Annuler',
  constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
  icon: const Icon(Icons.undo),
  onPressed: canUndo ? controller.undo : null,    // null = grisé automatiquement
)
```

**Puce d'état de sauvegarde :**

```dart
class SaveStatusChip extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final s = ref.watch(saveStatusProvider);       // enum: saved, saving, offline, failed
    final (icon, label, color) = switch (s) {
      SaveStatus.saved   => (Icons.check_circle, 'Enregistré', Colors.green),
      SaveStatus.saving  => (Icons.sync, 'Enregistrement…', Colors.blueGrey),
      SaveStatus.offline => (Icons.cloud_off, 'Hors ligne', Colors.orange),
      SaveStatus.failed  => (Icons.error, 'Échec · Réessayer', Colors.red),
    };
    return Semantics(
      label: label, liveRegion: true,
      child: ActionChip(avatar: Icon(icon, size: 16, color: color), label: Text(label),
          onPressed: s == SaveStatus.failed ? () => ref.read(notebookProvider.notifier).retrySave() : null),
    );
  }
}
```

### 6.3 Boutons et éléments à corriger — Angular (éditeur web)

| #   | Élément actuel                                                             | Problème                                                                   | Correction précise                                                                                                                                                                                                                                                                      |
| --- | -------------------------------------------------------------------------- | -------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | `Confiance : 96 %` **codée en dur**                                        | Information fausse, trompeuse                                              | Calculer depuis le résultat : moyenne **pondérée par le nombre de caractères** des `lines[].confidence` ; afficher aussi la **confiance minimale** et le nombre de mots douteux. Si pas de résultat, ne rien afficher                                                                   |
| 2   | « Auto-save actif » statique                                               | Peut être faux                                                             | Même puce d'état que Flutter, branchée sur l'état réel du store                                                                                                                                                                                                                         |
| 3   | En-tête : `Enregistrer / Exporter PDF / Transcription OCR / Génération IA` | 4 actions de même poids, « Génération IA » vs « Transcription OCR » ambigu | Action principale unique **« Reconnaître l'écriture »** (bouton plein) ; `Exporter ▾` (menu : PDF fidèle, PDF structuré) ; `Enregistrer` devient discret. Fusionner « Génération IA » dans l'export structuré, ou la renommer clairement (« Mettre en forme avec l'IA ») avec infobulle |
| 4   | Panneau IA : `<pre>{{ fullMarkdown }}</pre>`                               | Texte brut non interactif                                                  | Remplacer par le composant **OcrResultPanel** (§6.4) : mots cliquables, confiance réelle, copier, correction                                                                                                                                                                            |
| 5   | Canvas sans zoom                                                           | Écriture fine impossible sur petit écran                                   | Zoom molette+Ctrl, pincement, pan à 2 doigts / espace+glisser, boutons `− 100 % +`, « Ajuster » (§3.3 NG-2)                                                                                                                                                                             |
| 6   | Événements souris + tactile séparés                                        | Pas de pression, pas de stylet                                             | **Pointer Events** (§3.3 NG-2), `touch-action: none`                                                                                                                                                                                                                                    |
| 7   | Barre d'outils horizontale dense                                           | Mélange outils, palette, épaisseurs, historique, pages                     | Regrouper : `[Outils]` `[Couleur + épaisseur en popover]` `[↩ ↷]` `[🗑 avec confirmation]` ; pages dans une barre dédiée en bas                                                                                                                                                         |
| 8   | Navigation de pages `‹ 1/1 ›`                                              | Minimaliste                                                                | Ajouter vignettes, suppression/duplication/réordonnancement de page, saisie directe du numéro                                                                                                                                                                                           |
| 9   | Modal export PDF                                                           | Pas d'état de chargement ni d'erreur                                       | Spinner par carte, désactivation pendant l'export, message d'erreur, nom de fichier proposé `Matière - Cours.pdf`                                                                                                                                                                       |
| 10  | Bouton « 🧹 Gomme »                                                        | Un seul mode                                                               | Mêmes deux modes que Flutter                                                                                                                                                                                                                                                            |
| 11  | Pas de raccourcis                                                          | —                                                                          | `Ctrl+Z/Y`, `Ctrl+S`, `P` stylo, `E` gomme, `+/−` zoom, `←/→` pages ; afficher une aide `?`                                                                                                                                                                                             |
| 12  | Pas d'état vide ni d'erreur                                                | —                                                                          | États vides illustrés (nouveau cours), bannière d'erreur réseau avec « Réessayer »                                                                                                                                                                                                      |
| 13  | Thème                                                                      | Pas de mode sombre                                                         | Variables CSS + `prefers-color-scheme` ; la **feuille** reste claire (ou option « feuille sombre » avec inversion contrôlée du trait par défaut)                                                                                                                                        |

**Calcul de la vraie confiance (Angular) :**

```typescript
// ocr-panel.component.ts
readonly avgConfidence = computed(() => {
  const lines = this.store.ocrResult()?.lines ?? [];
  const chars = lines.reduce((n, l) => n + l.text.length, 0);
  return chars ? lines.reduce((s, l) => s + l.confidence * l.text.length, 0) / chars : null;
});
readonly uncertainWords = computed(() =>
  (this.store.ocrResult()?.lines ?? []).flatMap(l => l.words ?? []).filter(w => w.confidence < 0.6).length);
```

```html
@if (avgConfidence() !== null) {
  <span class="stat-tag" [attr.data-level]="level(avgConfidence()!)">
    Confiance : {{ avgConfidence() | percent:'1.0-0' }}
  </span>
  @if (uncertainWords() > 0) { <span class="stat-tag warn">{{ uncertainWords() }} mot(s) à vérifier</span> }
}
```

### 6.4 La fonctionnalité centrale : le panneau de résultat OCR avec correction mot par mot

C'est **la** fonctionnalité qui manque. Elle fait le lien entre l'UI et l'apprentissage du modèle.

#### Ce que doit contenir la feuille de résultat (même contenu Flutter et Angular)

```
┌──────────────────────────────────────────────────────────────┐
│ Résultat de la reconnaissance            Langue : FR ▾   [✕] │
│ Confiance 87 %  ·  3 mots à vérifier                         │
│ ─────────────────────────────────────────────────────────── │
│ [ Texte ]  [ Mot à mot ]  [ Structure ]                      │
│ ─────────────────────────────────────────────────────────── │
│  Les  fonctions  d̲é̲r̲i̲v̲a̲b̲l̲e̲s̲  sont  c̲o̲n̲t̲i̲n̲u̲e̲s̲  …             │
│        (souligné pointillé orange)   (souligné rouge)        │
│                                                              │
│ Légende : ▬ sûr   ┄ à vérifier   ▃ probablement faux         │
│ ─────────────────────────────────────────────────────────── │
│ [ Copier ]  [ Partager ]  [ Exporter PDF structuré ]         │
└──────────────────────────────────────────────────────────────┘
```

- Onglet **Texte** : texte final, mots douteux soulignés (**style de soulignement différent selon le niveau**, pas seulement la couleur).
- Onglet **Mot à mot** : une ligne par ligne manuscrite, avec **la vignette de l'image de la ligne** à gauche (rendue côté serveur) et les mots en puces à droite — l'utilisateur compare l'écriture au texte.
- Onglet **Structure** : blocs h1/h2/texte/schéma comme aujourd'hui.
- Les corrections faites sont visibles immédiatement et marquées `✎ corrigé`.
- Bouton **Annuler** sur chaque correction (retour au texte du modèle).

#### Seuils de confiance (configurables côté serveur, calibrés sur le benchmark, §8.4)

| Niveau            | Seuil initial | Marquage                             |
| ----------------- | ------------- | ------------------------------------ |
| Sûr               | ≥ 0,80        | aucun                                |
| À vérifier        | 0,50 – 0,80   | soulignement pointillé orange        |
| Probablement faux | < 0,50        | soulignement plein rouge + icône `!` |

#### Interaction de correction (tap sur un mot)

```
┌──────────────── Corriger un mot ─────────────────┐
│  [ image de la zone manuscrite autour du mot ]    │
│                                                   │
│  Reconnu :  « derivables »        confiance 41 %  │
│  Suggestions :  ( dérivables )  ( derivable )     │
│  Votre correction :                               │
│  ┌─────────────────────────────────────────────┐ │
│  │ dérivables                                  │ │
│  └─────────────────────────────────────────────┘ │
│  ☐ Appliquer à tous les mots identiques de la page│
│  ☐ Aider à améliorer la reconnaissance (opt-in)   │
│                                                   │
│            [ Annuler ]      [ Corriger ]          │
└───────────────────────────────────────────────────┘
```

- Les **suggestions** viennent de l'API (`alternatives`, beam search + dictionnaire — §8.3).
- La case « Aider à améliorer » reflète `consent_train` (pré-cochée **uniquement** si l'utilisateur a déjà consenti dans les paramètres, jamais par défaut).
- Valider = **mise à jour locale instantanée** + `POST /ocr/feedback` en tâche de fond (file hors ligne si pas de réseau).
- Clavier Arabe/Allemand : le `TextField` adopte la **direction du texte** (`TextDirection.rtl` si la langue est `ar`).

#### Flutter — widgets

```dart
// features/notebook/presentation/ocr/word_chip.dart
enum ConfLevel { sure, check, wrong }
ConfLevel levelOf(double c) => c >= .80 ? ConfLevel.sure : c >= .50 ? ConfLevel.check : ConfLevel.wrong;

class WordChip extends StatelessWidget {
  const WordChip({super.key, required this.word, required this.onTap});
  final RecognizedWord word;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final lvl = levelOf(word.confidence);
    final deco = switch (lvl) {
      ConfLevel.sure  => TextDecoration.none,
      ConfLevel.check => TextDecoration.underline,        // + style dotted
      ConfLevel.wrong => TextDecoration.underline,        // + style solid, couleur rouge
    };
    return Semantics(
      label: '${word.text}, confiance ${(word.confidence * 100).round()} pour cent'
             '${word.corrected ? ", corrigé" : ""}',
      button: true,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(6),
        child: ConstrainedBox(
          constraints: const BoxConstraints(minHeight: 40, minWidth: 40),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 6),
            child: Text(word.text, style: TextStyle(
              decoration: deco,
              decorationStyle: lvl == ConfLevel.check ? TextDecorationStyle.dotted : TextDecorationStyle.solid,
              decorationColor: lvl == ConfLevel.wrong ? Colors.red : Colors.orange,
              fontStyle: word.corrected ? FontStyle.italic : FontStyle.normal,
            )),
          ),
        ),
      ),
    );
  }
}

// Ligne : Wrap des mots, en respectant la direction (RTL pour l'arabe)
Directionality(
  textDirection: lang == 'ar' ? TextDirection.rtl : TextDirection.ltr,
  child: Wrap(children: [for (final w in line.words) WordChip(word: w, onTap: () => _correct(line, w))]),
)
```

```dart
Future<void> _correct(LineResult line, RecognizedWord w) async {
  final result = await showModalBottomSheet<WordCorrection>(
    context: context, isScrollControlled: true, useSafeArea: true,
    builder: (_) => WordCorrectionSheet(line: line, word: w),
  );
  if (result == null) return;
  ref.read(ocrControllerProvider.notifier).applyCorrection(line.id, w.index, result.text);
  // → met à jour l'UI, puis enfile l'envoi : POST /ocr/feedback (voir §8.5)
}
```

#### Angular — composant

```typescript
@Component({
  selector: 'app-ocr-line', standalone: true, changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="line" [attr.dir]="lang() === 'ar' ? 'rtl' : 'ltr'">
      @for (w of line().words; track w.index) {
        <button type="button" class="word" [class]="level(w.confidence)"
                [attr.aria-label]="w.text + ', confiance ' + (w.confidence*100 | number:'1.0-0') + ' pour cent'"
                (click)="correct.emit(w)">{{ w.text }}</button>
      }
    </div>`,
  styles: [`
    .word { background:none; border:0; padding:6px 4px; min-height:44px; cursor:pointer; font:inherit; }
    .word.check { text-decoration: underline dotted orange; }
    .word.wrong { text-decoration: underline solid red; }
    .word.corrected { font-style: italic; }
  `],
})
export class OcrLineComponent {
  line = input.required<LineResult>();
  lang = input<string>('fr');
  correct = output<RecognizedWord>();
  level = (c: number) => c >= .8 ? 'sure' : c >= .5 ? 'check' : 'wrong';
}
```

### 6.5 Mode hors ligne et synchronisation

- Flutter : base locale (`drift` ou `isar`) = **source de vérité de l'éditeur** ; la synchro serveur est asynchrone. File d'opérations (`added`, `removed`, `corrections`) rejouée à la reconnexion, idempotente grâce aux `client_id`.
- Angular : `IndexedDB` (via `idb`) pour le brouillon courant ; avertissement `beforeunload` s'il reste des modifications non synchronisées.
- Gestion de conflit (`409`) : proposer « Garder ma version / Charger la version serveur / Fusionner (nouveaux tracés des deux côtés) ».

### 6.6 Écrans à ajouter ou à enrichir

#### Dashboard

- Recherche, tri (récents, alphabétique, matière), filtre par matière.
- Cartes de cours avec **vignette** de la page 1 (générée côté client à l'enregistrement, ≤ 20 Ko), date de modification, nombre de pages.
- Menu par carte : renommer, dupliquer, déplacer, exporter, supprimer (avec corbeille 30 jours).
- État vide guidé (« Créez votre première matière »), squelettes de chargement.

#### Authentification

- Afficher/masquer le mot de passe, validation en direct, messages d'erreur précis mais non énumérants.
- Mot de passe oublié (e-mail de réinitialisation à usage unique, expirant en 30 min).
- Verrouillage biométrique optionnel (Flutter : `local_auth`).

#### Paramètres (nouvel écran, absent aujourd'hui)

| Section         | Contenu                                                                                                                                                                                                                    |
| --------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Reconnaissance  | Langue par défaut (🇫🇷 🇬🇧 🇸🇦 🇩🇪), moteur préféré (Auto / Local / Serveur), seuils d'alerte de confiance                                                                                                                     |
| Écriture        | Stylet uniquement, rejet de la paume, épaisseur par défaut, grille (lignes / carreaux / vierge)                                                                                                                            |
| Confidentialité | Consentement « améliorer la reconnaissance » (`consent_train`), consentement « reconnaissance cloud avancée » (`consent_cloud_ocr`), **Mes corrections** (liste + suppression), Exporter mes données, Supprimer mon compte |
| Apparence       | Thème clair/sombre/système, langue de l'interface, taille du texte                                                                                                                                                         |
| À propos        | Version, version du modèle actif, licences                                                                                                                                                                                 |

#### Écran « Mes corrections » (transparence RGPD + valeur utilisateur)

Liste paginée des corrections, avec vignette de la ligne, texte avant/après, interrupteur « utilisée pour l'entraînement », bouton supprimer. Alimente `GET /ocr/corrections` et `DELETE /ocr/corrections/{id}` qui existent déjà.

### 6.7 Sélecteur de langue

- Composant unique `LanguageSelector` (chip `FR ▾` ouvrant une liste : Français, English, العربية, Deutsch).
- Valeur persistée dans `user_settings.ocr_language` ; **plus de `'en'` codé en dur** dans `api_client.dart` (ligne 196 selon l'audit).
- Valeur transmise dans `options.language` de chaque requête ; la réponse renvoie la langue et le moteur **réellement utilisés** (peut différer si repli) et l'UI l'affiche (« Reconnu avec : TrOCR-FR v2026.11 »).
- Optionnel : « Détection automatique » (§8.2).

### 6.8 Critères d'acceptation UI

- [ ] Plus aucune valeur de confiance codée en dur
- [ ] La puce d'état reflète l'état réel (test : couper le réseau → « Hors ligne »)
- [ ] Un tap sur un mot ouvre la correction ; valider met à jour le texte sans recharger
- [ ] Toutes les cibles tactiles ≥ 48 dp / 44 px (audit `flutter test` + axe-core)
- [ ] Lecteur d'écran : chaque bouton a un nom ; contraste AA
- [ ] Interface arabe entièrement en RTL, sans texte tronqué
- [ ] Angular : zoom 50–400 % sans décalage des tracés (les coordonnées stockées restent en repère page)

---

## 7. Le modèle IA — ce qui manque (diagnostic synthétique)

### 7.1 Tableau des manques

| #   | Manque                                                                      | Conséquence visible                                         | Réponse                                                                 | Section         |
| --- | --------------------------------------------------------------------------- | ----------------------------------------------------------- | ----------------------------------------------------------------------- | --------------- |
| M1  | Le modèle est **monolingue anglais** (IAM)                                  | « été » → « ete », « garçon » → « garcon », arabe illisible | Routage par langue + fine-tuning FR + moteurs dédiés (ar, de)           | §8.1, 8.2, 8.6  |
| M2  | `language` **ignoré** par le moteur ; Flutter force `'en'`                  | Changer la langue ne change rien                            | Registre de moteurs piloté par `options.language`                       | §8.1, 8.2, §6.7 |
| M3  | **Aucune correction mot par mot**                                           | L'utilisateur ne peut rien rectifier                        | API `words` + UI §6.4                                                   | §8.3            |
| M4  | **Aucun apprentissage** : `ocr/feedback` jamais appelé, corrections perdues | Le système refait les mêmes erreurs                         | Boucle de feedback, dictionnaire personnel, mémoire de lignes           | §8.5            |
| M5  | **Pas de ré-entraînement** ni de registre de modèles                        | Impossible d'améliorer et de revenir en arrière             | Pipeline MLOps (export → fine-tune → évaluation → promotion → rollback) | §8.6, 8.7       |
| M6  | **Post-traitement nul** (`re.sub`)                                          | Accents, ponctuation, apostrophes non corrigés              | Post-traitement par langue (dictionnaire, accents, typographie)         | §8.10           |
| M7  | **Confiance non calibrée** (greedy ≈ toujours 0,95)                         | L'utilisateur ne sait pas où le modèle doute                | Beam search + confiance min + calibration isotonique                    | §8.4            |
| M8  | **Benchmark vide** (`labels.json = {}`)                                     | Aucune amélioration n'est mesurable                         | Jeu de test annoté + CI                                                 | §8.9            |
| M9  | `preprocessing.py` vide, rendu non optimisé, `MAX_DESKEW_DEG` non appliqué  | Précision laissée sur la table                              | Module de rendu configurable + A/B                                      | §8.8            |
| M10 | Pas de repli en cas de faible confiance                                     | Une ligne ratée reste ratée                                 | Chaîne de moteurs + VLM sous consentement                               | §8.11           |
| M11 | Cache à empreinte grossière (miniature 64×16)                               | **Résultat périmé** si l'on ajoute un accent ou un point    | Empreinte basée sur le contenu exact des tracés + version du modèle     | §8.12           |
| M12 | Données temporelles des tracés perdues                                      | Précision inférieure à un moteur « online »                 | ML Kit Digital Ink sur mobile                                           | §8.13           |
| M13 | Pas de suivi qualité en production                                          | Dérive invisible                                            | Métriques taux de correction par langue/modèle                          | §9.3            |

### 7.2 Point de vigilance juridique (à traiter avant commercialisation)

Les poids `microsoft/trocr-base-handwritten` sont sous licence MIT, mais ils ont été **entraînés sur la base IAM**, dont les conditions d'usage sont, à ma connaissance, orientées recherche. ⚠️ **À VÉRIFIER** par le responsable du projet : licence IAM pour un usage commercial, licence RIMES, licence de chaque modèle communautaire. Documenter dans `docs/LICENCES_MODELES.md` : modèle, source, licence, date de vérification. Sans cette vérification, ne pas distribuer commercialement un modèle fine-tuné à partir de ces données.

---

## 8. Le modèle IA — corrections à appliquer, une par une

> Chaque sous-section : **Problème → Solution → Code → Vérification**.

### 8.1 TÂCHE ML-1 — Abstraction des moteurs et registre de modèles

**Problème :** le moteur TrOCR est un singleton unique ; impossible d'avoir un moteur par langue, un moteur de repli, ou une nouvelle version.

**Solution :** une interface commune, un registre à chargement paresseux (LRU : max 2 modèles en mémoire, un modèle `base` pèse ≈ 1,3 Go), une configuration YAML.

```python
# app/ml/engines/base.py
from dataclasses import dataclass, field
from typing import Protocol, Sequence
from PIL import Image

@dataclass
class WordOut:
    index: int
    text: str
    confidence: float                       # confiance calibrée [0,1]
    alternatives: list[str] = field(default_factory=list)
    bbox: list[float] | None = None         # [xMin,yMin,xMax,yMax] repère page (voir §8.3)
    corrected: bool = False                 # modifié par le dictionnaire utilisateur
    original: str | None = None

@dataclass
class LineOut:
    text: str
    confidence: float                       # confiance de la ligne (min pondérée, voir §8.4)
    min_word_confidence: float
    words: list[WordOut]
    alternatives: list[str] = field(default_factory=list)   # n-best de la ligne
    engine: str = ""
    model_version: str = ""

class OcrEngine(Protocol):
    name: str
    version: str
    languages: frozenset[str]
    def recognize_lines(self, images: Sequence[Image.Image], *, num_beams: int = 4,
                        n_best: int = 3, with_words: bool = True) -> list[LineOut]: ...
    def unload(self) -> None: ...
```

```yaml
# app/ml/models.yaml
engines:
  trocr_en:
    type: trocr
    source: microsoft/trocr-base-handwritten
    revision: <SHA du commit épinglé>          # ⚠️ renseigner
    languages: [en]
  trocr_fr:
    type: trocr
    source: ${MODELS_DIR}/trocr-fr/active      # modèle fine-tuné par NOTRE pipeline (§8.6)
    fallback_source: <modèle FR communautaire> # ⚠️ À VÉRIFIER (qualité + licence) — ex. agomberto/trocr-large-handwritten-fr
    languages: [fr]
  trocr_de:
    type: trocr
    source: microsoft/trocr-base-handwritten   # provisoire : + post-traitement DE (§8.10)
    languages: [de]
  vlm_fallback:
    type: vlm
    provider: <fournisseur>
    requires_consent: cloud_ocr
    languages: [fr, en, ar, de]

routing:                        # ordre = priorité ; le suivant n'est utilisé que si la confiance est insuffisante
  fr: { chain: [trocr_fr, vlm_fallback], min_confidence: 0.55 }
  en: { chain: [trocr_en, vlm_fallback], min_confidence: 0.55 }
  de: { chain: [trocr_de, vlm_fallback], min_confidence: 0.55 }
  ar: { chain: [vlm_fallback],           min_confidence: 0.0  }   # + ML Kit côté mobile (§8.13)
```

```python
# app/ml/registry.py
import threading
from collections import OrderedDict

class EngineRegistry:
    def __init__(self, cfg: dict, max_loaded: int = 2):
        self.cfg, self.max_loaded = cfg, max_loaded
        self._loaded: OrderedDict[str, OcrEngine] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, engine_name: str) -> OcrEngine:
        with self._lock:
            if engine_name in self._loaded:
                self._loaded.move_to_end(engine_name)
                return self._loaded[engine_name]
            while len(self._loaded) >= self.max_loaded:
                _, old = self._loaded.popitem(last=False)
                old.unload()                       # libère la mémoire (gc + torch.cuda.empty_cache())
            eng = build_engine(engine_name, self.cfg["engines"][engine_name])
            self._loaded[engine_name] = eng
            return eng

    def chain_for(self, language: str) -> tuple[list[str], float]:
        r = self.cfg["routing"].get(language) or self.cfg["routing"]["en"]
        return r["chain"], r["min_confidence"]
```

**Vérification :** test unitaire — demander `language="fr"` puis `"en"` retourne deux moteurs différents (`line.engine`), et le troisième chargement évince le moins récent.

### 8.2 TÂCHE ML-2 — La langue devient réellement active

**Chaîne complète à modifier :**

1. **Client** (§6.7) : envoie `options.language` choisi par l'utilisateur ; fin du `'en'` codé en dur.
2. **API** : `language` validé (`Literal["fr","en","ar","de","auto"]`).
3. **Service** :

```python
def run_pipeline(payload, user_ctx, on_progress):
    lang = payload.options.language or user_ctx.settings.ocr_language
    lines = segment(payload.strokes)
    images = [render_line(l, cfg=RENDER_CFG) for l in lines]
    if lang == "auto":
        return recognize_auto(images, user_ctx)
    return recognize_with_chain(images, lang, user_ctx, on_progress)

def recognize_with_chain(images, lang, user_ctx, on_progress):
    chain, min_conf = registry.chain_for(lang)
    results: list[LineOut | None] = [None] * len(images)
    pending = list(range(len(images)))
    for engine_name in chain:
        if not pending: break
        if engine_name == "vlm_fallback" and not user_ctx.settings.consent_cloud_ocr:
            continue                                        # JAMAIS de cloud sans consentement
        eng = registry.get(engine_name)
        outs = eng.recognize_lines([images[i] for i in pending], num_beams=beams_for(eng))
        still = []
        for i, out in zip(pending, outs):
            if results[i] is None or out.confidence > results[i].confidence:
                results[i] = out
            if out.confidence < min_conf:
                still.append(i)
        pending = still
    return results
```

4. **Mode `auto`** : essayer la langue préférée de l'utilisateur ; si la **confiance moyenne** < seuil **ou** si le **taux de mots présents dans le dictionnaire** de la langue < 50 %, essayer les autres langues disponibles et garder le meilleur score `confiance × taux_dictionnaire`. (Ne pas se fier à la seule détection de script : le moteur anglais ne produira jamais de caractères arabes.)
5. **Réponse** : toujours renvoyer `language`, `engine`, `modelVersion` réellement utilisés.

**Vérification :** même écriture, `fr` vs `en` → moteurs différents tracés dans la réponse ; test d'intégration avec un faux moteur.

### 8.3 TÂCHE ML-3 — Mots, alternatives et correction mot par mot (côté backend)

**Problème :** `recognize_line_with_word_scores()` existe mais n'est appelée nulle part (greedy uniquement, pas d'alternatives, pas de position).

#### a) Extraction des scores par mot en beam search avec n-best

```python
# app/ml/engines/trocr.py (extrait)
@torch.inference_mode()
def recognize_lines(self, images, *, num_beams=4, n_best=3, with_words=True):
    outs: list[LineOut] = []
    for chunk in batched(images, self.batch_size):
        pv = self.processor(images=[im.convert("RGB") for im in chunk], return_tensors="pt").pixel_values
        pv = pv.to(self.device, dtype=self.dtype)
        gen = self.model.generate(
            pv, num_beams=num_beams, num_return_sequences=n_best,
            max_new_tokens=128, early_stopping=True,
            return_dict_in_generate=True, output_scores=True,
        )
        # scores par token, alignés sur les séquences retournées (beam search)
        trans = self.model.compute_transition_scores(
            gen.sequences, gen.scores, gen.beam_indices, normalize_logits=False)   # log-probas
        seqs = gen.sequences.view(len(chunk), n_best, -1)
        trans = trans.view(len(chunk), n_best, -1)
        for b in range(len(chunk)):
            best_tokens = self.processor.tokenizer.convert_ids_to_tokens(seqs[b, 0, 1:])   # saute le token de départ
            probs = torch.exp(trans[b, 0]).tolist()
            words = group_tokens_to_words(best_tokens, probs)                # voir ci-dessous
            alts = [t.strip() for t in self.processor.batch_decode(seqs[b], skip_special_tokens=True)]
            outs.append(build_line_out(words, alts, self.name, self.version))
    return outs
```

> ⚠️ **À valider par un test** : avec le beam search, la somme des log-probas par token, divisée par la longueur selon `length_penalty`, doit redonner `sequences_scores` (écart < 1e-3). Si ce n'est pas le cas dans la version de `transformers` épinglée, ajuster `normalize_logits`. C'est le piège classique de cette API.

#### b) Regroupement tokens → mots

```python
def group_tokens_to_words(tokens: list[str], probs: list[float]) -> list[tuple[str, float]]:
    """BPE RoBERTa : un token commençant par 'Ġ' ouvre un nouveau mot.
    Confiance du mot = probabilité MINIMALE de ses tokens (un seul mauvais token suffit à douter)."""
    words, cur_t, cur_p = [], [], []
    for t, p in zip(tokens, probs):
        if t in ("</s>", "<pad>", "<s>"):
            if t == "</s>": break
            continue
        if t.startswith("Ġ") and cur_t:
            words.append(("".join(cur_t).replace("Ġ", ""), min(cur_p)))
            cur_t, cur_p = [], []
        cur_t.append(t); cur_p.append(p)
    if cur_t:
        words.append(("".join(cur_t).replace("Ġ", ""), min(cur_p)))
    return words
```

> Piège : la **ponctuation** collée à un mot (« bonjour, ») est un même mot pour ce découpage. C'est acceptable ; l'UI affiche le mot entier. Séparer la ponctuation finale seulement si le benchmark montre un gain.

#### c) Alternatives par mot

1. **n-best aligné** : si une hypothèse n-best a le **même nombre de mots** que la meilleure, les mots différents à la même position sont des alternatives.
2. **Dictionnaire** : pour tout mot < 0,80, ajouter jusqu'à 3 suggestions du correcteur de la langue (SymSpell, §8.10) et du **dictionnaire personnel** de l'utilisateur.
3. Dédupliquer, limiter à 3, trier par score.

#### d) Position des mots dans la page (pour afficher la zone manuscrite)

TrOCR n'aligne pas mots et pixels. On reconstitue par **clustering des tracés selon les espaces horizontaux** :

```python
def assign_word_boxes(line_strokes, words, rtl=False):
    """Découpe les tracés d'une ligne en groupes séparés par de grands espaces horizontaux ;
    si le nombre de groupes == nombre de mots, associe dans l'ordre de lecture.
    Sinon : répartition proportionnelle au nombre de caractères sur la largeur de la ligne."""
    boxes = sorted((bbox_of(s) for s in line_strokes), key=lambda b: b.xMin, reverse=rtl)
    h_med = median(b.yMax - b.yMin for b in boxes)
    groups, cur = [], [boxes[0]]
    for prev, b in zip(boxes, boxes[1:]):
        gap = (b.xMin - prev.xMax) if not rtl else (prev.xMin - b.xMax)
        if gap > 0.5 * h_med:                    # seuil à calibrer sur le benchmark
            groups.append(cur); cur = []
        cur.append(b)
    groups.append(cur)
    if len(groups) == len(words):
        return [union(g) for g in groups]
    return proportional_split(union(boxes), [len(w.text) for w in words], rtl)
```

#### e) Contrat d'API

```python
# app/schemas/recognition.py
class WordResult(BaseModel):
    index: int
    text: str
    confidence: float = Field(ge=0, le=1)
    alternatives: list[str] = []
    bbox: list[float] | None = None
    corrected: bool = False          # remplacé par le dictionnaire utilisateur
    original: str | None = None

class LineRecognitionResult(BaseModel):
    id: int
    stroke_ids: list[str]
    bbox: list[float]
    text: str
    confidence: float
    min_word_confidence: float
    words: list[WordResult] = []     # NOUVEAU
    alternatives: list[str] = []     # NOUVEAU (n-best de la ligne)
    thumbnail: str | None = None     # NOUVEAU : WebP base64 ≤ 8 Ko, uniquement si options.include_thumbnails
    engine: str
    model_version: str
```

- Route dédiée pour ré-analyser une seule ligne sélectionnée : `POST /api/v1/ocr/line-words` (corps = tracés de la ligne + langue) → `LineRecognitionResult`. Remplace l'usage non câblé de `reocr-line` ; **les clients doivent l'appeler** (bouton « Relire cette ligne » dans §6.4).
- `options.debug` : `False` par défaut ; les images de debug ne sont plus jamais renvoyées par défaut. Seule la **miniature** (≤ 320×64, WebP) sert à l'onglet « Mot à mot ».

**Vérification :** test sur une ligne synthétique : `len(words) == len(text.split())`, chaque `confidence ∈ [0,1]`, `alternatives` ≤ 3, et la sérialisation JSON < 20 Ko par ligne.

### 8.4 TÂCHE ML-4 — Confiance fiable et calibrée

**Problème :** moyenne des `max(softmax)` en greedy ≈ toujours 0,9+. Angular affiche même une valeur fictive.

**Solution en trois étages :**

1. **Brute** : beam search → probabilité de chaque token → confiance de mot = min des tokens (§8.3). Confiance de ligne = `0.5 × moyenne pondérée par la longueur + 0.5 × minimum des mots` (une ligne avec un mot douteux doit sortir en alerte).
2. **Calibration** : une probabilité de modèle n'est pas une probabilité d'être juste. Apprendre une fonction `confiance brute → P(mot correct)` sur le benchmark.

```python
# training/calibrate.py
from sklearn.isotonic import IsotonicRegression
import jiwer, joblib

def word_correctness(refs: list[str], hyps: list[str], hyp_confs: list[list[float]]):
    X, y = [], []
    for ref, hyp, confs in zip(refs, hyps, hyp_confs):
        out = jiwer.process_words(ref, hyp)
        for chunk in out.alignments[0]:
            if chunk.type == "equal":
                for k in range(chunk.hyp_end_idx - chunk.hyp_start_idx):
                    X.append(confs[chunk.hyp_start_idx + k]); y.append(1)
            elif chunk.type == "substitute":
                for k in range(chunk.hyp_end_idx - chunk.hyp_start_idx):
                    X.append(confs[chunk.hyp_start_idx + k]); y.append(0)
    return X, y

X, y = word_correctness(refs, hyps, confs)
iso = IsotonicRegression(out_of_bounds="clip").fit(X, y)
joblib.dump(iso, "artifacts/calibrator_fr.joblib")        # stocké avec la version du modèle
```

3. **Seuils** : choisir le seuil « sûr » tel que **≥ 95 %** des mots au-dessus sont corrects sur le benchmark ; le seuil « probablement faux » tel que **≥ 60 %** des mots en dessous sont réellement faux. Les écrire dans `models.yaml` par moteur et les exposer à l'UI (`thresholds: {sure: 0.8, wrong: 0.5}`).

**Métrique de qualité de la confiance :** ECE (Expected Calibration Error) < 0,08 ; tracer la courbe de fiabilité dans le rapport d'évaluation.

**Cas particulier :** si aucun calibrateur n'existe encore, renvoyer `calibrated: false` et l'UI affiche « confiance indicative » plutôt qu'un pourcentage affirmatif.

### 8.5 TÂCHE ML-5 — Apprendre de ses erreurs (boucle de feedback)

#### Les trois horizons d'apprentissage

| Horizon         | Mécanisme                                                                  | Effet                                                   | Délai                                    |
| --------------- | -------------------------------------------------------------------------- | ------------------------------------------------------- | ---------------------------------------- |
| **Immédiat**    | Mémoire de lignes + dictionnaire personnel                                 | La même erreur n'est pas refaite *pour cet utilisateur* | Instantané                               |
| **Court terme** | Mise à jour des listes de fréquence/lexique propres au projet, calibration | Meilleures suggestions et seuils                        | Quotidien/hebdomadaire                   |
| **Long terme**  | Fine-tuning du modèle (§8.6)                                               | Amélioration pour **tous** les utilisateurs consentants | Hebdomadaire à mensuel, après validation |

#### a) Enregistrement d'une correction

```python
# app/api/v1/ocr.py
@router.post("/ocr/feedback", status_code=201)
def feedback(body: FeedbackIn, user=Depends(current_user), db=Depends(get_db),
             settings: UserSettings = Depends(get_user_settings),
             _=Depends(rate_limit("feedback", per_minute=60))):
    if body.page_id:
        get_owned_page(body.page_id, user, db)                 # anti-IDOR
    train_ok = bool(body.consent_train and settings.consent_train)   # le serveur fait foi, pas le client
    corr = corrections_repo.create(
        db, user_id=user.id, page_id=body.page_id, scope=body.scope, word_index=body.word_index,
        stroke_ids=body.stroke_ids,
        strokes_json=body.strokes if train_ok else None,       # minimisation : pas de tracés sans consentement
        engine=body.engine, model_version=body.model_version, language=body.language,
        predicted_text=body.predicted_text, corrected_text=body.corrected_text,
        line_predicted=body.line_predicted, line_corrected=body.line_corrected,
        alternatives=body.alternatives, confidence=body.confidence,
        consent_train=train_ok, source=body.source,
    )
    user_dictionary_repo.bump(db, user.id, body.language, body.predicted_text, body.corrected_text)
    line_memory.store(user.id, body.stroke_fingerprint, body.line_corrected)    # §8.5 c
    return {"id": corr.id}
```

```python
class FeedbackIn(BaseModel):
    page_id: UUID | None = None
    scope: Literal["word", "line"]
    word_index: int | None = Field(default=None, ge=0, le=500)
    stroke_ids: list[str] = Field(max_length=500)
    strokes: list[Stroke] | None = Field(default=None, max_length=500)
    stroke_fingerprint: str = Field(max_length=64)
    language: Literal["fr", "en", "ar", "de"]
    engine: str = Field(max_length=64)
    model_version: str | None = Field(default=None, max_length=64)
    predicted_text: str = Field(max_length=MAX_TEXT_CORRECTION_LEN)
    corrected_text: str = Field(min_length=0, max_length=MAX_TEXT_CORRECTION_LEN)
    line_predicted: str | None = Field(default=None, max_length=MAX_TEXT_CORRECTION_LEN)
    line_corrected: str | None = Field(default=None, max_length=MAX_TEXT_CORRECTION_LEN)
    alternatives: list[str] | None = Field(default=None, max_length=5)
    confidence: float | None = Field(default=None, ge=0, le=1)
    consent_train: bool = False
    source: Literal["manual", "suggestion", "dictionary"] = "manual"
```

> **Anti-poison :** une correction n'entre dans le jeu d'entraînement qu'après filtres (§8.6.b). Un utilisateur malveillant ou négligent ne doit pas pouvoir dégrader le modèle commun.

#### b) Dictionnaire personnel — effet immédiat

```python
def bump(db, user_id, lang, wrong, right):
    w, r = wrong.strip().lower(), right.strip()
    if not w or not r or w == r.lower() or len(w) > 100 or " " in w:
        return
    stmt = pg_insert(UserDictionary).values(user_id=user_id, language=lang, wrong=w, right=r, count=1)
    stmt = stmt.on_conflict_do_update(constraint="uq_userdict",
        set_={"right": stmt.excluded.right, "count": UserDictionary.count + 1, "last_seen": func.now()})
    db.execute(stmt)

# Appliqué au post-traitement des résultats (jamais en silence : le mot est marqué `corrected`)
def apply_user_dictionary(words: list[WordOut], subs: dict[str, tuple[str, int]], conf_ceiling=0.85):
    for w in words:
        hit = subs.get(w.text.lower())
        if hit and w.confidence < conf_ceiling and (hit[1] >= 2 or w.confidence < 0.6):
            w.original, w.text, w.corrected = w.text, match_case(hit[0], w.text), True
```

Règles : n'agir que sur des mots **déjà corrigés par cet utilisateur** ; jamais sur un mot à confiance élevée ; toujours **réversible** (l'UI propose « Annuler la correction automatique ») ; plafonner la taille du dictionnaire (ex. 5 000 entrées/utilisateur, purge des plus anciennes).

#### c) Mémoire de lignes (exacte)

Si l'utilisateur corrige une ligne, puis relance l'OCR sans avoir modifié les tracés, **retourner le texte corrigé** sans rappeler le modèle. Clé : empreinte de contenu des tracés (§8.12), stockée en Redis (TTL 90 j) + persistée dans `ocr_corrections`. C'est le comportement attendu par l'utilisateur : « je l'ai déjà corrigé ».

#### d) Apprentissage actif (rentabiliser l'attention de l'utilisateur)

- Après un OCR, **mettre en avant** les mots à confiance 0,3–0,6 (la zone la plus informative) plutôt que ceux à 0,05 (illisibles) ou 0,95.
- Compteur discret « 3 mots à vérifier » (§6.3), jamais de popup bloquante.
- Statistiques de **confusions de caractères** pour comprendre les erreurs systématiques :

```python
import difflib, collections
def char_confusions(pairs):               # [(prédit, corrigé), ...]
    c = collections.Counter()
    for pred, true in pairs:
        for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, pred, true).get_opcodes():
            if op == "replace" and (i2 - i1) == (j2 - j1):
                for a, b in zip(pred[i1:i2], true[j1:j2]): c[(a, b)] += 1
    return c.most_common(30)           # ex. (('e','é'): 412, ('c','ç'): 57, ...)
```

Ce tableau (visible dans Grafana) dit **exactement quoi améliorer** : si `e→é` domine, le fine-tuning FR et la restauration d'accents sont la bonne priorité ; si ce sont des confusions `u/n`, c'est le rendu/segmentation.

### 8.6 TÂCHE ML-6 — Pipeline de ré-entraînement (MLOps)

```
corrections consenties ──► filtres qualité ──► rendu (même module qu'en production) ──► split par page
                                                                                          │
   données publiques/synthétiques (rejeu) ───────────────────────────────────────────────┤
                                                                                          ▼
                                          fine-tuning complet (ou LoRA si peu de données)
                                                                                          │
                                  évaluation : benchmark figé + hold-out de corrections
                                                                                          ▼
                           registre `model_versions` (candidate) ──► revue ──► canary 10 % ──► active
```

#### a) Déclenchement

- Tâche planifiée (Celery beat) hebdomadaire : lancer **seulement si** ≥ 500 nouvelles corrections validées pour la langue depuis le dernier modèle (sinon le bruit l'emporte).
- Jamais de promotion automatique en production dans les premières versions : **validation humaine** obligatoire.

#### b) Filtres qualité des corrections (anti-bruit / anti-poison)

```python
def keep(c) -> bool:
    if not c.consent_train or c.consent_withdrawn_at: return False
    if not c.strokes_json or not (1 <= len(c.corrected_text) <= 300): return False
    cer = char_error_rate(c.predicted_text, c.corrected_text)
    if cer > 0.6: return False                       # réécriture complète = probablement pas une correction
    if looks_like_spam(c.corrected_text): return False
    if user_contribution_share(c.user_id) > 0.05: return False   # plafonne l'influence d'un seul utilisateur
    return True
```

+ **Dédoublonnage** par empreinte de tracés, + **échantillon d'audit** manuel (50 lignes/mois relues par un humain).

#### c) Séparation train / val / test — règle d'or

**Par page (ou par utilisateur), jamais par ligne.** Sinon fuite de données et CER artificiellement bas.

```python
def split_of(page_id: str) -> str:
    h = int(hashlib.sha256(page_id.encode()).hexdigest(), 16) % 100
    return "test" if h < 10 else "val" if h < 20 else "train"        # déterministe et stable
```

Le **test** ne sert **jamais** à l'entraînement ni au réglage ; c'est le même jeu à chaque version → comparaisons valides.

#### d) Données d'entraînement : mélange et rejeu

| Source                                                                                                                              | Part indicative                         | Rôle                          |
| ----------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------- | ----------------------------- |
| Corrections consenties (rendu production)                                                                                           | 40–60 %                                 | Distribution réelle           |
| Jeu public français (ex. RIMES — ⚠️ licence à vérifier)                                                                              | 20–30 %                                 | Robustesse, vocabulaire       |
| Synthétique : texte FR rendu avec polices manuscrites + augmentations ; **ou tracés synthétiques rendus par notre module de rendu** | 10–30 %                                 | Accents, mots rares           |
| **Rejeu** (échantillon des anciennes données)                                                                                       | ≥ 20 %                                  | Éviter l'oubli catastrophique |
| Anglais (IAM)                                                                                                                       | 5–10 % si l'on veut conserver l'anglais | Éviter la régression EN       |

#### e) Script de fine-tuning (version production)

```python
# training/finetune_trocr.py
import torch, evaluate, random
from transformers import (TrOCRProcessor, VisionEncoderDecoderModel, Seq2SeqTrainer,
                          Seq2SeqTrainingArguments, default_data_collator, EarlyStoppingCallback)

def main(lang: str, base: str, out_dir: str, lr=3e-5, epochs=10, use_lora=False):
    processor = TrOCRProcessor.from_pretrained(base)
    model = VisionEncoderDecoderModel.from_pretrained(base)
    tok = processor.tokenizer
    model.config.decoder_start_token_id = tok.cls_token_id
    model.config.pad_token_id = tok.pad_token_id
    model.config.eos_token_id = tok.sep_token_id
    model.generation_config.max_new_tokens = 128
    model.generation_config.num_beams = 4

    if use_lora:                                        # peu de données (< ~3000 lignes) : plus sûr
        from peft import LoraConfig, get_peft_model
        model = get_peft_model(model, LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05,
                               target_modules=["query", "value"]))
    # sinon : TOUT le modèle est entraîné (la littérature montre que n'adapter que le décodeur est sous-optimal)

    train_ds = LineDataset("train", processor, augment=True)
    val_ds = LineDataset("val", processor, augment=False)
    cer = evaluate.load("cer")

    def metrics(p):
        p.label_ids[p.label_ids == -100] = tok.pad_token_id
        preds = tok.batch_decode(p.predictions, skip_special_tokens=True)
        refs = tok.batch_decode(p.label_ids, skip_special_tokens=True)
        return {"cer": cer.compute(predictions=preds, references=refs),
                "accent_err": accent_error_rate(preds, refs)}      # métrique dédiée au français

    args = Seq2SeqTrainingArguments(
        output_dir=out_dir, predict_with_generate=True, generation_num_beams=4,
        per_device_train_batch_size=4, gradient_accumulation_steps=8,       # batch effectif 32
        learning_rate=lr, weight_decay=0.01, warmup_ratio=0.05, lr_scheduler_type="cosine",
        num_train_epochs=epochs, fp16=torch.cuda.is_available(),
        eval_strategy="epoch", save_strategy="epoch", save_total_limit=2,
        load_best_model_at_end=True, metric_for_best_model="cer", greater_is_better=False,
        logging_steps=50, report_to="none", seed=42,
    )
    trainer = Seq2SeqTrainer(model=model, args=args, train_dataset=train_ds, eval_dataset=val_ds,
                             compute_metrics=metrics, data_collator=default_data_collator,
                             callbacks=[EarlyStoppingCallback(early_stopping_patience=2)])
    trainer.train()
    model.save_pretrained(f"{out_dir}/final", safe_serialization=True)
    processor.save_pretrained(f"{out_dir}/final")
```

**Augmentations (appliquées sur les VECTEURS avant rendu — l'avantage unique de Notely) :**

```python
def augment_strokes(strokes, rng):
    s = rng.uniform(0.9, 1.1)                       # échelle
    shear = rng.uniform(-0.2, 0.2)                  # italique
    rot = rng.uniform(-3, 3)                        # degrés
    jitter = rng.uniform(0, 0.6)                    # px de bruit par point
    width_scale = rng.uniform(0.8, 1.3)             # épaisseur
    return transform(strokes, s, shear, rot, jitter, width_scale)
```

(ne **pas** appliquer d'augmentation aux jeux val/test).

**Matériel :** GPU 12–16 Go suffisent avec FP16 + accumulation de gradient (⚠️ VRAM exacte non mesurée) ; Colab/Kaggle/cloud ponctuel possibles. Les données d'entraînement ne doivent **pas** quitter l'infrastructure maîtrisée sans que le consentement le couvre.

### 8.7 TÂCHE ML-7 — Promotion, canary et rollback

```python
# training/promote.py — règles de promotion (exemple, à ajuster après les premières versions)
def decide(candidate, current, bench):
    c, a = candidate.metrics, current.metrics
    checks = {
        "cer_fr_improved":  c["cer_fr"] <= a["cer_fr"] * 0.95,        # ≥ 5 % relatif
        "accents_improved": c["accent_err"] <= a["accent_err"],
        "no_en_regression": c["cer_en"] <= a["cer_en"] * 1.02,        # tolérance 2 %
        "latency_ok":       c["p95_ms_per_line"] <= a["p95_ms_per_line"] * 1.25,
        "calibration_ok":   c["ece"] < 0.08,
    }
    return all(checks.values()), checks
```

1. Le candidat est enregistré `status='candidate'` avec ses métriques.
2. Si les règles passent **et** qu'un humain approuve → `canary` : 10 % des utilisateurs (`hash(user_id) % 100 < 10`) pendant 3–7 jours ; comparer le **taux de correction** (corrections par 100 mots reconnus) canary vs actif.
3. Si le taux de correction du canary ≤ celui de l'actif → `active` ; l'ancien passe `retired` mais reste en stock **30 jours**.
4. **Rollback en une commande** : `python -m training.promote --rollback trocr-fr` → réactive la version précédente ; le registre recharge à chaud (vérification toutes les 60 s ou signal Redis, nouveau modèle chargé **avant** de basculer).
5. Chaque réponse OCR contient `modelVersion` ; chaque correction l'enregistre → on sait quelle version produit quelles erreurs.

### 8.8 TÂCHE ML-8 — Rendu et prétraitement (module `rendering.py`)

**Problème :** `preprocessing.py` vide ; rendu figé ; `MAX_DESKEW_DEG` jamais appliqué ; épaisseur de trait indépendante de la taille de la ligne.

```python
@dataclass(frozen=True)
class RenderConfig:
    padding_factor: float = 0.25          # candidats : 0.15 / 0.25 / 0.35 / 0.5
    render_scale: int = 2                 # candidats : 1 / 2 / 3
    stroke_rel_width: float = 0.06        # épaisseur = 0.06 × H_med (au lieu d'une largeur fixe)
    modulate_pressure: bool = False
    deskew: bool = True
    deskew_threshold_deg: float = 2.0
    max_deskew_deg: float = 15.0
    deslant: bool = False                 # cisaillement horizontal (corrige l'italique)
    min_aspect_pad: bool = True           # complète en blanc les lignes très courtes

def estimate_angle(points) -> float: ...  # régression linéaire (utils/geometry.estimate_slope)

def render_line(strokes, cfg: RenderConfig) -> Image.Image:
    angle = estimate_angle(all_points(strokes)) if cfg.deskew else 0.0
    if abs(angle) < cfg.deskew_threshold_deg or abs(angle) > cfg.max_deskew_deg:
        angle = 0.0                         # CLAMP : une ligne fusionnée par erreur n'est plus pivotée de 40°
    ...
```

**Protocole A/B** (une variable à la fois, mesurée avec le benchmark §8.9) : épaisseur, padding, échelle, `deslant`, modulation de pression, padding d'aspect. **Ne retenir** une valeur que si le CER baisse de façon reproductible. Garder `RenderConfig` dans la configuration versionnée avec le modèle (le modèle fine-tuné doit être utilisé avec **le même rendu** que celui de son entraînement — enregistrer `render_config` dans `model_versions.metrics`).

### 8.9 TÂCHE ML-9 — Benchmark réel (condition de toute décision)

#### Format du jeu de test

```json
[{"image": "l001.png", "text": "Les fonctions dérivables sont continues",
  "language": "fr", "category": "text", "has_accents": true, "page_group": "pg_017", "source": "app"}]
```

Catégories : `text`, `title`, `list`, `numbers`, `formula`, `mixed_lang`. Viser **200 lignes minimum** : ≥ 120 FR, 30 EN, 30 AR, 20 DE, dont ≥ 50 % avec accents/diacritiques ; **plusieurs écrivains**.

#### Collecte

- `benchmark/add_sample.py --from-session <fichier tracés>` : rend les lignes, propose l'OCR, l'humain corrige, enregistre `(image, texte)`.
- `--from-corrections` : importe des corrections consenties **dans le split `test` uniquement** (hash de page), jamais dans `train`.

#### Métriques

```python
def evaluate(engine, items, normalize=False):
    # CER, WER globaux ; ventilés par langue, catégorie, accents
    # + accent_error_rate : proportion de caractères accentués de la référence mal transcrits
    # + latence p50/p95 par ligne ; + ECE (calibration) ; + taux de troncature (> 128 tokens)
    ...
```

```python
def accent_error_rate(preds, refs):
    import difflib, unicodedata
    def accented(c): return unicodedata.normalize("NFD", c)[1:] != ""
    total = bad = 0
    for p, r in zip(preds, refs):
        sm = difflib.SequenceMatcher(None, p, r)
        ok = {j for blk in sm.get_matching_blocks() for j in range(blk.b, blk.b + blk.size)}
        for j, ch in enumerate(r):
            if accented(ch):
                total += 1; bad += j not in ok
    return bad / total if total else 0.0
```

#### CI

- `benchmark/baseline.json` versionné. La CI exécute un **sous-ensemble** (50 lignes) sur CPU ; échec si CER > baseline + 1 point absolu.
- Rapport complet (par langue/catégorie, courbe de fiabilité) en artefact de pipeline pour chaque candidat de modèle.

**Critère :** `python -m benchmark.eval_htr --engine trocr_fr --by language,category` produit un tableau lisible.

### 8.10 TÂCHE ML-10 — Post-traitement par langue

**Remplace** `re.sub(r'\s+',' ',text)`. Pipeline ordonné, chaque étape désactivable et mesurée :

```python
def postprocess(line: LineOut, lang: str, user_subs) -> LineOut:
    line = normalize_unicode(line)                    # NFC, apostrophes ' → ’ (typographique), espaces insécables
    line = apply_user_dictionary(line, user_subs)     # §8.5.b
    line = suggest_lexicon_fixes(line, lang)          # suggestions (accents, orthographe) : JAMAIS imposées
    line = typography(line, lang)                     # espace avant : ; ! ? en FR, œ/Œ, guillemets « »
    return line
```

#### Français — restauration d'accents par repliement

Principe : construire un index `forme sans accent → formes accentuées par fréquence` à partir d'un dictionnaire/lexique de fréquences français (⚠️ choisir et **vérifier la licence** : Lexique, listes Hunspell, etc.).

```python
import unicodedata
def fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

class AccentRestorer:
    def __init__(self, freq: dict[str, int]):
        self.freq, self.index = freq, {}
        for w, f in sorted(freq.items(), key=lambda kv: -kv[1]):
            self.index.setdefault(fold(w), w)          # la forme la plus fréquente d'abord

    def suggest(self, word: str, confidence: float) -> str | None:
        w = word.lower()
        if confidence >= 0.80 or w in self.freq:        # mot déjà valide ou sûr → on n'y touche pas
            return None
        cand = self.index.get(fold(w))
        return match_case(cand, word) if cand and cand != w else None
```

- **Suggestion** si 0,50 ≤ confiance < 0,80 (affichée dans la feuille de correction, jamais appliquée seule).
- **Application automatique** uniquement si le benchmark montre une précision ≥ 98 % pour cette règle sur votre jeu de test, et en marquant le mot `corrected` (réversible).
- Ne **jamais** toucher : nombres, mots entièrement en majuscules (sigles), mots capitalisés hors début de phrase, tokens contenant des chiffres, URL.
- Option : correction par modèle de langue sur les **seuls mots douteux**, avec contexte des mots voisins, en suggestion uniquement.

#### Allemand

Même mécanisme de repliement avec `ä ö ü ß` ; règle `ss ↔ ß` : si le mot replié `strasse` existe dans le lexique sous la forme `straße`, suggérer `Straße`. Majuscule des noms (Substantive) : **ne pas** corriger automatiquement (les notes d'étudiants contiennent des abréviations).

#### Arabe

- Normalisations *optionnelles* et séparées du texte affiché : suppression du tatweel (ـ), unification des formes d'alef (أ إ آ → ا) pour la **recherche**, jamais pour l'affichage.
- Ne pas appliquer d'espace avant ponctuation de type français ; utiliser `،` `؟` `؛`.
- Sens de lecture RTL : l'ordre des mots dans `words[]` reste l'ordre **logique** (premier mot lu = index 0) ; l'UI se charge de l'affichage (§6.4).
- Export PDF structuré : polices arabes (ex. Noto Naskh Arabic) et mise en forme du texte (`arabic-reshaper` + `python-bidi` pour des bibliothèques PDF qui ne gèrent pas le bidi nativement). ⚠️ À tester sur un vrai exemple.

#### Typographie et ponctuation

TrOCR omet ou substitue souvent la ponctuation. Si le benchmark montre un taux d'erreur de ponctuation élevé, tester un modèle de **restauration de ponctuation** léger **en suggestion**. Sinon, ne rien inventer.

### 8.11 TÂCHE ML-11 — Repli par modèle vision-langage (VLM), avec garde-fous

**Quand l'utiliser :** uniquement pour les lignes dont la confiance est sous le seuil du moteur principal, **et** si `consent_cloud_ocr = TRUE`, **et** si la langue le justifie (arabe, écriture très difficile).

```python
PROMPT = {
  "fr": "Transcris fidèlement ce texte manuscrit en français. Ne corrige ni l'orthographe ni la grammaire. "
        "Si un mot est illisible, écris [?]. Réponds uniquement par la transcription, sans commentaire.",
  "ar": "انسخ هذا النص المكتوب بخط اليد بدقة. لا تصحح الإملاء. اكتب [?] للكلمة غير المقروءة. أجب بالنص فقط.",
  # en, de : même structure
}
```

**Garde-fous :**

1. **Consentement explicite et séparé** (§4.8) ; journaliser l'événement d'envoi (sans le contenu).
2. **Anti-hallucination corrective** : si le texte VLM s'éloigne trop du moteur principal (`CER(vlm, principal) > 0.6`) alors que le moteur principal n'était pas désespéré (confiance > 0,4), **garder** le principal et proposer le VLM comme *alternative*.
3. **Ne jamais** envoyer plus que l'image de la ligne (pas de métadonnées, pas d'ID, pas d'e-mail).
4. **Timeouts** (10 s), **réessais bornés**, **disjoncteur** (circuit breaker) : après N échecs, désactiver temporairement le repli.
5. **Budget** : plafond d'appels par utilisateur et par jour ; métrique `vlm_calls_total`.
6. Clé API **uniquement** en variable d'environnement/coffre ; fournisseur et modèle configurés dans `models.yaml`, pas dans le code.
7. Marquer dans la réponse `engine="vlm"` ; l'UI affiche un badge « reconnu par IA avancée ».

Alternative locale : un VLM OCR léger auto-hébergé (⚠️ à benchmarker sur **vos** lignes avant tout choix ; ne pas se fier à un classement externe non lu).

### 8.12 TÂCHE ML-12 — Performance d'inférence et cache correct

#### a) Correction du cache (important)

**Problème :** l'empreinte actuelle = SHA-1 d'une **miniature 64×16** en niveaux de gris. Ajouter un accent ou un point ne change pas cette miniature → le cache **renvoie un ancien texte périmé**. De plus la clé ne contient pas la version du modèle ni le rendu.

```python
def line_cache_key(user_id, strokes, *, engine, model_version, render_cfg, num_beams, lang) -> str:
    h = hashlib.sha256()
    h.update(f"{user_id}|{engine}|{model_version}|{render_cfg.hash()}|{num_beams}|{lang}".encode())
    for s in sorted(strokes, key=lambda s: s.seq):
        h.update(s.client_id.encode())
        h.update(struct.pack(f"<{2 * len(s.points)}f", *[v for p in s.points for v in (round(p.x, 1), round(p.y, 1))]))
    return h.hexdigest()
```

- Stocker dans **Redis** (TTL 24 h, taille bornée) plutôt qu'en mémoire de processus (partagé entre workers, survit aux redémarrages).
- La clé inclut `model_version` → une promotion de modèle invalide automatiquement l'ancien cache.
- Test de non-régression : ajouter un accent à une ligne → **cache miss**.

#### b) Autres leviers (dans l'ordre, mesurer à chaque étape)

| Technique                                                                                                          | Quand                               | Gain                               | Risque                            |
| ------------------------------------------------------------------------------------------------------------------ | ----------------------------------- | ---------------------------------- | --------------------------------- |
| FP16 (`torch_dtype=torch.float16`, entrées `.half()`)                                                              | GPU                                 | mémoire ÷ 2, vitesse ↑             | vérifier le CER                   |
| Quantification dynamique int8 (`torch.quantization.quantize_dynamic(model, {torch.nn.Linear}, dtype=torch.qint8)`) | CPU                                 | CPU plus rapide, modèle plus léger | **mesurer** la perte de précision |
| ONNX Runtime (`optimum[onnxruntime]`, `ORTModelForVision2Seq`)                                                     | si la latence CPU reste un problème | latence CPU réduite                | parité des résultats à valider    |
| Batch + tri des lignes par largeur                                                                                 | toujours                            | débit ↑                            | faible                            |
| Warm-up au démarrage du worker                                                                                     | toujours                            | supprime la 1ʳᵉ requête lente      | nul                               |
| OCR **à la demande** + arrière-plan après 2 s d'inactivité (lignes modifiées seulement)                            | UX                                  | latence perçue ↓                   | faible                            |
| `num_beams` réduit sur CPU (2) et **jamais** de beam search sur toute la page si une seule ligne a changé          | CPU                                 | latence ÷ N                        | faible                            |

Cibles initiales (à confirmer par mesure) : p95 < 1,5 s/ligne CPU, < 0,3 s/ligne GPU ; page de 30 lignes < 10 s sur GPU.

### 8.13 TÂCHE ML-13 — ML Kit Digital Ink sur mobile (moteur « online »)

**Pourquoi :** vos tracés contiennent `(x, y, t, pression)` ; la rasterisation détruit cette information. Un moteur *online* lit directement les tracés, fonctionne **hors ligne**, couvre le **français et l'arabe** sans entraînement et répond en ~100 ms d'après la documentation de Google.

**Limites à respecter :**

- **Android/iOS uniquement** : inutilisable sur Flutter Web ni sur Angular → le backend reste le moteur de repli.
- Plugin Flutter **communautaire** : ⚠️ vérifier version, maintenance et signatures exactes avant d'écrire du code.
- ⚠️ Vérifier la **sémantique du score** des candidats (sens et échelle) avant de l'utiliser comme confiance ; ne pas le mélanger tel quel avec les confiances TrOCR. Passer par une calibration propre (§8.4).
- ML Kit ne donne pas de confiance **par mot** fiable : l'UI de correction reste utilisable (découpage sur espaces) mais sans coloration de confiance par mot ; utiliser le dictionnaire et les candidats alternatifs.
- Pas de ré-entraînement possible : les corrections alimentent seulement le dictionnaire personnel (§8.5.b).

**Architecture client (Flutter) :**

```dart
abstract class OcrEngineClient {
  String get name;
  Future<bool> supports(String language);
  Future<List<LineResult>> recognizeLines(List<List<StrokeModel>> lines, String language);
}

class MlKitEngine implements OcrEngineClient { /* modèles ~20 Mo téléchargés à la demande */ }
class RemoteEngine implements OcrEngineClient { /* POST /ocr/jobs puis polling */ }

class HybridOcr {
  Future<List<LineResult>> run(lines, lang) async {
    final out = <LineResult>[];
    final weak = <int>[];
    if (!kIsWeb && await mlkit.supports(lang)) {
      final r = await mlkit.recognizeLines(lines, lang);
      for (var i = 0; i < r.length; i++) { out.add(r[i]); if (r[i].confidence < threshold) weak.add(i); }
    } else {
      weak.addAll(List.generate(lines.length, (i) => i));
    }
    if (weak.isNotEmpty) {
      final remote = await server.recognizeLines([for (final i in weak) lines[i]], lang);
      // fusion : meilleur score par ligne ; marquer l'engine utilisé
    }
    return out;
  }
}
```

**Décision :** ML Kit est **un candidat à mesurer**, pas une vérité. Le comparer à TrOCR-FR sur le benchmark (rejeu des mêmes tracés) avant de le rendre moteur par défaut. Pour l'arabe, c'est actuellement la piste la plus réaliste sans entraînement.

### 8.14 Arabe et allemand — plan réaliste

| Langue       | Court terme (sans entraînement)                                                                             | Moyen terme                                                                                                                                                                                                                                                                     |
| ------------ | ----------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Arabe**    | ML Kit `ar` sur mobile ; repli VLM (consentement) ; interface RTL complète ; export PDF avec polices arabes | Évaluer un modèle HTR arabe dédié (⚠️ les noms de modèles cités dans l'audit, ex. `othrif/trocr-arabic-handwritten`, sont **non vérifiés** : tester existence, licence, qualité sur 30 lignes avant tout). Collecter des corrections AR consenties pour un fine-tuning ultérieur |
| **Allemand** | ML Kit `de` mobile ; TrOCR + post-traitement DE ; test benchmark                                            | Fine-tuning DE quand ≥ 500 corrections consenties                                                                                                                                                                                                                               |
| **Français** | TrOCR-FR communautaire (si le benchmark le justifie) + post-traitement accents + ML Kit `fr`                | Fine-tuning FR propre (§8.6)                                                                                                                                                                                                                                                    |
| **Anglais**  | TrOCR base actuel                                                                                           | Rien d'urgent                                                                                                                                                                                                                                                                   |

> **Ne jamais promettre** une qualité arabe/allemande avant d'avoir mesuré sur le benchmark.

### 8.15 Récapitulatif — pipeline OCR cible

```
Tracés ──► validation (limites) ──► segmentation hybride (grille + temps + BFS)
        ──► rendu configurable (RenderConfig versionné)
        ──► cache Redis (clé = contenu exact + modèle + rendu)
        ──► mémoire de lignes corrigées (réponse immédiate si ligne déjà corrigée)
        ──► chaîne de moteurs par langue : [TrOCR-lang → (VLM si consentement et confiance faible)]
              │      (mobile : ML Kit en premier, serveur en repli)
              ▼
        mots + confiance calibrée + alternatives
        ──► post-traitement : dictionnaire utilisateur → suggestions lexique → typographie
        ──► structuration (h1/h2/texte/schéma) ──► réponse (+ engine, modelVersion, langue)
        ──► UI : mots douteux soulignés → correction → /ocr/feedback → apprentissage
```

---

## 9. Tests, CI/CD et exploitation

### 9.1 Pyramide de tests

| Niveau              | Outils                                                               | À couvrir en priorité                                                                                         |
| ------------------- | -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Unitaires backend   | `pytest`                                                             | segmentation, regroupement tokens→mots, post-traitement, clés de cache, limites Pydantic                      |
| Intégration backend | `pytest` + base PostgreSQL de test (conteneur) + `httpx.AsyncClient` | **autorisation** (B ne voit pas A), upsert des tracés, rotation des refresh tokens, jobs OCR avec faux moteur |
| IA                  | `benchmark/`                                                         | CER/WER, ECE, non-régression                                                                                  |
| Flutter             | `flutter_test`, `golden_toolkit`, `integration_test`                 | parcours « écrire → reconnaître → corriger un mot », états de sauvegarde, RTL                                 |
| Angular             | Jest + Playwright                                                    | idem + zoom/coordonnées, accessibilité (`axe-core`)                                                           |
| Charge              | `locust`/`k6`                                                        | 50 utilisateurs, OCR concurrents, p95                                                                         |

### 9.2 Pipeline CI (GitHub Actions — squelette)

```yaml
name: ci
on: [pull_request]
jobs:
  backend:
    runs-on: ubuntu-latest
    services:
      postgres: { image: "postgres:16", env: { POSTGRES_PASSWORD: ci, POSTGRES_DB: notely_test }, ports: ["5432:5432"],
                  options: "--health-cmd pg_isready --health-interval 5s --health-retries 10" }
      redis: { image: "redis:7", ports: ["6379:6379"] }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12", cache: pip }
      - run: pip install -r requirements.lock -r requirements-dev.txt
      - run: ruff check . && ruff format --check . && mypy app
      - run: alembic upgrade head && alembic check
      - run: pytest
      - run: pip-audit -r requirements.lock
      - run: python -m benchmark.eval_htr --subset 50 --max-cer-regression 0.01
      - uses: gitleaks/gitleaks-action@v2
  flutter:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: subosito/flutter-action@v2
      - run: flutter pub get && flutter analyze && flutter test
  angular:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 22, cache: npm }
      - run: npm ci && npm run lint && npm test -- --watch=false && npm run build
      - run: npm audit --omit=dev --audit-level=high
  images:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t notely-api backend
      - uses: aquasecurity/trivy-action@master
        with: { image-ref: notely-api, severity: "HIGH,CRITICAL", exit-code: "1" }
```

### 9.3 Surveillance de la qualité IA en production

| Indicateur                     | Définition                                                         | Alerte                    |
| ------------------------------ | ------------------------------------------------------------------ | ------------------------- |
| **Taux de correction**         | corrections / 100 mots reconnus, par langue et par `model_version` | hausse > 20 % sur 7 jours |
| Confiance moyenne              | par langue/moteur                                                  | baisse brutale            |
| Taux de repli                  | lignes passées au moteur suivant / total                           | hausse                    |
| Latence p95 par ligne          | par moteur                                                         | > cible                   |
| Taux d'échec de jobs           | `failed / total`                                                   | > 1 %                     |
| Confusions de caractères       | top 30 (§8.5.d)                                                    | tendance                  |
| Part de corrections consenties | consentements / utilisateurs actifs                                | information produit       |

### 9.4 Déploiement

- Environnements : `dev` → `staging` (copie anonymisée / synthétique) → `prod`.
- Déploiement **progressif** (blue/green ou rolling) ; migrations rétro-compatibles.
- **Version minimale d'API** exposée (`X-Min-Client-Version`) : l'app mobile affiche « Mise à jour requise » si trop ancienne.
- Plan de reprise : RPO ≤ 24 h (sauvegarde), RTO ≤ 4 h ; test de restauration mensuel.

---

## 10. Feuille de route exécutable (liste de tâches pour l'agent)

> Cocher dans l'ordre. Chaque ligne = une PR. Les dépendances sont indiquées.

### Phase 0 — Urgences sécurité (1–2 jours)

- [ ] **SEC-1** Rotation des secrets, `config.py` sans défauts, `.env.example`, `gitleaks` *(aucune dépendance)*
- [ ] **SEC-4** Dépendances `get_owned_*` + tests d'autorisation sur toutes les routes *(dép. aucune)*
- [ ] **SEC-5** Limites Pydantic + limite de corps + simplification des tracés côté client
- [ ] **SEC-7** CORS unique et strict, désactivation de `/docs` en prod
- [ ] Suppression de `auth.py` legacy

### Phase 1 — Fondations (1 semaine)

- [ ] **DB-1** Alembic + baseline `stamp head`
- [ ] **DB-2** Corrections de schéma (A4, TIMESTAMPTZ, index, contraintes)
- [ ] **DB-3** Refonte `strokes` (UUID interne + `uq_stroke_page_client`) + upsert + sauvegarde différentielle + `409`
- [ ] **SEC-2/3** Argon2id + refresh à rotation (`refresh_tokens`) + logout *(dép. DB-1)*
- [ ] **SEC-6** Rate limiting (Redis)
- [ ] **CODE-1/2/3** Outillage qualité, erreurs uniformes, séparation routes/services/dépôts
- [ ] **ARCH-3** Docker Compose, Caddy, suppression de ngrok
- [ ] **ARCH-4** Logs structurés, Sentry, métriques

### Phase 2 — UX critique (1 semaine) *(dép. Phase 1 pour l'autosave et les erreurs)*

- [ ] **NG-1** Interceptor Angular + vraie confiance (§6.3 #1) — *quick win, à faire dès la Phase 0 si possible*
- [ ] **FLT-2** Intercepteur Dio (refresh sur 401), stockage sécurisé
- [ ] **FLT-3** UUID client + `SaveResult` + puce d'état de sauvegarde (Flutter et Angular)
- [ ] **NG-2** Pointer Events + zoom/pan Angular
- [ ] **FLT-1** Découpage de `notebook_screen.dart` + barre d'outils flottante + AppBar simplifiée (§6.2)
- [ ] Paramètres, sélecteur de langue (§6.6, 6.7), i18n fr/en/ar/de + RTL

### Phase 3 — Mesure et modèle de base (1–2 semaines)

- [ ] **ML-9** Benchmark réel (200 lignes) + métriques + baseline + CI *(à lancer en parallèle dès la Phase 0 : c'est de l'annotation)*
- [ ] **ML-8** Module de rendu configurable + clamp deskew + A/B
- [ ] **ML-12a** Cache correct (Redis, clé de contenu) + `debug=False`
- [ ] **ML-1/2** Registre de moteurs + routage par langue (le `language` devient actif)
- [ ] **ML-3** Mots + alternatives + `line-words` + miniatures
- [ ] **ML-4** Confiance calibrée *(dép. benchmark)*
- [ ] **ML-10** Post-traitement FR (accents en suggestion), DE, typographie

### Phase 4 — Correction et apprentissage (1–2 semaines)

- [ ] **UI §6.4** Panneau de résultat à 3 onglets + correction mot par mot (Flutter + Angular) *(dép. ML-3)*
- [ ] **DB-4** Tables `user_settings`, `user_dictionary`, extension `ocr_corrections`
- [ ] **ML-5** `POST /ocr/feedback` câblé, dictionnaire personnel, mémoire de lignes, écran « Mes corrections »
- [ ] **SEC-8** Consentements, export/suppression de compte, audit
- [ ] **ARCH-2** API de jobs + worker Celery *(peut précéder la Phase 4 si les timeouts gênent)*

### Phase 5 — Modèles et échelle (2–4 semaines)

- [ ] **ML-13** Prototype ML Kit (Android) + comparaison au benchmark
- [ ] **ML-11** Repli VLM sous consentement (si le benchmark le justifie)
- [ ] **ML-6** Pipeline d'export + fine-tuning FR *(dép. ≥ 500 corrections consenties **ou** données publiques/synthétiques + benchmark)*
- [ ] **ML-7** Registre `model_versions`, canary, rollback
- [ ] **ML-12b** FP16/int8/ONNX selon mesure
- [ ] Segmentation hybride grille + temps (CODE-4 + évaluation de gain)
- [ ] **§9** Surveillance qualité IA, tests de charge, déploiement progressif

---

## Annexe A — Variables d'environnement (`.env.example`)

```
ENV=dev
DATABASE_URL=postgresql+psycopg://notely:CHANGE_ME@db:5432/notely
REDIS_URL=redis://redis:6379/0
JWT_SECRET_KEY=GENERER_AVEC_secrets.token_urlsafe_64
ACCESS_TOKEN_MINUTES=15
REFRESH_TOKEN_DAYS=30
CORS_ORIGINS=http://localhost:4200
OCR_DEFAULT_LANGUAGE=fr
OCR_DEVICE=auto
OCR_MAX_LOADED_MODELS=2
MODELS_DIR=/models
SENTRY_DSN=
VLM_API_KEY=            # uniquement si repli cloud activé
```

## Annexe B — Points à ne pas affirmer sans mesure ni vérification

| Sujet                                                                           | Statut                                |
| ------------------------------------------------------------------------------- | ------------------------------------- |
| Gain de CER de chaque amélioration (beam, rendu, ML Kit, fine-tuning, VLM)      | **Hypothèse** — non mesuré sur Notely |
| Modèles HF tiers (FR, AR) : existence, licence, qualité sur écriture d'étudiant | ⚠️ **À VÉRIFIER**                      |
| Signatures du plugin ML Kit Flutter, sémantique du score des candidats          | ⚠️ **À VÉRIFIER**                      |
| Licences IAM, RIMES, jeux synthétiques et lexiques de fréquence                 | ⚠️ **À VÉRIFIER**                      |
| Équivalence `compute_transition_scores` avec beam search ↔ `sequences_scores`   | ⚠️ **À VALIDER par test** (§8.3)       |
| VRAM nécessaire au fine-tuning complet                                          | ⚠️ **Non mesurée**                     |
| Noms de fichiers/lignes issus des audits                                        | ⚠️ **À confirmer** dans le code réel   |

## Annexe C — Glossaire rapide

- **CER / WER** : taux d'erreur par caractère / par mot (plus bas = mieux).
- **IDOR** : accès à la ressource d'un autre utilisateur en changeant un identifiant.
- **ECE** : erreur de calibration attendue (la confiance annoncée correspond-elle à la réalité ?).
- **Canary** : déploiement d'une nouvelle version à une petite fraction des utilisateurs.
- **HTR online / offline** : reconnaissance à partir des tracés (online) ou d'une image (offline).
- **Rejeu** : réinjection d'anciennes données lors d'un ré-entraînement pour éviter d'oublier.
