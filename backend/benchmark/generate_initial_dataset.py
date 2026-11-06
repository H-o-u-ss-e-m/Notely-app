"""
Générateur de lignes d'évaluation synthétiques pour initialiser le benchmark Notely.
Crée des échantillons de texte manuscrit / cursif (Français avec accents, Anglais, etc.)
conformément aux spécifications du plan §8.9.
"""
import os
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

_BENCHMARK_ITEMS = [
    # Français - phrases courantes et accents (§8.9)
    {"text": "Les fonctions dérivables sont continues", "language": "fr", "category": "text"},
    {"text": "Une intégrale indéfinie est une primitive", "language": "fr", "category": "text"},
    {"text": "Théorème des accroissements finis", "language": "fr", "category": "title"},
    {"text": "Le déterminant de la matrice est nul", "language": "fr", "category": "text"},
    {"text": "Soit f une fonction continue sur [a, b]", "language": "fr", "category": "text"},
    {"text": "Calcul de la dérivée première de g(x)", "language": "fr", "category": "text"},
    {"text": "L'élève a résolu l'équation différentielle", "language": "fr", "category": "text"},
    {"text": "Méthode d'Euler et approximations", "language": "fr", "category": "title"},
    {"text": "La suite converge vers une limite finie", "language": "fr", "category": "text"},
    {"text": "Étude des variations et tableau de signes", "language": "fr", "category": "text"},
    {"text": "Les nombres complexes et le plan d'Argand", "language": "fr", "category": "title"},
    {"text": "Racines carrées et polynôme du second degré", "language": "fr", "category": "text"},
    # Anglais - IAM style standard
    {"text": "The quick brown fox jumps over the lazy dog", "language": "en", "category": "text"},
    {"text": "Linear algebra and vector spaces", "language": "en", "category": "title"},
    {"text": "Machine learning with deep neural networks", "language": "en", "category": "text"},
    {"text": "Continuous functions on compact domains", "language": "en", "category": "text"},
    {"text": "Differential calculus and optimization problems", "language": "en", "category": "text"},
    # Formules / Symboles / Listes
    {"text": "1. Définition et propriétés fondamentales", "language": "fr", "category": "list"},
    {"text": "2. Exemples d'application en physique", "language": "fr", "category": "list"},
    {"text": "f(x) = ax^2 + bx + c", "language": "en", "category": "formula"},
]


def generate_benchmark_samples(output_dir: str = "backend/benchmark/dataset"):
    out_dir = Path(output_dir)
    images_dir = out_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    labels_file = out_dir / "labels.json"

    # Essayer de trouver une police système lisible
    font = None
    possible_fonts = [
        "C:\\Windows\\Fonts\\segoepb.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\calibri.ttf",
        "C:\\Windows\\Fonts\\consola.ttf",
    ]
    for pf in possible_fonts:
        if os.path.exists(pf):
            try:
                font = ImageFont.truetype(pf, size=32)
                break
            except Exception:
                continue

    if font is None:
        font = ImageFont.load_default()

    labels = []
    for idx, item in enumerate(_BENCHMARK_ITEMS, start=1):
        filename = f"l{idx:04d}.png"
        img_path = images_dir / filename

        # Créer une image 600x80 fond blanc
        img = Image.new("RGB", (700, 80), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)

        # Dessiner le texte en noir centré verticalement
        draw.text((25, 22), item["text"], fill=(0, 0, 0), font=font)
        img.save(img_path, format="PNG")

        labels.append({
            "image": filename,
            "text": item["text"],
            "language": item["language"],
            "type": item["category"],
            "category": item["category"],
            "has_accents": any(c in "éèêëàâäôöûüùçîïÉÈÊÀÂÔÛÎ" for c in item["text"]),
        })

    labels_file.write_text(json.dumps(labels, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Génération terminée : {len(labels)} échantillons générés dans {images_dir}")


if __name__ == "__main__":
    generate_benchmark_samples()
