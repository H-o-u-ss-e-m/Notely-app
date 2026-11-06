class WordModel {
  final int index;
  String text;
  final double confidence;
  final bool calibrated;
  final List<String> alternatives;
  final List<double>? bbox;
  bool corrected;
  String? original;

  WordModel({
    required this.index,
    required this.text,
    required this.confidence,
    this.calibrated = false,
    this.alternatives = const [],
    this.bbox,
    this.corrected = false,
    this.original,
  });

  factory WordModel.fromJson(Map<String, dynamic> json) => WordModel(
        index: json['index'] as int? ?? 0,
        text: json['text'] as String? ?? '',
        confidence: (json['confidence'] as num?)?.toDouble() ?? 0.0,
        calibrated: json['calibrated'] as bool? ?? false,
        alternatives: List<String>.from(json['alternatives'] ?? []),
        bbox: json['bbox'] != null
            ? (json['bbox'] as List).map((v) => (v as num).toDouble()).toList()
            : null,
        corrected: json['corrected'] as bool? ?? false,
        original: json['original'] as String?,
      );
}

class LineRecognitionModel {
  final int id;
  final List<String> strokeIds;
  final List<double> bbox;
  final String text;
  final double confidence;
  final bool calibrated;
  final double minWordConfidence;
  final List<WordModel> words;
  final List<String> alternatives;
  final String? thumbnail;
  final String? imageBase64;
  final String engine;
  final String modelVersion;

  LineRecognitionModel({
    required this.id,
    required this.strokeIds,
    required this.bbox,
    required this.text,
    required this.confidence,
    this.calibrated = false,
    this.minWordConfidence = 0.0,
    this.words = const [],
    this.alternatives = const [],
    this.thumbnail,
    this.imageBase64,
    this.engine = 'trocr',
    this.modelVersion = 'v3',
  });

  factory LineRecognitionModel.fromJson(Map<String, dynamic> json) => LineRecognitionModel(
        id: json['id'] as int? ?? 0,
        strokeIds: List<String>.from(json['stroke_ids'] ?? []),
        bbox: (json['bbox'] as List? ?? []).map((v) => (v as num).toDouble()).toList(),
        text: json['text'] as String? ?? '',
        confidence: (json['confidence'] as num?)?.toDouble() ?? 0.0,
        calibrated: json['calibrated'] as bool? ?? false,
        minWordConfidence: (json['min_word_confidence'] as num?)?.toDouble() ?? 0.0,
        words: (json['words'] as List? ?? [])
            .map((w) => WordModel.fromJson(w as Map<String, dynamic>))
            .toList(),
        alternatives: List<String>.from(json['alternatives'] ?? []),
        thumbnail: json['thumbnail'] as String?,
        imageBase64: json['image_base64'] as String?,
        engine: json['engine'] as String? ?? 'trocr',
        modelVersion: json['model_version'] as String? ?? 'v3',
      );
}

class RecognitionResponseModel {
  final bool success;
  final double processingTimeMs;
  final int lineCount;
  final List<LineRecognitionModel> lines;
  final String fullText;
  final String modelName;
  final String language;
  final bool calibrated;

  RecognitionResponseModel({
    required this.success,
    required this.processingTimeMs,
    required this.lineCount,
    required this.lines,
    required this.fullText,
    required this.modelName,
    this.language = 'fr',
    this.calibrated = false,
  });

  factory RecognitionResponseModel.fromJson(Map<String, dynamic> json) => RecognitionResponseModel(
        success: json['success'] as bool? ?? true,
        processingTimeMs: (json['processingTimeMs'] as num?)?.toDouble() ?? 0.0,
        lineCount: json['lineCount'] as int? ?? 0,
        lines: (json['lines'] as List? ?? []).map((l) => LineRecognitionModel.fromJson(l)).toList(),
        fullText: json['fullText'] as String? ?? json['full_text'] as String? ?? '',
        modelName: json['modelName'] as String? ?? json['model_name'] as String? ?? '',
        language: json['language'] as String? ?? 'fr',
        calibrated: json['calibrated'] as bool? ?? false,
      );
}
