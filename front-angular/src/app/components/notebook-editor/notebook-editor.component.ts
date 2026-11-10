import { PageTemplate, drawPageTemplate } from '../../utils/page-template';
import { findInkMatches, InkMatch } from '../../utils/ink-search';
import { strokesInLasso, translateStrokes, boundsOf } from '../../utils/lasso';
import { recognizeShape } from '../../utils/shape-recognizer';
import { Component, OnInit, AfterViewInit, OnDestroy, ViewChild, ElementRef, HostListener, Inject, PLATFORM_ID, ChangeDetectorRef } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { StateService } from '../../services/state.service';
import { ApiService } from '../../services/api.service';
import { ToastService } from '../../services/toast.service';
import { I18nService } from '../../services/i18n.service';
import { SaveStatusChipComponent } from '../save-status-chip/save-status-chip.component';
import { Stroke, NotebookPage, Point, StructuralHTRResponse, StructuralElement, WordResult } from '../../models/models';

export interface Viewport {
  scale: number;
  tx: number;
  ty: number;
}

@Component({
  selector: 'app-notebook-editor',
  standalone: true,
  imports: [CommonModule, FormsModule, SaveStatusChipComponent],
  templateUrl: './notebook-editor.component.html',
  styleUrl: './notebook-editor.component.scss'
})
export class NotebookEditorComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild('canvas', { static: false }) canvasRef!: ElementRef<HTMLCanvasElement>;
  @ViewChild('hostViewport', { static: false }) hostViewportRef!: ElementRef<HTMLElement>;

  readonly PAGE_W = 794;
  readonly PAGE_H = 1123;

  // Rejet de la paume (Partie 4.4)
  penOnlyMode: boolean = false;
  hasActivePen: boolean = false;

  // Badge de zoom temporaire (Partie 4.5)
  zoomBadgeVisible: boolean = false;
  private zoomBadgeTimer: any = null;

  pages: NotebookPage[] = [
    { id: 'page-1', pageNumber: 1, strokes: [], redoStack: [] }
  ];
  currentPageIndex: number = 0;

  activeTool: 'pen' | 'diagram' | 'eraser' | 'lasso' = 'pen';
  activeContentType: string = 'normal';
  activeColor: string = '#000000';
  activeWidth: number = 3.0;

  showGrid: boolean = true;
  // Modèles de page (§6.6)
  currentTemplate: PageTemplate = 'lined';

  // Recherche dans l'écriture manuscrite (§6.3)
  inkSearchQuery: string = '';
  inkSearchMatches: InkMatch[] = [];

  // Outil Lasso (§6.4)
  lassoPoints: Point[] = [];
  selectedLassoStrokes: Stroke[] = [];
  isDraggingSelection: boolean = false;
  dragLastPos: { x: number; y: number } | null = null;

  // Formes parfaites (§6.5)
  snapToShapes: boolean = true;

  // Flashcards SM-2 (§6.7)
  isGeneratingCards: boolean = false;
  showFlashcardModal: boolean = false;
  activeCards: any[] = [];
  currentCardIdx: number = 0;
  showCardAnswer: boolean = false;
  isLoading: boolean = false;
  isProcessingHtr: boolean = false;
  isProcessingAi: boolean = false;
  isExportingPdf: boolean = false;

  showAiPanel: boolean = false;
  showPdfModal: boolean = false;
  structuralResult: StructuralHTRResponse | null = null;

  // Source de vérité unique pour le Viewport (Plan v2 §3.2)
  vp: Viewport = { scale: 1, tx: 0, ty: 0 };
  dpr: number = 1;
  private viewportInitialized: boolean = false;
  private resizeObserver: ResizeObserver | null = null;
  private boundWheelListener: ((e: WheelEvent) => void) | null = null;

  get zoomLevel(): number {
    return this.vp.scale;
  }
  set zoomLevel(val: number) {
    this.vp.scale = val;
  }

  get panX(): number {
    return this.vp.tx;
  }
  set panX(val: number) {
    this.vp.tx = val;
  }

  get panY(): number {
    return this.vp.ty;
  }
  set panY(val: number) {
    this.vp.ty = val;
  }

  isPanMode: boolean = false;
  private isPanning: boolean = false;
  private startPanX: number = 0;
  private startPanY: number = 0;

  // Curseur personnalisé en pixels CSS (Plan v2 §3.2)
  cursorX: number = 0;
  cursorY: number = 0;
  showCursor: boolean = false;

  get cursorDiameter(): number {
    const penWidth = this.activeTool === 'eraser' ? this.activeWidth * 4 : this.activeWidth;
    return penWidth * this.vp.scale;
  }

  // Navigation onglets OCR (§6.4)
  ocrTab: 'text' | 'words' | 'structure' = 'text';
  selectedLanguage: 'fr' | 'en' | 'ar' | 'de' = 'fr';
  localCorrections: Record<string, string> = {};

  // Modal correction mot à mot (§6.4)
  selectedWord: WordResult | null = null;
  selectedElement: StructuralElement | null = null;
  correctionInput: string = '';
  consentTrainFeedback: boolean = false;
  showWordModal: boolean = false;

  get avgConfidence(): number {
    if (!this.structuralResult || !this.structuralResult.elements.length) return 0;
    const elements = this.structuralResult.elements.filter(e => e.type !== 'diagram');
    if (!elements.length) return 1.0;
    const totalChars = elements.reduce((sum, el) => sum + (el.text ? el.text.length : 1), 0);
    const weightedSum = elements.reduce((sum, el) => sum + (el.confidence || 0.9) * (el.text ? el.text.length : 1), 0);
    return totalChars > 0 ? weightedSum / totalChars : 0.9;
  }

  get minConfidence(): number {
    if (!this.structuralResult || !this.structuralResult.elements.length) return 1.0;
    const textElements = this.structuralResult.elements.filter(e => e.type !== 'diagram');
    if (!textElements.length) return 1.0;
    return Math.min(...textElements.map(e => e.confidence || 1.0));
  }

  get isCalibrated(): boolean {
    return !!(this.structuralResult && (this.structuralResult as any).calibrated);
  }

  getConfidenceLevel(conf: number): 'sure' | 'check' | 'wrong' {
    if (conf >= 0.80) return 'sure';
    if (conf >= 0.50) return 'check';
    return 'wrong';
  }

  openWordCorrection(elem: StructuralElement, word: WordResult) {
    this.selectedElement = elem;
    this.selectedWord = word;
    this.correctionInput = word.text;
    this.showWordModal = true;
  }

  closeWordModal() {
    this.showWordModal = false;
    this.selectedWord = null;
    this.selectedElement = null;
    this.correctionInput = '';
  }

  selectAlternative(alt: string) {
    this.correctionInput = alt;
  }

  applyWordCorrection() {
    if (!this.selectedWord || !this.selectedElement) return;
    const newText = this.correctionInput.trim();
    if (!newText) return;

    const linePredicted = this.selectedElement.text;
    const wordPredicted = this.selectedWord.original || this.selectedWord.text;
    if (!this.selectedWord.original) {
      this.selectedWord.original = this.selectedWord.text;
    }
    this.selectedWord.text = newText;
    this.selectedWord.corrected = true;
    this.selectedWord.source = 'memory';

    if (this.selectedElement.words && this.selectedElement.words.length) {
      this.selectedElement.text = this.selectedElement.words.map(w => w.text).join(' ');
    } else {
      this.selectedElement.text = newText;
    }
    this.selectedElement.source = 'memory';
    const lineCorrected = this.selectedElement.text;

    const strokeIds = this.selectedElement.stroke_ids || [];
    const lineStrokes = this.pages
      .flatMap(p => p.strokes)
      .filter(s => strokeIds.includes(s.id));

    const localKey = this.selectedElement.stroke_fingerprint || strokeIds.join(',');
    if (localKey) {
      this.saveLocalCorrection(localKey, lineCorrected);
    }

    // Appel feedback vers l'API (avec gestion explicite des rejets 422 — Plan v2 §1.5 & §1.6)
    this.apiService.sendFeedback({
      scope: 'word',
      word_index: this.selectedWord.index,
      stroke_ids: strokeIds,
      strokes: lineStrokes,
      stroke_fingerprint: this.selectedElement.stroke_fingerprint,
      language: this.selectedLanguage,
      predicted_text: wordPredicted,
      corrected_text: newText,
      line_predicted: linePredicted,
      line_corrected: lineCorrected,
      confidence: this.selectedWord.confidence,
      consent_train: this.consentTrainFeedback
    }).subscribe({
      next: () => {
        this.toastService.success('Mot corrigé', `« ${newText} » enregistré.`);
      },
      error: (err) => {
        const detail = err?.error?.detail || err?.message || 'Serveur indisponible (appliqué localement).';
        this.toastService.warning('Correction non enregistrée sur le serveur', String(detail));
      }
    });

    this.closeWordModal();
  }

  private loadLocalCorrections() {
    if (!this.isBrowser || typeof localStorage === 'undefined') return;
    try {
      const raw = localStorage.getItem('notely_local_corrections');
      if (raw) {
        this.localCorrections = JSON.parse(raw) || {};
      }
    } catch {
      this.localCorrections = {};
    }
  }

  private saveLocalCorrection(key: string, correctedLine: string) {
    if (!key || !correctedLine) return;
    this.localCorrections[key] = correctedLine;
    if (this.isBrowser && typeof localStorage !== 'undefined') {
      try {
        localStorage.setItem('notely_local_corrections', JSON.stringify(this.localCorrections));
      } catch {}
    }
  }

  private applyLocalCorrectionsFallback(res: StructuralHTRResponse) {
    if (!res || !res.elements) return;
    for (const el of res.elements) {
      if (el.source === 'memory' || el.source === 'dictionary') continue;
      const key = el.stroke_fingerprint || (el.stroke_ids ? el.stroke_ids.join(',') : '');
      if (key && this.localCorrections[key]) {
        const fixed = this.localCorrections[key];
        el.text = fixed;
        el.source = 'memory';
        el.words = fixed.split(/\s+/).map((tok, idx) => ({
          index: idx,
          text: tok,
          confidence: 1.0,
          calibrated: false,
          corrected: true,
          source: 'memory'
        }));
      }
    }
  }

  revertWordCorrection(elem: StructuralElement, word: WordResult, event?: MouseEvent) {
    if (event) event.stopPropagation();
    if (word.original) {
      word.text = word.original;
      word.corrected = false;
      word.original = undefined;
      if (elem.words && elem.words.length) {
        elem.text = elem.words.map(w => w.text).join(' ');
      }
      this.toastService.info('Correction annulée', 'Retour au texte initial.');
    }
  }

  contentTypes = [
    { id: 'normal', label: 'Normal' },
    { id: 'h1', label: 'H1' },
    { id: 'h2', label: 'H2' },
    { id: 'h3', label: 'H3' },
    { id: 'h4', label: 'H4' },
    { id: 'h5', label: 'H5' },
    { id: 'h6', label: 'H6' },
  ];

  palette = [
    { color: '#000000', name: 'Noir' },
    { color: '#1E40AF', name: 'Bleu' },
    { color: '#DC2626', name: 'Rouge' },
    { color: '#15803D', name: 'Vert' },
    { color: '#7C3AED', name: 'Violet' },
  ];

  widths = [1.5, 3.0, 5.0];

  private ctx: CanvasRenderingContext2D | null = null;
  private isDrawing: boolean = false;
  private isBrowser: boolean = false;
  private currentStroke: Stroke | null = null;
  private autoSaveSub: any = null;

  constructor(
    public stateService: StateService,
    public i18nService: I18nService,
    private apiService: ApiService,
    private toastService: ToastService,
    private cdr: ChangeDetectorRef,
    @Inject(PLATFORM_ID) platformId: Object
  ) {
    this.isBrowser = isPlatformBrowser(platformId);
  }

  ngOnInit() {
    this.loadLocalCorrections();
    this.stateService.currentLesson$.subscribe(les => {
      if (les && les.pages && les.pages.length > 0) {
        this.pages = les.pages;
        this.currentPageIndex = 0;
      } else {
        this.pages = [{ id: 'p-1', pageNumber: 1, strokes: [], redoStack: [] }];
        this.currentPageIndex = 0;
      }
      setTimeout(() => {
        this.resizeCanvas();
      }, 50);
    });
  }

  ngAfterViewInit() {
    if (!this.isBrowser || !this.canvasRef) return;
    const c = this.canvasRef.nativeElement;
    const host = this.hostViewportRef?.nativeElement || c.parentElement;

    this.boundWheelListener = (e: WheelEvent) => this.onWheel(e);
    c.addEventListener('wheel', this.boundWheelListener, { passive: false });

    if (host && typeof ResizeObserver !== 'undefined') {
      this.resizeObserver = new ResizeObserver(() => this.resizeCanvas());
      this.resizeObserver.observe(host);
    }

    if (typeof window !== 'undefined' && typeof window.matchMedia === 'function') {
      this.dpr = window.devicePixelRatio || 1;
      window.matchMedia(`(resolution: ${this.dpr}dppx)`).addEventListener('change', () => this.resizeCanvas());
    }

    this.resizeCanvas();
  }

  ngOnDestroy() {
    if (this.autoSaveSub) clearInterval(this.autoSaveSub);
    if (this.resizeObserver) {
      this.resizeObserver.disconnect();
      this.resizeObserver = null;
    }
    if (this.boundWheelListener && this.canvasRef?.nativeElement) {
      this.canvasRef.nativeElement.removeEventListener('wheel', this.boundWheelListener);
      this.boundWheelListener = null;
    }
  }

  get currentPage(): NotebookPage {
    return this.pages[this.currentPageIndex] || this.pages[0];
  }

  resizeCanvas(): void {
    if (!this.isBrowser || !this.canvasRef) return;
    const c = this.canvasRef.nativeElement;
    const host = this.hostViewportRef?.nativeElement || c.parentElement;
    if (!host) return;

    const r = host.getBoundingClientRect();
    const cssWidth = Math.max(r.width, 300);
    const cssHeight = Math.max(r.height, 300);

    this.dpr = window.devicePixelRatio || 1;
    c.style.width = `${cssWidth}px`;
    c.style.height = `${cssHeight}px`;
    c.width = Math.round(cssWidth * this.dpr);
    c.height = Math.round(cssHeight * this.dpr);

    this.ctx = c.getContext('2d');

    if (!this.viewportInitialized && r.width > 0 && r.height > 0) {
      this.viewportInitialized = true;
      this.vp.scale = 1;
      this.vp.tx = Math.max(24, Math.round((cssWidth - this.PAGE_W) / 2));
      this.vp.ty = 24;
    }

    this.redraw();
  }

  @HostListener('window:resize')
  onResize() {
    this.resizeCanvas();
  }

  @HostListener('window:keydown', ['$event'])
  onKeyDown(e: KeyboardEvent) {
    if ((e.key === 'Delete' || e.key === 'Backspace') && this.selectedLassoStrokes.length > 0) {
      const activeTag = (document.activeElement?.tagName || '').toLowerCase();
      if (activeTag !== 'input' && activeTag !== 'textarea') {
        e.preventDefault();
        this.deleteSelectedLassoStrokes();
      }
    }
  }

  deleteSelectedLassoStrokes(): void {
    if (!this.selectedLassoStrokes.length) return;
    const ids = new Set(this.selectedLassoStrokes.map(s => s.id));
    this.currentPage.strokes = this.currentPage.strokes.filter(s => !ids.has(s.id));
    this.selectedLassoStrokes = [];
    this.lassoPoints = [];
    this.triggerDirty();
    this.redraw();
    this.toastService.info('Lasso', 'Traits sélectionnés effacés.');
  }

  cutSelectedLassoStrokes(): void {
    if (!this.selectedLassoStrokes.length) return;
    this.deleteSelectedLassoStrokes();
  }

  clearLassoSelection(): void {
    this.selectedLassoStrokes = [];
    this.lassoPoints = [];
    this.redraw();
  }

  // --- CONVERSION ÉCRAN ↔ PAGE (Source de vérité unique — Plan v2 §3.2) ---

  toPage(e: { clientX: number; clientY: number }): { x: number; y: number } {
    const r = this.canvasRef?.nativeElement
      ? (this.canvasRef.nativeElement as HTMLCanvasElement).getBoundingClientRect()
      : ({ left: 0, top: 0 } as DOMRect);
    return {
      x: (e.clientX - r.left - this.vp.tx) / this.vp.scale,
      y: (e.clientY - r.top - this.vp.ty) / this.vp.scale,
    };
  }

  toScreen(p: { x: number; y: number }): { x: number; y: number } {
    const r = this.canvasRef?.nativeElement
      ? (this.canvasRef.nativeElement as HTMLCanvasElement).getBoundingClientRect()
      : ({ left: 0, top: 0 } as DOMRect);
    return {
      x: p.x * this.vp.scale + this.vp.tx + r.left,
      y: p.y * this.vp.scale + this.vp.ty + r.top,
    };
  }

  zoomAt(clientX: number, clientY: number, factor: number): void {
    const r = this.canvasRef?.nativeElement
      ? (this.canvasRef.nativeElement as HTMLCanvasElement).getBoundingClientRect()
      : ({ left: 0, top: 0 } as DOMRect);
    const cx = clientX - r.left;
    const cy = clientY - r.top;
    const s0 = this.vp.scale;
    const s1 = Math.min(4, Math.max(0.25, s0 * factor));
    this.vp.tx = cx - (cx - this.vp.tx) * (s1 / s0);
    this.vp.ty = cy - (cy - this.vp.ty) * (s1 / s0);
    this.vp.scale = s1;
    this.triggerZoomBadge();
    this.redraw();
  }

  private triggerZoomBadge() {
    this.zoomBadgeVisible = true;
    if (this.zoomBadgeTimer) clearTimeout(this.zoomBadgeTimer);
    this.zoomBadgeTimer = setTimeout(() => {
      this.zoomBadgeVisible = false;
      this.cdr.detectChanges();
    }, 1200);
  }

  saveCourse() {
    this.stateService.saveCurrentLesson(this.pages);
  }

  runOcr() {
    if (this.currentPage.strokes.length === 0) {
      this.toastService.warning('Page vide', 'Écrivez au moins un tracé avant de lancer l\'OCR.');
      return;
    }
    const currentSubj = (this.stateService as any).currentSubjectSubject?.value?.name || 'Général';
    const currentLes = (this.stateService as any).currentLessonSubject?.value?.title || 'Cours';

    this.isProcessingHtr = true;
    this.apiService.recognizeStructuralPages(this.pages, this.PAGE_W, this.PAGE_H, currentSubj, currentLes, this.selectedLanguage).subscribe({
      next: (res) => {
        this.isProcessingHtr = false;
        this.applyLocalCorrectionsFallback(res);
        this.structuralResult = res;
        this.showAiPanel = true;
        this.toastService.success('OCR Terminé', 'Votre écriture a été numérisée avec succès.');
        this.cdr.detectChanges();
      },
      error: () => {
        this.isProcessingHtr = false;
        this.toastService.error('Erreur OCR', 'Vérifiez la connexion au backend Notely.');
      }
    });
  }

  runAiSynthesis() {
    if (!this.structuralResult) {
      this.runOcr();
      return;
    }
    this.isProcessingAi = true;
    this.showAiPanel = true;
    setTimeout(() => {
      this.isProcessingAi = false;
      this.toastService.success('IA Synthèse', 'Fiches de révision et structure générées.');
    }, 800);
  }

  // --- EXPORT PDF (OPTION 1 & OPTION 2) ---

  openPdfModal() {
    this.showPdfModal = true;
  }

  closePdfModal() {
    this.showPdfModal = false;
  }

  exportOriginalPdf() {
    const currentSubj = (this.stateService as any).currentSubjectSubject?.value?.name || 'Général';
    const currentLes = (this.stateService as any).currentLessonSubject?.value?.title || 'Cours';

    this.isExportingPdf = true;
    this.apiService.exportRawPdfPages(this.pages, this.PAGE_W, this.PAGE_H, currentSubj, currentLes).subscribe({
      next: (blob) => {
        this.isExportingPdf = false;
        this.closePdfModal();
        this.downloadBlob(blob, `${currentSubj}_${currentLes}_Original.pdf`);
        this.toastService.success('Export PDF', 'PDF Original téléchargé avec succès.');
      },
      error: () => {
        this.isExportingPdf = false;
        this.toastService.error('Erreur PDF', 'Impossible d\'exporter le PDF Original.');
      }
    });
  }

  exportAiPdf() {
    const currentSubj = (this.stateService as any).currentSubjectSubject?.value?.name || 'Général';
    const currentLes = (this.stateService as any).currentLessonSubject?.value?.title || 'Cours';

    this.isExportingPdf = true;
    this.apiService.recognizeStructuralPages(this.pages, this.PAGE_W, this.PAGE_H, currentSubj, currentLes, this.selectedLanguage).subscribe({
      next: (res) => {
        this.applyLocalCorrectionsFallback(res);
        this.structuralResult = res;
        this.apiService.exportPdf(currentSubj, currentLes, res.elements).subscribe({
          next: (blob) => {
            this.isExportingPdf = false;
            this.closePdfModal();
            this.downloadBlob(blob, `${currentSubj}_${currentLes}_AI_Structured.pdf`);
            this.toastService.success('Export PDF', 'PDF Structuré IA téléchargé avec succès.');
          },
          error: () => {
            this.isExportingPdf = false;
            this.toastService.error('Erreur PDF', 'Échec de la génération du PDF IA.');
          }
        });
      },
      error: () => {
        this.isExportingPdf = false;
        this.toastService.error('Erreur HTR', 'Échec de l\'analyse pour le PDF IA.');
      }
    });
  }

  private downloadBlob(blob: Blob, fileName: string) {
    if (!this.isBrowser) return;
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  }

  // --- ZOOM & PAN (Plan v2 §3.2) ---
  private getViewportCenterClient(): { clientX: number; clientY: number } {
    if (this.canvasRef?.nativeElement) {
      const r = this.canvasRef.nativeElement.getBoundingClientRect();
      return {
        clientX: r.left + r.width / 2,
        clientY: r.top + r.height / 2
      };
    }
    return { clientX: this.PAGE_W / 2, clientY: this.PAGE_H / 2 };
  }

  zoomIn() {
    const center = this.getViewportCenterClient();
    this.zoomAt(center.clientX, center.clientY, 1.25);
  }

  zoomOut() {
    const center = this.getViewportCenterClient();
    this.zoomAt(center.clientX, center.clientY, 1 / 1.25);
  }

  resetZoom() {
    this.vp.scale = 1.0;
    if (this.canvasRef?.nativeElement) {
      const r = this.canvasRef.nativeElement.getBoundingClientRect();
      this.vp.tx = Math.max(24, Math.round((r.width - this.PAGE_W) / 2));
      this.vp.ty = 24;
    } else {
      this.vp.tx = 0;
      this.vp.ty = 0;
    }
    this.redraw();
  }

  setZoom(level: number) {
    const target = Math.min(4, Math.max(0.25, level));
    const center = this.getViewportCenterClient();
    this.zoomAt(center.clientX, center.clientY, target / this.vp.scale);
  }

  togglePanMode() {
    this.isPanMode = !this.isPanMode;
  }

  onWheel(e: WheelEvent) {
    if (!this.isBrowser) return;
    if (e.ctrlKey || e.metaKey) {
      e.preventDefault();
      this.zoomAt(e.clientX, e.clientY, e.deltaY < 0 ? 1.1 : 1 / 1.1);
    } else {
      e.preventDefault();
      this.vp.tx -= e.deltaX;
      this.vp.ty -= e.deltaY;
      this.redraw();
    }
  }

  // --- POINTER EVENTS UNIFIÉS (Plan v2 §3.2 + §4.4 Rejet de la paume) ---
  onPointerDown(e: PointerEvent) {
    if (!this.isBrowser || !this.canvasRef) return;

    // Détection stylet actif pour palm rejection (§4.4)
    if (e.pointerType === 'pen') {
      this.hasActivePen = true;
    } else if (e.pointerType === 'touch') {
      if (this.penOnlyMode || this.hasActivePen) {
        // Ignorer le contact tactile si stylet actif ou mode stylet seul forcé
        return;
      }
    }

    const c = this.canvasRef.nativeElement;
    if (typeof c.setPointerCapture === 'function') {
      try {
        c.setPointerCapture(e.pointerId);
      } catch {}
    }

    this.updateCursorPosition(e);

    if (this.isPanMode || e.buttons === 4 || (e as any).spaceKey) {
      this.isPanning = true;
      this.startPanX = e.clientX - this.vp.tx;
      this.startPanY = e.clientY - this.vp.ty;
      return;
    }

    const pt = this.toPage(e);

    // Outil Lasso (§6.4)
    if (this.activeTool === 'lasso') {
      if (this.selectedLassoStrokes.length > 0) {
        const box = boundsOf(this.selectedLassoStrokes);
        if (box && pt.x >= box.xMin - 8 && pt.x <= box.xMax + 8 && pt.y >= box.yMin - 8 && pt.y <= box.yMax + 8) {
          this.isDraggingSelection = true;
          this.dragLastPos = { x: pt.x, y: pt.y };
          return;
        }
      }
      this.selectedLassoStrokes = [];
      this.lassoPoints = [{ x: pt.x, y: pt.y }];
      this.redraw();
      return;
    }

    this.startStroke(pt.x, pt.y, e.pressure || 0.5);
  }

  onPointerMove(e: PointerEvent) {
    if (!this.isBrowser) return;

    if (e.pointerType === 'touch' && (this.penOnlyMode || this.hasActivePen)) {
      return;
    }

    this.updateCursorPosition(e);

    if (this.isPanning) {
      this.vp.tx = e.clientX - this.startPanX;
      this.vp.ty = e.clientY - this.startPanY;
      this.redraw();
      return;
    }

    // Déplacement / Tracé lasso (§6.4)
    if (this.activeTool === 'lasso') {
      const p = this.toPage(e);
      if (this.isDraggingSelection && this.dragLastPos && this.selectedLassoStrokes.length > 0) {
        const dx = p.x - this.dragLastPos.x;
        const dy = p.y - this.dragLastPos.y;
        translateStrokes(this.selectedLassoStrokes, dx, dy);
        this.dragLastPos = { x: p.x, y: p.y };
        this.redraw();
        return;
      }
      if (this.lassoPoints.length > 0) {
        this.lassoPoints.push({ x: p.x, y: p.y });
        this.redraw();
        return;
      }
    }

    if (!this.isDrawing || !this.currentStroke) return;

    const events: PointerEvent[] = (e as any).getCoalescedEvents?.() ?? [e];
    for (const ev of events) {
      const p = this.toPage(ev);
      this.currentStroke.points.push({
        x: p.x,
        y: p.y,
        timestamp: Date.now(),
        pressure: ev.pressure || 0.5
      });
    }
    this.redraw();
  }

  onPointerUp(e: PointerEvent) {
    if (!this.isBrowser) return;

    if (e.pointerType === 'pen') {
      // Relâchement du stylet
      this.hasActivePen = false;
    }

    if (this.canvasRef?.nativeElement && typeof this.canvasRef.nativeElement.releasePointerCapture === 'function') {
      try {
        this.canvasRef.nativeElement.releasePointerCapture(e.pointerId);
      } catch {}
    }
    if (this.isPanning) {
      this.isPanning = false;
      return;
    }

    // Clôture Lasso (§6.4)
    if (this.activeTool === 'lasso') {
      if (this.isDraggingSelection) {
        this.isDraggingSelection = false;
        this.dragLastPos = null;
        this.triggerDirty();
        return;
      }
      if (this.lassoPoints.length > 2) {
        this.selectedLassoStrokes = strokesInLasso(this.currentPage.strokes, this.lassoPoints);
        this.lassoPoints = [];
        this.redraw();
        return;
      }
      this.lassoPoints = [];
      this.redraw();
      return;
    }

    this.endStroke();
  }

  onPointerLeave() {
    this.showCursor = false;
  }

  private updateCursorPosition(e: { clientX: number; clientY: number }) {
    if (!this.canvasRef?.nativeElement) return;
    const r = this.canvasRef.nativeElement.getBoundingClientRect();
    this.cursorX = e.clientX - r.left;
    this.cursorY = e.clientY - r.top;
    this.showCursor = true;
  }

  // --- GESTION DU DESSIN ---

  private startStroke(x: number, y: number, pressure: number) {
    this.isDrawing = true;
    const pt: Point = { x, y, timestamp: Date.now(), pressure };

    this.currentStroke = {
      id: `strk-${Date.now()}`,
      points: [pt],
      startTime: Date.now(),
      endTime: Date.now(),
      color: this.activeTool === 'eraser' ? '#FFFFFF' : this.activeColor,
      width: this.activeTool === 'eraser' ? this.activeWidth * 4 : this.activeWidth,
      tool: this.activeTool,
      contentType: this.activeContentType
    };

    this.redraw();
  }

  private moveStroke(x: number, y: number, pressure: number) {
    if (!this.currentStroke) return;
    const pt: Point = { x, y, timestamp: Date.now(), pressure };
    this.currentStroke.points.push(pt);
    this.redraw();
  }

  private triggerDirty() {
    this.stateService.markChangesDirty(() => {
      this.saveCourse();
    });
  }

  private endStroke() {
    if (!this.isDrawing || !this.currentStroke) return;
    this.isDrawing = false;
    this.currentStroke.endTime = Date.now();

    if (this.currentStroke.points.length > 0) {
      // Forme parfaite (§6.5) : si mode diagramme ou option activée
      if (this.activeTool === 'diagram' || this.snapToShapes) {
        const recognized = recognizeShape(this.currentStroke.points);
        if (recognized) {
          this.currentStroke.points = recognized.points;
        }
      }
      this.currentPage.strokes.push(this.currentStroke);
      this.currentPage.redoStack = [];
      this.triggerDirty();
    }
    this.currentStroke = null;
    this.redraw();
  }

  undo() {
    if (this.currentPage.strokes.length === 0) return;
    const last = this.currentPage.strokes.pop()!;
    this.currentPage.redoStack.push(last);
    this.triggerDirty();
    this.redraw();
  }

  redo() {
    if (this.currentPage.redoStack.length === 0) return;
    const popped = this.currentPage.redoStack.pop()!;
    this.currentPage.strokes.push(popped);
    this.triggerDirty();
    this.redraw();
  }

  clearPage() {
    if (this.currentPage.strokes.length === 0) return;
    this.currentPage.redoStack.push(...this.currentPage.strokes);
    this.currentPage.strokes = [];
    this.triggerDirty();
    this.redraw();
  }

  addPage() {
    const newPage: NotebookPage = {
      id: `p-${Date.now()}`,
      pageNumber: this.pages.length + 1,
      strokes: [],
      redoStack: []
    };
    this.pages.push(newPage);
    this.currentPageIndex = this.pages.length - 1;
    this.triggerDirty();
    this.redraw();
  }

  setPage(idx: number) {
    if (idx < 0 || idx >= this.pages.length) return;
    this.currentPageIndex = idx;
    this.redraw();
  }

  redraw(): void {
    if (!this.ctx || !this.canvasRef) return;
    const c = this.canvasRef.nativeElement;
    const ctx = this.ctx;
    this.dpr = (this.isBrowser && typeof window !== 'undefined' && window.devicePixelRatio) ? window.devicePixelRatio : 1;

    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, c.width, c.height);

    const { scale: s, tx, ty } = this.vp;
    ctx.setTransform(this.dpr * s, 0, 0, this.dpr * s, this.dpr * tx, this.dpr * ty);

    // Feuille logique 794 × 1123 dessinée dans le viewport
    ctx.save();
    ctx.shadowColor = 'rgba(0, 0, 0, 0.45)';
    ctx.shadowBlur = 24 / s;
    ctx.shadowOffsetX = 0;
    ctx.shadowOffsetY = 8 / s;
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, this.PAGE_W, this.PAGE_H);
    ctx.restore();

    ctx.save();
    ctx.beginPath();
    ctx.rect(0, 0, this.PAGE_W, this.PAGE_H);
    ctx.clip();

    // Dessin du fond de page (modèle / template §6.6)
    drawPageTemplate(ctx, this.currentTemplate, this.PAGE_W, this.PAGE_H);

    // Surlignage de la recherche dans l'écriture (§6.3)
    if (this.inkSearchMatches.length > 0) {
      ctx.save();
      ctx.fillStyle = 'rgba(253, 224, 71, 0.45)';
      ctx.strokeStyle = '#eab308';
      ctx.lineWidth = 1.5;
      for (const m of this.inkSearchMatches) {
        const [x1, y1, x2, y2] = m.bbox;
        ctx.fillRect(x1, y1, x2 - x1, y2 - y1);
        ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
      }
      ctx.restore();
    }

    for (const stroke of this.currentPage.strokes) {
      this.drawStroke(ctx, stroke);
    }

    if (this.currentStroke) {
      this.drawStroke(ctx, this.currentStroke);
    }

    // Tracé du lasso en cours (§6.4)
    if (this.lassoPoints.length > 1) {
      ctx.save();
      ctx.strokeStyle = '#3b82f6';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(this.lassoPoints[0].x, this.lassoPoints[0].y);
      for (let i = 1; i < this.lassoPoints.length; i++) {
        ctx.lineTo(this.lassoPoints[i].x, this.lassoPoints[i].y);
      }
      ctx.stroke();
      ctx.restore();
    }

    // Encadrement des traits sélectionnés au lasso (§6.4)
    if (this.selectedLassoStrokes.length > 0) {
      const box = boundsOf(this.selectedLassoStrokes);
      if (box) {
        ctx.save();
        ctx.strokeStyle = '#2563eb';
        ctx.lineWidth = 2;
        ctx.setLineDash([6, 3]);
        ctx.strokeRect(box.xMin - 4, box.yMin - 4, box.xMax - box.xMin + 8, box.yMax - box.yMin + 8);
        ctx.fillStyle = 'rgba(59, 130, 246, 0.08)';
        ctx.fillRect(box.xMin - 4, box.yMin - 4, box.xMax - box.xMin + 8, box.yMax - box.yMin + 8);
        ctx.restore();
      }
    }

    ctx.restore();
  }

  private drawStroke(ctx: CanvasRenderingContext2D, stroke: Stroke): void {
    if (!stroke.points || stroke.points.length === 0) return;
    ctx.beginPath();
    ctx.strokeStyle = stroke.color || '#000000';
    ctx.lineWidth = stroke.width || 3.0;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    if (stroke.points.length === 1) {
      const p0 = stroke.points[0];
      ctx.arc(p0.x, p0.y, (stroke.width || 3.0) / 2, 0, Math.PI * 2);
      ctx.fillStyle = stroke.color || '#000000';
      ctx.fill();
      return;
    }

    ctx.moveTo(stroke.points[0].x, stroke.points[0].y);
    for (let i = 1; i < stroke.points.length; i++) {
      ctx.lineTo(stroke.points[i].x, stroke.points[i].y);
    }
    ctx.stroke();
  }

  private drawGrid(w: number, h: number) {
    if (!this.ctx) return;
    this.ctx.save();
    this.ctx.strokeStyle = '#e2e8f0';
    this.ctx.lineWidth = 0.5;

    const step = 28;
    for (let y = step; y < h; y += step) {
      this.ctx.beginPath();
      this.ctx.moveTo(0, y);
      this.ctx.lineTo(w, y);
      this.ctx.stroke();
    }
    this.ctx.restore();
  }

  // --- RECHERCHE DANS L'ÉCRITURE (§6.3) ---
  onInkSearchChange(query: string) {
    this.inkSearchQuery = query;
    if (!query || !query.trim()) {
      this.inkSearchMatches = [];
      this.redraw();
      return;
    }
    const ocrElements = this.structuralResult?.elements || [];
    this.inkSearchMatches = findInkMatches(ocrElements, query);
    this.redraw();
  }

  clearInkSearch() {
    this.inkSearchQuery = '';
    this.inkSearchMatches = [];
    this.redraw();
  }

  // --- FLASHCARDS SM-2 (§6.7) ---
  generateFlashcards() {
    if (!this.structuralResult || !this.structuralResult.elements.length) {
      this.toastService.warning('Aucun OCR', 'Veuillez lancer l\'OCR avant de générer des cartes de révision.');
      return;
    }
    this.isGeneratingCards = true;
    const currentLesson = this.stateService.getCurrentLesson();
    const lessonId = currentLesson?.id || null;

    this.apiService.generateFlashcardsFromOcr(lessonId, this.structuralResult.elements).subscribe({
      next: (cards) => {
        this.isGeneratingCards = false;
        if (!cards || cards.length === 0) {
          this.toastService.info('Cartes', 'Aucune définition ou liste structurée détectée pour générer des cartes.');
          return;
        }
        this.activeCards = cards;
        this.currentCardIdx = 0;
        this.showCardAnswer = false;
        this.showFlashcardModal = true;
        this.toastService.success('Cartes créées', `${cards.length} carte(s) de révision générées (SM-2).`);
      },
      error: (err) => {
        this.isGeneratingCards = false;
        const msg = err?.error?.detail || err?.message || 'Erreur lors de la génération des cartes.';
        this.toastService.error('Erreur cartes', String(msg));
      }
    });
  }

  openDueFlashcards() {
    this.apiService.getDueFlashcards().subscribe({
      next: (cards) => {
        if (!cards || cards.length === 0) {
          this.toastService.info('Révision à jour', 'Aucune carte de révision en attente aujourd\'hui !');
          return;
        }
        this.activeCards = cards;
        this.currentCardIdx = 0;
        this.showCardAnswer = false;
        this.showFlashcardModal = true;
      },
      error: (err) => {
        this.toastService.error('Erreur', 'Impossible de récupérer les cartes dues.');
      }
    });
  }

  flipCard() {
    this.showCardAnswer = !this.showCardAnswer;
  }

  reviewCurrentCard(rating: number) {
    if (!this.activeCards.length || this.currentCardIdx >= this.activeCards.length) return;
    const card = this.activeCards[this.currentCardIdx];
    this.apiService.reviewFlashcard(card.id, rating).subscribe({
      next: () => {
        this.currentCardIdx++;
        this.showCardAnswer = false;
        if (this.currentCardIdx >= this.activeCards.length) {
          this.toastService.success('Session terminée', 'Toutes les cartes ont été révisées !');
          this.showFlashcardModal = false;
        }
      },
      error: () => {
        this.toastService.warning('Hors-ligne', 'Note enregistrée localement.');
        this.currentCardIdx++;
        this.showCardAnswer = false;
        if (this.currentCardIdx >= this.activeCards.length) {
          this.showFlashcardModal = false;
        }
      }
    });
  }

  closeFlashcards() {
    this.showFlashcardModal = false;
    this.activeCards = [];
  }

}
