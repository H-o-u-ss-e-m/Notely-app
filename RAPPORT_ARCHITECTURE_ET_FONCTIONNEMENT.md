# 📘 Notely — Guide Complet d'Architecture, d'Intelligence Artificielle et de Fonctionnement

Ce document constitue la référence exhaustive de l'application **Notely (Smart Handwriting Notebook)**. Il détaille le fonctionnement conceptuel et technique de chaque composant : le moteur d'Intelligence Artificielle (HTR), le Backend Python, le Frontend Web Angular et l'Application Mobile Flutter.

---

## 📑 Sommaire
1. [Vue d'Ensemble & Vision Produit](#1-vue-densemble--vision-produit)
2. [Le Cœur d'Intelligence Artificielle (IA & HTR)](#2-le-cœur-dintelligence-artificielle-ia--htr)
   - 2.1 Le Modèle Pré-entraîné (TrOCR de Microsoft)
   - 2.2 Du Tracé Vectoriel au Texte : Le Pipeline de Transformation
   - 2.3 Le Moteur Spécialisé pour la Langue Arabe
   - 2.4 Comment l'IA "Apprend", s'Améliore et Mémorise
   - 2.5 Sécurité de l'Apprentissage (Filtre Anti-Poison)
   - 2.6 Cartographie des Fichiers IA
3. [Architecture du Backend (Python / FastAPI)](#3-architecture-du-backend-python--fastapi)
   - 3.1 Stack Technologique & Principes
   - 3.2 Modèles de Données & Persistance PostgreSQL
   - 3.3 Sécurité, Authentification & Autorisation (SEC)
   - 3.4 Détail Fichier par Fichier du Backend
4. [Architecture du Frontend Web (Angular)](#4-architecture-du-frontend-web-angular)
   - 4.1 Moteur de Dessin Canvas HTML5 & Viewport Mathématique
   - 4.2 Les Fonctionnalités Produit Intelligentes (Lasso, Formes, Recherche, SM-2)
   - 4.3 Détail Fichier par Fichier du Frontend
5. [Architecture Mobile (Flutter)](#5-architecture-mobile-flutter)
   - 5.1 Encre Numérique & CustomPainter
   - 5.2 Synchronisation Différentielle & Réseau Résilient
   - 5.3 Détail Fichier par Fichier du Mobile
6. [Guide de Démarrage et Déploiement](#6-guide-de-démarrage-et-déploiement)

---

## 1. Vue d'Ensemble & Vision Produit

### Qu'est-ce que Notely ?
**Notely** est une plateforme de prise de notes manuscrites augmentée par Intelligence Artificielle. Elle permet à des étudiants, chercheurs et professionnels d'écrire naturellement (au stylet ou au doigt) sur tablette, PC ou mobile, tout en bénéficiant :
- D'une **reconnaissance d'écriture manuscrite synchrone et asynchrone (HTR - Handwritten Text Recognition)** multilingue (Français, Anglais, Arabe, Allemand).
- D'une **compréhension structurelle** de la note (distinction automatique entre titres H1-H6, paragraphes de cours et schémas/diagrammes).
- D'une **capacité d'apprentissage continu local** : l'application apprend des corrections de l'utilisateur sur son style d'écriture sans ré-entraînement lourd.
- D'outils pédagogiques intégrés : **recherche dans l'encre manuscrite**, **reconnaissance de formes géométriques parfaites**, **outil lasso vectoriel**, **export PDF vectoriel structuré** et **génération automatique de flashcards de révision espacée (SuperMemo SM-2)**.

### Les 3 Piliers Applicatifs
```
┌─────────────────────────────────────────────────────────────┐
│                       NOTELY CLIENTS                        │
│                                                             │
│   [ Front-End Web Angular ]        [ Mobile Flutter App ]   │
│   (HTML5 Canvas, Pan/Zoom,         (CustomPainter tactile,  │
│    Lasso, Formes, Templates)        Stylet, Rejet paume)    │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP REST / JSON / Bearer JWT
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                      BACKEND NOTELY                         │
│                                                             │
│   FastAPI (Python 3.10)                                     │
│   ├── Moteur IA HTR (TrOCR + Arabic Engine)                 │
│   ├── Mémoire Géométrique & Dictionnaire Personnel         │
│   ├── Sécurité (Argon2id, Rotation Refresh, Anti-IDOR)      │
│   └── Export Document PDF (ReportLab + Bidi)                │
└──────────────────────────────┬──────────────────────────────┘
                               │
               ┌───────────────┴───────────────┐
               ▼                               ▼
     [ PostgreSQL 15+ ]                 [ Redis 7 / Celery ]
     Données relationnelles,            Cache HTR, Jobs asynchrones
     tracés, utilisateurs, cartes       et files de traitement lourd
```

---

## 2. Le Cœur d'Intelligence Artificielle (IA & HTR)

### 2.1 Le Modèle Pré-entraîné (TrOCR de Microsoft)
Pour transcrire des écritures manuscrites cursives libres, Notely utilise **TrOCR (`microsoft/trocr-base-handwritten`)**, conçu par Microsoft Research.

#### Pourquoi cette technologie ?
Traditionnellement, l'OCR fonctionnait en deux étapes fragiles : couper l'image caractère par caractère (segmentation), puis reconnaître chaque lettre individuellement. En écriture manuscrite liée (cursive), les lettres s'entremêlent et cette approche échoue fréquemment.

**TrOCR utilise une architecture Transformer Vision Encodeur-Décodeur (similaire à GPT, mais pour l'image) :**
1. **L'Encodeur Visuel (Vision Transformer - ViT)** : 
   - L'image de la ligne d'écriture est découpée en petits patchs carrés (16x16 pixels).
   - Ces patchs sont projetés sous forme de vecteurs (tokens visuels).
   - Des mécanismes d'attention spatiale capturent la forme des lettres, les boucles, les ligatures et l'inclinaison.
2. **Le Décodeur Linguistique (BART / RoBERTa)** :
   - Fonctionne comme un modèle de langage.
   - Il prédit les mots de gauche à droite en utilisant à la fois l'information visuelle et la probabilité des mots dans la langue (par exemple, après "Le théorème de", il privilégie "Pythagore" plutôt qu'une suite de lettres sans sens).

#### Accélération Matérielle (GPU CUDA)
Le fichier [`backend/app/core/device.py`](backend/app/core/device.py) détecte automatiquement la présence d'une carte graphique NVIDIA (`torch.cuda.is_available()`). Si CUDA est disponible, le modèle est chargé en **précision demi-flottante (FP16)**, ce qui divise la consommation mémoire par 2 et accélère l'inférence par 3.

---

### 2.2 Du Tracé Vectoriel au Texte : Le Pipeline de Transformation
Quand vous écrivez sur l'écran, vous ne manipulez pas une photo, mais une suite de coordonnées mathématiques :
$$\text{Point} = (x, y, \text{timestamp}, \text{pression})$$

Le pipeline transformant ces tracés en texte comprend 5 étapes :
1. **Segmentation spatiale ([`backend/app/services/segmentation_service.py`](backend/app/services/segmentation_service.py))** :
   - Regroupe les traits qui appartiennent à la même ligne horizontale.
   - Sépare les zones d'écriture des schémas/diagrammes grâce à l'analyse de densité et d'orientation des traits.
2. **Rendu matriciel adaptatif ([`backend/app/ml/rendering.py`](backend/app/ml/rendering.py))** :
   - Dessine la ligne de points sous forme d'image matricielle haute résolution (lissage anti-aliasing, padding proportionnel).
   - Applique un redressement de l'angle d'écriture (*deskew*) si la ligne est penchée.
3. **Inférence neuronale ([`backend/app/ml/engines/trocr.py`](backend/app/ml/engines/trocr.py))** :
   - L'image est normalisée à 384×384 pixels et envoyée à TrOCR.
   - Génération avec faisceau (*Beam Search*) produisant le texte transcrit, la confiance moyenne et des hypothèses alternatives (*n-best*).
4. **Post-traitement linguistique ([`backend/app/domain/text_postprocess.py`](backend/app/domain/text_postprocess.py))** :
   - Recollage des apostrophes françaises, harmonisation des majuscules en début de phrase, règles typographiques.
5. **Couche de correction adaptative ([`backend/app/domain/correction_layer.py`](backend/app/domain/correction_layer.py))** :
   - Application de la mémoire personnelle de l'utilisateur (voir section 2.4).

---

### 2.3 Le Moteur Spécialisé pour la Langue Arabe
L'écriture arabe présente deux spécificités majeures que les modèles standards occidentaux ne peuvent pas traiter correctement :
1. **L'orientation Droite-à-Gauche (RTL)**.
2. **La nature fortement cursive et contextuelle** : une lettre change de glyphe selon qu'elle est isolée, initiale, médiane ou finale, et porte des signes diacritiques (Tashkeel) et étirements (Tatweel `ـ`).

Dans [`backend/app/ml/engines/arabic_engine.py`](backend/app/ml/engines/arabic_engine.py) :
- Le routage automatique par langue s'effectue via [`backend/app/ml/models.yaml`](backend/app/ml/models.yaml).
- Lors de l'export PDF ([`backend/app/services/pdf_generator_service.py`](backend/app/services/pdf_generator_service.py)), le texte arabe passe par `arabic_reshaper.reshape()` (connexion des formes de lettres) puis par l'algorithme bidirectionnel `bidi.algorithm.get_display()` pour un affichage parfait dans ReportLab avec la police vectorielle `Noto Sans Arabic`.

---

### 2.4 Comment l'IA "Apprend", s'Améliore et Mémorise

Une idée reçue fréquente en IA est qu'un système doit ré-entraîner ses poids synaptiques (gradient descent) pour chaque correction utilisateur. En production, c'est impossible : ré-entraîner un modèle de 350 millions de paramètres prendrait plusieurs minutes, consommerait trop d'énergie et risquerait de dégrader les autres mots (*catastrophic forgetting*).

**Notely utilise une approche moderne hybride à 3 niveaux :**

#### Niveau 1 : La Mémoire Géométrique par Empreinte de Tracé (Ink Hash)
- Fichier : [`backend/app/domain/line_memory.py`](backend/app/domain/line_memory.py)
- **Le concept** : Quand vous écrivez un mot, votre geste produit une silhouette géométrique unique.
- Le tracé est normalisé dans une grille binaire de 32×8 bits. On obtient une empreinte numérique (*ink hash*).
- Deux écritures du même mot par la même personne ont une distance de Hamming très faible ($\le 12$).
- **Résultat** : Si vous corrigez un mot une fois, la prochaine fois que vous écrirez ce mot avec une gestuelle similaire, Notely reconnaît l'empreinte géométrique et substitue immédiatement la correction exacte, avec une latence quasi nulle ($<1 \text{ ms}$).

#### Niveau 2 : Le Dictionnaire Personnel Contextuel
- Fichier : [`backend/app/domain/user_dictionary.py`](backend/app/domain/user_dictionary.py)
- Table : `user_dictionary` en base PostgreSQL.
- **Le concept** : Si l'IA confond fréquemment votre écriture du mot "intégrale" avec "integrale" ou "integrat", chaque correction incrémente un compteur de substitution `(wrong -> right)` propre à votre compte.
- Dès que le modèle hésite ou prédit le mot erroné, la couche de post-traitement consulte votre dictionnaire et applique votre correction.

#### Niveau 3 : Le Fine-Tuning Différé (MLOps)
- Table : `ocr_corrections` en base PostgreSQL.
- Fichier : [`backend/app/api/ocr_feedback.py`](backend/app/api/ocr_feedback.py)
- Si l'utilisateur a coché l'option de consentement RGPD (`consent_train = True`), la paire `(image_tracé, texte_corrigé)` est enregistrée dans la base d'apprentissage.
- Périodiquement, l'administrateur peut exporter ce jeu de données pour ré-entraîner officiellement une nouvelle version du modèle TrOCR (fine-tuning supervisé).

---

### 2.5 Sécurité de l'Apprentissage (Filtre Anti-Poison)
Un utilisateur malveillant ou distrait pourrait tenter de corrompre le dictionnaire (par exemple corriger le mot "bonjour" en "zzzzzzzz" ou en propos grossiers).

Le module [`backend/app/domain/anti_poison.py`](backend/app/domain/anti_poison.py) valide chaque correction avant enregistrement :
1. **Distance de Levenshtein normalisée** : Si le texte prédit avait une confiance élevée ($>80\%$) et que la correction est radicalement différente sans justification, elle est rejetée (`CORRECTION_TOO_FAR`).
2. **Détection de répétitions/spam** : Rejette les motifs répétitifs ("aaaaa", "qwertyuiop").
3. **Tolérance par langue** : En arabe, où le modèle TrOCR latin sortait parfois des suites de lettres absurdes ("ooooa"), le filtre est intelligemment adapté pour autoriser le remplacement par le mot arabe valide sans blocage erroné.

---

### 2.6 Cartographie des Fichiers IA
| Fichier | Rôle & Responsabilité |
| :--- | :--- |
| [`backend/app/ml/engines/trocr.py`](backend/app/ml/engines/trocr.py) | Wrapper d'inférence HuggingFace TrOCR (PyTorch, FP16 CUDA, beam search). |
| [`backend/app/ml/engines/arabic_engine.py`](backend/app/ml/engines/arabic_engine.py) | Moteur spécialisé Arabe (normalisation Unicode, tashkeel, tatweel). |
| [`backend/app/ml/registry.py`](backend/app/ml/registry.py) | Gestionnaire multi-moteurs avec politique LRU (déchargement mémoire propre). |
| [`backend/app/ml/rendering.py`](backend/app/ml/rendering.py) | Conversion géométrique : traits vectoriels $\to$ image PIL avec redressement. |
| [`backend/app/ml/cache.py`](backend/app/ml/cache.py) | Cache mémoire L1 SHA-256 évitant de recalculer l'OCR sur des traits identiques. |
| [`backend/app/domain/correction_layer.py`](backend/app/domain/correction_layer.py) | Couche pivot combinant mémoire géométrique, cache et dictionnaire. |
| [`backend/app/domain/line_memory.py`](backend/app/domain/line_memory.py) | Calcul de l'empreinte géométrique d'encre (*ink hash*) et distance de Hamming. |
| [`backend/app/domain/anti_poison.py`](backend/app/domain/anti_poison.py) | Gardien de sécurité rejetant les fausses corrections et injections. |
| [`backend/app/domain/sm2.py`](backend/app/domain/sm2.py) | Algorithme de répétition espacée SuperMemo-2 et générateur de cartes OCR. |

---

## 3. Architecture du Backend (Python / FastAPI)

### 3.1 Stack Technologique & Principes
- **FastAPI** : Framework asynchrone ultra-rapide basé sur Starlette et Pydantic.
- **SQLAlchemy 2.0** : ORM pour la modélisation objet des données et les requêtes SQL.
- **Alembic** : Outil de migrations transactionnelles pour faire évoluer le schéma de base de données sans perte de données.
- **PostgreSQL 15+** : Base de données relationnelle sécurisée (remplace l'ancien Firestore/Firebase).
- **Argon2id** : Algorithme de hachage cryptographique de pointe pour les mots de passe (résistant aux attaques GPU/ASIC).
- **ReportLab** : Moteur de génération de documents PDF professionnels.

---

### 3.2 Modèles de Données & Persistance PostgreSQL
Toutes les tables sont déclarées dans [`backend/app/db/models/`](backend/app/db/models/) :
- `users` : Comptes utilisateurs (ID UUIDv4, email unique, mot de passe Argon2id, rôle étudiant/professeur).
- `subjects` : Espaces de travail ou matières (ex: Mathématiques, Physique).
- `lessons` : Cours ou chapitres contenant des pages.
- `pages` : Pages du carnet avec numéro d'ordre et dimensions.
- `strokes` : Traits vectoriels individuels avec clé primaire UUID, identifiant client unique par page pour la synchronisation différentielle et support du soft-delete.
- `flashcards` : Cartes de révision espacée avec statut SM-2 (`repetitions`, `interval_days`, `ease_factor`, `next_review_date`).
- `ocr_corrections` : Historique des corrections mot-à-mot et consentements RGPD.
- `user_dictionary` : Substitutions apprises par utilisateur et par langue.

---

### 3.3 Sécurité, Authentification & Autorisation (SEC)
1. **Tokens JWT sécurisés** : 
   - `access_token` éphémère (durée de vie 15 min).
   - `refresh_token` avec rotation stricte et révocation globale (`POST /api/v1/auth/logout-all`).
2. **Protection Anti-IDOR (Insecure Direct Object Reference)** :
   - Chaque requête vérifie que la ressource demandée (cours, matière, carte) appartient bien à l'utilisateur connecté via son `user_id` extrait du token cryptographique. Si un utilisateur tente d'accéder au cours d'un autre, le serveur répond `404 Not Found` sans révéler l'existence de la ressource.
3. **Protection contre le Brute-Force** :
   - Verrouillage progressif après 5 échecs de connexion consécutifs (`Lockout`).
   - Temps constant de comparaison (`fake_verify()`) pour neutraliser les attaques par analyse temporelle (*timing attacks*).

---

### 3.4 Détail Fichier par Fichier du Backend
- [`backend/app/main.py`](backend/app/main.py) : Point d'entrée de l'application. Initialise FastAPI, configure les middlewares (CORS dynamique, limitation de taille de corps anti-DoS, request-id, rate-limiting) et enregistre tous les routeurs.
- [`backend/app/core/config.py`](backend/app/core/config.py) : Gestion centralisée des variables d'environnement (`.env`) avec validation stricte (interdiction des clés compromises, validation de la complexité JWT).
- [`backend/app/core/security.py`](backend/app/core/security.py) : Fonctions de chiffrement Argon2id, vérification de mot de passe et génération de jetons JWT.
- [`backend/app/api/flashcards.py`](backend/app/api/flashcards.py) : Endpoints de création, révision SM-2 et génération automatique de cartes depuis l'OCR.
- [`backend/app/api/recognition.py`](backend/app/api/recognition.py) : Endpoints d'analyse d'écriture synchrone.
- [`backend/app/api/ocr_jobs.py`](backend/app/api/ocr_jobs.py) : Endpoints de soumission asynchrone pour les cours complets multi-pages avec interrogation de progression.
- [`backend/app/services/pdf_generator_service.py`](backend/app/services/pdf_generator_service.py) : Générateur de PDF imprimables vectoriels conservant schémas et styles typographiques.

---

## 4. Architecture du Frontend Web (Angular)

### 4.1 Moteur de Dessin Canvas HTML5 & Viewport Mathématique
Le composant [`front-angular/src/app/components/notebook-editor/`](front-angular/src/app/components/notebook-editor/) implémente un canvas vectoriel haute performance :
- **Prise en compte du Device Pixel Ratio (DPR)** : Garantit une netteté absolue sur les écrans Retina et 4K sans flou de pixelisation.
- **Source unique de vérité Viewport (`scale`, `tx`, `ty`)** :
  Toute conversion entre l'écran tactile et la feuille logique standard (794×1123 px A4) est régie par deux fonctions bijectives vérifiées par tests unitaires :
  $$\text{toPage}(x_{\text{écran}}, y_{\text{écran}}) = \left(\frac{x - tx}{\text{scale}}, \frac{y - ty}{\text{scale}}\right)$$
  $$\text{toScreen}(x_{\text{page}}, y_{\text{page}}) = (x \cdot \text{scale} + tx, y \cdot \text{scale} + ty)$$

---

### 4.2 Les Fonctionnalités Produit Intelligentes

#### A. Outil Lasso Vectoriel ([`front-angular/src/app/utils/lasso.ts`](front-angular/src/app/utils/lasso.ts))
- L'utilisateur entoure des éléments tracés sur l'écran.
- L'algorithme de lancer de rayon (*Ray-Casting Algorithm*) teste chaque point du tracé à l'intérieur du polygone.
- Les traits sélectionnés sont regroupés, encadrés par un rectangle bleu en pointillés et peuvent être translatés en groupe par simple glisser-déposer.

#### B. Reconnaissance de "Forme Parfaite" ([`front-angular/src/app/utils/shape-recognizer.ts`](front-angular/src/app/utils/shape-recognizer.ts))
- Transforme instantanément un tracé à main levée approximatif en figure géométrique pure :
  - **Ligne droite** : vérifie la distance maximale de chaque point par rapport à la corde.
  - **Cercle / Ellipse** : analyse l'écart-type de la distance radiale par rapport au barycentre.
  - **Rectangle** : analyse la proximité avec la boîte englobante et la présence des 4 sommets.
- **Protection anti-faux-positifs** : Le rapport de longueur de périmètre vérifie que les écritures ondulées ou spirales ne sont jamais transformées par erreur en rectangles.

#### C. Recherche dans l'Écriture Manuscrite ([`front-angular/src/app/utils/ink-search.ts`](front-angular/src/app/utils/ink-search.ts))
- Permet de chercher un mot clé directement dans des notes manuscrites.
- Applique une normalisation Unicode NFKD (suppression des accents en français, suppression du Tashkeel et uniformisation des variantes d'Alef en arabe).
- Surligne instantanément en jaune translucide les boîtes englobantes des mots correspondants sur le canvas.

#### D. Modèles de Fond de Page ([`front-angular/src/app/utils/page-template.ts`](front-angular/src/app/utils/page-template.ts))
- Rendu en direct de 4 réglures professionnelles :
  - `lined` : Lignage classique d'écolier.
  - `grid` : Quadrillage millimétrique 5mm.
  - `dots` : Grille de points type Bullet Journal.
  - `blank` : Page blanche pure.

---

### 4.3 Détail Fichier par Fichier du Frontend
- [`front-angular/src/app/components/notebook-editor/notebook-editor.component.ts`](front-angular/src/app/components/notebook-editor/notebook-editor.component.ts) : Contrôleur principal de l'éditeur de notes (gestion des événements de pointeur unifiés, zoom à la molette, sélection d'outils, modale de révision de cartes).
- [`front-angular/src/app/components/save-status-chip/save-status-chip.component.ts`](front-angular/src/app/components/save-status-chip/save-status-chip.component.ts) : Indicateur d'enregistrement réactif à 4 états visuels (`saved`, `saving`, `dirty`, `error`).
- [`front-angular/src/app/services/api.service.ts`](front-angular/src/app/services/api.service.ts) : Service d'accès à l'API REST avec injection de Bearer Token.
- [`front-angular/src/app/interceptors/auth.interceptor.ts`](front-angular/src/app/interceptors/auth.interceptor.ts) : Intercepteur HTTP interceptant les erreurs 401 pour rafraîchir l'access token de façon transparente.
- [`front-angular/src/app/services/i18n.service.ts`](front-angular/src/app/services/i18n.service.ts) : Système de traduction multilingue réactif (Français, Anglais, Arabe, Allemand).

---

## 5. Architecture Mobile (Flutter)

### 5.1 Encre Numérique & CustomPainter
L'application mobile ([`mobile/`](mobile/)) est construite avec Flutter pour garantir 60 à 120 images par seconde sur écran tactile :
- [`notebook_painter.dart`](mobile/lib/features/notebook/widgets/notebook_painter.dart) : Utilise l'API Canvas Skia/Impeller de Flutter pour dessiner les traits avec lissage par courbes de Bézier quadratiques, affichage des motifs de page (Ligné, Quadrillé, Pointillés, Blanc) et tracé interactif de la sélection Lasso en pointillés.
- **Outil Lasso & Sélection Polygonale** : Intègre l'algorithme Ray-Casting pour capturer collectivement les traits manuscrits et offre une barre d'actions rapide flottante pour couper ou supprimer les traits sélectionnés en un geste.
- **Rejet de Paume (`penOnlyMode`)** : Quand l'utilisateur écrit avec un stylet actif (`PointerDeviceKind.stylus`), les contacts tactiles accidentels des doigts ou de la paume de la main sont ignorés.
- **Gestion des Espaces & Cours** : [`dashboard_screen.dart`](mobile/lib/features/dashboard/dashboard_screen.dart) intègre les modales d'édition du nom et de la couleur des espaces, ainsi que le renommage et la suppression de cours.

---

### 5.2 Synchronisation Différentielle & Réseau Résilient
Pour économiser la bande passante mobile et la batterie :
- Au lieu de renvoyer l'intégralité du carnet à chaque trait, le client envoie des requêtes différentielles `PATCH /api/v1/pages/{id}/strokes` contenant uniquement les nouveaux traits ajoutés (`added`) et les traits effacés (`removedClientIds`).
- Les jetons de session sont stockés dans le trousseau sécurisé natif du système d'exploitation via `flutter_secure_storage` (Keystore sous Android, Keychain sous iOS).

---

## 6. Guide de Démarrage et Déploiement

### En Développement Local

```cmd
# Terminal 1 — Backend FastAPI
conda activate ocr_hand
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — Mobile Flutter sur PC (Navigateur Edge)
cd mobile
flutter run -d edge

# Terminal 3 — Frontend Web Angular
cd front-angular
npm start
```

### En Conteneurs Docker (Production)
```cmd
docker compose up -d
```
Les conteneurs lancent automatiquement :
1. La base de données PostgreSQL avec initialisation des volumes persistants.
2. Le serveur Redis.
3. Le conteneur éphémère de migration Alembic.
4. L'API Gunicorn / FastAPI sous utilisateur non-root avec healthcheck.
5. Le reverse-proxy Caddy sécurisé avec chiffrement TLS automatique.
