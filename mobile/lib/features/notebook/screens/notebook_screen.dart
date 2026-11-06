import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math';
import 'dart:ui';
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';
import '../../../models/stroke_model.dart';
import '../../../models/structural_model.dart';
import '../../../models/recognition_model.dart';
import '../../../models/course_model.dart';
import '../../../core/network/api_client.dart';
import '../../../core/config/env_config.dart';
import '../widgets/notebook_painter.dart';
import '../widgets/course_drawer.dart';
import '../../dashboard/dashboard_screen.dart';

// ════════════════════════════════════════════════════════════════════════════
//  DIMENSIONS LOGIQUES DE LA FEUILLE (référentiel stable, indépendant écran)
//
//  794 × 1123 px ≈ A4 à 96 dpi.
//  TOUS les points tracés sont en coordonnées de ce référentiel.
//  Le zoom / déplacement sont des transformations d'affichage UNIQUEMENT.
//  PostgreSQL stocke TOUJOURS les coordonnées logiques de la feuille.
// ════════════════════════════════════════════════════════════════════════════
const double kPageWidth  = 794.0;
const double kPageHeight = 1123.0;

class NotebookScreen extends StatefulWidget {
  final SubjectModel? initialSubject;
  final LessonModel? initialLesson;

  const NotebookScreen({
    super.key,
    this.initialSubject,
    this.initialLesson,
  });

  @override
  State<NotebookScreen> createState() => _NotebookScreenState();
}

class _NotebookScreenState extends State<NotebookScreen> {
  // ── Pages ─────────────────────────────────────────────────────────────────
  final List<NotebookPageModel> _pages = [
    NotebookPageModel(id: 'page-1', pageNumber: 1, strokes: [], redoStack: []),
  ];
  int _currentPageIndex = 0;

  StrokeModel?               _currentStroke;
  StructuralHTRResponseModel? _structuralResult;
  bool _isLoading = false;
  bool _showGrid  = true;
  // Langue sélectionnée pour la reconnaissance (P2 UX Critique)
  String _selectedLanguage = 'fr';

  // ── Auto-Save ─────────────────────────────────────────────────────────────
  Timer?  _autoSaveTimer;
  String  _lastSavedTime      = '';
  bool    _hasUnsavedChanges  = false;

  // ── Outils ────────────────────────────────────────────────────────────────
  String _activeTool        = 'pen';
  final String _activeContentType = 'normal';
  String _activeColor       = '#000000';
  double _activeWidth       = 3.0;

  List<SubjectModel> _subjects        = [];
  SubjectModel?      _currentSubject;
  LessonModel?       _currentLesson;

  final List<Map<String, dynamic>> _palette = [
    {'color': '#000000', 'name': 'Noir',   'value': const Color(0xFF000000)},
    {'color': '#1E40AF', 'name': 'Bleu',   'value': const Color(0xFF1E40AF)},
    {'color': '#DC2626', 'name': 'Rouge',  'value': const Color(0xFFDC2626)},
    {'color': '#15803D', 'name': 'Vert',   'value': const Color(0xFF15803D)},
    {'color': '#7C3AED', 'name': 'Violet', 'value': const Color(0xFF7C3AED)},
  ];
  final List<double> _widths = [1.5, 3.0, 5.0];

  // ── Zoom & Pan ────────────────────────────────────────────────────────────
  //
  //  ARCHITECTURE :
  //  ┌─ InteractiveViewer(constrained: false)
  //  │    └─ Listener  ← event.localPosition = coordonnées LOGIQUES de la feuille
  //  │         └─ Container(shadow)
  //  │              └─ ClipRect
  //  │                   └─ CustomPaint(size: kPageWidth × kPageHeight)
  //  │
  //  • InteractiveViewer applique la matrice [scale, tx, ty] à la feuille.
  //  • Flutter inverse cette matrice pour transformer les touches en
  //    coordonnées locales du Listener → elles sont DIRECTEMENT en
  //    coordonnées logiques de la feuille.
  //  • Aucune conversion manuelle n'est nécessaire lors du dessin.
  //  • Les coordonnées persistées dans PostgreSQL sont toujours logiques.
  //
  final TransformationController _transformationController =
      TransformationController();

  double  _zoomLevel           = 1.0;
  bool    _isPanMode           = false;
  int     _activePointers      = 0;
  Size    _canvasSize          = Size.zero;
  bool    _transformInitialized = false;

  static const double _minZoom = 0.25;
  static const double _maxZoom = 4.0;

  // ── Raccourcis ────────────────────────────────────────────────────────────
  NotebookPageModel get _currentPage => _pages[_currentPageIndex];
  List<StrokeModel>  get _strokes    => _currentPage.strokes;
  List<StrokeModel>  get _redoStack  => _currentPage.redoStack;
  int get _totalStrokesInDoc =>
      _pages.fold(0, (sum, p) => sum + p.strokes.length);

  // ═══════════════════════════════════════════════════════════════════════════
  //  Cycle de vie
  // ═══════════════════════════════════════════════════════════════════════════

  @override
  void initState() {
    super.initState();
    _loadSubjectsAndLesson();
    _autoSaveTimer =
        Timer.periodic(const Duration(minutes: 5), (_) => _autoSaveCourse());
  }

  @override
  void dispose() {
    _autoSaveTimer?.cancel();
    _transformationController.dispose();
    super.dispose();
  }

  // ═══════════════════════════════════════════════════════════════════════════
  //  Navigation — Retour au Dashboard
  // ═══════════════════════════════════════════════════════════════════════════

  Future<void> _navigateToDashboard() async {
    if (_hasUnsavedChanges) {
      final result = await showDialog<String>(
        context: context,
        barrierDismissible: false,
        builder: (ctx) => AlertDialog(
          backgroundColor: const Color(0xFF1E293B),
          title: const Text('Modifications non sauvegardées',
              style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
          content: const Text(
            'Vous avez des changements non enregistrés.\nQue souhaitez-vous faire ?',
            style: TextStyle(color: Color(0xFF94A3B8)),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx, 'cancel'),
              child: const Text('Annuler',
                  style: TextStyle(color: Color(0xFF64748B))),
            ),
            TextButton(
              onPressed: () => Navigator.pop(ctx, 'discard'),
              child: const Text('Quitter sans sauvegarder',
                  style: TextStyle(color: Color(0xFFEF4444))),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF4F46E5),
                  foregroundColor: Colors.white),
              onPressed: () => Navigator.pop(ctx, 'save'),
              child: const Text('Sauvegarder et quitter'),
            ),
          ],
        ),
      );
      if (result == null || result == 'cancel') return;
      if (result == 'save') await _saveCourseManually();
    }
    if (!mounted) return;
    Navigator.pushAndRemoveUntil(
      context,
      MaterialPageRoute(builder: (_) => const DashboardScreen()),
      (route) => false,
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  //  Zoom — méthodes
  //
  //  La matrice de l'InteractiveViewer est :
  //    screen_pos = scale × page_pos + (tx, ty)
  //  Inverse : page_pos = (screen_pos − (tx, ty)) / scale
  //
  //  _zoomLevel = valeur réelle extraite de la matrice.
  //  Affichage en % = (_zoomLevel × 100).round()
  // ═══════════════════════════════════════════════════════════════════════════

  /// Ajuste la feuille pour qu'elle soit entièrement visible et centrée.
  void _fitPage() {
    if (_canvasSize == Size.zero) return;

    final scaleX = _canvasSize.width  / kPageWidth;
    final scaleY = _canvasSize.height / kPageHeight;
    // 92 % pour laisser une petite marge autour de la feuille
    final fitScale = min(scaleX, scaleY) * 0.92;

    final tx = (_canvasSize.width  - kPageWidth  * fitScale) / 2.0;
    final ty = (_canvasSize.height - kPageHeight * fitScale) / 2.0;

    _transformationController.value = _makeMatrix(fitScale, tx, ty);
    if (mounted) setState(() => _zoomLevel = fitScale);
  }

  /// Zoom avant (×1.2 centré sur le milieu de la vue).
  void _zoomIn()  => _applyZoom(_zoomLevel * 1.2);

  /// Zoom arrière (÷1.2 centré sur le milieu de la vue).
  void _zoomOut() => _applyZoom(_zoomLevel / 1.2);

  /// Applique `targetZoom` en gardant le point de la feuille sous le
  /// centre du viewport à la même position visuelle.
  void _applyZoom(double targetZoom) {
    targetZoom = targetZoom.clamp(_minZoom, _maxZoom);
    if ((targetZoom - _zoomLevel).abs() < 0.001) return;
    if (_canvasSize == Size.zero) return;

    final double cx = _canvasSize.width  / 2.0;
    final double cy = _canvasSize.height / 2.0;

    final Matrix4 m  = _transformationController.value;
    final double   tx = m.entry(0, 3);
    final double   ty = m.entry(1, 3);

    // Point de la feuille actuellement sous le centre du viewport
    final double px = (cx - tx) / _zoomLevel;
    final double py = (cy - ty) / _zoomLevel;

    // Nouvelle translation pour que ce même point reste sous le centre
    final double newTx = cx - px * targetZoom;
    final double newTy = cy - py * targetZoom;

    _transformationController.value = _makeMatrix(targetZoom, newTx, newTy);
    setState(() => _zoomLevel = targetZoom);
  }

  /// Construit une matrice affine 2D : scale + translation.
  Matrix4 _makeMatrix(double scale, double tx, double ty) {
    return Matrix4.identity()
      ..setEntry(0, 0, scale)
      ..setEntry(1, 1, scale)
      ..setEntry(2, 2, 1.0)
      ..setEntry(3, 3, 1.0)
      ..setEntry(0, 3, tx)
      ..setEntry(1, 3, ty);
  }

  /// Bascule mode Dessin ↔ Déplacement.
  void _togglePanMode() {
    setState(() {
      _isPanMode     = !_isPanMode;
      _currentStroke = null; // Annule le tracé en cours
    });
  }

  // ═══════════════════════════════════════════════════════════════════════════
  //  Chargement des données
  // ═══════════════════════════════════════════════════════════════════════════

  Future<void> _loadSubjectsAndLesson() async {
    setState(() => _isLoading = true);
    final subs = await ApiClient.fetchSubjects();
    if (!mounted) return;

    SubjectModel? selSubj;
    LessonModel?  selLes;

    if (widget.initialSubject != null && widget.initialLesson != null) {
      selSubj = widget.initialSubject;
      selLes  = widget.initialLesson;
    } else if (subs.isNotEmpty) {
      selSubj = subs.first;
      if (subs.first.lessons.isNotEmpty) selLes = subs.first.lessons.first;
    }

    setState(() {
      _subjects       = subs;
      _currentSubject = selSubj;
      _currentLesson  = selLes;
    });

    if (selSubj != null && selLes != null) {
      await _fetchLessonFromApi(selSubj.id, selLes.id);
    } else {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _fetchLessonFromApi(String subjectId, String lessonId) async {
    setState(() => _isLoading = true);
    final freshLesson = await ApiClient.getLesson(subjectId, lessonId);
    if (!mounted) return;
    setState(() {
      _isLoading = false;
      if (freshLesson != null) {
        _currentLesson = freshLesson;
        if (freshLesson.pages.isNotEmpty) {
          _pages.clear();
          _pages.addAll(freshLesson.pages);
          _currentPageIndex = 0;
        }
      }
    });
  }

  // ═══════════════════════════════════════════════════════════════════════════
  //  Sauvegarde
  // ═══════════════════════════════════════════════════════════════════════════

  Future<void> _autoSaveCourse() async {
    if (!_hasUnsavedChanges ||
        _currentSubject == null ||
        _currentLesson == null) {
      return;
    }
    final success = await ApiClient.updateLesson(
        _currentSubject!.id, _currentLesson!.id, _currentLesson!.title, _pages);
    if (success && mounted) {
      final now = DateTime.now();
      setState(() {
        _lastSavedTime =
            '${now.hour.toString().padLeft(2, '0')}:${now.minute.toString().padLeft(2, '0')}';
        _hasUnsavedChanges = false;
      });
    }
  }

  Future<void> _saveCourseManually() async {
    final subj = _currentSubject;
    final les  = _currentLesson;
    if (subj == null || les == null) return;

    setState(() => _isLoading = true);
    final now     = DateTime.now();
    final timeStr =
        '${now.hour.toString().padLeft(2, '0')}:${now.minute.toString().padLeft(2, '0')}';
    final success =
        await ApiClient.updateLesson(subj.id, les.id, les.title, _pages);
    if (!mounted) return;
    setState(() {
      _isLoading = false;
      if (success) {
        _lastSavedTime     = timeStr;
        _hasUnsavedChanges = false;
      }
    });
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        backgroundColor: const Color(0xFF1E293B),
        content: Row(children: [
          Icon(success ? Icons.check_circle : Icons.error_outline,
              color: success ? const Color(0xFF4ADE80) : Colors.red, size: 18),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              success
                  ? 'Cours "${les.title}" enregistré à $timeStr'
                  : 'Erreur lors de la sauvegarde du cours',
              style: const TextStyle(
                  color: Colors.white, fontWeight: FontWeight.bold),
            ),
          ),
        ]),
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  //  Gestion Multi-Pages
  // ═══════════════════════════════════════════════════════════════════════════

  void _previousPage() {
    if (_currentPageIndex > 0) setState(() => _currentPageIndex--);
  }

  void _nextPage() {
    if (_currentPageIndex < _pages.length - 1) {
      setState(() => _currentPageIndex++);
    }
  }

  void _addPage() {
    setState(() {
      _pages.add(NotebookPageModel(
        id:         'page-${DateTime.now().millisecondsSinceEpoch}',
        pageNumber: _pages.length + 1,
        strokes:    [],
        redoStack:  [],
      ));
      _currentPageIndex  = _pages.length - 1;
      _hasUnsavedChanges = true;
    });
  }

  void _deletePage() {
    if (_pages.length <= 1) {
      setState(() {
        _currentPage.strokes.clear();
        _currentPage.redoStack.clear();
        _hasUnsavedChanges = true;
      });
      return;
    }
    setState(() {
      _pages.removeAt(_currentPageIndex);
      for (int i = 0; i < _pages.length; i++) {
        _pages[i].pageNumber = i + 1;
      }
      if (_currentPageIndex >= _pages.length) {
        _currentPageIndex = _pages.length - 1;
      }
      _hasUnsavedChanges = true;
    });
  }

  // ═══════════════════════════════════════════════════════════════════════════
  //  Dessin — SYSTÈME DE COORDONNÉES
  //
  //  Le Listener est placé DANS l'InteractiveViewer.
  //  Flutter applique l'inverse de la matrice de transformation lors du
  //  hit-testing → event.localPosition est DÉJÀ en coordonnées logiques
  //  de la feuille (référentiel kPageWidth × kPageHeight).
  //
  //  Les points enregistrés dans PostgreSQL sont donc stables et
  //  indépendants du zoom et de la taille de l'écran.
  // ═══════════════════════════════════════════════════════════════════════════

  void _onPointerDown(PointerDownEvent event) {
    _activePointers++;

    // ≥2 doigts → l'InteractiveViewer gère le zoom / pan → annuler le tracé
    if (_activePointers > 1 || _isPanMode) {
      if (_currentStroke != null) setState(() => _currentStroke = null);
      return;
    }

    final now      = DateTime.now().millisecondsSinceEpoch.toDouble();
    final strokeId = 'stroke-$now-${Random().nextInt(1000)}';

    // Coordonnées logiques de la feuille (déjà converties par Flutter)
    final point = PointModel(
      x:         event.localPosition.dx,
      y:         event.localPosition.dy,
      timestamp: now,
      pressure:  event.pressure > 0 ? event.pressure : 1.0,
    );

    if (_activeTool == 'eraser') {
      _eraseStrokesNear(point);
      return;
    }

    setState(() {
      _redoStack.clear();
      _currentStroke = StrokeModel(
        id:          strokeId,
        points:      [point],
        startTime:   now,
        endTime:     now,
        color:       _activeTool == 'diagram' ? '#1E40AF' : _activeColor,
        width:       _activeTool == 'diagram' ? 2.0 : _activeWidth,
        tool:        _activeTool,
        contentType: _activeTool == 'pen' ? _activeContentType : 'normal',
        pointerType: event.kind == PointerDeviceKind.stylus ? 'pen' : 'touch',
        bbox: BoundingBoxModel(
          xMin: point.x, yMin: point.y, xMax: point.x, yMax: point.y,
        ),
      );
    });
  }

  void _onPointerMove(PointerMoveEvent event) {
    if (_activePointers > 1 || _isPanMode) return;

    final now   = DateTime.now().millisecondsSinceEpoch.toDouble();
    final point = PointModel(
      x:         event.localPosition.dx,
      y:         event.localPosition.dy,
      timestamp: now,
      pressure:  event.pressure > 0 ? event.pressure : 1.0,
    );

    if (_activeTool == 'eraser') {
      _eraseStrokesNear(point);
      return;
    }

    if (_currentStroke == null) return;

    final old = _currentStroke!.bbox;
    setState(() {
      _currentStroke = StrokeModel(
        id:          _currentStroke!.id,
        points:      List<PointModel>.from(_currentStroke!.points)..add(point),
        startTime:   _currentStroke!.startTime,
        endTime:     now,
        color:       _currentStroke!.color,
        width:       _currentStroke!.width,
        tool:        _currentStroke!.tool,
        contentType: _currentStroke!.contentType,
        pointerType: _currentStroke!.pointerType,
        bbox: BoundingBoxModel(
          xMin: min(old.xMin, point.x),
          yMin: min(old.yMin, point.y),
          xMax: max(old.xMax, point.x),
          yMax: max(old.yMax, point.y),
        ),
      );
    });
  }

  void _onPointerUp(PointerUpEvent event) {
    _activePointers = max(0, _activePointers - 1);
    if (_isPanMode) return;
    if (_currentStroke != null) {
      setState(() {
        _strokes.add(_currentStroke!);
        _currentStroke     = null;
        _hasUnsavedChanges = true;
      });
    }
  }

  void _onPointerCancel(PointerCancelEvent event) {
    _activePointers = max(0, _activePointers - 1);
    if (_currentStroke != null) setState(() => _currentStroke = null);
  }

  void _eraseStrokesNear(PointModel point) {
    const eraseRadius = 18.0;
    bool erasedAny    = false;
    setState(() {
      _strokes.removeWhere((stroke) {
        for (final p in stroke.points) {
          if (sqrt(pow(p.x - point.x, 2) + pow(p.y - point.y, 2)) <= eraseRadius) {
            erasedAny = true;
            return true;
          }
        }
        return false;
      });
    });
    if (erasedAny) {
      _redoStack.clear();
      _hasUnsavedChanges = true;
    }
  }

  void _undo() {
    if (_strokes.isNotEmpty) {
      setState(() {
        _redoStack.add(_strokes.removeLast());
        _hasUnsavedChanges = true;
      });
    }
  }

  void _redo() {
    if (_redoStack.isNotEmpty) {
      setState(() {
        _strokes.add(_redoStack.removeLast());
        _hasUnsavedChanges = true;
      });
    }
  }

  void _clearCanvas() {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Effacer toute la page ?'),
        content: const Text('Tous les tracés manuscrits de la page courante seront supprimés.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Annuler'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFFEF4444), foregroundColor: Colors.white),
            onPressed: () {
              Navigator.pop(ctx);
              setState(() {
                _strokes.clear();
                _redoStack.clear();
                _structuralResult  = null;
                _hasUnsavedChanges = true;
              });
            },
            child: const Text('Effacer'),
          ),
        ],
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  //  Export PDF
  // ═══════════════════════════════════════════════════════════════════════════

  void _openExportOptionsModal() {
    if (_totalStrokesInDoc == 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
            content: Text('Veuillez écrire un cours manuscrit avant d\'exporter.')),
      );
      return;
    }
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Options d\'exportation PDF'),
        content: Text(
          'Votre cours contient ${_pages.length} page(s).\nComment souhaitez-vous générer le document ?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Annuler'),
          ),
          OutlinedButton(
            onPressed: () {
              Navigator.pop(context);
              _exportRawPdf();
            },
            child: const Text('PDF Original (Manuscrit Tel Quel)'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF1E40AF),
                foregroundColor: Colors.white),
            onPressed: () {
              Navigator.pop(context);
              _recognizeStructuralHTR();
            },
            child: const Text('PDF IA Structuré'),
          ),
        ],
      ),
    );
  }

  Future<void> _exportRawPdf() async {
    setState(() => _isLoading = true);
    try {
      // On utilise les dimensions LOGIQUES de la feuille pour l'export PDF
      final pdfBytes = await ApiClient.exportRawPdfPages(
        pages:        _pages,
        canvasWidth:  kPageWidth,
        canvasHeight: kPageHeight,
        subject:      _currentSubject?.name ?? 'Mathématiques',
        lessonTitle:  _currentLesson?.title  ?? 'Chapitre 1',
      );
      if (!mounted) return;
      _saveAndShowSuccessDialog(
        'PDF Original Généré (${pdfBytes.length} octets)',
        '${_currentSubject?.name ?? "Cours"}_${_currentLesson?.title ?? "Chapitre"}_Original.pdf',
        pdfBytes,
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Erreur export PDF brut : $e'), backgroundColor: Colors.red),
      );
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _recognizeStructuralHTR() async {
    setState(() => _isLoading = true);
    try {
      final result = await ApiClient.recognizeStructuralPages(
        pages:        _pages,
        canvasWidth:  kPageWidth,
        canvasHeight: kPageHeight,
        subject:      _currentSubject?.name ?? 'Mathématiques',
        lessonTitle:  _currentLesson?.title  ?? 'Chapitre 1',
        language:     _selectedLanguage.toLowerCase(),
      );
      if (!mounted) return;
      setState(() => _structuralResult = result);
      _showStructuralBottomSheet();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Erreur HTR Structurel : $e'), backgroundColor: Colors.red),
      );
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _downloadPDF() async {
    if (_structuralResult == null || _structuralResult!.elements.isEmpty) {
      await _recognizeStructuralHTR();
      if (_structuralResult == null) return;
    }
    setState(() => _isLoading = true);
    try {
      final pdfBytes = await ApiClient.exportPdf(
        subject:     _structuralResult!.subject,
        lessonTitle: _structuralResult!.lessonTitle,
        elements:    _structuralResult!.elements,
      );
      if (!mounted) return;
      _saveAndShowSuccessDialog(
        'Document PDF IA Généré (${pdfBytes.length} octets)',
        '${_structuralResult!.subject}_${_structuralResult!.lessonTitle}_AI.pdf',
        pdfBytes,
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Erreur export PDF : $e'), backgroundColor: Colors.red),
      );
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _saveAndShowSuccessDialog(
      String title, String filename, List<int> pdfBytes) async {
    String savedPath = '/storage/emulated/0/Download/$filename';
    try {
      final downloadDir = Directory('/storage/emulated/0/Download');
      if (await downloadDir.exists()) {
        final file = File('${downloadDir.path}/$filename');
        await file.writeAsBytes(pdfBytes, flush: true);
        savedPath = file.path;
      }
    } catch (e) {
      debugPrint('Note: écriture stockage direct : $e');
    }
    if (!mounted) return;
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Row(children: [
          const Icon(Icons.check_circle, color: Colors.green),
          const SizedBox(width: 8),
          Expanded(child: Text(title, style: const TextStyle(fontSize: 16))),
        ]),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Fichier enregistré dans vos Téléchargements :'),
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                  color: Colors.grey.shade100,
                  borderRadius: BorderRadius.circular(6)),
              child: SelectableText(savedPath,
                  style: const TextStyle(
                      fontSize: 12, color: Colors.blue, fontWeight: FontWeight.bold)),
            ),
          ],
        ),
        actions: [
          ElevatedButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  int _selectedOcrTab = 0; // 0 = Texte, 1 = Mot à mot, 2 = Structure

  void _showStructuralBottomSheet() {
    showModalBottomSheet(
      context:            context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (context) => StatefulBuilder(
        builder: (context, setModalState) => Container(
          padding: const EdgeInsets.all(20),
          height:  MediaQuery.of(context).size.height * 0.85,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(_structuralResult?.subject ?? 'Cours Manuscrit',
                            style: const TextStyle(
                                fontSize: 14, color: Colors.blue, fontWeight: FontWeight.bold)),
                        Text(_structuralResult?.lessonTitle ?? 'Titre du Cours',
                            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                      ],
                    ),
                  ),
                  IconButton(
                      icon: const Icon(Icons.close),
                      onPressed: () => Navigator.pop(context)),
                ],
              ),
              // Badge de confiance réelle (§8.4)
              Builder(builder: (context) {
                final textElements = (_structuralResult?.elements ?? [])
                    .where((e) => e.type != 'diagram')
                    .toList();
                final avgConf = textElements.isEmpty
                    ? 1.0
                    : textElements.fold<double>(0.0, (acc, e) => acc + e.confidence) /
                        textElements.length;
                final confPct = (avgConf * 100).round();
                final isHigh = avgConf >= 0.8;
                final isLow = avgConf < 0.5;

                return Container(
                  margin: const EdgeInsets.symmetric(vertical: 8),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: isHigh
                        ? Colors.green.shade50
                        : isLow
                            ? Colors.red.shade50
                            : Colors.orange.shade50,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(
                      color: isHigh
                          ? Colors.green.shade300
                          : isLow
                              ? Colors.red.shade300
                              : Colors.orange.shade300,
                    ),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        isHigh
                            ? Icons.check_circle_outline
                            : isLow
                                ? Icons.error_outline
                                : Icons.help_outline,
                        size: 18,
                        color: isHigh
                            ? Colors.green.shade700
                            : isLow
                                ? Colors.red.shade700
                                : Colors.orange.shade700,
                      ),
                      const SizedBox(width: 8),
                      Text(
                        '${((_structuralResult as dynamic)?.calibrated == true) ? "Confiance" : "Confiance indicative"} : $confPct%  •  ${textElements.length} bloc(s)',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                          color: isHigh
                              ? Colors.green.shade800
                              : isLow
                                  ? Colors.red.shade800
                                  : Colors.orange.shade800,
                        ),
                      ),
                    ],
                  ),
                );
              }),

              // Barre de 3 onglets (§6.4)
              Container(
                margin: const EdgeInsets.symmetric(vertical: 8),
                decoration: BoxDecoration(
                  color: Colors.grey.shade200,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Row(
                  children: [
                    _buildTabButton('Texte', 0, setModalState),
                    _buildTabButton('Mot à mot', 1, setModalState),
                    _buildTabButton('Structure', 2, setModalState),
                  ],
                ),
              ),
              const Divider(),

              // Contenu selon l'onglet actif
              Expanded(
                child: _selectedOcrTab == 0
                    ? _buildTextTab(setModalState)
                    : _selectedOcrTab == 1
                        ? _buildWordsTab(setModalState)
                        : _buildStructureTab(),
              ),

              const SizedBox(height: 10),
              ElevatedButton.icon(
                onPressed: _downloadPDF,
                icon:  const Icon(Icons.picture_as_pdf),
                label: const Text('Télécharger le Document PDF IA'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF1E40AF),
                  foregroundColor: Colors.white,
                  minimumSize: const Size(double.infinity, 44),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTabButton(String label, int index, StateSetter setModalState) {
    final isSelected = _selectedOcrTab == index;
    return Expanded(
      child: GestureDetector(
        onTap: () {
          setModalState(() => _selectedOcrTab = index);
          setState(() => _selectedOcrTab = index);
        },
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 8),
          decoration: BoxDecoration(
            color: isSelected ? const Color(0xFF1E40AF) : Colors.transparent,
            borderRadius: BorderRadius.circular(8),
          ),
          child: Text(
            label,
            textAlign: TextAlign.center,
            style: TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 13,
              color: isSelected ? Colors.white : Colors.grey.shade700,
            ),
          ),
        ),
      ),
    );
  }

  // Onglet 1 : Texte avec mots douteux stylés et cliquables (§6.4)
  Widget _buildTextTab(StateSetter setModalState) {
    final elements = _structuralResult?.elements ?? [];
    return ListView.builder(
      itemCount: elements.length,
      itemBuilder: (context, idx) {
        final elem = elements[idx];
        if (elem.type == 'diagram') return const SizedBox.shrink();

        if (elem.words.isEmpty) {
          return Padding(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Text(elem.text, style: const TextStyle(fontSize: 15, height: 1.6)),
          );
        }

        return Padding(
          padding: const EdgeInsets.symmetric(vertical: 6),
          child: Wrap(
            spacing: 4,
            runSpacing: 4,
            children: elem.words.map((w) {
              final isWrong = w.confidence < 0.50;
              final isCheck = w.confidence >= 0.50 && w.confidence < 0.80;

              return InkWell(
                onTap: () => _showWordCorrectionBottomSheet(elem, w, setModalState),
                borderRadius: BorderRadius.circular(4),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 2, vertical: 1),
                  decoration: BoxDecoration(
                    border: isWrong
                        ? const Border(bottom: BorderSide(color: Colors.red, width: 2))
                        : isCheck
                            ? const Border(bottom: BorderSide(color: Colors.orange, width: 1.5))
                            : null,
                  ),
                  child: Text(
                    '${w.text}${w.corrected ? " ✎" : ""}',
                    style: TextStyle(
                      fontSize: 15,
                      fontStyle: w.corrected ? FontStyle.italic : FontStyle.normal,
                      color: isWrong
                          ? Colors.red.shade900
                          : isCheck
                              ? Colors.orange.shade900
                              : w.corrected
                                  ? Colors.blue.shade700
                                  : Colors.black87,
                      fontWeight: isWrong ? FontWeight.bold : FontWeight.normal,
                    ),
                  ),
                ),
              );
            }).toList(),
          ),
        );
      },
    );
  }

  // Onglet 2 : Mot à mot avec miniatures de lignes (§6.4)
  Widget _buildWordsTab(StateSetter setModalState) {
    final elements = _structuralResult?.elements ?? [];
    return ListView.builder(
      itemCount: elements.length,
      itemBuilder: (context, idx) {
        final elem = elements[idx];
        if (elem.type == 'diagram') return const SizedBox.shrink();

        final imgSrc = elem.thumbnail ?? elem.imageBase64;

        return Card(
          margin: const EdgeInsets.symmetric(vertical: 6),
          elevation: 1,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          child: Padding(
            padding: const EdgeInsets.all(10),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (imgSrc != null && imgSrc.isNotEmpty)
                  Center(
                    child: Container(
                      margin: const EdgeInsets.only(bottom: 8),
                      padding: const EdgeInsets.all(4),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: Colors.grey.shade300),
                      ),
                      child: Builder(builder: (context) {
                        try {
                          final clean = imgSrc.contains(',') ? imgSrc.split(',').last : imgSrc;
                          return Image.memory(base64Decode(clean), height: 44, fit: BoxFit.contain);
                        } catch (_) {
                          return const SizedBox.shrink();
                        }
                      }),
                    ),
                  ),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: elem.words.map((w) {
                    final isWrong = w.confidence < 0.50;
                    final isCheck = w.confidence >= 0.50 && w.confidence < 0.80;

                    return ActionChip(
                      onPressed: () => _showWordCorrectionBottomSheet(elem, w, setModalState),
                      backgroundColor: isWrong
                          ? Colors.red.shade50
                          : isCheck
                              ? Colors.orange.shade50
                              : Colors.grey.shade100,
                      side: BorderSide(
                        color: isWrong
                            ? Colors.red.shade400
                            : isCheck
                                ? Colors.orange.shade400
                                : Colors.grey.shade300,
                      ),
                      label: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            w.text,
                            style: TextStyle(
                              fontSize: 13,
                              fontWeight: isWrong ? FontWeight.bold : FontWeight.normal,
                              color: isWrong
                                  ? Colors.red.shade900
                                  : isCheck
                                      ? Colors.orange.shade900
                                      : Colors.black87,
                            ),
                          ),
                          if (w.corrected) ...[
                            const SizedBox(width: 4),
                            const Text('✎', style: TextStyle(fontSize: 10, color: Colors.blue)),
                            const SizedBox(width: 2),
                            InkWell(
                              onTap: () {
                                if (w.original != null) {
                                  w.text = w.original!;
                                  w.corrected = false;
                                  elem.text = elem.words.map((m) => m.text).join(' ');
                                  setModalState(() {});
                                  setState(() {});
                                }
                              },
                              child: const Icon(Icons.undo, size: 14, color: Colors.grey),
                            ),
                          ],
                        ],
                      ),
                    );
                  }).toList(),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  // Onglet 3 : Structure (Markdown, titres, schémas)
  Widget _buildStructureTab() {
    return ListView.builder(
      itemCount: _structuralResult?.elements.length ?? 0,
      itemBuilder: (context, idx) {
        final elem = _structuralResult!.elements[idx];
        if (elem.type == 'h1') {
          return Padding(
            padding: const EdgeInsets.symmetric(vertical: 8),
            child: Text(elem.text,
                style: const TextStyle(
                    fontSize: 20, fontWeight: FontWeight.bold, color: Color(0xFF1E40AF))),
          );
        } else if (elem.type == 'h2') {
          return Padding(
            padding: const EdgeInsets.symmetric(vertical: 6),
            child: Text(elem.text,
                style: const TextStyle(
                    fontSize: 17, fontWeight: FontWeight.bold, color: Color(0xFF0D9488))),
          );
        } else if (elem.type == 'h3') {
          return Padding(
            padding: const EdgeInsets.symmetric(vertical: 5),
            child: Text(elem.text,
                style: const TextStyle(
                    fontSize: 15, fontWeight: FontWeight.bold, color: Color(0xFF7C3AED))),
          );
        } else if (elem.type == 'diagram') {
          return Container(
            margin:  const EdgeInsets.symmetric(vertical: 8),
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: Colors.blue.shade50,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: Colors.blue.shade200),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Schéma (Page ${elem.pageNumber})',
                    style: const TextStyle(
                        fontSize: 12, fontWeight: FontWeight.bold, color: Colors.blue)),
                const SizedBox(height: 6),
                if (elem.imageBase64 != null && elem.imageBase64!.isNotEmpty)
                  Builder(builder: (context) {
                    try {
                      final b64 = elem.imageBase64!.contains(',')
                          ? elem.imageBase64!.split(',').last.trim()
                          : elem.imageBase64!.trim();
                      return Image.memory(base64Decode(b64),
                          height: 140, fit: BoxFit.contain);
                    } catch (err) {
                      return Text('[Image indisponible : $err]',
                          style: const TextStyle(fontSize: 11, color: Colors.red));
                    }
                  }),
              ],
            ),
          );
        } else {
          return Padding(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Text(elem.text, style: const TextStyle(fontSize: 14, height: 1.6)),
          );
        }
      },
    );
  }

  // Modal de correction mot à mot (§6.4)
  void _showWordCorrectionBottomSheet(
    StructuralElementModel elem,
    WordModel word,
    StateSetter modalSetState,
  ) {
    final controller = TextEditingController(text: word.text);
    bool consentTrain = false;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => Padding(
          padding: EdgeInsets.only(
            left: 20,
            right: 20,
            top: 20,
            bottom: MediaQuery.of(ctx).viewInsets.bottom + 20,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text('Corriger un mot',
                      style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold)),
                  IconButton(
                    icon: const Icon(Icons.close),
                    onPressed: () => Navigator.pop(ctx),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                'Reconnu : « ${word.original ?? word.text} »  (Confiance ${(word.confidence * 100).round()}%)',
                style: const TextStyle(fontSize: 13, color: Colors.grey),
              ),
              if (word.alternatives.isNotEmpty) ...[
                const SizedBox(height: 10),
                const Text('Suggestions :', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                const SizedBox(height: 4),
                Wrap(
                  spacing: 6,
                  children: word.alternatives.map((alt) {
                    return ActionChip(
                      label: Text(alt),
                      onPressed: () {
                        controller.text = alt;
                        setDialogState(() {});
                      },
                    );
                  }).toList(),
                ),
              ],
              const SizedBox(height: 14),
              TextField(
                controller: controller,
                autofocus: true,
                textDirection: _selectedLanguage == 'ar' ? TextDirection.rtl : TextDirection.ltr,
                decoration: InputDecoration(
                  labelText: 'Votre correction',
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                ),
              ),
              const SizedBox(height: 10),
              CheckboxListTile(
                value: consentTrain,
                onChanged: (val) => setDialogState(() => consentTrain = val ?? false),
                title: const Text('Aider à améliorer la reconnaissance (opt-in)',
                    style: TextStyle(fontSize: 12)),
                controlAffinity: ListTileControlAffinity.leading,
                contentPadding: EdgeInsets.zero,
              ),
              const SizedBox(height: 12),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: () => Navigator.pop(ctx),
                    child: const Text('Annuler'),
                  ),
                  const SizedBox(width: 8),
                  ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF1E40AF),
                      foregroundColor: Colors.white,
                    ),
                    onPressed: () {
                      final newText = controller.text.trim();
                      if (newText.isNotEmpty) {
                        final linePredicted = elem.text;
                        final wordPredicted = word.original ?? word.text;
                        word.original ??= word.text;
                        word.text = newText;
                        word.corrected = true;
                        word.source = 'memory';
                        elem.text = elem.words.map((w) => w.text).join(' ');
                        elem.source = 'memory';
                        final lineCorrected = elem.text;

                        final lineStrokes = _pages
                            .expand((p) => p.strokes)
                            .where((s) => elem.strokeIds.contains(s.id))
                            .map((s) => s.toJson())
                            .toList();

                        // Appel asynchrone feedback complet (Plan v2 §1.3 & §1.5)
                        ApiClient.sendFeedback({
                          'scope': 'word',
                          'word_index': word.index,
                          'stroke_ids': elem.strokeIds,
                          'strokes': lineStrokes,
                          'stroke_fingerprint': elem.strokeFingerprint,
                          'language': _selectedLanguage.toLowerCase(),
                          'predicted_text': wordPredicted,
                          'corrected_text': newText,
                          'line_predicted': linePredicted,
                          'line_corrected': lineCorrected,
                          'confidence': word.confidence,
                          'consent_train': consentTrain,
                        });

                        modalSetState(() {});
                        setState(() {});
                      }
                      Navigator.pop(ctx);
                    },
                    child: const Text('Corriger'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  //  Paramètres serveur
  // ═══════════════════════════════════════════════════════════════════════════

  void _showServerSettingsDialog() {
    final controller = TextEditingController(text: EnvConfig.baseUrl);
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Connexion Serveur PC'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('URL par défaut (câble USB ADB) :',
                style: TextStyle(fontSize: 12)),
            const SelectableText('http://127.0.0.1:8000/api/v1',
                style: TextStyle(fontWeight: FontWeight.bold, color: Colors.blue)),
            const SizedBox(height: 14),
            TextField(
              controller: controller,
              decoration: const InputDecoration(
                  labelText: 'URL API du Backend PC', border: OutlineInputBorder()),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () {
              EnvConfig.setRuntimeUrl('http://127.0.0.1:8000/api/v1');
              Navigator.pop(context);
              _loadSubjectsAndLesson();
            },
            child: const Text('Reset Câble USB'),
          ),
          ElevatedButton(
            onPressed: () {
              EnvConfig.setRuntimeUrl(controller.text);
              Navigator.pop(context);
              _loadSubjectsAndLesson();
            },
            child: const Text('Enregistrer'),
          ),
        ],
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  //  Dialogs Nouveau Sujet / Nouveau Cours
  // ═══════════════════════════════════════════════════════════════════════════

  void _openNewSubjectFromDrawer() {
    final controller    = TextEditingController();
    String selectedColor = '#1E40AF';
    final colors = ['#1E40AF', '#DC2626', '#15803D', '#7C3AED', '#D97706', '#0D9488'];

    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('Nouvel Espace de Travail'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Nom de la matière :', style: TextStyle(fontSize: 13)),
              const SizedBox(height: 6),
              TextField(
                controller: controller,
                autofocus: true,
                decoration: const InputDecoration(
                    hintText: 'Ex: Mathématiques', border: OutlineInputBorder()),
              ),
              const SizedBox(height: 14),
              const Text('Couleur :', style: TextStyle(fontSize: 13)),
              const SizedBox(height: 8),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: colors.map((colHex) {
                  final isSelected = selectedColor == colHex;
                  final colorVal = Color(int.parse(colHex.replaceFirst('#', '0xFF')));
                  return GestureDetector(
                    onTap: () => setDialogState(() => selectedColor = colHex),
                    child: Container(
                      padding: const EdgeInsets.all(2),
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        border: Border.all(
                          color: isSelected ? Colors.black : Colors.transparent,
                          width: 2,
                        ),
                      ),
                      child: CircleAvatar(
                        radius: 12,
                        backgroundColor: colorVal,
                        child: isSelected
                            ? const Icon(Icons.check, size: 12, color: Colors.white)
                            : null,
                      ),
                    ),
                  );
                }).toList(),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Annuler'),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF1E40AF), foregroundColor: Colors.white),
              onPressed: () async {
                final name = controller.text.trim();
                if (name.isEmpty) return;
                final created = await ApiClient.createSubject(name, selectedColor);
                final newSubj = created ??
                    SubjectModel(
                      id:      'subj-${DateTime.now().millisecondsSinceEpoch}',
                      name:    name,
                      color:   selectedColor,
                      lessons: [],
                    );
                setState(() {
                  _subjects.add(newSubj);
                  _currentSubject = newSubj;
                });
                if (context.mounted) {
                  Navigator.pop(context);
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('Espace "$name" créé avec succès.')),
                  );
                }
              },
              child: const Text('Créer l\'espace'),
            ),
          ],
        ),
      ),
    );
  }

  void _openNewLessonFromDrawer() {
    final titleController = TextEditingController();
    SubjectModel? targetSubject =
        _currentSubject ?? (_subjects.isNotEmpty ? _subjects.first : null);

    if (_subjects.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Veuillez d\'abord créer un espace de travail.')),
      );
      _openNewSubjectFromDrawer();
      return;
    }

    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('Nouveau Cours'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Titre du cours :', style: TextStyle(fontSize: 13)),
              const SizedBox(height: 6),
              TextField(
                controller: titleController,
                autofocus: true,
                decoration: const InputDecoration(
                    hintText: 'Ex: Fonctions & Dérivées', border: OutlineInputBorder()),
              ),
              const SizedBox(height: 14),
              const Text('Espace de rattachement :', style: TextStyle(fontSize: 13)),
              const SizedBox(height: 6),
              DropdownButtonFormField<SubjectModel>(
                initialValue: targetSubject,
                items: _subjects
                    .map((s) => DropdownMenuItem(value: s, child: Text(s.name)))
                    .toList(),
                onChanged: (val) {
                  if (val != null) setDialogState(() => targetSubject = val);
                },
                decoration: const InputDecoration(border: OutlineInputBorder()),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Annuler'),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF1E40AF), foregroundColor: Colors.white),
              onPressed: () async {
                final title = titleController.text.trim();
                if (title.isEmpty || targetSubject == null) return;
                final created = await ApiClient.createLesson(title, targetSubject!.id);
                final newLes = created ??
                    LessonModel(
                      id:        'les-${DateTime.now().millisecondsSinceEpoch}',
                      subjectId: targetSubject!.id,
                      title:     title,
                      updatedAt: DateTime.now().toIso8601String().split('T').first,
                      pages: [
                        NotebookPageModel(
                            id: 'page-1', pageNumber: 1, strokes: [], redoStack: [])
                      ],
                    );
                setState(() {
                  targetSubject!.lessons.insert(0, newLes);
                  _currentSubject = targetSubject;
                  _currentLesson  = newLes;
                  _pages.clear();
                  _pages.addAll(newLes.pages.isNotEmpty
                      ? newLes.pages
                      : [
                          NotebookPageModel(
                              id: 'page-1', pageNumber: 1, strokes: [], redoStack: [])
                        ]);
                  _currentPageIndex = 0;
                });
                if (context.mounted) Navigator.pop(context);
              },
              child: const Text('Commencer à écrire'),
            ),
          ],
        ),
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  //  BUILD
  // ═══════════════════════════════════════════════════════════════════════════

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: _buildAppBar(),
      drawer: CourseDrawer(
        subjects:       _subjects,
        activeSubject:  _currentSubject,
        activeLesson:   _currentLesson,
        onSelectLesson: (subj, lesson) {
          setState(() {
            _currentSubject = subj;
            _currentLesson  = lesson;
          });
          _fetchLessonFromApi(subj.id, lesson.id);
        },
        onCreateSubject:      _openNewSubjectFromDrawer,
        onCreateLesson:       _openNewLessonFromDrawer,
        onOpenServerSettings: _showServerSettingsDialog,
        onGoHome:             _navigateToDashboard,
      ),
      body: SafeArea(
        child: _isLoading
            ? const Center(child: CircularProgressIndicator(color: Color(0xFF818CF8)))
            : Column(
                children: [
                  _buildToolbar(),
                  _buildZoomBar(),
                  Expanded(child: _buildCanvas()),
                ],
              ),
      ),
    );
  }

  // ── AppBar ────────────────────────────────────────────────────────────────

  AppBar _buildAppBar() {
    return AppBar(
      backgroundColor: const Color(0xFF1E293B),
      elevation: 0,
      // Hamburger → ouvre le Drawer (le bouton Home est DANS le Drawer)
      leading: Builder(
        builder: (ctx) => IconButton(
          tooltip: 'Menu',
          icon: const Icon(Icons.menu, color: Colors.white),
          onPressed: () => Scaffold.of(ctx).openDrawer(),
        ),
      ),
      title: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Flexible(
                child: Text(
                  _currentLesson?.title ?? 'Cahier Notely',
                  style: const TextStyle(
                      fontSize: 15, fontWeight: FontWeight.bold, color: Colors.white),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              const SizedBox(width: 6),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: const Color(0xFF6366F1).withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: const Color(0xFF6366F1)),
                ),
                child: Text(
                  _currentSubject?.name ?? 'Notely',
                  style: const TextStyle(
                      fontSize: 10, color: Color(0xFFA5B4FC), fontWeight: FontWeight.bold),
                ),
              ),
              if (_hasUnsavedChanges)
                const Padding(
                  padding: EdgeInsets.only(left: 4),
                  child: Icon(Icons.circle, size: 8, color: Color(0xFFFBBF24)),
                ),
            ],
          ),
          Row(
            children: [
              const Icon(Icons.sync, size: 10, color: Color(0xFF4ADE80)),
              const SizedBox(width: 4),
              Text(
                _lastSavedTime.isNotEmpty
                    ? 'Sauvegardé à $_lastSavedTime'
                    : 'Auto-save toutes les 5 min',
                style: const TextStyle(fontSize: 10, color: Color(0xFF94A3B8)),
              ),
            ],
          ),
        ],
      ),
            actions: [
        // Sélecteur de langue OCR (P2 UX Critique / §6.7)
        PopupMenuButton<String>(
          tooltip: 'Langue de reconnaissance',
          initialValue: _selectedLanguage,
          onSelected: (lang) => setState(() => _selectedLanguage = lang),
          itemBuilder: (context) => const [
            PopupMenuItem(value: 'fr', child: Text('FR - Français')),
            PopupMenuItem(value: 'en', child: Text('EN - English')),
            PopupMenuItem(value: 'ar', child: Text('AR - Arabe')),
            PopupMenuItem(value: 'de', child: Text('DE - Deutsch')),
          ],
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            margin: const EdgeInsets.symmetric(vertical: 12),
            decoration: BoxDecoration(
              color: const Color(0xFF334155),
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: const Color(0xFF6366F1)),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  _selectedLanguage.toUpperCase(),
                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white),
                ),
                const Icon(Icons.arrow_drop_down, size: 16, color: Colors.white70),
              ],
            ),
          ),
        ),
        const SizedBox(width: 4),
        // Action principale : Reconnaître l'écriture (§6.2 #5)
        ElevatedButton.icon(
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFF4F46E5),
            foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            visualDensity: VisualDensity.compact,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
          ),
          onPressed: _recognizeStructuralHTR,
          icon: const Icon(Icons.auto_awesome, size: 16),
          label: const Text('Reconnaître', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
        ),
        // Menu 'Plus' (⋮) regroupant les actions secondaires (§6.2 #1)
        PopupMenuButton<String>(
          tooltip: 'Plus d\'options',
          icon: const Icon(Icons.more_vert, color: Colors.white70),
          onSelected: (val) {
            switch (val) {
              case 'save':
                _saveCourseManually();
                break;
              case 'export':
                _openExportOptionsModal();
                break;
              case 'grid':
                setState(() => _showGrid = !_showGrid);
                break;
              case 'clear':
                if (_strokes.isNotEmpty) _clearCanvas();
                break;
            }
          },
          itemBuilder: (context) => [
            const PopupMenuItem(
              value: 'save',
              child: ListTile(
                leading: Icon(Icons.save_outlined, color: Color(0xFF60A5FA)),
                title: Text('Enregistrer manuellement'),
                contentPadding: EdgeInsets.zero,
                dense: true,
              ),
            ),
            const PopupMenuItem(
              value: 'export',
              child: ListTile(
                leading: Icon(Icons.picture_as_pdf, color: Color(0xFF34D399)),
                title: Text('Exporter PDF (Fidèle / Structuré)'),
                contentPadding: EdgeInsets.zero,
                dense: true,
              ),
            ),
            PopupMenuItem(
              value: 'grid',
              child: ListTile(
                leading: Icon(_showGrid ? Icons.grid_off : Icons.grid_on),
                title: Text(_showGrid ? 'Masquer quadrillage' : 'Afficher quadrillage'),
                contentPadding: EdgeInsets.zero,
                dense: true,
              ),
            ),
            const PopupMenuDivider(),
            PopupMenuItem(
              value: 'clear',
              enabled: _strokes.isNotEmpty,
              child: const ListTile(
                leading: Icon(Icons.delete_outline, color: Color(0xFFEF4444)),
                title: Text('Effacer la page'),
                contentPadding: EdgeInsets.zero,
                dense: true,
              ),
            ),
          ],
        ),
      ],
    );
  }

  // ── Barre d'outils de dessin ──────────────────────────────────────────────

  Widget _buildToolbar() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      color: const Color(0xFF1E293B),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: [
            // Outils
            SegmentedButton<String>(
              style: SegmentedButton.styleFrom(
                selectedBackgroundColor: const Color(0xFF4F46E5),
                selectedForegroundColor: Colors.white,
                backgroundColor:  const Color(0xFF0F172A),
                foregroundColor:  const Color(0xFF94A3B8),
                visualDensity:    VisualDensity.compact,
                tapTargetSize:    MaterialTapTargetSize.shrinkWrap,
              ),
              segments: const [
                ButtonSegment(value: 'pen',
                    label: Text('Stylet', style: TextStyle(fontSize: 12)),
                    icon: Icon(Icons.edit, size: 15)),
                ButtonSegment(value: 'diagram',
                    label: Text('Schéma', style: TextStyle(fontSize: 12)),
                    icon: Icon(Icons.interests, size: 15)),
                ButtonSegment(value: 'eraser',
                    label: Text('Gomme', style: TextStyle(fontSize: 12)),
                    icon: Icon(Icons.cleaning_services, size: 15)),
              ],
              selected: {_activeTool},
              onSelectionChanged: (set) => setState(() => _activeTool = set.first),
            ),

            const SizedBox(width: 10),
            const VerticalDivider(width: 1, color: Colors.white24),
            const SizedBox(width: 10),

            // Couleurs
            if (_activeTool != 'eraser') ...[
              Row(
                children: _palette.map((item) {
                  final isSel = _activeColor == item['color'];
                  return GestureDetector(
                    onTap: () => setState(() => _activeColor = item['color'] as String),
                    child: Container(
                      margin: const EdgeInsets.symmetric(horizontal: 3),
                      padding: const EdgeInsets.all(2),
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        border: Border.all(
                          color: isSel ? Colors.white : Colors.transparent,
                          width: 2,
                        ),
                      ),
                      child: CircleAvatar(radius: 9, backgroundColor: item['value'] as Color),
                    ),
                  );
                }).toList(),
              ),
              const SizedBox(width: 10),
              const VerticalDivider(width: 1, color: Colors.white24),
              const SizedBox(width: 10),
            ],

            // Épaisseurs
            Row(
              children: _widths.map((w) {
                final isSel = _activeWidth == w;
                return Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 2),
                  child: InkWell(
                    onTap: () => setState(() => _activeWidth = w),
                    borderRadius: BorderRadius.circular(6),
                    child: Container(
                      padding: const EdgeInsets.all(5),
                      decoration: BoxDecoration(
                        color: isSel
                            ? const Color(0xFF4F46E5).withValues(alpha: 0.3)
                            : Colors.transparent,
                        border: Border.all(
                          color: isSel ? const Color(0xFF6366F1) : Colors.transparent,
                        ),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Container(
                        width: 14, height: w * 2,
                        decoration: BoxDecoration(
                            color: Colors.white, borderRadius: BorderRadius.circular(2)),
                      ),
                    ),
                  ),
                );
              }).toList(),
            ),

            const SizedBox(width: 10),
            const VerticalDivider(width: 1, color: Colors.white24),
            const SizedBox(width: 10),

            // Annuler / Rétablir (P2 UX Critique / §6.2 #7)
            IconButton(
              tooltip: 'Annuler (Ctrl+Z)',
              icon: const Icon(Icons.undo, size: 20),
              color: _strokes.isNotEmpty ? Colors.white : Colors.white30,
              onPressed: _strokes.isNotEmpty ? _undo : null,
              constraints: const BoxConstraints(minWidth: 44, minHeight: 44),
            ),
            IconButton(
              tooltip: 'Rétablir (Ctrl+Y)',
              icon: const Icon(Icons.redo, size: 20),
              color: _redoStack.isNotEmpty ? Colors.white : Colors.white30,
              onPressed: _redoStack.isNotEmpty ? _redo : null,
              constraints: const BoxConstraints(minWidth: 44, minHeight: 44),
            ),
            const SizedBox(width: 8),
            const VerticalDivider(width: 1, color: Colors.white24),
            const SizedBox(width: 8),

            // Pages
            Row(
              children: [
                IconButton(
                  icon: const Icon(Icons.chevron_left, color: Colors.white),
                  onPressed: _currentPageIndex > 0 ? _previousPage : null,
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                ),
                Text(
                  '${_currentPageIndex + 1}/${_pages.length}',
                  style: const TextStyle(
                      color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13),
                ),
                IconButton(
                  icon: const Icon(Icons.chevron_right, color: Colors.white),
                  onPressed:
                      _currentPageIndex < _pages.length - 1 ? _nextPage : null,
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                ),
                TextButton.icon(
                  onPressed: _addPage,
                  icon:  const Icon(Icons.add, size: 15, color: Color(0xFFA5B4FC)),
                  label: const Text('+Page',
                      style: TextStyle(color: Color(0xFFA5B4FC), fontSize: 11)),
                  style: TextButton.styleFrom(padding: const EdgeInsets.symmetric(horizontal: 4)),
                ),
                if (_pages.length > 1)
                  IconButton(
                    icon: const Icon(Icons.delete, color: Color(0xFFEF4444), size: 17),
                    tooltip:  'Supprimer cette page',
                    onPressed: _deletePage,
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  // ── Barre de zoom ─────────────────────────────────────────────────────────

  Widget _buildZoomBar() {
    final zoomPct = (_zoomLevel * 100).round();

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
      color: const Color(0xFF0F172A),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Mode dessin / déplacement
          Tooltip(
            message: _isPanMode
                ? 'Mode déplacement — cliquer pour dessiner'
                : 'Mode dessin — cliquer pour déplacer',
            child: InkWell(
              onTap: _togglePanMode,
              borderRadius: BorderRadius.circular(6),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: _isPanMode
                      ? const Color(0xFF4F46E5).withValues(alpha: 0.3)
                      : Colors.transparent,
                  border: Border.all(
                    color: _isPanMode ? const Color(0xFF6366F1) : Colors.white24,
                  ),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Row(children: [
                  Icon(
                    _isPanMode ? Icons.pan_tool : Icons.edit,
                    size: 14,
                    color: _isPanMode ? const Color(0xFF818CF8) : Colors.white60,
                  ),
                  const SizedBox(width: 4),
                  Text(
                    _isPanMode ? 'Dépl.' : 'Dessin',
                    style: TextStyle(
                        fontSize: 11,
                        color: _isPanMode ? const Color(0xFF818CF8) : Colors.white60),
                  ),
                ]),
              ),
            ),
          ),

          const SizedBox(width: 8),
          const VerticalDivider(width: 1, color: Colors.white24, indent: 4, endIndent: 4),
          const SizedBox(width: 4),

          // Zoom out
          IconButton(
            tooltip:     'Dézoomer',
            icon:        const Icon(Icons.remove, size: 16),
            color:       Colors.white70,
            onPressed:   _zoomLevel > _minZoom ? _zoomOut : null,
            padding:     EdgeInsets.zero,
            constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
          ),

          // Indicateur % — tap → fit page
          Tooltip(
            message: 'Ajuster à la page',
            child: InkWell(
              onTap: _fitPage,
              borderRadius: BorderRadius.circular(4),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
                decoration: BoxDecoration(
                  border: Border.all(color: Colors.white12),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  '$zoomPct%',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                    color: zoomPct == 100 ? Colors.white54 : const Color(0xFF818CF8),
                  ),
                ),
              ),
            ),
          ),

          // Zoom in
          IconButton(
            tooltip:     'Zoomer',
            icon:        const Icon(Icons.add, size: 16),
            color:       Colors.white70,
            onPressed:   _zoomLevel < _maxZoom ? _zoomIn : null,
            padding:     EdgeInsets.zero,
            constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
          ),

          const SizedBox(width: 4),
          const VerticalDivider(width: 1, color: Colors.white24, indent: 4, endIndent: 4),
          const SizedBox(width: 4),

          // Fit to page
          Tooltip(
            message: 'Ajuster à la page',
            child: IconButton(
              icon:        const Icon(Icons.fit_screen, size: 16),
              color:       Colors.white54,
              onPressed:   _fitPage,
              padding:     EdgeInsets.zero,
              constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
            ),
          ),
        ],
      ),
    );
  }

  // ── Canvas principal ──────────────────────────────────────────────────────
  //
  //  Architecture des coordonnées :
  //
  //  ┌─ InteractiveViewer (constrained: false)
  //  │    Applique matrix4 = [scale, tx, ty] à la feuille.
  //  │    Flutter inverse cette matrice pour le hit-testing.
  //  │
  //  │  └─ Listener
  //  │       event.localPosition = coordonnées LOGIQUES de la feuille
  //  │       (kPageWidth × kPageHeight) — aucune conversion manuelle.
  //  │
  //  │     └─ Container(shadow)   — ombre portée autour de la feuille
  //  │          └─ ClipRect        — empêche les tracés de déborder
  //  │               └─ CustomPaint(size: kPageWidth × kPageHeight)
  //  │                    Dessine : fond blanc + lignes + tracés.
  //  │                    Tous en coordonnées logiques stables.

  Widget _buildCanvas() {
    return LayoutBuilder(builder: (context, constraints) {
      // Mémoriser la taille disponible (sans setState — usage non-réactif)
      final available = constraints.biggest;
      if (available.isFinite && available != _canvasSize) {
        _canvasSize = available;
        // Initialiser la transformation au premier affichage
        if (!_transformInitialized) {
          _transformInitialized = true;
          SchedulerBinding.instance.addPostFrameCallback((_) {
            if (mounted) _fitPage();
          });
        }
      }

      return Container(
        // Fond de travail (bureau autour de la feuille)
        color: const Color(0xFF0F172A),
        child: InteractiveViewer(
          transformationController: _transformationController,
          constrained:   false,   // ← La feuille garde sa taille logique
          minScale:      _minZoom,
          maxScale:      _maxZoom,
          panEnabled:    _isPanMode,
          scaleEnabled:  true,
          // Marge généreuse pour naviguer au-delà des bords
          boundaryMargin: const EdgeInsets.all(400),
          onInteractionUpdate: (_) {
            final z = _transformationController.value.getMaxScaleOnAxis();
            if ((z - _zoomLevel).abs() > 0.005) {
              setState(() => _zoomLevel = z);
            }
          },
          child: Listener(
            onPointerDown:   _onPointerDown,
            onPointerMove:   _onPointerMove,
            onPointerUp:     _onPointerUp,
            onPointerCancel: _onPointerCancel,
            child: _buildPageWidget(),
          ),
        ),
      );
    });
  }

  /// La feuille physique : ombre + fond blanc clipé + tracés.
  Widget _buildPageWidget() {
    return Container(
      width:  kPageWidth,
      height: kPageHeight,
      decoration: BoxDecoration(
        // Ombre portée pour un effet "feuille posée sur un bureau"
        boxShadow: [
          BoxShadow(
            color:      Colors.black.withValues(alpha: 0.5),
            blurRadius: 24,
            offset:     const Offset(0, 8),
          ),
        ],
      ),
      // ClipRect : garantit qu'aucun tracé ne dépasse visuellement des
      // bords de la feuille — sans modifier les données en base.
      child: ClipRect(
        child: CustomPaint(
          painter: NotebookPainter(
            strokes:       _strokes,
            currentStroke: _currentStroke,
            showGrid:      _showGrid,
          ),
          size: const Size(kPageWidth, kPageHeight),
        ),
      ),
    );
  }
}
