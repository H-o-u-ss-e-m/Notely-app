import 'package:flutter/material.dart';
import '../../../models/stroke_model.dart';
import '../../../models/recognition_model.dart';

class NotebookPainter extends CustomPainter {
  final List<StrokeModel> strokes;
  final StrokeModel? currentStroke;
  final List<LineRecognitionModel>? debugLines;
  final bool showGrid;

  NotebookPainter({
    required this.strokes,
    this.currentStroke,
    this.debugLines,
    this.showGrid = true,
  });

  @override
  void paint(Canvas canvas, Size size) {
    // 1. Fond papier cahier
    final bgPaint = Paint()..color = const Color(0xFFFDFBF7);
    canvas.drawRect(Rect.fromLTWH(0, 0, size.width, size.height), bgPaint);

    // 2. Lignes de cahier + marge rouge classique
    if (showGrid) {
      final linePaint = Paint()
        ..color = const Color(0xFFE5E7EB)
        ..strokeWidth = 1.0;

      for (double y = 40; y < size.height; y += 32) {
        canvas.drawLine(Offset(0, y), Offset(size.width, y), linePaint);
      }

      // Marge verticale rouge à gauche
      final marginPaint = Paint()
        ..color = const Color(0xFFFCA5A5)
        ..strokeWidth = 1.5;
      canvas.drawLine(const Offset(40, 0), Offset(40, size.height), marginPaint);
    }

    // 3. Dessiner les strokes complétés
    for (final stroke in strokes) {
      _drawSmoothStroke(canvas, stroke);
    }

    // 4. Dessiner le stroke en cours d'écriture
    if (currentStroke != null) {
      _drawSmoothStroke(canvas, currentStroke!);
    }

    // 5. Overlay de segmentation debug (Bounding Boxes)
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
