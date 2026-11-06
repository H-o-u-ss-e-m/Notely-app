class NotelyTranslations {
  final String save;
  final String saveTooltip;
  final String recognize;
  final String recognizeTooltip;
  final String exportPdf;
  final String exportPdfTooltip;
  final String aiSummary;
  final String aiSummaryTooltip;
  final String pen;
  final String diagram;
  final String eraser;
  final String palmRejection;
  final String undo;
  final String redo;
  final String clearPage;
  final String addPage;
  final String deletePage;

  const NotelyTranslations({
    required this.save,
    required this.saveTooltip,
    required this.recognize,
    required this.recognizeTooltip,
    required this.exportPdf,
    required this.exportPdfTooltip,
    required this.aiSummary,
    required this.aiSummaryTooltip,
    required this.pen,
    required this.diagram,
    required this.eraser,
    required this.palmRejection,
    required this.undo,
    required this.redo,
    required this.clearPage,
    required this.addPage,
    required this.deletePage,
  });

  static const NotelyTranslations fr = NotelyTranslations(
    save: 'Enregistrer',
    saveTooltip: 'Enregistrer les modifications sur le serveur (Ctrl+S)',
    recognize: 'Reconnaître le texte',
    recognizeTooltip: 'Lancer la reconnaissance HTR sur les tracés manuscrits',
    exportPdf: 'Exporter PDF',
    exportPdfTooltip: 'Exporter le cours actuel au format PDF (original ou structuré)',
    aiSummary: 'Synthèse & Fiches IA',
    aiSummaryTooltip: 'Structurer le cours et créer des cartes de révision',
    pen: 'Stylet',
    diagram: 'Schéma',
    eraser: 'Gomme',
    palmRejection: 'Rejet paume',
    undo: 'Annuler (Ctrl+Z)',
    redo: 'Rétablir (Ctrl+Y)',
    clearPage: 'Effacer la page',
    addPage: '+Page',
    deletePage: 'Supprimer cette page',
  );

  static const NotelyTranslations en = NotelyTranslations(
    save: 'Save',
    saveTooltip: 'Save changes to the server (Ctrl+S)',
    recognize: 'Recognize text',
    recognizeTooltip: 'Run HTR handwriting recognition on strokes',
    exportPdf: 'Export PDF',
    exportPdfTooltip: 'Export lesson to PDF format (original or structured)',
    aiSummary: 'AI Summary & Cards',
    aiSummaryTooltip: 'Structure notes and generate flashcards',
    pen: 'Pen',
    diagram: 'Diagram',
    eraser: 'Eraser',
    palmRejection: 'Palm rejection',
    undo: 'Undo (Ctrl+Z)',
    redo: 'Redo (Ctrl+Y)',
    clearPage: 'Clear page',
    addPage: '+Page',
    deletePage: 'Delete page',
  );

  static const NotelyTranslations ar = NotelyTranslations(
    save: 'حفظ',
    saveTooltip: 'حفظ التعديلات على الخادم (Ctrl+S)',
    recognize: 'التعرف على النص',
    recognizeTooltip: 'تشغيل التعرف على الكتابة اليدوية',
    exportPdf: 'تصدير PDF',
    exportPdfTooltip: 'تصدير الدرس بتنسيق PDF',
    aiSummary: 'ملخص وبطاقات الذكاء الاصطناعي',
    aiSummaryTooltip: 'تنظيم الملاحظات وتوليد بطاقات المراجعة',
    pen: 'قلم',
    diagram: 'مخطط',
    eraser: 'ممحاة',
    palmRejection: 'رفض راحة اليد',
    undo: 'تراجع (Ctrl+Z)',
    redo: 'إعادة (Ctrl+Y)',
    clearPage: 'مسح الصفحة',
    addPage: '+صفحة',
    deletePage: 'حذف الصفحة',
  );

  static NotelyTranslations of(String lang) {
    switch (lang.toLowerCase()) {
      case 'ar':
        return ar;
      case 'en':
        return en;
      case 'fr':
      default:
        return fr;
    }
  }
}
