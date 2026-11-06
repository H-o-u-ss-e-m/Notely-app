"""
Ajouter un exemple annoté au dataset de benchmark.

Usage :
    python -m benchmark.add_sample --image path/to/line.png --text "Le texte correct"
    python -m benchmark.add_sample --image line.png --text "Bonjour monde" --lang fr --type paragraph
"""
import sys
import json
import shutil
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    parser = argparse.ArgumentParser(description="Ajouter un exemple au dataset HTR")
    parser.add_argument("--image", required=True, help="Chemin vers l'image PNG de la ligne")
    parser.add_argument("--text", required=True, help="Transcription correcte")
    parser.add_argument("--lang", default="fr", help="Langue : fr | en | ar")
    parser.add_argument("--type", default="paragraph",
                        help="Type : paragraph | title | list | formula | mixed")
    parser.add_argument("--dataset", default="benchmark/dataset", help="Dossier du dataset")
    args = parser.parse_args()

    ddir = Path(args.dataset)
    images_dir = ddir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    labels_path = ddir / "labels.json"

    # Charger ou créer labels.json
    if labels_path.exists():
        items = json.loads(labels_path.read_text(encoding="utf-8"))
    else:
        items = []

    # Vérifier l'image source
    src = Path(args.image)
    if not src.exists():
        print(f"[ERROR] Image introuvable : {src}")
        sys.exit(1)

    # Copier l'image avec un nom séquentiel
    img_name = f"l{len(items)+1:04d}{src.suffix}"
    dst = images_dir / img_name
    shutil.copy2(src, dst)

    # Ajouter l'entrée dans labels.json
    items.append({
        "image": img_name,
        "text": args.text,
        "language": args.lang,
        "type": args.type,
    })

    labels_path.write_text(
        json.dumps(items, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"✅ Exemple ajouté : {img_name} → '{args.text}'")
    print(f"   Dataset total  : {len(items)} exemple(s)")


if __name__ == "__main__":
    main()
