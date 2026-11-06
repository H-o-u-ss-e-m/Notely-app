import 'package:mobile/models/recognition_model.dart';

class StructuralElementModel {
  final int id;
  final String type; // 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'paragraph', 'diagram'
  String text;
  final double confidence;
  final bool calibrated;
  final double minWordConfidence;
  final List<WordModel> words;
  final List<String> alternatives;
  final String? thumbnail;
  final List<double> bbox;
  final String? imageBase64;
  final List<String> strokeIds;
  final int pageNumber;
  String? source;
  final String? strokeFingerprint;

  StructuralElementModel({
    required this.id,
    required this.type,
    required this.text,
    required this.confidence,
    this.calibrated = false,
    this.minWordConfidence = 1.0,
    this.words = const [],
    this.alternatives = const [],
    this.thumbnail,
    required this.bbox,
    this.imageBase64,
    required this.strokeIds,
    this.pageNumber = 1,
    this.source,
    this.strokeFingerprint,
  });

  factory StructuralElementModel.fromJson(Map<String, dynamic> json) => StructuralElementModel(
        id: json['id'] as int? ?? 0,
        type: json['type'] as String? ?? 'paragraph',
        text: json['text'] as String? ?? '',
        confidence: (json['confidence'] as num?)?.toDouble() ?? 1.0,
        calibrated: json['calibrated'] as bool? ?? false,
        minWordConfidence: (json['min_word_confidence'] as num?)?.toDouble() ?? 1.0,
        words: (json['words'] as List? ?? [])
            .map((w) => WordModel.fromJson(w as Map<String, dynamic>))
            .toList(),
        alternatives: List<String>.from(json['alternatives'] ?? []),
        thumbnail: json['thumbnail'] as String?,
        bbox: (json['bbox'] as List? ?? []).map((e) => (e as num).toDouble()).toList(),
        imageBase64: json['image_base64'] as String?,
        strokeIds: (json['stroke_ids'] as List? ?? []).map((e) => e.toString()).toList(),
        pageNumber: json['pageNumber'] as int? ?? 1,
        source: json['source'] as String?,
        strokeFingerprint: json['stroke_fingerprint'] as String?,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'type': type,
        'text': text,
        'confidence': confidence,
        'calibrated': calibrated,
        'words': words.map((w) => {
              'index': w.index,
              'text': w.text,
              'confidence': w.confidence,
              'corrected': w.corrected,
              'original': w.original,
            }).toList(),
        'bbox': bbox,
        'thumbnail': thumbnail,
        'image_base64': imageBase64,
        'stroke_ids': strokeIds,
        'pageNumber': pageNumber,
      };
}

class StructuralHTRResponseModel {
  final bool success;
  final double processingTimeMs;
  final String subject;
  final String lessonTitle;
  final List<StructuralElementModel> elements;
  final String fullMarkdown;
  final bool calibrated;
  final String language;

  StructuralHTRResponseModel({
    required this.success,
    required this.processingTimeMs,
    required this.subject,
    required this.lessonTitle,
    required this.elements,
    required this.fullMarkdown,
    this.calibrated = false,
    this.language = 'fr',
  });

  factory StructuralHTRResponseModel.fromJson(Map<String, dynamic> json) => StructuralHTRResponseModel(
        success: json['success'] as bool? ?? true,
        processingTimeMs: (json['processingTimeMs'] as num?)?.toDouble() ?? 0.0,
        subject: json['subject'] as String? ?? 'Cours Manuscrit',
        lessonTitle: json['lessonTitle'] as String? ?? 'Chapitre 1',
        elements: (json['elements'] as List? ?? [])
            .map((e) => StructuralElementModel.fromJson(e as Map<String, dynamic>))
            .toList(),
        fullMarkdown: json['fullMarkdown'] as String? ?? '',
        calibrated: json['calibrated'] as bool? ?? false,
        language: json['language'] as String? ?? 'fr',
      );
}
