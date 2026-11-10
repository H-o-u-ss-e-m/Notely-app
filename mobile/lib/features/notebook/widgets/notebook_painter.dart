import 'package:flutter/material.dart';
import '../../../models/stroke_model.dart';
import '../../../models/recognition_model.dart';

class NotebookPainter extends CustomPainter {
  final List<StrokeModel> strokes;
  final StrokeModel? currentStroke;
  final List<LineRecognitionModel>? debugLines;
  final bool showGrid;
  final String pageTemplate; // 'lined' | 'grid' | 'dots' | 'blank'
  final List<Offset>? lassoPoints;
  final List<StrokeModel>? selectedLassoStrokes;

  NotebookPainter({
    required this.strokes,
    this.currentStroke,
    this.debugLines,
    this.showGrid = true,
    this.pageTemplate = 'lined',
    this.lassoPoints,
    this.selectedLassoStrokes,
  });

  @override
  void paint(Canvas canvas, Size size) {
    // 1. Fond papier cahier
    final bgPaint = Paint()..color = const Color(0xFFFDFBF7);
    canvas.drawRect(Rect.fromLTWH(0, 0, size.width, size.height), bgPaint);

    // 2. Fond de page : Lignes / Quadrillage / Pointillés / Blanc (§6.4)
    if (showGrid) {
      _drawPageTemplate(canvas, size);
    }

    // 3. Dessiner les strokes complétés
    for (final stroke in strokes) {
      _drawSmoothStroke(canvas, stroke);
    }

    // 4. Dessiner le stroke en cours d'écriture
    if (currentStroke != null) {
      _drawSmoothStroke(canvas, currentStroke!);
    }

    // 5. Tracé du lasso en cours (§6.4)
    if (lassoPoints != null && lassoPoints!.length > 1) {
      _drawLasso(canvas);
    }

    // 6. Encadrement des traits sélectionnés au lasso (§6.4)
    if (selectedLassoStrokes != null && selectedLassoStrokes!.isNotEmpty) {
      _drawSelectedLassoBox(canvas);
    }

    // 7. Overlay de segmentation debug (Bounding Boxes)
    if (debugLines != null && debugLines!.isNotEmpty) {
      final colors = [
        Colors.red,
        Colors.green,
        Colors.blue,
        Colors.purple,
        Colors.orange
      ];

      for (int i = 0; i < debugLines!.length; i++) {
        final line = debugLines![i];
        final color = colors[i % colors.length];
        final bbox = line.bbox; // [xMin, yMin, xMax, yMax]

        final rectPaint = Paint()
          ..color = color
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2.0;

        final rect = Rect.fromLTRB(bbox[0], bbox[1], bbox[2], bbox[3]);
        canvas.drawRect(rect, rectPaint);
      }
    }
  }

  void _drawPageTemplate(Canvas canvas, Size size) {
    if (pageTemplate == 'blank') return;

    const double step = 32.0;
    final linePaint = Paint()
      ..color = const Color(0xFFE5E7EB)
      ..strokeWidth = 0.8;

    if (pageTemplate == 'lined' || pageTemplate == 'grid') {
      for (double y = 40; y < size.height; y += step) {
        canvas.drawLine(Offset(0, y), Offset(size.width, y), linePaint);
      }

      // Marge verticale rouge à gauche
      final marginPaint = Paint()
        ..color = const Color(0xFFFCA5A5)
        ..strokeWidth = 1.2;
      canvas.drawLine(const Offset(40, 0), Offset(40, size.height), marginPaint);
    }

    if (pageTemplate == 'grid') {
      for (double x = 40 + step; x < size.width; x += step) {
        canvas.drawLine(Offset(x, 0), Offset(x, size.height), linePaint);
      }
    }

    if (pageTemplate == 'dots') {
      final dotPaint = Paint()
        ..color = const Color(0xFFCBD5E1)
        ..style = PaintingStyle.fill;
      for (double y = 40; y < size.height; y += step) {
        for (double x = 40; x < size.width; x += step) {
          canvas.drawCircle(Offset(x, y), 1.2, dotPaint);
        }
      }
    }
  }

  void _drawLasso(Canvas canvas) {
    final lassoPaint = Paint()
      ..color = const Color(0xFF6366F1)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5;

    final path = Path()..moveTo(lassoPoints![0].dx, lassoPoints![0].dy);
    for (int i = 1; i < lassoPoints!.length; i++) {
      path.lineTo(lassoPoints![i].dx, lassoPoints![i].dy);
    }

    canvas.drawPath(path, lassoPaint);
  }

  void _drawSelectedLassoBox(Canvas canvas) {
    double minX = double.infinity, minY = double.infinity;
    double maxX = double.negativeInfinity, maxY = double.negativeInfinity;

    for (final s in selectedLassoStrokes!) {
      for (final p in s.points) {
        if (p.x < minX) minX = p.x;
        if (p.y < minY) minY = p.y;
        if (p.x > maxX) maxX = p.x;
        if (p.y > maxY) maxY = p.y;
      }
    }

    if (minX == double.infinity) return;

    final rect = Rect.fromLTRB(minX - 6, minY - 6, maxX + 6, maxY + 6);

    // Fond teinté
    final bgSelPaint = Paint()
      ..color = const Color(0xFF4F46E5).withValues(alpha: 0.12)
      ..style = PaintingStyle.fill;
    canvas.drawRect(rect, bgSelPaint);

    // Bordure violette
    final borderPaint = Paint()
      ..color = const Color(0xFF6366F1)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5;
    canvas.drawRect(rect, borderPaint);
  }

  void _drawSmoothStroke(Canvas canvas, StrokeModel stroke) {
    if (stroke.points.isEmpty) return;

    final isEraser = stroke.tool == 'eraser';
    final color = isEraser ? const Color(0xFFFDFBF7) : _parseHexColor(stroke.color);

    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round
      ..isAntiAlias = true
      ..filterQuality = FilterQuality.high
      ..strokeWidth = isEraser ? (stroke.width * 5.0) : stroke.width;

    final pts = stroke.points;

    if (pts.length == 1) {
      final dotPaint = Paint()
        ..color = color
        ..style = PaintingStyle.fill;
      canvas.drawCircle(Offset(pts.first.x, pts.first.y), (isEraser ? (stroke.width * 5.0) : stroke.width) / 2.0, dotPaint);
    } else if (pts.length == 2) {
      canvas.drawLine(Offset(pts[0].x, pts[0].y), Offset(pts[1].x, pts[1].y), paint);
    } else {
      final path = Path();
      path.moveTo(pts[0].x, pts[0].y);

      for (int i = 1; i < pts.length - 1; i++) {
        final p0 = pts[i];
        final p1 = pts[i + 1];

        // Lissage fluide par courbe quadratique (Bezier)
        final controlPoint = Offset(p0.x, p0.y);
        final endPoint = Offset((p0.x + p1.x) / 2.0, (p0.y + p1.y) / 2.0);

        path.quadraticBezierTo(controlPoint.dx, controlPoint.dy, endPoint.dx, endPoint.dy);
      }

      // Reliage au dernier point
      final lastPoint = pts.last;
      path.lineTo(lastPoint.x, lastPoint.y);

      canvas.drawPath(path, paint);
    }
  }

  Color _parseHexColor(String hexString) {
    try {
      final buffer = StringBuffer();
      if (hexString.length == 6 || hexString.length == 7) buffer.write('ff');
      buffer.write(hexString.replaceFirst('#', ''));
      return Color(int.parse(buffer.toString(), radix: 16));
    } catch (_) {
      return Colors.black;
    }
  }

  @override
  bool shouldRepaint(covariant NotebookPainter oldDelegate) => true;
}
