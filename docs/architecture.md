# Architecture Monorepo - Smart Handwriting Notebook

## 1. Vue d'ensemble 3-Tier
```
+------------------------+      +------------------------+
|  Web Client (Angular)  |      | Mobile Client (Flutter)|
|  HTML5 Pointer Events  |      | Touch / Stylus Painter |
+-----------+------------+      +-----------+------------+
            |                               |
            +---------------+---------------+
                            | REST API (JSON)
                            v
            +-------------------------------+
            |  Python FastAPI Backend       |
            |  - Adaptive Stroke Clustering |
            |  - Baseline Deskewing         |
            |  - High-DPI Crop Preprocessor |
            |  - TrOCR Engine (CUDA/CPU)    |
            +-------------------------------+
```

## 2. Format de Stroke Universel
Angular et Flutter partagent la même représentation JSON vectorielle des tracés.

```json
{
  "id": "stroke-1694200000-1",
  "points": [
    {"x": 120.5, "y": 100.2, "timestamp": 1694200000100, "pressure": 0.8}
  ],
  "startTime": 1694200000100,
  "endTime": 1694200000250,
  "color": "#000000",
  "width": 3.0,
  "tool": "pen",
  "pointerType": "pen",
  "bbox": {"xMin": 120.5, "yMin": 100.2, "xMax": 125.0, "yMax": 115.0}
}
```

## 3. Inférence IA Unifiée
- Le modèle **TrOCR (`microsoft/trocr-base-handwritten`)** est chargé **une seule fois** au démarrage du backend Python.
- Ni Angular ni Flutter n'exécutent de réseau de neurones localement, ce qui préserve l'autonomie et les performances des appareils mobiles.
