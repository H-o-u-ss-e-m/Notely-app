class PointModel {
  final double x;
  final double y;
  final double timestamp;
  final double pressure;

  PointModel({
    required this.x,
    required this.y,
    required this.timestamp,
    this.pressure = 1.0,
  });

  Map<String, dynamic> toJson() => {
        'x': x,
        'y': y,
        'timestamp': timestamp,
        'pressure': pressure,
      };

  factory PointModel.fromJson(Map<String, dynamic> json) => PointModel(
        x: (json['x'] as num).toDouble(),
        y: (json['y'] as num).toDouble(),
        timestamp: (json['timestamp'] as num?)?.toDouble() ?? 0.0,
        pressure: (json['pressure'] as num?)?.toDouble() ?? 1.0,
      );
}

class BoundingBoxModel {
  final double xMin;
  final double yMin;
  final double xMax;
  final double yMax;

  BoundingBoxModel({
    required this.xMin,
    required this.yMin,
    required this.xMax,
    required this.yMax,
  });

  Map<String, dynamic> toJson() => {
        'xMin': xMin,
        'yMin': yMin,
        'xMax': xMax,
        'yMax': yMax,
      };

  factory BoundingBoxModel.fromJson(Map<String, dynamic> json) => BoundingBoxModel(
        xMin: (json['xMin'] as num).toDouble(),
        yMin: (json['yMin'] as num).toDouble(),
        xMax: (json['xMax'] as num).toDouble(),
        yMax: (json['yMax'] as num).toDouble(),
      );
}

class StrokeModel {
  final String id;
  final List<PointModel> points;
  final double startTime;
  final double endTime;
  final String color;
  final double width;
  final String tool;
  final String contentType; // 'normal', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'
  final String pointerType;
  final BoundingBoxModel bbox;

  StrokeModel({
    required this.id,
    required this.points,
    required this.startTime,
    required this.endTime,
    this.color = '#000000',
    this.width = 3.0,
    this.tool = 'pen',
    this.contentType = 'normal',
    this.pointerType = 'touch',
    required this.bbox,
  });

  Map<String, dynamic> toJson() => {
        'id': id,
        'points': points.map((p) => p.toJson()).toList(),
        'startTime': startTime,
        'endTime': endTime,
        'color': color,
        'width': width,
        'tool': tool,
        'contentType': contentType,
        'pointerType': pointerType,
        'bbox': bbox.toJson(),
      };

  factory StrokeModel.fromJson(Map<String, dynamic> json) {
    final pts = (json['points'] as List? ?? []).map((p) => PointModel.fromJson(p as Map<String, dynamic>)).toList();
    
    // Auto calculate bbox if missing
    BoundingBoxModel bboxVal;
    if (json['bbox'] != null) {
      bboxVal = BoundingBoxModel.fromJson(json['bbox'] as Map<String, dynamic>);
    } else if (pts.isNotEmpty) {
      double minX = pts.first.x, maxX = pts.first.x;
      double minY = pts.first.y, maxY = pts.first.y;
      for (final pt in pts) {
        if (pt.x < minX) minX = pt.x;
        if (pt.x > maxX) maxX = pt.x;
        if (pt.y < minY) minY = pt.y;
        if (pt.y > maxY) maxY = pt.y;
      }
      bboxVal = BoundingBoxModel(xMin: minX, yMin: minY, xMax: maxX, yMax: maxY);
    } else {
      bboxVal = BoundingBoxModel(xMin: 0, yMin: 0, xMax: 0, yMax: 0);
    }

    return StrokeModel(
      id: json['id'] as String? ?? 'strk-${DateTime.now().millisecondsSinceEpoch}',
      points: pts,
      startTime: (json['startTime'] as num?)?.toDouble() ?? 0.0,
      endTime: (json['endTime'] as num?)?.toDouble() ?? 0.0,
      color: json['color'] as String? ?? '#000000',
      width: (json['width'] as num?)?.toDouble() ?? 3.0,
      tool: json['tool'] as String? ?? 'pen',
      contentType: json['contentType'] as String? ?? 'normal',
      pointerType: json['pointerType'] as String? ?? 'touch',
      bbox: bboxVal,
    );
  }
}

class NotebookPageModel {
  final String id;
  int pageNumber;
  final List<StrokeModel> strokes;
  final List<StrokeModel> redoStack;

  NotebookPageModel({
    required this.id,
    required this.pageNumber,
    required this.strokes,
    required this.redoStack,
  });

  Map<String, dynamic> toJson() => {
        'id': id,
        'pageNumber': pageNumber,
        'strokes': strokes.map((s) => s.toJson()).toList(),
        'redoStack': redoStack.map((s) => s.toJson()).toList(),
      };

  factory NotebookPageModel.fromJson(Map<String, dynamic> json) => NotebookPageModel(
        id: json['id'] as String? ?? 'p-${json['pageNumber'] ?? 1}',
        pageNumber: json['pageNumber'] as int? ?? 1,
        strokes: (json['strokes'] as List? ?? [])
            .map((s) => StrokeModel.fromJson(s as Map<String, dynamic>))
            .toList(),
        redoStack: (json['redoStack'] as List? ?? [])
            .map((s) => StrokeModel.fromJson(s as Map<String, dynamic>))
            .toList(),
      );
}
