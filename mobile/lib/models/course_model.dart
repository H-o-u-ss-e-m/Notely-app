import 'stroke_model.dart';

class LessonModel {
  final String id;
  final String subjectId;
  final String title;
  final String updatedAt;
  final int pageCount;
  final List<NotebookPageModel> pages;

  LessonModel({
    required this.id,
    this.subjectId = '',
    required this.title,
    required this.updatedAt,
    this.pageCount = 1,
    this.pages = const [],
  });

  Map<String, dynamic> toJson() => {
        'id': id,
        'subjectId': subjectId,
        'title': title,
        'updatedAt': updatedAt,
        'pageCount': pageCount,
        'pages': pages.map((p) => p.toJson()).toList(),
      };

  factory LessonModel.fromJson(Map<String, dynamic> json) => LessonModel(
        id: json['id'] as String? ?? '',
        subjectId: json['subjectId'] as String? ?? '',
        title: json['title'] as String? ?? 'Cours sans titre',
        updatedAt: json['updatedAt'] as String? ?? '',
        pageCount: json['pageCount'] as int? ?? (json['pages'] as List? ?? []).length,
        pages: (json['pages'] as List? ?? [])
            .map((p) => NotebookPageModel.fromJson(p as Map<String, dynamic>))
            .toList(),
      );
}

class SubjectModel {
  final String id;
  final String name;
  final String color;
  final String description;
  final List<LessonModel> lessons;

  SubjectModel({
    required this.id,
    required this.name,
    required this.color,
    this.description = '',
    required this.lessons,
  });

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'color': color,
        'description': description,
        'lessons': lessons.map((l) => l.toJson()).toList(),
      };

  factory SubjectModel.fromJson(Map<String, dynamic> json) => SubjectModel(
        id: json['id'] as String? ?? '',
        name: json['name'] as String? ?? '',
        color: json['color'] as String? ?? '#1E40AF',
        description: json['description'] as String? ?? '',
        lessons: (json['lessons'] as List? ?? [])
            .map((l) => LessonModel.fromJson(l as Map<String, dynamic>))
            .toList(),
      );
}
