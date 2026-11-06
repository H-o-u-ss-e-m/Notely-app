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
