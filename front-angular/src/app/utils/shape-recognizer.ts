import { Point } from '../models/models';

export type ShapeType = 'line' | 'circle' | 'ellipse' | 'rectangle';

export interface RecognizedShape {
  type: ShapeType;
  points: Point[];
}

const dist = (a: Point, b: Point) => Math.hypot(a.x - b.x, a.y - b.y);

function pathLength(pts: Point[]): number {
  let l = 0;
  for (let i = 1; i < pts.length; i++) l += dist(pts[i - 1], pts[i]);
  return l;
}

function distToSegment(p: Point, a: Point, b: Point): number {
  const dx = b.x - a.x, dy = b.y - a.y;
  const len2 = dx * dx + dy * dy;
  if (len2 === 0) return dist(p, a);
  const t = Math.max(0, Math.min(1, ((p.x - a.x) * dx + (p.y - a.y) * dy) / len2));
  return Math.hypot(p.x - (a.x + t * dx), p.y - (a.y + t * dy));
}

function withMeta(x: number, y: number, ref: Point, i: number): Point {
  return { x, y, timestamp: (ref.timestamp ?? 0) + i, pressure: ref.pressure ?? 0.5 };
}

/**
 * « Forme parfaite » : transforme un tracé approximatif en ligne, cercle/ellipse ou rectangle
 * (rectangle aligné sur les axes). Retourne `null` si aucune forme n'est reconnue :
 * l'écriture manuscrite normale n'est alors jamais modifiée.
 */
export function recognizeShape(points: Point[]): RecognizedShape | null {
  if (!points || points.length < 8) return null;

  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const p of points) {
    minX = Math.min(minX, p.x); maxX = Math.max(maxX, p.x);
    minY = Math.min(minY, p.y); maxY = Math.max(maxY, p.y);
  }
  const w = maxX - minX, h = maxY - minY;
  const diag = Math.hypot(w, h);
  if (diag < 30) return null;

  const first = points[0], last = points[points.length - 1];
  const chord = dist(first, last);
  const total = pathLength(points);
  if (total === 0) return null;

  // ── Ligne : tous les points proches de la corde ──
  if (chord >= 30) {
    const maxDev = Math.max(...points.map(p => distToSegment(p, first, last)));
    if (maxDev <= 0.06 * chord) {
      return { type: 'line', points: [withMeta(first.x, first.y, first, 0), withMeta(last.x, last.y, last, 1)] };
    }
  }

  // ── Formes fermées ──
  if (chord > 0.25 * total) return null; // tracé non refermé

  // Rectangle : points collés aux bords de la boîte englobante ET passage près des 4 coins
  if (w > 15 && h > 15) {
    const borderDist = (p: Point) => Math.min(p.x - minX, maxX - p.x, p.y - minY, maxY - p.y);
    const meanBorder = points.reduce((s, p) => s + borderDist(p), 0) / points.length;
    const corners: Point[] = [
      { x: minX, y: minY }, { x: maxX, y: minY }, { x: maxX, y: maxY }, { x: minX, y: maxY },
    ];
    const cornersHit = corners.every(c => Math.min(...points.map(p => dist(p, c))) <= 0.08 * diag);
    // Le périmètre parcouru doit correspondre à celui du rectangle (écarte zigzags et boucles multiples)
    const perimRatio = total / (2 * (w + h));
    if (meanBorder <= 0.04 * diag && cornersHit && perimRatio >= 0.85 && perimRatio <= 1.3) {
      const r = [corners[0], corners[1], corners[2], corners[3], corners[0]];
      return { type: 'rectangle', points: r.map((c, i) => withMeta(c.x, c.y, first, i)) };
    }
  }

  // Cercle / ellipse : rayon (normalisé sur l'ellipse englobante) quasi constant
  const cx = (minX + maxX) / 2, cy = (minY + maxY) / 2;
  const rx = w / 2, ry = h / 2;
  if (rx > 8 && ry > 8) {
    const norm = points.map(p => Math.hypot((p.x - cx) / rx, (p.y - cy) / ry));
    const mean = norm.reduce((a, b) => a + b, 0) / norm.length;
    const sd = Math.sqrt(norm.reduce((s, v) => s + (v - mean) ** 2, 0) / norm.length);
    const ellipsePerim = Math.PI * (rx + ry);
    const loopRatio = total / ellipsePerim;
    if (mean > 0 && sd / mean <= 0.12 && loopRatio >= 0.85 && loopRatio <= 1.3) {
      const ratio = Math.min(rx, ry) / Math.max(rx, ry);
      const isCircle = ratio >= 0.8;
      const rC = (rx + ry) / 2;
      const n = 64;
      const out: Point[] = [];
      for (let i = 0; i <= n; i++) {
        const a = (2 * Math.PI * i) / n;
        out.push(withMeta(cx + (isCircle ? rC : rx) * Math.cos(a), cy + (isCircle ? rC : ry) * Math.sin(a), first, i));
      }
      return { type: isCircle ? 'circle' : 'ellipse', points: out };
    }
  }
  return null;
}
