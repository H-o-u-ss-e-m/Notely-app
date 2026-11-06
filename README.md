# 📝 Notely — Smart Digital Ink & Handwritten OCR Monorepo

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-CUDA%20Capable-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)
![Angular](https://img.shields.io/badge/Angular-19+-DD0031?style=for-the-badge&logo=angular&logoColor=white)
![Flutter](https://img.shields.io/badge/Flutter-3.x-02569B?style=for-the-badge&logo=flutter&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![License](https://img.shields.io/badge/License-Proprietary-red?style=for-the-badge)

**Application 3-tier de prise de notes numériques multiplateforme (Web & Mobile) avec moteur de reconnaissance d'écriture manuscrite (HTR/OCR), couche de correction auto-apprenante bilingue (Français/Arabe/Anglais) et synchronisation différentielle des tracés.**

</div>

---

## 🌟 Présentation Générale

**Notely** est une suite complète de prise de notes manuscrites conçue pour offrir une expérience fluide au stylet ou au doigt sur tablettes, ordinateurs portables et smartphones. Elle combine :

1. **Un Canvas vectoriel haute fidélité** avec gestion précise du zoom/panoramique, rendu vectoriel et synchronisation différentielle des tracés.
2. **Un pipeline OCR/HTR multi-niveaux** : segmentation de lignes, inférence TrOCR / vision-language models, normalisation linguistique approfondie (notamment les spécificités de la langue arabe : tashkeel, tatweel, variantes d'alef) et cache SHA-256 haute performance.
3. **Une couche de correction intelligente (CorrectionLayer v2)** :
   - Dictionnaire personnel utilisateur appliqué dès la 1ère correction.
   - Mémoire de lignes vectorielles avec `ink_hash` tolérant (rasterisation 32×8 et distance de Hamming).
   - Filtre anti-poison probabiliste intelligent (gestion fine du CER pour l'arabe et les scripts complexes).
4. **Une architecture sécurisée de niveau production** :
   - Hachage de mot de passe **Argon2id** (RFC 9106).
   - Refresh tokens opaques à rotation stricte par famille (`family_id`, détection de rejeu & invalidation instantanée).
   - Contrôle d'accès strict anti-IDOR (`get_owned_*`) et limitation de débit (`slowapi` rate limiting).
   - Intercepteurs HTTP réactifs (Angular & Flutter) sérialisant le renouvellement de session sur 401 via `shareReplay(1)` / `QueuedInterceptorsWrapper`.

---

## 🏗️ Architecture du Monorepo

```text
Notely/
├── backend/                       # API REST Python FastAPI & Intelligence HTR
│   ├── app/
│   │   ├── api/                   # Routeurs REST v1 (Auth, Cours, OCR, Feedbacks)
│   │   ├── core/                  # Sécurité (Argon2id, JWT), config, rate limiting
│   │   ├── db/                    # Modèles SQLAlchemy (PostgreSQL) & sessions
│   │   ├── domain/                # CorrectionLayer v2, LineMemory, AntiPoison, UserDict
│   │   ├── ml/                    # Moteurs OCR (TrOCR, VLM, base engines), Cache SHA-256
│   │   ├── modules/               # Modules métier découplés (Auth, Courses, etc.)
│   │   ├── schemas/               # Contrats Pydantic v2
│   │   └── services/              # Orchestration HTR structurelle & segmentation
│   ├── tests/                     # 90+ tests automatisés Pytest (Unitaires & Intégration)
│   ├── requirements.txt           # Dépendances Python
│   └── alembic.ini                # Gestionnaire de migrations de base de données
├── front-angular/                 # Application Web SPA (Angular 19 Standalone)
│   ├── src/app/
│   │   ├── components/            # Composants UI (Notebook Editor, Canvas vectoriel)
│   │   ├── interceptors/          # Intercepteur HTTP 401 réactif (shareReplay)
│   │   ├── services/              # AuthService, ApiService (synchronisation PATCH)
│   │   └── models/                # Modèles TypeScript stricts
│   └── package.json               # Scripts de build Vite & Vitest
├── mobile/                        # Application Mobile (Flutter 3.x Android/iOS/Desktop)
│   ├── lib/
│   │   ├── core/network/          # Dio Client, AuthInterceptor, SecureTokenStore
│   │   ├── features/notebook/     # Écran de prise de notes, CustomPainter
│   │   └── models/                # Modèles Dart désérialisés
│   └── pubspec.yaml               # Dépendances Flutter (Dio, FlutterSecureStorage, etc.)
├── migrations/                    # Scripts de migration de base de données Alembic
└── shared/                        # Spécification universelle du schéma de tracé vectoriel
```

---

## 🚀 Démarrage Rapide

### Prérequis
* **Python** 3.10+ (ou environnement Conda dédié)
* **Node.js** 20+ et **npm**
* **Flutter SDK** 3.x
* **PostgreSQL** 16+ et **Redis**

---

### 1. Backend (FastAPI + PyTorch)

```bash
# 1. Cloner et naviguer dans le dossier
cd backend

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Configurer l'environnement (.env)
cp .env.example .env

# 4. Appliquer les migrations de base de données
alembic upgrade head

# 5. Lancer l'API de développement
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

* Swagger UI interactif : `http://localhost:8000/docs`
* Métriques Prometheus : `http://localhost:8000/metrics`

---

### 2. Frontend Web (Angular 19)

```bash
# 1. Naviguer dans le dossier web
cd front-angular

# 2. Installer les dépendances
npm install

# 3. Lancer en local
npm start
# L'application est accessible sur http://localhost:4200
```

---

### 3. Application Mobile (Flutter)

```bash
# 1. Naviguer dans le dossier mobile
cd mobile

# 2. Récupérer les paquets
flutter pub get

# 3. Lancer sur émulateur ou appareil connecté
flutter run
```

---

## 🧪 Tests et Qualité de Code

Le projet maintient une couverture de tests rigoureuse sur toutes les couches :

### Backend
```bash
pytest backend/tests -v
```
* **90 tests unitaires & d'intégration** validant la sécurité P0, l'anti-poison, la normalisation arabe, le cache HTR, la synchronisation différentielle `DB-3` et les dépendances anti-IDOR.

### Web (Angular)
```bash
cd front-angular
npm test -- --watch=false
npm run build
```
* Tests unitaires Vitest vérifiant notamment la gestion des requêtes concurrentes `401` et l'injection des en-têtes d'authentification.

### Mobile (Flutter)
```bash
cd mobile
flutter analyze
flutter test
```
* Analyse statique sans aucun avertissement et tests de non-régression de l'inversion géométrique de viewport et du stockage sécurisé des sessions.

---

## 🔒 Sécurité & Bonnes Pratiques

* **Hachage Argon2id** : Protection maximale contre les attaques GPU et par dictionnaire.
* **Rotation des Refresh Tokens** : Chaque refresh invalide le token précédent. La réutilisation d'un ancien token révoque immédiatement toute la famille de sessions.
* **IDOR Prevention** : Les ressources (`Lesson`, `Page`, `Stroke`) sont strictement filtrées par la propriété de l'utilisateur authentifié.
* **Protection API** : Limitation de débit par route sensible (ex. `10 req/min` sur login/refresh/OCR) via `slowapi`.

---

## 👥 Auteur & Contribution

* **Auteur** : [Houssem Rezgui](https://github.com/H-o-u-ss-e-m)
* **Projet** : Notely App — Système intelligent de prise de notes manuscrites.
