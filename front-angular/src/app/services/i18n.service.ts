import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

export type SupportedLocale = 'fr' | 'en' | 'ar';

export interface Translations {
  actions: {
    back: string;
    save: string;
    saveTooltip: string;
    exportPdf: string;
    exportPdfTooltip: string;
    runOcr: string;
    runOcrRunning: string;
    runOcrTooltip: string;
    aiAssist: string;
    aiAssistRunning: string;
    aiAssistTooltip: string;
    undo: string;
    redo: string;
    clear: string;
    newPage: string;
    deletePage: string;
  };
  tools: {
    pen: string;
    penTooltip: string;
    diagram: string;
    diagramTooltip: string;
    eraser: string;
    eraserTooltip: string;
    pan: string;
    panTooltip: string;
  };
  saveStatus: {
    saved: string;
    saving: string;
    dirty: string;
    error: string;
  };
  zoom: {
    zoomIn: string;
    zoomOut: string;
    reset: string;
    fitPage: string;
  };
}

const FR_TRANSLATIONS: Translations = {
  actions: {
    back: 'Retour',
    save: 'Enregistrer',
    saveTooltip: 'Sauvegarder immédiatement les modifications sur le serveur (Ctrl+S)',
    exportPdf: 'Exporter PDF',
    exportPdfTooltip: 'Exporter le cours actuel au format PDF (original ou structuré)',
    runOcr: 'Reconnaître le texte',
    runOcrRunning: 'Reconnaissance en cours…',
    runOcrTooltip: 'Convertir les tracés manuscrits en texte éditable et vérifiable',
    aiAssist: 'Synthèse & Fiches IA',
    aiAssistRunning: 'Génération IA en cours…',
    aiAssistTooltip: 'Structurer le cours, extraire les points clés et créer des cartes de révision',
    undo: 'Annuler (Ctrl+Z)',
    redo: 'Rétablir (Ctrl+Y)',
    clear: 'Effacer la page',
    newPage: '+ Page',
    deletePage: 'Supprimer la page'
  },
  tools: {
    pen: 'Stylet',
    penTooltip: 'Écriture manuscrite au stylet ou au doigt',
    diagram: 'Schémas',
    diagramTooltip: 'Dessiner des graphiques et schémas vectoriels',
    eraser: 'Gomme',
    eraserTooltip: 'Effacer les tracés touchés',
    pan: 'Déplacement',
    panTooltip: 'Naviguer sur la feuille sans dessiner (Pan)'
  },
  saveStatus: {
    saved: 'Enregistré',
    saving: 'Enregistrement…',
    dirty: 'Modifications non enregistrées',
    error: 'Échec de l\'enregistrement'
  },
  zoom: {
    zoomIn: 'Zoom avant (+)',
    zoomOut: 'Zoom arrière (-)',
    reset: 'Réinitialiser zoom (100%)',
    fitPage: 'Ajuster à la page'
  }
};

const EN_TRANSLATIONS: Translations = {
  actions: {
    back: 'Back',
    save: 'Save',
    saveTooltip: 'Save changes immediately to the server (Ctrl+S)',
    exportPdf: 'Export PDF',
    exportPdfTooltip: 'Export current lesson to PDF format (original or structured)',
    runOcr: 'Recognize text',
    runOcrRunning: 'Recognizing text…',
    runOcrTooltip: 'Convert handwritten strokes into editable and verifiable text',
    aiAssist: 'AI Summary & Cards',
    aiAssistRunning: 'AI generation in progress…',
    aiAssistTooltip: 'Structure notes, extract key points, and create flashcards',
    undo: 'Undo (Ctrl+Z)',
    redo: 'Redo (Ctrl+Y)',
    clear: 'Clear page',
    newPage: '+ Page',
    deletePage: 'Delete page'
  },
  tools: {
    pen: 'Pen',
    penTooltip: 'Handwriting with stylus or touch',
    diagram: 'Diagrams',
    diagramTooltip: 'Draw shapes and vector diagrams',
    eraser: 'Eraser',
    eraserTooltip: 'Erase touched strokes',
    pan: 'Pan',
    panTooltip: 'Move across the canvas without drawing'
  },
  saveStatus: {
    saved: 'Saved',
    saving: 'Saving…',
    dirty: 'Unsaved changes',
    error: 'Failed to save'
  },
  zoom: {
    zoomIn: 'Zoom in (+)',
    zoomOut: 'Zoom out (-)',
    reset: 'Reset zoom (100%)',
    fitPage: 'Fit to page'
  }
};

const AR_TRANSLATIONS: Translations = {
  actions: {
    back: 'رجوع',
    save: 'حفظ',
    saveTooltip: 'حفظ التعديلات فوراً على الخادم (Ctrl+S)',
    exportPdf: 'تصدير PDF',
    exportPdfTooltip: 'تصدير الدرس بتنسيق PDF (أصلي أو منسق)',
    runOcr: 'التعرف على النص',
    runOcrRunning: 'جاري التعرف على الكتابة…',
    runOcrTooltip: 'تحويل الخط اليدوي إلى نص قابل للتعديل والتحقق',
    aiAssist: 'ملخص وبطاقات الذكاء الاصطناعي',
    aiAssistRunning: 'جاري المعالجة بالذكاء الاصطناعي…',
    aiAssistTooltip: 'تنظيم الملاحظات وتلخيصها وإنشاء بطاقات المراجعة',
    undo: 'تراجع (Ctrl+Z)',
    redo: 'إعادة (Ctrl+Y)',
    clear: 'مسح الصفحة',
    newPage: '+ صفحة',
    deletePage: 'حذف الصفحة'
  },
  tools: {
    pen: 'قلم',
    penTooltip: 'الكتابة اليدوية بالقلم أو اللمس',
    diagram: 'مخططات',
    diagramTooltip: 'رسم الأشكال والمخططات المتجهية',
    eraser: 'ممحاة',
    eraserTooltip: 'مسح الخطوط المحددة',
    pan: 'تحريك',
    panTooltip: 'التنقل في الصفحة بدون رسم'
  },
  saveStatus: {
    saved: 'تم الحفظ',
    saving: 'جاري الحفظ…',
    dirty: 'تعديلات غير محفوظة',
    error: 'فشل الحفظ'
  },
  zoom: {
    zoomIn: 'تكبير (+)',
    zoomOut: 'تصغير (-)',
    reset: 'إعادة ضبط التكبير (100%)',
    fitPage: 'ملاءمة الصفحة'
  }
};

@Injectable({
  providedIn: 'root'
})
export class I18nService {
  private currentLocaleSubject = new BehaviorSubject<SupportedLocale>('fr');
  currentLocale$ = this.currentLocaleSubject.asObservable();

  private translations: Record<SupportedLocale, Translations> = {
    fr: FR_TRANSLATIONS,
    en: EN_TRANSLATIONS,
    ar: AR_TRANSLATIONS
  };

  constructor() {
    if (typeof window !== 'undefined' && window.localStorage) {
      const saved = localStorage.getItem('notely_locale') as SupportedLocale;
      if (saved && (saved === 'fr' || saved === 'en' || saved === 'ar')) {
        this.currentLocaleSubject.next(saved);
      }
    }
  }

  get currentLocale(): SupportedLocale {
    return this.currentLocaleSubject.value;
  }

  setLocale(locale: SupportedLocale) {
    this.currentLocaleSubject.next(locale);
    if (typeof window !== 'undefined' && window.localStorage) {
      localStorage.setItem('notely_locale', locale);
    }
  }

  t(): Translations {
    return this.translations[this.currentLocaleSubject.value] || FR_TRANSLATIONS;
  }
}
