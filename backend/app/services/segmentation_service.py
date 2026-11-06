import math
import numpy as np
from collections import deque
from typing import List, Dict
from app.schemas.strokes import Stroke
from app.core.config import settings
from app.utils.geometry import estimate_slope

class SegmentationService:
    """
    Service de segmentation adaptatif des tracés vectoriels en lignes manuscrites.
    """
    def segment_strokes(self, strokes: List[Stroke]) -> List[Dict]:
        valid_strokes = [
            s for s in strokes 
            if s.tool != "eraser" and len(s.points) >= settings.MIN_STROKE_POINTS
        ]

        if not valid_strokes:
            return []

        if len(valid_strokes) == 1:
            s = valid_strokes[0]
            b = s.calculate_bbox()
            return [{
                "id": 1,
                "stroke_ids": [s.id],
                "strokes": [s],
                "bbox": [b.xMin, b.yMin, b.xMax, b.yMax],
                "center_y": (b.yMin + b.yMax) / 2.0,
                "slanted_angle": 0.0
            }]

        stroke_info = []
        heights = []

        for idx, s in enumerate(valid_strokes):
            b = s.calculate_bbox()
            ys = [p.y for p in s.points]
            xs = [p.x for p in s.points]

            w = max(b.xMax - b.xMin, 1.0)
            h = max(b.yMax - b.yMin, 1.0)
            y_center = (b.yMin + b.yMax) / 2.0
            y_median = float(np.median(ys))
            x_center = (b.xMin + b.xMax) / 2.0

            stroke_info.append({
                "index": idx,
                "stroke": s,
                "bbox": b,
                "xMin": b.xMin,
                "xMax": b.xMax,
                "yMin": b.yMin,
                "yMax": b.yMax,
                "width": w,
                "height": h,
                "y_center": y_center,
                "y_median": y_median,
                "x_center": x_center,
                "xs": xs,
                "ys": ys
            })
            heights.append(h)

        # Taille d'écriture médiane H_med
        H_med = float(np.median(heights))
        if H_med < 5.0:
            H_med = 15.0

        n = len(stroke_info)
        # Tri des tracés par y_center pour la fenêtre spatiale O(n log n)
        stroke_info.sort(key=lambda s: s["y_center"])

        # Graphe d'adjacence sous forme de liste de voisins
        adj_list: Dict[int, List[int]] = {i: [i] for i in range(n)}

        # Fenêtre voisine verticale (CODE-4) : n'inspecte que les tracés dans la bande 2.5 * H_med
        max_v_band = 2.5 * H_med

        for i in range(n):
            s1 = stroke_info[i]
            for j in range(i + 1, n):
                s2 = stroke_info[j]

                dy_center = abs(s2["y_center"] - s1["y_center"])
                # Élagage immédiat : tous les tracés suivants sont encore plus bas
                if dy_center > max_v_band:
                    break

                dy_median = abs(s1["y_median"] - s2["y_median"])

                y_overlap_min = max(s1["yMin"], s2["yMin"])
                y_overlap_max = min(s1["yMax"], s2["yMax"])
                vertical_overlap = max(0.0, y_overlap_max - y_overlap_min)
                overlap_ratio = vertical_overlap / min(s1["height"], s2["height"])

                if s1["xMax"] < s2["xMin"]:
                    dx_gap = s2["xMin"] - s1["xMax"]
                elif s2["xMax"] < s1["xMin"]:
                    dx_gap = s1["xMin"] - s2["xMax"]
                else:
                    dx_gap = 0.0

                condition_centers = (dy_center <= 0.70 * H_med) or (dy_median <= 0.65 * H_med)
                condition_overlap = (overlap_ratio >= 0.35) and (dx_gap <= 8.0 * H_med)

                is_dot = (s1["height"] < 0.35 * H_med) or (s2["height"] < 0.35 * H_med)
                condition_dot = False
                if is_dot and dx_gap <= 3.0 * H_med and dy_center <= 1.8 * H_med:
                    condition_dot = True

                # Proximité temporelle (continuité d'écriture manuscrite)
                time_proximity = False
                t1_end = getattr(s1["stroke"], "endTime", 0.0) or 0.0
                t2_start = getattr(s2["stroke"], "startTime", 0.0) or 0.0
                if t1_end > 0 and t2_start > 0:
                    dt = abs(t2_start - t1_end)
                    if dt < 2.5 and dy_center <= 0.85 * H_med and dx_gap <= 4.0 * H_med:
                        time_proximity = True

                if (condition_centers and dx_gap <= 10.0 * H_med) or condition_overlap or condition_dot or time_proximity:
                    adj_list[i].append(j)
                    adj_list[j].append(i)

        visited = [False] * n
        clusters = []

        for i in range(n):
            if not visited[i]:
                cluster: List[int] = []
                q: deque = deque([i])
                visited[i] = True
                while q:
                    curr = q.popleft()          # O(1) BFS
                    cluster.append(curr)
                    for neighbor in adj_list.get(curr, []):
                        if not visited[neighbor]:
                            visited[neighbor] = True
                            q.append(neighbor)
                clusters.append(cluster)

        line_groups = []
        max_deskew = getattr(settings, "MAX_DESKEW_DEG", 15.0)

        for cluster_indices in clusters:
            group_strokes = [stroke_info[idx]["stroke"] for idx in cluster_indices]
            group_infos = [stroke_info[idx] for idx in cluster_indices]

            x_min = min(info["xMin"] for info in group_infos)
            x_max = max(info["xMax"] for info in group_infos)
            y_min = min(info["yMin"] for info in group_infos)
            y_max = max(info["yMax"] for info in group_infos)
            center_y = float(np.mean([info["y_center"] for info in group_infos]))

            all_xs = [x for info in group_infos for x in info["xs"]]
            all_ys = [y for info in group_infos for y in info["ys"]]
            slanted_angle = estimate_slope(all_xs, all_ys)

            # Application effective du clamp de redressement (MAX_DESKEW_DEG / §8.8)
            if abs(slanted_angle) > max_deskew:
                slanted_angle = 0.0

            line_groups.append({
                "stroke_ids": [s.id for s in group_strokes],
                "strokes": group_strokes,
                "bbox": [x_min, y_min, x_max, y_max],
                "center_y": center_y,
                "slanted_angle": slanted_angle
            })

        line_groups.sort(key=lambda g: g["center_y"])
        for line_id, line in enumerate(line_groups, start=1):
            line["id"] = line_id

        return line_groups

segmentation_service = SegmentationService()
