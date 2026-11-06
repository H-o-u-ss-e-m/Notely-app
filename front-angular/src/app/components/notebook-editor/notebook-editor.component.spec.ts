import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { NotebookEditorComponent } from './notebook-editor.component';

describe('NotebookEditorComponent — Viewport & Zoom Coordinate Precision (Partie 3)', () => {
  let comp: NotebookEditorComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NotebookEditorComponent],
      providers: [provideHttpClient()],
    }).compileComponents();

    const fixture = TestBed.createComponent(NotebookEditorComponent);
    comp = fixture.componentInstance;
  });

  it('toPage(toScreen(p)) == p pour tous les zooms [0.25, 0.5, 1, 2, 4]', () => {
    for (const s of [0.25, 0.5, 1, 2, 4]) {
      comp.vp = { scale: s, tx: 37, ty: -12 };
      const p = { x: 300, y: 500 };
      const screen = comp.toScreen(p);
      const back = comp.toPage({ clientX: screen.x, clientY: screen.y });
      expect(back.x).toBeCloseTo(p.x, 6);
      expect(back.y).toBeCloseTo(p.y, 6);
    }
  });

  it('zoomAt garde le point de la feuille sous le curseur invariant pour tous les facteurs de zoom', () => {
    comp.vp = { scale: 1, tx: 48, ty: 24 };
    const cursor = { clientX: 350, clientY: 420 };
    const pageBefore = comp.toPage(cursor);

    for (const factor of [0.5, 0.5, 2.0, 2.0, 1.5, 1 / 1.5]) {
      comp.zoomAt(cursor.clientX, cursor.clientY, factor);
      const pageAfter = comp.toPage(cursor);
      expect(pageAfter.x).toBeCloseTo(pageBefore.x, 5);
      expect(pageAfter.y).toBeCloseTo(pageBefore.y, 5);
    }
  });

  it('borne le zoom dans [0.25, 4]', () => {
    comp.vp = { scale: 1, tx: 0, ty: 0 };
    comp.zoomAt(100, 100, 0.01);
    expect(comp.vp.scale).toBe(0.25);

    comp.zoomAt(100, 100, 100);
    expect(comp.vp.scale).toBe(4);
  });

  it('calcule le diametre du curseur personnalise en penWidth * vp.scale', () => {
    comp.activeTool = 'pen';
    comp.activeWidth = 3.0;
    comp.vp = { scale: 0.5, tx: 0, ty: 0 };
    expect(comp.cursorDiameter).toBeCloseTo(1.5, 5);

    comp.vp = { scale: 2.0, tx: 0, ty: 0 };
    expect(comp.cursorDiameter).toBeCloseTo(6.0, 5);
  });
});
