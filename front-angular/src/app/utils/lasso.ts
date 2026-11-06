import { Point, Stroke } from '../models/models';

export function pointInPolygon(p: { x: number; y: number }, poly: { x: number; y: number }[]): boolean {
  let inside = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const xi = poly[i].x, yi = poly[i].y, xj = poly[j].x, yj = poly[j].y;
    const intersect = (yi > p.y) !== (yj > p.y) && p.x < ((xj - xi) * (p.y - yi)) / (yj - yi) + xi;
    if (intersect) inside = !inside;
  }
  return inside;
}

/** Tracés dont au moins `minFraction` des points sont à l'intérieur du lasso (polygone ≥ 3 sommets). */
export function strokesInLasso(strokes: Stroke[], polygon: { x: number; y: number }[], minFraction = 0.8): Stroke[] {
  if (polygon.length < 3) return [];
  return strokes.filter(s => {
    if (!s.points.length) return false;
    const inside = s.points.filter(p => pointInPolygon(p, polygon)).length;
    return inside / s.points.length >= minFraction;
  });
}

export function boundsOf(strokes: Stroke[]): { xMin: number; yMin: number; xMax: number; yMax: number } | null {
  let b: { xMin: number; yMin: number; xMax: number; yMax: number } | null = null;
  for (const s of strokes) {
    for (const p of s.points) {
      if (!b) b = { xMin: p.x, yMin: p.y, xMax: p.x, yMax: p.y };
      else {
        b.xMin = Math.min(b.xMin, p.x); b.yMin = Math.min(b.yMin, p.y);
        b.xMax = Math.max(b.xMax, p.x); b.yMax = Math.max(b.yMax, p.y);
      }
    }
  }
  return b;
}

/** Déplace les tracés (mutation) et met à jour leur bbox. */
export function translateStrokes(strokes: Stroke[], dx: number, dy: number): void {
  for (const s of strokes) {
    s.points = s.points.map((p: Point) => ({ ...p, x: p.x + dx, y: p.y + dy }));
    if (s.bbox) {
      s.bbox = { xMin: s.bbox.xMin + dx, yMin: s.bbox.yMin + dy, xMax: s.bbox.xMax + dx, yMax: s.bbox.yMax + dy };
    }
  }
}
