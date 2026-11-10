# Manuel d'Utilisation - Smart Notebook HTR Multi-Pages & Générateur de Cours PDF

Ce guide décrit comment tester et utiliser l'application **Smart Notebook** en version **Web (Angular)** et en version **Mobile (Android Flutter)** avec le backend IA FastAPI.

---

## 1. Démarrage Rapide des 3 Composants

### A. Backend FastAPI (Python)
Dans une invite de commande Anaconda Prompt (environnement `ocr_hand`) ou PowerShell :
```cmd
cd C:\Users\rezgu\Desktop\Home\OCR_Manuscrit
python ocr_handwritten.py
```
> **Serveur REST API disponible sur** : `http://localhost:8000/api/v1`

---

### B. Interface Web Angular (PC / Laptop / Tablette)
Dans une nouvelle invite de commande :
```cmd
cd C:\Users\rezgu\Desktop\Home\OCR_Manuscrit\front-angular
ng serve -o
```
> **Application Web ouverte sur** : `http://localhost:4200`

---

### C. Application Mobile Flutter (Téléphone Android branché en USB)
Dans une troisième invite de commande avec débogage USB activé :
```cmd
"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe" reverse tcp:8000 tcp:8000
cd C:\Users\rezgu\Desktop\Home\OCR_Manuscrit\mobile
flutter run -d 23021RAA2Y
```

---

## 2. Fonctionnalités & Utilisation

### A. Gestion Multi-Pages
- **Navigation** : Utilisez les boutons `[ ◄ ]` et `[ ► ]` pour passer d'une page à l'autre.
- **Ajout de page** : Cliquez sur `[ + Page ]` pour ajouter une nouvelle feuille vierge.
- **Suppression** : Cliquez sur l'icône corbeille `[ 🗑 ]` pour effacer ou supprimer la page actuelle.

### B. Sélection du Type de Contenu (H1 à H6 et Normal)
- **`[ Normal ]`** : Pour écrire le texte ordinaire, les paragraphes et les explications.
- **`[ H1 ]`** : Pour marquer la zone écrite comme Grand Titre Principal (ex: Titre de chapitre).
- **`[ H2 ]` .. `[ H6 ]`** : Pour les sous-titres hiérarchiques.
> *Note : L'écriture reste naturelle et manuscrite lors du tracé. La métadonnée est transmise à l'IA pour garantir un formatage typographique parfait.*

### C. Outil Schéma / Graphique (📐)
- Basculez sur l'outil **`📐 Schéma`** pour dessiner des graphes, des axes X-Y, des formes ou des figures géométriques.
- Lors de l'exportation IA, ces éléments sont automatiquement découpés et insérés comme captures graphiques haute fidélité dans le document final.

### D. Outil Lasso Vectoriel (✂️) — *Nouveau (Web & Mobile)*
- Sélectionnez l'icône **`Lasso`** dans la barre d'outils.
- Entourez un groupe de mots ou de dessins à main levée : le polygone se referme et met en surbrillance les traits capturés.
- **Actions rapides** :
  - Sur **Mobile** : Une barre d'action flottante apparaît en bas avec les boutons **`Effacer`** et **`Couper`**.
  - Sur **Web** : Cliquez sur l'action dans la barre d'outils ou appuyez simplement sur la touche **`Suppr`** ou **`Retour arrière`** de votre clavier.

### E. Gabarits de Fond de Page — *Nouveau (Web & Mobile)*
- Cliquez sur le menu déroulant de gabarit dans la barre d'outils :
  - **Ligné** : Lignes horizontales d'écolier pour guider l'écriture droite.
  - **Quadrillé** : Grille à carreaux 5mm pour mathématiques et schémas.
  - **Pointillés** : Trame de points discrets (style Bullet Journal).
  - **Blanc** : Feuille blanche unie pour dessin et croquis libres.

### F. Sélection de la Langue IA (FR, EN, AR, DE) — *Nouveau*
- Sélectionnez la langue d'inférence dans le menu déroulant :
  - 🇫🇷 **Français** (`fr`)
  - 🇬🇧 **Anglais** (`en`)
  - 🇸🇦 **Arabe** (`ar`) avec support bidirectionnel (RTL)
  - 🇩🇪 **Allemand** (`de`) avec support des umlauts et composés

### G. Gestion des Matières et Cours (CRUD Complet) — *Nouveau (Web & Mobile)*
- **Modifier un Espace / Matière** : Cliquez sur l'icône crayon `✏️` à côté du nom de l'espace pour modifier son titre ou lui attribuer une nouvelle couleur distinctive.
- **Supprimer un Espace** : Cliquez sur l'icône poubelle `🗑️` pour supprimer l'espace et ses cours associés (avec modale de confirmation).
- **Renommer ou Supprimer un Cours** : Sur chaque carte de cours, le menu d'options `⋮` permet de renommer le cours ou de le supprimer définitivement.

---

## 3. Les Deux Modes d'Exportation PDF

Cliquez sur le bouton bleu **"📄 Générer Cours (PDF)"** en bas à droite :

1. **Option 1 : Exporter Tel Quel (Dessin Exact)**
   - Exporte **l'intégralité des pages du cours** exactement comme elles ont été écrites.
   - Conserve les traits vectoriels, les couleurs et les schémas originaux.
   - Génère un unique PDF multi-pages ordonné (`Page 1 / N`, `Page 2 / N`, etc.).

2. **Option 2 : Transformer avec l'IA (Document Structuré)**
   - L'IA analyse l'ensemble des pages.
   - Reconnaissance HTR du texte et des formules.
   - Respect absolu des niveaux de titres définis (`H1`, `H2`...).
   - Insertion propre des schémas découpés.
   - Génération d'un document PDF typographique professionnel ReportLab avec sauts de page automatiques.

---

## 4. Dépannage Rapide

| Symptôme | Cause Probable | Solution |
| :--- | :--- | :--- |
| `Serveur Hors-Ligne` sur mobile | Câble USB débranché ou port non redirigé | Réexécutez `adb reverse tcp:8000 tcp:8000` |
| Erreur HTR sur le web | Le backend Python n'est pas démarré | Lancez `python ocr_handwritten.py` dans le terminal backend |
| Menu invisible sur petit écran | Sidebar repliée en mode responsive | Cliquez sur le bouton hamburger `☰` en haut à gauche |
