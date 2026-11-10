<div align="center">

<img src="assets/logo.png" alt="Notely Logo" width="220" />

# 📝 Notely — Smart Digital Ink & Handwritten OCR

### *Le Carnet de Notes Numérique Intelligent, Vectoriel et Auto-Apprenant*

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PyTorch](https://img.shields.io/badge/PyTorch-CUDA%20FP16-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)](https://pytorch.org/)
[![Angular](https://img.shields.io/badge/Angular-19+-DD0031?style=for-the-badge&logo=angular&logoColor=white)](https://angular.dev/)
[![Flutter](https://img.shields.io/badge/Flutter-3.x-02569B?style=for-the-badge&logo=flutter&logoColor=white)](https://flutter.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose%20Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![License: Proprietary](https://img.shields.io/badge/License-Proprietary-red.svg?style=for-the-badge)](#-licence)
[![Release](https://img.shields.io/badge/Release-v1.0.0-success?style=for-the-badge)](https://github.com/H-o-u-ss-e-m/Notely-app/releases)

<p align="center">
  <b>Notely</b> est une plateforme multiplateforme (Web & Mobile) de prise de notes manuscrites augmentée par Intelligence Artificielle. Elle allie la liberté du papier et de l'encre vectorielle à la puissance d'un moteur de reconnaissance d'écriture manuscrite (HTR) multilingue (Français, Anglais, Arabe), doté d'un système d'apprentissage continu qui retient vos corrections personnelles en temps réel.
</p>

[Comprendre Notely (Grand Public)](#-partie-1--comprendre-notely-en-clair-pour-monsieur-tout-le-monde) • [Architecture & Cœur IA (Ingénieur)](#-partie-2--architecture-ingénierie--cœur-dia-pour-les-experts) • [Installation](#-démarrage-rapide--déploiement) • [Sécurité](#-sécurité-avancée--devsecops) • [Tests](#-qualité-de-code--suite-de-tests)

</div>

---

## 📑 Sommaire

1. [🌟 Partie 1 : Comprendre Notely en Clair (Pour Monsieur Tout-le-Monde)](#-partie-1--comprendre-notely-en-clair-pour-monsieur-tout-le-monde)
   - [1.1 Qu'est-ce que Notely ?](#11-quest-ce-que-notely-)
   - [1.2 Les Fonctionnalités Phares au Quotidien](#12-les-fonctionnalités-phares-au-quotidien)
   - [1.3 Comment l'Application S'adapte à Votre Écriture ?](#13-comment-lapplication-sadapte-à-votre-écriture-)
   - [1.4 Une Expérience Fluide sur Tous Vos Écrans](#14-une-expérience-fluide-sur-tous-vos-écrans)
   - [1.5 La Sécurité de Vos Données en Toute Simplicité](#15-la-sécurité-de-vos-données-en-toute-simplicité)
2. [🧠 Partie 2 : Architecture, Ingénierie & Cœur d'IA (Pour les Experts)](#-partie-2--architecture-ingénierie--cœur-dia-pour-les-experts)
   - [2.1 Philosophie d'Architecture : Clean Architecture & DDD](#21-philosophie-darchitecture--clean-architecture--ddd)
   - [2.2 Le Pipeline HTR : Du Tracé Vectoriel au Texte Transcrit](#22-le-pipeline-htr--du-tracé-vectoriel-au-texte-transcrit)
   - [2.3 Le Cœur d'Inférence IA : Vision Transformer (TrOCR de Microsoft)](#23-le-cœur-dinférence-ia--vision-transformer-trocr-de-microsoft)
   - [2.4 Le Moteur Spécialisé pour la Langue Arabe (RTL, Tashkeel, Bidi)](#24-le-moteur-spécialisé-pour-la-langue-arabe-rtl-tashkeel-bidi)
   - [2.5 Le Système d'Apprentissage Continu à 3 Niveaux](#25-le-système-dapprentissage-continu-à-3-niveaux)
   - [2.6 Filtre Anti-Poisoning & Gardien de Sécurité de l'Apprentissage](#26-filtre-anti-poisoning--gardien-de-sécurité-de-lapprentissage)
   - [2.7 Responsive Web, Moteur Canvas HTML5 & Viewport Mathématique](#27-responsive-web-moteur-canvas-html5--viewport-mathématique)
   - [2.8 Moteur Mobile Flutter : Encre Skia 120 FPS & Rejet de Paume](#28-moteur-mobile-flutter--encre-skia-120-fps--rejet-de-paume)
   - [2.9 Synchronisation Différentielle Bidirectionnelle](#29-synchronisation-différentielle-bidirectionnelle)
3. [🔒 Sécurité Avancée & DevSecOps](#-sécurité-avancée--devsecops)
4. [📐 Cartographie du Monorepo](#-cartographie-du-monorepo)
5. [🚀 Démarrage Rapide & Déploiement](#-démarrage-rapide--déploiement)
   - [5.1 Prérequis](#51-prérequis)
   - [5.2 Lancement en Local (Développement)](#52-lancement-en-local-développement)
   - [5.3 Déploiement Conteneurisé avec Docker Compose](#53-déploiement-conteneurisé-avec-docker-compose)
6. [🧪 Qualité de Code & Suite de Tests](#-qualité-de-code--suite-de-tests)
7. [👥 Auteur & Remerciements](#-auteur--remerciements)

---

## 🌟 Partie 1 : Comprendre Notely en Clair (Pour Monsieur Tout-le-Monde)

### 1.1 Qu'est-ce que Notely ?

Prendre des notes sur un vrai carnet avec un stylo est intuitif et rapide, mais impossible à rechercher, à corriger proprement ou à convertir en document dactylographié sans tout recopier à la main. D'un autre côté, taper au clavier pendant un cours ou une réunion d'affaires est souvent rigide et inadapté pour faire un schéma ou poser une formule de calcul.

**Notely résout ce dilemme :**
C'est un carnet de notes numérique intelligent accessible sur navigateur web (PC, Mac, Chromebook), tablette tactile et smartphone. Vous écrivez à la main avec votre stylet ou votre doigt comme sur du papier libre, et l'application transforme instantanément vos tracés manuscrits en texte informatique propre, structuré et exportable en PDF professionnel.

```
   Écriture naturelle au stylet             Conversion IA instantanée            Export & Révision
┌─────────────────────────────────┐        ┌─────────────────────────┐        ┌───────────────────────┐
│  ✍️ "Théorème de Pythagore"      │  ───▶  │  📄 Titre H1 :          │  ───▶  │  📕 PDF imprimable    │
│  [ Schéma d'un triangle ]       │        │     Théorème de         │        │  🗂️ Flashcards SM-2   │
│  "a² + b² = c²"                 │        │     Pythagore           │        │  🔍 Recherche de mot  │
└─────────────────────────────────┘        └─────────────────────────┘        └───────────────────────┘
```

---

### 1.2 Les Fonctionnalités Phares au Quotidien

* ✍️ **Écriture Manuscrite Haute Fidélité** : Une sensation de glisse naturelle, sans saccade ni temps de latence, avec rendu anti-crénelé et lissage automatique des traits.
* 🤖 **Reconnaissance Magique de Texte (OCR / HTR)** : Convertit instantanément vos notes manuscrites (Français, Anglais et Arabe) en texte éditable et structuré (titres principaux, paragraphes et schémas).
* 📐 **Dessin de Formes Géométriques Parfaites** : Tracez un cercle approximatif, un rectangle penché ou un trait tremblotant à main levée : Notely détecte immédiatement votre intention et le transforme en figure géométrique vectorielle parfaite !
* 🔍 **Recherche dans vos Notes Manuscrites** : Tapez un mot dans la barre de recherche : Notely retrouve immédiatement l'endroit exact où vous l'avez gribouillé sur vos pages et le surligne en couleur, même si vous écrivez de manière brouillonne.
* ✂️ **Outil Lasso Vectoriel** : Entourez n'importe quel morceau de texte ou dessin avec le lasso pour le déplacer sur la page, le redimensionner ou le supprimer sans affecter le reste de vos notes.
* 🗂️ **Création Automatique de Cartes Mémoire (Flashcards)** : L'IA identifie automatiquement les définitions et questions clés de vos notes et génère des cartes de révision espacée (technologie SuperMemo SM-2) pour vous aider à mémoriser vos cours sur le long terme.
* 📄 **Exportation PDF Haute Définition** : Exportez vos carnets en PDF vectoriel impeccable, prêt pour l'impression ou l'envoi par email, respectant la mise en page et les écritures de droite à gauche (Arabe).
* 📝 **Choix de Pages Personnalisées** : Papier blanc, quadrillé 5mm (petits carreaux), ligné d'écolier ou à points (Bullet Journal).

---

### 1.3 Comment l'Application S'adapte à Votre Écriture ?

Chaque individu possède une écriture manuscrite unique : certains écrivent penché, d'autres lient à peine les lettres ou accentuent fortement certains caractères.

Dans la plupart des logiciels classiques, si l'intelligence artificielle commet une erreur sur votre écriture, elle refera systématiquement la même erreur jour après jour.

**Dans Notely, l'application possède une mémoire adaptative :**
1. Lorsque l'application lit mal l'un de vos mots, vous cliquez dessus et saisissez la bonne correction.
2. **Notely enregistre instantanément votre geste :** elle mémorise la signature visuelle de votre tracé ainsi que votre dictionnaire personnel.
3. Dès la prochaine fois que vous écrirez ce mot de la même manière, **l'application s'en souviendra et l'écrira correctement sans se tromper**, avec une rapidité fulgurante.

---

### 1.4 Une Expérience Fluide sur Tous Vos Écrans

* **Sur Ordinateur & Navigateur Web (Angular 19)** : Une interface réactive qui s'ajuste dynamiquement à la taille de votre fenêtre et à la résolution de votre moniteur (écrans Retina et 4K ultra-nets). Vous zoomez et vous déplacez sur votre page comme sur une carte géographique.
* **Sur Tablette & Mobile (Flutter)** : Conçu pour les écrans tactiles, avec **rejet intelligent de la paume de la main**. Vous pouvez poser votre main sur l'écran pour écrire confortablement au stylet sans déclencher de faux traits involontaires.
* **Sauvegarde Silencieuse** : Chaque trait est synchronisé instantanément avec le serveur. Si vous perdez votre connexion réseau ou fermez votre navigateur par mégarde, rien n'est perdu.

---

### 1.5 La Sécurité de Vos Données en Toute Simplicité

Vos cours, vos brouillons et vos documents personnels méritent une confidentialité totale :
* **Coffre-fort Numérique** : Vos mots de passe sont protégés par un système de hachage de niveau bancaire (**Argon2id**), rendant impossible leur décryptage même en cas de tentative d'intrusion.
* **Cloisonnement Strict** : Aucun autre utilisateur ne peut accéder à vos cours ou vos notes sans autorisation explicite.
* **Respect de la Vie Privée (RGPD)** : Vos données d'écriture vous appartiennent. L'utilisation de vos corrections pour améliorer les futurs modèles d'IA ne se fait qu'avec votre consentement libre et éclairé.

---

## 🧠 Partie 2 : Architecture, Ingénierie & Cœur d'IA (Pour les Experts)

Cette section détaille les choix d'ingénierie logicielle, les formalismes mathématiques et les pipelines MLOps implémentés dans le projet.

---

### 2.1 Philosophie d'Architecture : Clean Architecture & DDD

Le backend Notely applique rigoureusement les préceptes de la **Clean Architecture (Robert C. Martin / Uncle Bob)** combinée aux principes du **Domain-Driven Design (DDD)** et à l'**Architecture Hexagonale (Ports & Adapters)** :

```
┌────────────────────────────────────────────────────────────────────────┐
│                   EXTERNAL INTERFACES & INFRASTRUCTURE                 │
│   Web (Angular 19), Mobile (Flutter), PostgreSQL 16, Redis 7, Caddy    │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    CONTROLLERS & API ADAPTERS                    │  │
│  │       FastAPI Routers (/api/v1/courses, /recognition, /auth)     │  │
│  │  ┌────────────────────────────────────────────────────────────┐  │  │
│  │  │                     APPLICATION SERVICES                   │  │  │
│  │  │  HandwritingService, StructuralHtrService, PdfGenerator   │  │  │
│  │  │  ┌──────────────────────────────────────────────────────┐  │  │  │
│  │  │  │                   DOMAIN CORE (PUR)                  │  │  │  │
│  │  │  │   LineMemory, CorrectionLayer, AntiPoisonFilter,     │  │  │  │
│  │  │  │   SM2Engine, TextPostprocessor (Zéro Dépendance)     │  │  │  │
│  │  │  └──────────────────────────────────────────────────────┘  │  │  │
│  │  └────────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

#### Principes Fondamentaux Respectés :
1. **Règle de Dépendance Unidirectionnelle** : Les couches internes ignorent totalement l'existence des couches externes. Le domaine métier ([`backend/app/domain/`](backend/app/domain/)) ne dépend ni de FastAPI, ni de SQLAlchemy, ni d'un quelconque framework web.
2. **Inversion de Dépendances (DIP)** : L'accès aux modèles d'IA, aux caches et à la persistance s'effectue via des contrats et registres d'interfaces ([`backend/app/ml/registry.py`](backend/app/ml/registry.py)).
3. **Ségrégation des Responsabilités (SRP)** : La segmentation spatiale, l'inférence neuronale, la correction adaptative et la génération de documents sont découplées en services autonomes et testables unitairement en isolation.

---

### 2.2 Le Pipeline HTR : Du Tracé Vectoriel au Texte Transcrit

Contrairement aux OCR classiques qui traitent des documents scannés statiques, Notely traite des données d'**encre numérique dynamique (Digital Ink)**.

Un tracé manuscrit brut $S$ est une séquence temporelle de points d'échantillonnage :
$$S = \{(x_i, y_i, t_i, p_i)\}_{i=1}^N \quad \text{où } x, y \in \mathbb{R}^2, \; t = \text{timestamp}, \; p = \text{pression}$$

Le pipeline de transcription traverse 5 étapes spécialisées :

```
 1. Tracé Vectoriel         2. Segmentation Spatiale      3. Rendu Matriciel & Deskew
   (JSON Coordinates)   ──▶    (Grouping & Layout)    ──▶    (Anti-aliased PIL Canvas)
                                                                       │
 5. Texte Structuré         4. Post-Process & Mémoire                  ▼
   (Markdown / PDF)     ◀──    (CorrectionLayer & Dict) ◀── 4. Inférence Vision Transformer
                                                                (TrOCR ViT + BART FP16)
```

1. **Segmentation Spatiale & Structuration de Page** ([`backend/app/services/segmentation_service.py`](backend/app/services/segmentation_service.py)) :
   - Regroupement des traits par projection horizontale d'histogrammes et clustering DBSCAN/K-means sur l'axe vertical $Y$.
   - Classification sémantique de la structure de document : détection automatique des niveaux de titres ($H1 \dots H6$), paragraphes de texte continu et zones de dessins ou diagrammes (basée sur l'isotropie et la densité des tracés).
2. **Rendu Matriciel Adaptatif & Normalisation** ([`backend/app/ml/rendering.py`](backend/app/ml/rendering.py)) :
   - Rasterisation vectorielle vers matricielle à haute résolution avec interpolation par spline et lissage anti-aliasing.
   - Calcul de la pente d'écriture (*deskew*) par régression sur les boîtes englobantes et redressement affine de l'angle d'inclinaison.
3. **Cache Déterministe SHA-256 L1** ([`backend/app/ml/cache.py`](backend/app/ml/cache.py)) :
   - Les coordonnées normalisées des traits sont hachées en clé cryptographique SHA-256.
   - Si les traits n'ont pas varié, le résultat HTR est servi instantanément avec une latence inférieure à $2 \text{ ms}$ sans solliciter le GPU.

---

### 2.3 Le Cœur d'Inférence IA : Vision Transformer (TrOCR de Microsoft)

Pour la transcription d'écritures manuscrites occidentales libres et cursives, Notely embarque l'architecture de référence **TrOCR (`microsoft/trocr-base-handwritten`)** :

```
 Image de Ligne (384×384)
            │
            ▼
┌───────────────────────┐
│  Vision Transformer   │  Découpage en patchs carrés de 16×16 pixels
│   Encodeur (ViT)      │  Projection linéaire en vecteurs de dimension D
│                       │  Multi-Head Self-Attention capturant les ligatures
└───────────┬───────────┘
            │ Représentations latentes visuelles
            ▼
┌───────────────────────┐
│ Décodeur Linguistique │  Modèle autorégressif basé sur BART / RoBERTa
│      (BART/LM)        │  Cross-Attention visuelle + Modélisation du langage
│                       │  Décodage par faisceau (Beam Search, width=4)
└───────────┬───────────┘
            │
            ▼
     Texte Transcrit + Score de Confiance Mathématique (Softmax Probability)
```

#### Optimisations d'Inférence Industrielle :
* **Inférence Demi-Précision FP16** : Détection dynamique de l'accélération matérielle NVIDIA CUDA ([`backend/app/core/device.py`](backend/app/core/device.py)). En mode FP16, l'empreinte VRAM est réduite de $50\%$ et le débit d'inférence est multiplié par $3\times$.
* **Gestionnaire LRU Dynamique** ([`backend/app/ml/registry.py`](backend/app/ml/registry.py)) : Déchargement propre des poids des modèles inactifs de la mémoire vive pour préserver les ressources serveur en cas d'inactivité prolongée.

---

### 2.4 Le Moteur Spécialisé pour la Langue Arabe (RTL, Tashkeel, Bidi)

L'écriture manuscrite arabe pose des défis algorithmiques majeurs :
1. **Nature Cursive Contextuelle** : Chaque caractère adopte l'une des 4 formes morphologiques distinctes selon sa position (Isolée, Initiale, Médiane, Finale).
2. **Direction de Lecture Inversée (Right-to-Left - RTL)**.
3. **Signes Diacritiques (Tashkeel) et Élongations Typographiques (Tatweel `ـ`)**.

Notely intègre un moteur dédié ([`backend/app/ml/engines/arabic_engine.py`](backend/app/ml/engines/arabic_engine.py)) et un pipeline typographique de précision :
* **Normalisation Unicode & Nettoyage Canonique** : Harmonisation des variantes d'Alef (`أ`, `إ`, `آ` $\to$ `ا`), unification des formes de Yaa (`ى` $\to$ `ي`) et stripping paramétrable des diacritiques.
* **Moteur Bidirectionnel pour Export PDF** ([`backend/app/services/pdf_generator_service.py`](backend/app/services/pdf_generator_service.py)) :
  L'export vectoriel PDF sous ReportLab applique successivement :
  1. `arabic_reshaper.reshape()` pour lier morphologiquement les glyphes entre eux.
  2. L'algorithme bidi standard Unicode (`bidi.algorithm.get_display()`) pour inverser l'ordre des caractères tout en préservant l'orientation des nombres et des termes latins intégrés.
  3. L'inclusion de la typographie vectorielle TrueType **Noto Sans Arabic**.

---

### 2.5 Le Système d'Apprentissage Continu à 3 Niveaux

Ré-entraîner un modèle Transformer de plusieurs centaines de millions de paramètres à chaque fois qu'un utilisateur rectifie une lettre est impossible en temps réel (consommation GPU démesurée, risque d'oubli catastrophique — *catastrophic forgetting*).

**Notely résout ce problème grâce à un système d'apprentissage continu hybride à 3 étages :**

```
 ┌─────────────────────────────────────────────────────────────────────────┐
 │                   CORRECTION APPORTÉE PAR L'UTILISATEUR                 │
 └────────────────────────────────────┬────────────────────────────────────┘
                                      │
              Passe par le Filtre de Sécurité Anti-Poisoning
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        ▼                             ▼                             ▼
┌───────────────┐             ┌───────────────┐             ┌───────────────┐
│   NIVEAU 1    │             │   NIVEAU 2    │             │   NIVEAU 3    │
│   Mémoire     │             │  Dictionnaire │             │  Fine-Tuning  │
│  Géométrique  │             │   Personnel   │             │   Supervisé   │
│  (Ink Hash)   │             │  (PostgreSQL) │             │  Différé MLOps│
├───────────────┤             ├───────────────┤             ├───────────────┤
│ Hash binaire  │             │ Substitutions │             │ Dataset       │
│  grille 32×8  │             │ contextuelles │             │ labellisé     │
│ Hamming ≤ 12  │             │ par compte    │             │ (Image/Texte) │
│ Latence <1 ms │             │ utilisateur   │             │ Consent. RGPD │
└───────────────┘             └───────────────┘             └───────────────┘
```

#### Niveau 1 : La Mémoire Géométrique d'Encre (Ink Hash & Hamming)
* Implémentation : [`backend/app/domain/line_memory.py`](backend/app/domain/line_memory.py)
* **Principe Mathématique** : Tout mot manuscrit écrit par un scripteur présente une signature visuelle caractéristique. Le nuage de points est normalisé et projeté sur une grille binaire de $32 \times 8$ bits (soit 256 bits).
* L'empreinte binaire résultante est comparée aux écritures corrigées antérieures par **Distance de Hamming** :
  $$D_H(h_1, h_2) = \sum_{k=1}^{256} (h_{1}[k] \oplus h_{2}[k])$$
* Si $D_H \le 12$, le système reconnaît immédiatement la signature motrice de l'auteur et substitue instantanément la correction exacte, avec une complexité temporelle $O(1)$ et une latence inférieure à $1 \text{ ms}$.

#### Niveau 2 : Le Dictionnaire Personnel Contextuel
* Implémentation : [`backend/app/domain/user_dictionary.py`](backend/app/domain/user_dictionary.py)
* Table persistée : `user_dictionary` sous PostgreSQL.
* Quand un scripteur a une lettre ambiguë récurrente (ex. son "r" ressemble à un "v"), chaque validation incrémente un compteur de poids conditionnel $W(\text{prédit} \to \text{corrigé})$.
* Lorsque le décodeur HTR hésite avec un score de confiance inférieur au seuil de certitude, la couche de post-traitement interroge le dictionnaire du profil actif et bascule automatiquement sur l'orthographe habituelle de l'utilisateur.

#### Niveau 3 : Le Fine-Tuning Supervisé Différé (Pipeline MLOps)
* Implémentation : [`backend/app/api/ocr_feedback.py`](backend/app/api/ocr_feedback.py)
* Avec le consentement explicite de l'utilisateur (`consent_train = True`), la paire labellisée `(image_matricielle, texte_vérité_terrain)` est historisée dans `ocr_corrections`.
* Ce jeu de données permet d'entraîner périodiquement des checkpoints spécialisés de TrOCR par descente de gradient avec régularisation LoRA / PEFT.

---

### 2.6 Filtre Anti-Poisoning & Gardien de Sécurité de l'Apprentissage

Un système d'apprentissage automatique connecté aux retours utilisateurs est vulnérable aux **attaques par empoisonnement de données (Data Poisoning)** : saisies absurdes, spam, ou tentatives de corrompre le dictionnaire avec des substitutions malveillantes.

Le module [`backend/app/domain/anti_poison.py`](backend/app/domain/anti_poison.py) filtre chaque proposition de correction avant persistance :

$$CER_{\text{norm}}(S_{\text{prédit}}, S_{\text{corrigé}}) = \frac{\text{Levenshtein}(S_{\text{prédit}}, S_{\text{corrigé}})}{\max(|S_{\text{prédit}}|, |S_{\text{corrigé}}|)}$$

1. **Conditionnement par la Confiance Neuronale** : Si l'IA avait une confiance très élevée ($> 85\%$) sur une prédiction et que l'utilisateur soumet une chaîne sans aucun rapport sémantique ou géométrique, la modification est rejetée avec le code d'erreur `CORRECTION_TOO_FAR`.
2. **Détection de Chaînes Répétitives & Spam** : Analyse d'entropie rejetant les boucles de caractères identiques (ex. "zzzzzzz", "aaaaa").
3. **Pondération Multilingue Adaptative** : En arabe, où les modèles HTR latins produisent parfois des chaînes de consonnes déstructurées, le seuil de tolérance de Levenshtein est assoupli pour accepter la correction arabe authentique sans faux rejet.

---

### 2.7 Responsive Web, Moteur Canvas HTML5 & Viewport Mathématique

L'éditeur web Angular ([`front-angular/src/app/components/notebook-editor/`](front-angular/src/app/components/notebook-editor/)) intègre un moteur de dessin vectoriel sur Canvas HTML5 conçu pour être réactif sur n'importe quel écran :

#### 1. Gestion du Device Pixel Ratio (DPR)
Pour éviter le flou de pixelisation inhérent aux écrans haute densité (Apple Retina, écrans 4K/QHD) :
```typescript
const dpr = window.devicePixelRatio || 1;
canvas.width = clientWidth * dpr;
canvas.height = clientHeight * dpr;
ctx.scale(dpr, dpr);
```
Un écouteur d'événements `window.matchMedia('(resolution: ...)')` réajuste le buffer en direct si l'utilisateur déplace la fenêtre d'un moniteur standard vers un moniteur haute résolution.

#### 2. Bijections Mathématiques Bijectives du Viewport
La page logique possède une taille fixe standard (format A4 : $794 \times 1123 \text{ px}$).
Le positionnement à l'écran lors des opérations de zoom ($scale$) et de panoramique ($tx, ty$) est garanti par deux transformations inverses rigoureuses :

$$\begin{aligned}
\text{toPage}(x_{\text{écran}}, y_{\text{écran}}) &= \left(\frac{x_{\text{écran}} - tx}{scale}, \; \frac{y_{\text{écran}} - ty}{scale}\right) \\
\text{toScreen}(x_{\text{page}}, y_{\text{page}}) &= (x_{\text{page}} \cdot scale + tx, \; y_{\text{page}} \cdot scale + ty)
\end{aligned}$$

#### 3. Reconnaissance Géométrique de Forme Parfaite en Temps Réel
Le module [`shape-recognizer.ts`](front-angular/src/app/utils/shape-recognizer.ts) analyse les points tracés à la volée :
* **Détection de Segments Droits** : Calcule la distance orthogonale maximale de chaque point à la corde joignant le point de départ et le point d'arrivée.
* **Détection de Cercles / Ellipses** : Analyse la variance radiale par rapport au centre de gravité géométrique $\sigma_R / \mu_R$.
* **Détection de Rectangles** : Évalue la corrélation avec la boîte englobante orientée et la présence de 4 sommets à angles orthogonaux.
* **Protection Anti-Faux-Positifs** : Un ratio de longueur curvimétrique élimine les gribouillis et les lettres manuscrites pour empêcher toute régularisation intempestive.

#### 4. Outil Lasso Vectoriel & Ray-Casting
Le fichier [`lasso.ts`](front-angular/src/app/utils/lasso.ts) implémente l'algorithme de lancer de rayon (*Ray-Casting Algorithm*) pour déterminer l'appartenance d'un trait au polygone fermé tracé par l'utilisateur, permettant la manipulation collective des tracés.

---

### 2.8 Moteur Mobile Flutter : Encre Skia 120 FPS & Rejet de Paume

L'application mobile ([`mobile/`](mobile/)) est développée avec Flutter pour garantir une fluidité absolue (60 à 120 images par seconde sur écrans ProMotion) :
* **Moteur Graphique Bas Niveau** : Implémentation via `CustomPainter` avec interpolation par courbes de Bézier quadratiques lissant les micro-tremblements du stylet.
* **Rejet Matériel de la Paume (`Palm Rejection`)** :
  L'application interroge le type de pointeur physique fourni par le système (`PointerDeviceKind`). Dès qu'un stylet actif est détecté (`PointerDeviceKind.stylus`), tous les événements tactiles provenant des doigts ou de la paume (`PointerDeviceKind.touch`) sont instantanément ignorés.

---

### 2.9 Synchronisation Différentielle Bidirectionnelle

Pour préserver la bande passante et l'autonomie sur les réseaux mobiles, Notely bannit la réémission complète des pages de carnet à chaque trait.

Le protocole utilise une synchronisation différentielle atomique via `PATCH /api/v1/pages/{id}/strokes` :
```json
{
  "added": [
    {
      "clientId": "uuid-stroke-001",
      "tool": "pen",
      "color": "#1e293b",
      "size": 2.5,
      "points": [{"x": 102.4, "y": 88.1, "p": 0.8, "t": 173000000}]
    }
  ],
  "removedClientIds": ["uuid-stroke-legacy-99"]
}
```
Les identifiants clients uniques (`clientId`) préviennent les doublons en cas de coupure réseau temporaire et garantissent l'idempotence des opérations.

---

## 🔒 Sécurité Avancée & DevSecOps

Notely implémente une architecture de sécurité en profondeur (*Defense in Depth*) conforme aux standards OWASP Top 10 :

```
┌────────────────────────────────────────────────────────────────────────┐
│                        COUCHES DE SÉCURITÉ NOTELY                      │
├────────────────────────────────────────────────────────────────────────┤
│ 1. Mots de Passe       │ Argon2id (RFC 9106) avec salage cryptographique│
│ 2. Authentification   │ JWT éphémères (15 min) + Refresh Tokens opaques│
│ 3. Familles de Session │ Rotation stricte de Refresh Token + Détection │
│                        │ de réutilisation frauduleuse et révocation    │
│ 4. Autorisation       │ Prévention Anti-IDOR stricte (get_owned_*)     │
│ 5. Protection Réseau  │ Rate Limiting distribué (slowapi / Redis)     │
│ 6. Protection DoS     │ Limitation stricte de taille de payload HTTP  │
│ 7. Stockage Mobile    │ Android Keystore & iOS Keychain chiffré AES   │
└────────────────────────────────────────────────────────────────────────┘
```

1. **Hachage Argon2id** : Vainqueur de la *Password Hashing Competition*, Argon2id offre une résistance maximale contre les attaques matérielles par GPU, ASIC et tables arc-en-ciel.
2. **Rotation des Jetons par Famille (`family_id`)** : Chaque rafraîchissement émet un nouveau couple de tokens et invalide le précédent. Si un jeton rafraîchi antérieur est rejoué (signe d'interception malveillante), l'intégralité de la famille de sessions est immédiatement révoquée.
3. **Contrôle d'Accès Anti-IDOR (Insecure Direct Object Reference)** : Chaque ressource (matière, cours, page, tracé, carte de révision) est vérifiée contre l'identifiant du token signé. Un utilisateur tentant d'accéder aux données d'un tiers reçoit une réponse `404 Not Found` sans fuite de métadonnées.

---

## 📐 Cartographie du Monorepo

```text
OCR_Manuscrit/
├── assets/                        # Logo et ressources visuelles du projet
│   └── logo.png
├── backend/                       # API REST FastAPI & Moteur d'Intelligence Artificielle
│   ├── app/
│   │   ├── api/                   # Points de terminaison REST v1
│   │   │   ├── auth.py            # Authentification & gestion des sessions
│   │   │   ├── courses.py         # Gestion des matières, cours et pages
│   │   │   ├── flashcards.py      # Révision espacée SM-2 & génération de cartes
│   │   │   ├── ocr_feedback.py    # Retours utilisateurs & apprentissage continu
│   │   │   ├── ocr_jobs.py        # Jobs asynchrones Celery multi-pages
│   │   │   └── recognition.py     # Reconnaissance synchrone d'écriture
│   │   ├── core/                  # Configuration système, sécurité Argon2id, JWT
│   │   ├── db/                    # Modèles de données relationnels SQLAlchemy
│   │   ├── domain/                # Cœur métier pur (LineMemory, AntiPoison, SM2)
│   │   ├── ml/                    # Moteurs d'inférence TrOCR, Arabe, rendu vectoriel
│   │   ├── services/              # Services d'orchestration, segmentation et PDF
│   │   └── workers/               # Workers Celery pour les traitements lourds
│   ├── tests/                     # 90+ tests automatisés pytest (couverture P0)
│   ├── alembic.ini                # Configuration des migrations de schéma
│   └── requirements.txt           # Dépendances Python
├── front-angular/                 # Application Web SPA (Angular 19 Standalone)
│   ├── src/app/
│   │   ├── components/            # Composants UI (Dashboard, Notebook Editor)
│   │   ├── interceptors/          # Intercepteur HTTP avec sérialisation 401
│   │   ├── services/              # AuthService, ApiService, i18n
│   │   └── utils/                 # Mathématiques Canvas, Lasso, ShapeRecognizer
│   └── package.json               # Configuration des dépendances et scripts Vite
├── mobile/                        # Application Mobile (Flutter 3.x)
│   ├── lib/
│   │   ├── core/network/          # Client Dio, gestion sécurisée des tokens
│   │   ├── features/notebook/     # CustomPainter Skia, rejet de paume
│   │   └── models/                # Modèles de données Dart
│   └── pubspec.yaml               # Dépendances Flutter
├── docker-compose.yml             # Orchestration complète en conteneurs
├── Dockerfile                     # Image Docker unifiée multi-stage
└── Caddyfile                      # Configuration du reverse-proxy avec TLS
```

---

## 🚀 Démarrage Rapide & Déploiement

### 5.1 Prérequis

* **Python** 3.10+ (ou environnement Conda recommandé)
* **Node.js** 20+ et **npm**
* **Flutter SDK** 3.x
* **PostgreSQL** 16+ et **Redis** 7+
* *(Optionnel pour accélération IA)* : Carte graphique NVIDIA avec pilotes **CUDA 11.8+ / 12.x**

---

### 5.2 Lancement en Local (Développement)

#### 1. Backend Python FastAPI

```bash
# Se placer dans le répertoire backend
cd backend

# Créer et activer un environnement virtuel (ou Conda)
python -m venv venv
# Sous Linux/Mac : source venv/bin/activate
# Sous Windows : .\venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt

# Initialiser la configuration
cp .env.example .env

# Exécuter les migrations de base de données
alembic upgrade head

# Démarrer le serveur API
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
* **Documentation Interactive Swagger UI** : `http://localhost:8000/docs`
* **Métriques Prometheus** : `http://localhost:8000/metrics`

#### 2. Frontend Web Angular

```bash
# Se placer dans le répertoire web
cd front-angular

# Installer les paquets
npm install

# Lancer le serveur de développement
npm start
# Accessible sur http://localhost:4200
```

#### 3. Application Mobile Flutter

```bash
# Se placer dans le répertoire mobile
cd mobile

# Récupérer les dépendances
flutter pub get

# Lancer sur navigateur de test ou appareil connecté
flutter run -d edge # ou chrome, android, ios
```

---

### 5.3 Déploiement Conteneurisé avec Docker Compose

Pour un déploiement de production complet en une seule commande (incluant PostgreSQL, Redis, les migrations automatiques Alembic, l'API FastAPI sous Gunicorn, le worker Celery et le reverse-proxy sécurisé Caddy) :

```bash
# 1. Configurer vos variables d'environnement de production
cp .env.example .env
# Renseigner POSTGRES_PASSWORD et JWT_SECRET_KEY dans le fichier .env

# 2. Démarrer l'ensemble des services
docker compose up -d --build
```

---

## 🧪 Qualité de Code & Suite de Tests

Le monorepo intègre une suite de tests automatisés exhaustive garantissant la fiabilité des algorithmes mathématiques, de la sécurité et des couches d'IA :

### Tests Backend (Pytest)
```bash
pytest backend/tests -v
```
* **90+ tests unitaires et d'intégration** :
  * Validation stricte des contrats de sécurité P0 (Argon2id, rotation de tokens, anti-IDOR).
  * Résilience du filtre anti-poisoning face aux attaques Levenshtein.
  * Invariance de la normalisation de la langue arabe.
  * Exactitude du calcul de distance de Hamming sur l'`ink_hash`.
  * Résilience de la synchronisation différentielle des tracés.

### Tests Frontend Web (Vitest)
```bash
cd front-angular
npm test -- --watch=false
```
* Validation des transformations bijectives de Viewport ($toPage \leftrightarrow toScreen$).
* Tests de non-régression de l'intercepteur de renouvellement de session HTTP concurrent.

### Tests Mobile (Flutter Test)
```bash
cd mobile
flutter test
flutter analyze
```

---


---

## 🌿 Stratégie Git & Cycle de Versionnement

* **Branche principale `main`** : Branche de production protégée, toujours stable.
* **Branches de travail courtes** :
  * `feat/<nom>` : Développement de nouvelles fonctionnalités.
  * `fix/<nom>` : Correction d'anomalies.
* **Validation CI obligatoire** : Chaque Pull Request doit valider l'ensemble des tests unitaires, l'analyse statique et le build de production avant fusion.
* **Versionnement SemVer** : `v1.0.0` scelle la première version majeure stable de l'application.

---

## 🌐 Configuration Multi-Environnements de l'API

L'URL du backend n'est jamais figée en dur pour assurer la portabilité :
* **Web (Angular 19)** :
  * Développement local : `front-angular/src/environments/environment.ts` (`http://127.0.0.1:8000/api/v1`).
  * Production / Reverse-Proxy : `front-angular/src/environments/environment.prod.ts` (chemin relatif `/api/v1` via Caddy/Nginx).
* **Mobile (Flutter)** :
  * Configuration au build : `flutter run --dart-define=API_URL=https://mon-domaine.com`
  * Émulateur Android : bascule automatique sur `http://10.0.2.2:8000/api/v1`.
  * Modification dynamique à chaud via les paramètres de l'application (`EnvConfig.setRuntimeUrl`).

---

## 🛡️ Données Personnelles, RGPD & Suppression de Compte

Notely respecte la vie privée et les critères de publication du Google Play Store :
* **Minimisation des données** : Les mots de passe sont protégés par hachage Argon2id salé.
* **Portabilité des données** : Téléchargement complet de ses notes et corrections via `GET /api/v1/me/export`.
* **Droit à l'effacement immédiat** : L'utilisateur peut supprimer définitivement son compte et l'ensemble de ses données en cascade via l'endpoint :
  ```http
  DELETE /api/v1/me
  ```
  Cette opération détruit instantanément cours, pages, tracés vectoriels et entrées de dictionnaire associées.

---

## 📄 Licence

Ce projet est distribué sous **Licence Propriétaire (All Rights Reserved — Accès en Consultation / Évaluation uniquement)**. Toute reproduction, modification, déploiement commercial ou exploitation sans autorisation écrite est strictement interdite. Consultez le fichier [`LICENSE`](LICENSE) pour l'intégralité des termes légaux.

## 👥 Auteur & Remerciements

* **Conception & Développement** : **[Houssem Rezgui](https://github.com/H-o-u-ss-e-m)**
* **Spécialité** : Intelligence Artificielle Appliquée, Reconnaissance d'Écriture Manuscrite (HTR) & Architectures Logicielles Modernes.
* **Projet** : Notely — Système d'Encre Numérique Intelligente et de Reconnaissance Manuscrite.

---

<div align="center">
  <sub>Fait avec passion pour l'excellence en Intelligence Artificielle et en Ingénierie Logicielle.</sub>
</div>
