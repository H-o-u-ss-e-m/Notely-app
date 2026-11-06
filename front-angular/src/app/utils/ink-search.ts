import { StructuralElement } from '../models/models';

const AR_MARKS = /[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED\u0640\u200e\u200f]/g;

/** Normalisation de comparaison (insensible à la casse, aux accents, au tashkeel et aux variantes d'alef). */
export function normalizeForSearch(text: string): string {
  let t = (text || '').normalize('NFKD').replace(/[\u0300-\u036f]/g, '');
  t = t.replace(AR_MARKS, '').replace(/[إأآٱ]/g, 'ا').replace(/ى/g, 'ي').replace(/ة/g, 'ه');
  return t.toLowerCase().replace(/\s+/g, ' ').trim();
}

export interface InkMatch {
  elementId: number;
  pageNumber: number;
  text: string;
  bbox: number[]; // [xMin, yMin, xMax, yMax] — repère page
}

/**
 * Recherche dans l'écriture reconnue. Requête d'un mot : correspondance par mot (bbox du mot si
 * disponible, sinon bbox de la ligne). Requête de plusieurs mots : correspondance dans le texte de la ligne.
 */
export function findInkMatches(elements: StructuralElement[], query: string): InkMatch[] {
  const q = normalizeForSearch(query);
  if (!q) return [];
  const out: InkMatch[] = [];
  for (const el of elements || []) {
    if (el.type === 'diagram') continue;
    const page = el.pageNumber ?? 1;
    if (!q.includes(' ') && el.words && el.words.length) {
      for (const w of el.words) {
        if (normalizeForSearch(w.text).includes(q)) {
          out.push({ elementId: el.id, pageNumber: page, text: w.text, bbox: w.bbox && w.bbox.length === 4 ? w.bbox : el.bbox });
        }
      }
    } else if (normalizeForSearch(el.text).includes(q)) {
      out.push({ elementId: el.id, pageNumber: page, text: el.text, bbox: el.bbox });
    }
  }
  return out;
}
