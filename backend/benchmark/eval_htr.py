"""
Script d'évaluation HTR complet (ML-9 / §8.9).
Calcule le CER, WER, accent_error_rate et ventile par langue et catégorie.
"""
import sys
import json
import time
import argparse
from pathlib import Path
from typing import Callable, List, Tuple

# Ajouter le dossier backend au path Python
sys.path.insert(0, str(Path(__file__).parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from benchmark.metrics import cer, wer, empty_rate, accent_error_rate
from PIL import Image


def load_dataset(dataset_dir: str) -> List[dict]:
    """Charge le jeu de test depuis labels.json."""
    ddir = Path(dataset_dir)
    labels_path = ddir / "labels.json"

    if not labels_path.exists():
        print(f"[WARN] Fichier labels.json introuvable dans {ddir}")
        return []

    items = json.loads(labels_path.read_text(encoding="utf-8"))
    images_dir = ddir / "images"
    valid = []
    missing = 0

    for it in items:
        img_path = images_dir / it["image"]
        if img_path.exists():
            valid.append({**it, "path": str(img_path)})
        else:
            missing += 1

    if missing:
        print(f"[WARN] {missing} image(s) manquante(s) ignorées.")
    print(f"[INFO] {len(valid)}/{len(items)} exemples chargés depuis {ddir}")
    return valid


def evaluate_engine(
    recognize_fn: Callable[[Image.Image, dict], Tuple[str, float]],
    dataset: List[dict],
    engine_name: str,
) -> dict:
    """Évalue un moteur OCR sur le dataset et ventile par langue/catégorie."""
    refs: List[str] = []
    hyps: List[str] = []
    confs: List[float] = []
    latencies: List[float] = []
    errors: List[dict] = []

    # Ventilation par langue
    by_lang = {}
    by_cat = {}

    for item in dataset:
        img = Image.open(item["path"]).convert("RGB")
        t0 = time.perf_counter()
        try:
            text, conf = recognize_fn(img, item)
        except Exception as e:
            text, conf = "", 0.0
            print(f"  [ERROR] {item['image']} : {e}")
        latencies.append(time.perf_counter() - t0)
        confs.append(float(conf))
        refs.append(item["text"])
        hyps.append(text)

        lang = item.get("language", "unknown")
        cat = item.get("category", item.get("type", "unknown"))

        by_lang.setdefault(lang, {"refs": [], "hyps": []})
        by_lang[lang]["refs"].append(item["text"])
        by_lang[lang]["hyps"].append(text)

        by_cat.setdefault(cat, {"refs": [], "hyps": []})
        by_cat[cat]["refs"].append(item["text"])
        by_cat[cat]["hyps"].append(text)

        if text.strip() != item["text"].strip():
            errors.append({
                "image": item["image"],
                "ref": item["text"],
                "hyp": text,
                "language": lang,
                "category": cat,
            })

    import numpy as np

    # Calcul de l'ECE (Expected Calibration Error)
    # Bins de confiance : [0, 0.2), [0.2, 0.4), [0.4, 0.6), [0.6, 0.8), [0.8, 1.0]
    num_bins = 5
    bin_limits = np.linspace(0.0, 1.0, num_bins + 1)
    accuracies = [1.0 if r.strip() == h.strip() else 0.0 for r, h in zip(refs, hyps)]
    ece_val = 0.0
    total_n = len(refs)

    for i in range(num_bins):
        low, high = bin_limits[i], bin_limits[i + 1]
        in_bin = [k for k in range(total_n) if low <= confs[k] <= high or (i == num_bins - 1 and confs[k] >= high)]
        if in_bin:
            bin_acc = sum(accuracies[k] for k in in_bin) / len(in_bin)
            bin_conf = sum(confs[k] for k in in_bin) / len(in_bin)
            ece_val += (len(in_bin) / total_n) * abs(bin_acc - bin_conf)

    n = len(dataset)
    p50 = round(float(np.percentile(latencies, 50)), 3) if latencies else 0.0
    p95 = round(float(np.percentile(latencies, 95)), 3) if latencies else 0.0

    result = {
        "engine": engine_name,
        "n": n,
        "CER": round(cer(refs, hyps), 4),
        "WER": round(wer(refs, hyps), 4),
        "accent_error_rate": round(accent_error_rate(hyps, refs), 4),
        "empty_rate": round(empty_rate(hyps), 4),
        "ECE": round(ece_val, 4),
        "latency_mean_s": round(sum(latencies) / len(latencies), 3) if latencies else 0,
        "latency_p50_s": p50,
        "latency_p95_s": p95,
        "latency_max_s": round(max(latencies), 3) if latencies else 0,
        "latency_total_s": round(sum(latencies), 3),
        "by_language": {
            l: {
                "CER": round(cer(d["refs"], d["hyps"]), 4),
                "WER": round(wer(d["refs"], d["hyps"]), 4),
                "n": len(d["refs"]),
            }
            for l, d in by_lang.items()
        },
        "by_category": {
            c: {
                "CER": round(cer(d["refs"], d["hyps"]), 4),
                "WER": round(wer(d["refs"], d["hyps"]), 4),
                "n": len(d["refs"]),
            }
            for c, d in by_cat.items()
        },
        "errors_sample": errors[:10],
    }
    return result


def print_result(r: dict) -> None:
    """Affiche les métriques de façon claire."""
    print(f"  ── {r['engine']} ──")
    print(f"     CER global       : {r['CER']*100:.2f}%")
    print(f"     WER global       : {r['WER']*100:.2f}%")
    print(f"     Erreur accents   : {r['accent_error_rate']*100:.2f}%")
    print(f"     Lignes vides     : {r['empty_rate']*100:.1f}%")
    print(f"     ECE (calibration): {r.get('ECE', 0.0):.4f}")
    print(f"     Latence moyenne  : {r['latency_mean_s']:.3f} s/ligne (p50: {r.get('latency_p50_s', 0):.3f}s, p95: {r.get('latency_p95_s', 0):.3f}s)")

    if "by_language" in r:
        print("     Ventilation par langue :")
        for lang, lres in r["by_language"].items():
            print(f"       • [{lang.upper()}] ({lres['n']} ex) : CER={lres['CER']*100:.2f}% | WER={lres['WER']*100:.2f}%")


def main():
    parser = argparse.ArgumentParser(description="Évaluation HTR Notely")
    default_dataset = "backend/benchmark/dataset" if Path("backend/benchmark/dataset").exists() else "benchmark/dataset"
    parser.add_argument("--dataset", default=default_dataset)
    parser.add_argument("--beams", type=int, default=1, help="num_beams pour TrOCR (1=greedy, 4=beam)")
    parser.add_argument("--postprocess", action="store_true", help="Activer le post-traitement ML-10")
    parser.add_argument("--subset", type=int, default=None, help="Nombre max d'échantillons à évaluer (ex: 50 pour la CI rapide)")
    parser.add_argument("--output", default="benchmark/results/latest.json")
    parser.add_argument("--compare-with", default=None, help="Chemin du JSON de baseline pour vérifier la non-régression (CI)")
    parser.add_argument("--max-cer-regression", type=float, default=None, help="Tolérance de régression CER max (ex: 0.01 pour 1 point absolu)")
    args = parser.parse_args()

    dataset = load_dataset(args.dataset)
    if not dataset:
        print("[ERROR] Dataset vide — impossible d'évaluer.")
        sys.exit(1)

    if args.subset and len(dataset) > args.subset:
        print(f"[INFO] Évaluation restreinte à un sous-ensemble de {args.subset} exemples (CI rapide).")
        dataset = dataset[:args.subset]

    from app.ml.trocr_engine import trocr_engine
    from app.ml.engines.base import LineOut, WordOut
    from app.domain.text_postprocess import postprocess_line

    trocr_engine.load_model()

    def trocr_recognize(img: Image.Image, item: dict) -> Tuple[str, float]:
        raw_text, conf = trocr_engine.recognize_line(img, num_beams=args.beams)
        if args.postprocess:
            words = [WordOut(index=i, text=w, confidence=conf) for i, w in enumerate(raw_text.split())]
            line_obj = LineOut(text=raw_text, confidence=conf, min_word_confidence=conf, words=words)
            processed = postprocess_line(line_obj, lang=item.get("language", "fr"))
            return processed.text, processed.confidence
        return raw_text, conf

    engine_label = f"trocr-{args.beams}beams" + ("+postprocess" if args.postprocess else "")
    print(f"\n{'='*60}")
    print(f"  ÉVALUATION HTR BENCHMARK — {len(dataset)} exemples ({engine_label})")
    print(f"{'='*60}\n")

    r = evaluate_engine(trocr_recognize, dataset, engine_label)
    print_result(r)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps([r], indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nRésultats sauvegardés dans {out_path}")

    # Vérification de non-régression CI (§8.9 / --max-cer-regression)
    if args.compare_with and args.max_cer_regression is not None:
        comp_path = Path(args.compare_with)
        if comp_path.exists():
            base_data = json.loads(comp_path.read_text(encoding="utf-8"))
            base_entry = base_data[0] if isinstance(base_data, list) else base_data
            base_cer = base_entry.get("CER", 1.0)
            diff = r["CER"] - base_cer
            print(f"\n[CI NON-RÉGRESSION] CER actuel: {r['CER']*100:.2f}% vs Baseline: {base_cer*100:.2f}% (diff: {diff*100:+.2f}%)")
            if diff > args.max_cer_regression:
                print(f"[CI ÉCHEC] Régression CER ({diff*100:+.2f}%) supérieure au seuil toléré ({args.max_cer_regression*100:.2f}%)")
                sys.exit(1)
            else:
                print(f"[CI SUCCÈS] Pas de régression critique (seuil max toléré: +{args.max_cer_regression*100:.2f}%)")
        else:
            print(f"[WARN] Fichier de comparaison {comp_path} introuvable.")


if __name__ == "__main__":
    main()
