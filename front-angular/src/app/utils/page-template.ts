export type PageTemplate = 'blank' | 'lined' | 'grid' | 'dots';

export const PAGE_TEMPLATES: { id: PageTemplate; label: string }[] = [
  { id: 'blank', label: 'Page blanche' },
  { id: 'lined', label: 'Lignée' },
  { id: 'grid', label: 'Quadrillée' },
  { id: 'dots', label: 'Pointillée' },
];

export const TEMPLATE_STEP = 28; // px (repère page 794×1123)

/** Dessine le fond de page dans le repère logique de la feuille. */
export function drawPageTemplate(ctx: CanvasRenderingContext2D, template: PageTemplate, w: number, h: number): void {
  if (template === 'blank') return;
  ctx.save();
  ctx.strokeStyle = '#e2e8f0';
  ctx.fillStyle = '#cbd5e1';
  ctx.lineWidth = 0.5;
  const step = TEMPLATE_STEP;
  if (template === 'lined' || template === 'grid') {
    for (let y = step; y < h; y += step) {
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
    }
  }
  if (template === 'grid') {
    for (let x = step; x < w; x += step) {
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
    }
  }
  if (template === 'dots') {
    for (let y = step; y < h; y += step) {
      for (let x = step; x < w; x += step) {
        ctx.beginPath(); ctx.arc(x, y, 1, 0, Math.PI * 2); ctx.fill();
      }
    }
  }
  ctx.restore();
}

export function isPageTemplate(v: unknown): v is PageTemplate {
  return v === 'blank' || v === 'lined' || v === 'grid' || v === 'dots';
}
