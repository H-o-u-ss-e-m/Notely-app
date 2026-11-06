# Smart Handwriting Notebook (Monorepo Web & Mobile HTR)

Application logicielle 3-tier professionnelle de Notebook Numérique avec reconnaissance d'écriture manuscrite multi-lignes basée sur **FastAPI**, **TrOCR**, **Angular (Web)** et **Flutter (Mobile)**.

---

## 1. Architecture du Monorepo

```
OCR_Manuscrit/
├── backend/                       # API Python FastAPI + TrOCR (PyTorch/CUDA)
│   ├── app/
│   │   ├── api/                   # Endpoints REST Versionnés (/api/v1/)
│   │   ├── core/                  # Configuration, device manager, logging
│   │   ├── schemas/               # Schémas de validation Pydantic
│   │   ├── services/              # Logique métier (segmentation, OCR, documents)
│   │   ├── ml/                    # Moteur TrOCR préchargé 1x & preprocessing
│   │   └── utils/                 # Géométrie vectorielle & transformations
│   ├── tests/                     # Tests automatisés Pytest
│   ├── requirements.txt           # Dépendances Python
│   └── .env.example               # Configuration d'environnement
├── web/                           # Application Web Angular (Responsive PC/Tablette)
│   ├── src/                       # Modèles, services, canvas HTML5 Pointer Events
│   └── package.json               # Dépendances Angular
├── mobile/                        # Application Mobile Flutter (Android / iOS)
│   ├── lib/                       # Widgets Painter, CustomPainter, API Client
│   └── pubspec.yaml               # Dépendances Flutter
├── shared/                        # Spécification JSON universelle du Stroke
│   └── stroke_schema.json
├── docs/                          # Guides réseau & architecture
│   ├── architecture.md
│   └── network_setup.md
├── ocr_handwritten.py             # Launcher principal Anaconda
├── run_monorepo.py                # Launcher alternatif backend
└── README.md                      # Documentation globale
```

---

## 2. Installation et Lancement

### Étape 1 : Activer l'environnement Anaconda & installer les dépendances Backend
Dans votre **Anaconda Prompt** :
```bash
conda activate ocr_hand
cd C:\Users\rezgu\Desktop\Home\OCR_Manuscrit
pip install -r backend/requirements.txt
```

### Étape 2 : Lancer le Backend FastAPI (PC)
```bash
python ocr_handwritten.py
```
Le serveur démarre sur `http://localhost:8000` et écoute sur `0.0.0.0:8000`.

- **Documentation Swatger API** : `http://localhost:8000/api/v1/docs`
- **Statut Serveur & IA** : `http://localhost:8000/api/v1/health`

---

## 3. Connexion Mobile (Flutter sur Téléphone Android)

1. Connectez votre téléphone Android au **même réseau Wi-Fi** que votre PC.
2. Trouvez l'adresse IPv4 de votre PC (`ipconfig` dans la console Windows, ex: `192.168.1.50`).
3. Dans le fichier `mobile/lib/core/config/env_config.dart`, renseignez :
   ```dart
   static String baseUrl = "http://192.168.1.50:8000/api/v1";
   ```
4. Dans le dossier `mobile/`, lancez l'application Flutter :
   ```bash
   flutter run
   ```

---

## 4. Endpoints API Versionnés (/api/v1/)

| Méthode | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/health` | Vérifie l'état du serveur, du modèle TrOCR et de CUDA/CPU |
| `POST` | `/api/v1/recognition` | Inférence HTR complète (Strokes -> Segmentation -> Deskew -> TrOCR) |
| `POST` | `/api/v1/segmentation` | Inférence de Debug (Segmentation et bounding boxes sans OCR) |
| `POST` | `/api/v1/reocr-line` | Ré-inférence TrOCR sur une ligne spécifique |
| `POST` | `/api/v1/documents` | Création d'une note / document |
| `GET` | `/api/v1/documents/{id}/export/pdf` | Exportation d'un document au format PDF |

---

## 5. Exécution des Tests Automatisés Backend

```bash
python -m pytest backend/tests/
```
