import { recognizeShape } from './shape-recognizer';
import { strokesInLasso, translateStrokes, boundsOf, pointInPolygon } from './lasso';
import { findInkMatches, normalizeForSearch } from './ink-search';
import { Point, Stroke, StructuralElement } from '../models/models';

// Génère des points bruités de façon déterministe
function noise(i: number, amp: number): number {
  return Math.sin(i * 12.9898) * amp;
}

function circlePts(cx: number, cy: number, r: number, n = 60, amp = 2): Point[] {
  return Array.from({ length: n + 1 }, (_, i) => {
    const a = (2 * Math.PI * i) / n;
    return { x: cx + r * Math.cos(a) + noise(i, amp), y: cy + r * Math.sin(a) + noise(i + 99, amp) };
  });
}

function rectPts(x0: number, y0: number, x1: number, y1: number, per = 15, amp = 1.5): Point[] {
  const pts: Point[] = [];
  const edges: [number, number, number, number][] = [[x0, y0, x1, y0], [x1, y0, x1, y1], [x1, y1, x0, y1], [x0, y1, x0, y0]];
  let k = 0;
  for (const [ax, ay, bx, by] of edges) {
    for (let i = 0; i < per; i++) {
      const t = i / per;
      pts.push({ x: ax + (bx - ax) * t + noise(k, amp), y: ay + (by - ay) * t + noise(k + 7, amp) });
      k++;
    }
  }
  pts.push({ x: x0, y: y0 });
  return pts;
}

describe('recognizeShape (Forme parfaite)', () => {
  it('reconnaît une ligne droite approximative', () => {
    const pts: Point[] = Array.from({ length: 30 }, (_, i) => ({ x: 10 + i * 8, y: 50 + noise(i, 2) }));
    const r = recognizeShape(pts);
    expect(r?.type).toBe('line');
    expect(r?.points.length).toBe(2);
  });

  it('reconnaît un cercle', () => {
    const r = recognizeShape(circlePts(200, 200, 60));
    expect(r?.type).toBe('circle');
    expect(r!.points.length).toBeGreaterThan(30);
  });

  it('reconnaît une ellipse', () => {
    const pts = circlePts(200, 200, 60).map(p => ({ x: 200 + (p.x - 200) * 2, y: p.y }));
    expect(recognizeShape(pts)?.type).toBe('ellipse');
  });

  it('reconnaît un rectangle', () => {
    const r = recognizeShape(rectPts(100, 100, 300, 220));
    expect(r?.type).toBe('rectangle');
    expect(r!.points.length).toBe(5);
  });

  it('ne modifie pas une écriture libre (zigzag / spirale)', () => {
    const zig: Point[] = Array.from({ length: 40 }, (_, i) => ({ x: i * 6, y: i % 2 === 0 ? 0 : 40 }));
    expect(recognizeShape(zig)).toBeNull();
    const spiral: Point[] = Array.from({ length: 80 }, (_, i) => ({ x: 100 + i * Math.cos(i / 5), y: 100 + i * Math.sin(i / 5) }));
    expect(recognizeShape(spiral)).toBeNull();
  });

  it('ignore les tracés trop courts', () => {
    expect(recognizeShape([{ x: 0, y: 0 }, { x: 1, y: 1 }])).toBeNull();
    expect(recognizeShape(Array.from({ length: 10 }, (_, i) => ({ x: i, y: 0 })))).toBeNull();
  });
});

describe('lasso', () => {
  const square = [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 100 }, { x: 0, y: 100 }];
  const mk = (id: string, pts: [number, number][]): Stroke => ({
    id, startTime: 0, endTime: 0,
    points: pts.map(([x, y]) => ({ x, y })),
    bbox: { xMin: Math.min(...pts.map(p => p[0])), yMin: Math.min(...pts.map(p => p[1])), xMax: Math.max(...pts.map(p => p[0])), yMax: Math.max(...pts.map(p => p[1])) },
  });

  it('pointInPolygon', () => {
    expect(pointInPolygon({ x: 50, y: 50 }, square)).toBe(true);
    expect(pointInPolygon({ x: 150, y: 50 }, square)).toBe(false);
  });

  it('sélectionne seulement les tracés majoritairement dans le lasso', () => {
    const inside = mk('in', [[10, 10], [50, 50], [90, 90]]);
    const outside = mk('out', [[200, 200], [250, 250]]);
    const partial = mk('part', [[10, 10], [20, 20], [300, 300], [400, 400], [500, 500]]);
    const sel = strokesInLasso([inside, outside, partial], square);
    expect(sel.map(s => s.id)).toEqual(['in']);
    expect(strokesInLasso([inside], [{ x: 0, y: 0 }, { x: 1, y: 1 }])).toEqual([]);
  });

  it('translateStrokes déplace points et bbox', () => {
    const s = mk('a', [[0, 0], [10, 10]]);
    translateStrokes([s], 5, -3);
    expect(s.points[1]).toEqual({ x: 15, y: 7 });
    expect(s.bbox).toEqual({ xMin: 5, yMin: -3, xMax: 15, yMax: 7 });
    expect(boundsOf([s])).toEqual({ xMin: 5, yMin: -3, xMax: 15, yMax: 7 });
  });
});

describe('ink-search', () => {
  const els: StructuralElement[] = [
    {
      id: 1, type: 'h1', text: 'Équation du second degré', confidence: 1, bbox: [10, 10, 300, 40], pageNumber: 1,
      words: [
        { index: 0, text: 'Équation', confidence: 1, bbox: [10, 10, 100, 40] },
        { index: 1, text: 'du', confidence: 1 },
        { index: 2, text: 'second', confidence: 1, bbox: [140, 10, 200, 40] },
      ],
    },
    { id: 2, type: 'paragraph', text: 'مَدْرَسَة جميلة', confidence: 1, bbox: [10, 60, 300, 90], pageNumber: 2 },
    { id: 3, type: 'diagram', text: 'équation', confidence: 1, bbox: [0, 0, 1, 1] },
  ];

  it('normalise accents, casse, tashkeel et alef', () => {
    expect(normalizeForSearch('ÉQUATION')).toBe('equation');
    expect(normalizeForSearch('مَدْرَسَة')).toBe(normalizeForSearch('مدرسه'));
    expect(normalizeForSearch('أحمد')).toBe(normalizeForSearch('احمد'));
  });

  it('trouve un mot avec sa bbox de mot, sans tenir compte des accents', () => {
    const m = findInkMatches(els, 'equation');
    expect(m.length).toBe(1);
    expect(m[0].bbox).toEqual([10, 10, 100, 40]);
  });

  it('retombe sur la bbox de ligne si le mot n\'a pas de bbox', () => {
    const m = findInkMatches(els, 'du');
    expect(m[0].bbox).toEqual([10, 10, 300, 40]);
  });

  it('cherche une phrase et en arabe, ignore les schémas', () => {
    expect(findInkMatches(els, 'second degre').map(x => x.elementId)).toEqual([1]);
    const ar = findInkMatches(els, 'مدرسة');
    expect(ar.map(x => x.pageNumber)).toEqual([2]);
    expect(findInkMatches(els, '')).toEqual([]);
  });
});
