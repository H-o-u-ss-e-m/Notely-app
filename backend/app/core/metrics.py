"""
Module de métriques Prometheus pour la surveillance qualité IA Notely (§9.3).
Expose les métriques temps réel sans dépendance externe obligatoire :
- ocr_line_latency_seconds (histogramme / centiles)
- ocr_confidence (histogramme de confiance calibrée)
- ocr_corrections_total{language, engine} (compteur de corrections)
- ocr_cache_hit_ratio (ratio de succès du cache)
- ocr_queue_depth (profondeur de file des jobs asynchrones)
- ocr_vlm_calls_total (compteur d'appels VLM cloud)
"""
import time
import threading
from typing import Dict, List, Tuple
from collections import defaultdict


class MetricsCollector:
    def __init__(self):
        self._lock = threading.Lock()
        self._corrections_count: Dict[Tuple[str, str], int] = defaultdict(int)
        self._corrections_applied: Dict[Tuple[str, str], int] = defaultdict(int)
        self._repeat_errors: Dict[str, int] = defaultdict(int)
        self._vlm_calls: int = 0
        self._latencies: List[float] = []
        self._confidences: List[float] = []
        self._cache_hits: int = 0
        self._cache_misses: int = 0
        self._queue_depth: int = 0
        self._failed_jobs: int = 0
        self._total_jobs: int = 0

    def record_correction_applied(self, lang: str, source: str) -> None:
        with self._lock:
            self._corrections_applied[(lang or "fr", source or "memory")] += 1

    def record_repeat_error(self, lang: str) -> None:
        with self._lock:
            self._repeat_errors[lang or "fr"] += 1

    def record_ocr_line(self, latency_s: float, confidence: float) -> None:
        with self._lock:
            self._latencies.append(latency_s)
            self._confidences.append(confidence)
            if len(self._latencies) > 2000:
                self._latencies = self._latencies[-1000:]
                self._confidences = self._confidences[-1000:]

    def record_correction(self, language: str, engine: str) -> None:
        with self._lock:
            self._corrections_count[(language, engine)] += 1

    def record_vlm_call(self) -> None:
        with self._lock:
            self._vlm_calls += 1

    def record_cache_access(self, hit: bool) -> None:
        with self._lock:
            if hit:
                self._cache_hits += 1
            else:
                self._cache_misses += 1

    def set_queue_depth(self, depth: int) -> None:
        with self._lock:
            self._queue_depth = max(0, depth)

    def record_job_outcome(self, success: bool) -> None:
        with self._lock:
            self._total_jobs += 1
            if not success:
                self._failed_jobs += 1

    def generate_prometheus_text(self) -> str:
        """Génère le texte standard au format d'exposition Prometheus."""
        lines = []
        with self._lock:
            # 1. Latence par ligne
            lines.append("# HELP ocr_line_latency_seconds Latence de reconnaissance par ligne en secondes.")
            lines.append("# TYPE ocr_line_latency_seconds summary")
            if self._latencies:
                import numpy as np
                p50 = float(np.percentile(self._latencies, 50))
                p95 = float(np.percentile(self._latencies, 95))
                p99 = float(np.percentile(self._latencies, 99))
                lines.append(f'ocr_line_latency_seconds{{quantile="0.5"}} {p50:.4f}')
                lines.append(f'ocr_line_latency_seconds{{quantile="0.95"}} {p95:.4f}')
                lines.append(f'ocr_line_latency_seconds{{quantile="0.99"}} {p99:.4f}')
                lines.append(f'ocr_line_latency_seconds_sum {sum(self._latencies):.4f}')
                lines.append(f'ocr_line_latency_seconds_count {len(self._latencies)}')
            else:
                lines.append('ocr_line_latency_seconds_count 0')

            # 2. Confiance
            lines.append("\n# HELP ocr_confidence Score de confiance moyen par ligne.")
            lines.append("# TYPE ocr_confidence gauge")
            avg_conf = sum(self._confidences) / len(self._confidences) if self._confidences else 0.0
            lines.append(f"ocr_confidence {avg_conf:.4f}")

            # 3. Corrections de mots par langue et moteur
            lines.append("\n# HELP ocr_corrections_total Nombre total de corrections soumises par les utilisateurs.")
            lines.append("# TYPE ocr_corrections_total counter")
            if self._corrections_count:
                for (lang, eng), count in self._corrections_count.items():
                    lines.append(f'ocr_corrections_total{{language="{lang}",engine="{eng}"}} {count}')
            else:
                lines.append('ocr_corrections_total{language="fr",engine="trocr_fr"} 0')

            # 4. Cache hit ratio
            lines.append("\n# HELP ocr_cache_hit_ratio Taux de succès du cache HTR exact.")
            lines.append("# TYPE ocr_cache_hit_ratio gauge")
            total_cache = self._cache_hits + self._cache_misses
            ratio = (self._cache_hits / total_cache) if total_cache > 0 else 0.0
            lines.append(f"ocr_cache_hit_ratio {ratio:.4f}")

            # 5. Profondeur de file de tâches
            lines.append("\n# HELP ocr_queue_depth Nombre de jobs OCR en cours ou en attente.")
            lines.append("# TYPE ocr_queue_depth gauge")
            lines.append(f"ocr_queue_depth {self._queue_depth}")

            # 6. Appels VLM cloud
            lines.append("\n# HELP ocr_vlm_calls_total Nombre total d'appels au repli vision-langage cloud.")
            lines.append("# TYPE ocr_vlm_calls_total counter")
            lines.append(f"ocr_vlm_calls_total {self._vlm_calls}")

            # 7. Taux d'échec des jobs
            lines.append("\n# HELP ocr_job_failure_ratio Taux d'échec des jobs asynchrones.")
            lines.append("# TYPE ocr_job_failure_ratio gauge")
            fail_ratio = (self._failed_jobs / self._total_jobs) if self._total_jobs > 0 else 0.0
            lines.append(f"ocr_job_failure_ratio {fail_ratio:.4f}")

            # 8. Corrections appliquées (Partie 2.4 — memory / dictionary)
            lines.append("\n# HELP ocr_correction_applied_total Nombre de corrections appliquées par la couche finale.")
            lines.append("# TYPE ocr_correction_applied_total counter")
            if self._corrections_applied:
                for (lang, src), count in self._corrections_applied.items():
                    lines.append(f'ocr_correction_applied_total{{lang="{lang}",source="{src}"}} {count}')
            else:
                lines.append('ocr_correction_applied_total{lang="fr",source="memory"} 0')

            # 9. Erreurs répétées sur mots déjà connus (Partie 2.4)
            lines.append("\n# HELP ocr_repeat_error_total Nombre de fois où un mot déjà corrigé est de nouveau corrigé.")
            lines.append("# TYPE ocr_repeat_error_total counter")
            if self._repeat_errors:
                for lang, count in self._repeat_errors.items():
                    lines.append(f'ocr_repeat_error_total{{lang="{lang}"}} {count}')
            else:
                lines.append('ocr_repeat_error_total{lang="fr"} 0')

        return "\n".join(lines) + "\n"


metrics_collector = MetricsCollector()
