import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../config/env_config.dart';
import '../../models/stroke_model.dart';
import '../../models/recognition_model.dart';
import '../../models/structural_model.dart';
import '../../models/course_model.dart';

class ApiClient {
  static String? authToken;
  static String? refreshToken;
  static Map<String, dynamic>? currentUser;

  // Timer de refresh automatique du token (55 min avant l'expiration de 60 min)
  static Timer? _refreshTimer;
  static const Duration _refreshBefore = Duration(minutes: 55);

  // ── Session persistence ─────────────────────────────────────────────────

  static File get _sessionFile {
    final tempDir = Directory.systemTemp;
    return File('${tempDir.path}/notely_user_session.json');
  }

  static Future<void> saveSession(String token, String? refresh, Map<String, dynamic>? user) async {
    authToken    = token;
    refreshToken = refresh;
    currentUser  = user;
    if (!kIsWeb) {
      try {
        await _sessionFile.writeAsString(
          jsonEncode({'token': token, 'refresh': refresh, 'user': user}),
          flush: true,
        );
      } catch (e) {
        debugPrint('Erreur saveSession: $e');
      }
    }
    // Planifier le refresh automatique
    _scheduleTokenRefresh();
  }

  static Future<void> loadSession() async {
    if (kIsWeb) return;
    try {
      final file = _sessionFile;
      if (await file.exists()) {
        final data = jsonDecode(await file.readAsString());
        authToken    = data['token'] as String?;
        refreshToken = data['refresh'] as String?;
        currentUser  = data['user'] as Map<String, dynamic>?;
        if (authToken != null) _scheduleTokenRefresh();
      }
    } catch (e) {
      debugPrint('Erreur loadSession: $e');
    }
  }

  static Future<void> clearSession() async {
    _refreshTimer?.cancel();
    _refreshTimer = null;
    authToken     = null;
    refreshToken  = null;
    currentUser   = null;
    if (!kIsWeb) {
      try {
        if (await _sessionFile.exists()) await _sessionFile.delete();
      } catch (_) {}
    }
  }

  // ── Auto Refresh Token ──────────────────────────────────────────────────

  static void _scheduleTokenRefresh() {
    _refreshTimer?.cancel();
    if (refreshToken == null) return;
    _refreshTimer = Timer(_refreshBefore, () async {
      await _doRefresh();
    });
  }

  static Future<void> _doRefresh() async {
    if (refreshToken == null) return;
    try {
      final url = Uri.parse('${EnvConfig.baseUrl}/auth/refresh');
      final response = await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'refresh_token': refreshToken}),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final newAccess  = data['access_token'] as String?;
        final newRefresh = data['refresh_token'] as String?;
        final user       = data['user'] as Map<String, dynamic>?;
        if (newAccess != null) {
          await saveSession(newAccess, newRefresh ?? refreshToken, user ?? currentUser);
          debugPrint('[ApiClient] Token rafraîchi automatiquement.');
        }
      } else {
        debugPrint('[ApiClient] Refresh échoué (${response.statusCode}) — session expirée.');
        await clearSession();
      }
    } catch (e) {
      debugPrint('[ApiClient] Erreur refresh token: $e');
    }
  }

  // ── Headers ─────────────────────────────────────────────────────────────

  static Map<String, String> _getHeaders() {
    final headers = {'Content-Type': 'application/json'};
    if (authToken != null && authToken!.isNotEmpty) {
      headers['Authorization'] = 'Bearer $authToken';
    }
    return headers;
  }

  // ── Auth ────────────────────────────────────────────────────────────────

  static Future<Map<String, dynamic>> login(String email, String password) async {
    final url = Uri.parse('${EnvConfig.baseUrl}/auth/login');
    final response = await http.post(
      url,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email, 'password': password}),
    ).timeout(const Duration(seconds: 10));

    if (response.statusCode == 200) {
      final jsonMap = jsonDecode(response.body);
      final token   = jsonMap['access_token'] as String?;
      final refresh = jsonMap['refresh_token'] as String?;
      final user    = jsonMap['user'] as Map<String, dynamic>?;
      if (token != null) {
        await saveSession(token, refresh, user);
      }
      return jsonMap;
    } else {
      final err = jsonDecode(response.body);
      throw Exception(err['detail'] ?? 'Identifiants invalides');
    }
  }

  static Future<Map<String, dynamic>> register(String email, String password, String name) async {
    final url = Uri.parse('${EnvConfig.baseUrl}/auth/register');
    final response = await http.post(
      url,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'email': email,
        'password': password,
        'full_name': name,
        'role': 'student'
      }),
    ).timeout(const Duration(seconds: 10));

    if (response.statusCode == 200 || response.statusCode == 201) {
      final jsonMap = jsonDecode(response.body);
      final token   = jsonMap['access_token'] as String?;
      final refresh = jsonMap['refresh_token'] as String?;
      final user    = jsonMap['user'] as Map<String, dynamic>?;
      if (token != null) {
        await saveSession(token, refresh, user);
      }
      return jsonMap;
    } else {
      final err = jsonDecode(response.body);
      throw Exception(err['detail'] ?? "Échec de l'inscription");
    }
  }

  static Future<void> logout() async {
    if (refreshToken != null) {
      try {
        final url = Uri.parse('${EnvConfig.baseUrl}/auth/logout');
        await http.post(
          url,
          headers: _getHeaders(),
          body: jsonEncode({'refresh_token': refreshToken}),
        ).timeout(const Duration(seconds: 5));
      } catch (_) {}
    }
    await clearSession();
  }

  // ── Recognition ─────────────────────────────────────────────────────────

  static Future<RecognitionResponseModel> recognizeStrokes({
    required List<StrokeModel> strokes,
    required double canvasWidth,
    required double canvasHeight,
    String language = 'fr',
  }) async {
    await loadSession();
    final url = Uri.parse('${EnvConfig.baseUrl}/recognition');
    final body = jsonEncode({
      'strokes': strokes.map((s) => s.toJson()).toList(),
      'options': {'debug': true, 'deskew': true, 'language': language},
      'canvasWidth': canvasWidth,
      'canvasHeight': canvasHeight,
    });
    final response = await http.post(url, headers: _getHeaders(), body: body)
        .timeout(const Duration(seconds: 15));
    if (response.statusCode == 200) {
      return RecognitionResponseModel.fromJson(jsonDecode(response.body));
    } else {
      throw Exception('Erreur API (${response.statusCode}): ${response.body}');
    }
  }

  static Future<StructuralHTRResponseModel> recognizeStructuralPages({
    required List<NotebookPageModel> pages,
    required double canvasWidth,
    required double canvasHeight,
    String subject = "Cours Manuscrit",
    String lessonTitle = "Chapitre 1",
    String language = "fr",
  }) async {
    await loadSession();
    final url = Uri.parse('${EnvConfig.baseUrl}/structural-htr');
    final pagePayload = pages.map((p) => {
      'pageNumber': p.pageNumber,
      'strokes': p.strokes.map((s) => s.toJson()).toList(),
      'width': canvasWidth,
      'height': canvasHeight,
    }).toList();
    final body = jsonEncode({
      'pages': pagePayload,
      'canvasWidth': canvasWidth,
      'canvasHeight': canvasHeight,
      'subject': subject,
      'lessonTitle': lessonTitle,
      'language': language,
    });
    final response = await http.post(url, headers: _getHeaders(), body: body)
        .timeout(const Duration(seconds: 35));
    if (response.statusCode == 200) {
      return StructuralHTRResponseModel.fromJson(jsonDecode(response.body));
    } else {
      throw Exception('Erreur HTR (${response.statusCode}): ${response.body}');
    }
  }

  // ── PDF Export ───────────────────────────────────────────────────────────

  static Future<Uint8List> exportPdf({
    required String subject,
    required String lessonTitle,
    required List<StructuralElementModel> elements,
  }) async {
    final url = Uri.parse('${EnvConfig.baseUrl}/export-pdf');
    final body = jsonEncode({
      'subject': subject,
      'lessonTitle': lessonTitle,
      'elements': elements.map((e) => e.toJson()).toList(),
    });
    final response = await http.post(url, headers: _getHeaders(), body: body)
        .timeout(const Duration(seconds: 25));
    if (response.statusCode == 200) return response.bodyBytes;
    throw Exception('Erreur PDF (${response.statusCode})');
  }

  static Future<Uint8List> exportRawPdfPages({
    required List<NotebookPageModel> pages,
    required double canvasWidth,
    required double canvasHeight,
    String subject = "Cours Manuscrit",
    String lessonTitle = "Chapitre 1",
  }) async {
    final url = Uri.parse('${EnvConfig.baseUrl}/export-pdf-raw');
    final pagePayload = pages.map((p) => {
      'pageNumber': p.pageNumber,
      'strokes': p.strokes.map((s) => s.toJson()).toList(),
      'width': canvasWidth,
      'height': canvasHeight,
    }).toList();
    final body = jsonEncode({
      'pages': pagePayload,
      'canvasWidth': canvasWidth,
      'canvasHeight': canvasHeight,
      'subject': subject,
      'lessonTitle': lessonTitle,
    });
    final response = await http.post(url, headers: _getHeaders(), body: body)
        .timeout(const Duration(seconds: 30));
    if (response.statusCode == 200) return response.bodyBytes;
    throw Exception('Erreur PDF brut (${response.statusCode})');
  }

  // ── Courses ──────────────────────────────────────────────────────────────

  static Future<SubjectModel?> createSubject(String name, String color) async {
    try {
      final url = Uri.parse('${EnvConfig.baseUrl}/courses/subjects');
      final response = await http.post(url, headers: _getHeaders(),
          body: jsonEncode({'name': name, 'color': color}))
          .timeout(const Duration(seconds: 8));
      if (response.statusCode == 200 || response.statusCode == 201) {
        return SubjectModel.fromJson(jsonDecode(response.body));
      }
    } catch (e) {
      debugPrint('Erreur createSubject: $e');
    }
    return null;
  }

  static Future<LessonModel?> createLesson(String title, String subjectId) async {
    try {
      final url = Uri.parse('${EnvConfig.baseUrl}/courses/lessons');
      final response = await http.post(url, headers: _getHeaders(),
          body: jsonEncode({'title': title, 'subjectId': subjectId}))
          .timeout(const Duration(seconds: 8));
      if (response.statusCode == 200 || response.statusCode == 201) {
        return LessonModel.fromJson(jsonDecode(response.body));
      }
    } catch (e) {
      debugPrint('Erreur createLesson: $e');
    }
    return null;
  }

  static Future<LessonModel?> getLesson(String subjectId, String lessonId) async {
    try {
      final url = Uri.parse('${EnvConfig.baseUrl}/courses/subjects/$subjectId/lessons/$lessonId');
      final response = await http.get(url, headers: _getHeaders())
          .timeout(const Duration(seconds: 10));
      if (response.statusCode == 200) {
        return LessonModel.fromJson(jsonDecode(response.body));
      }
    } catch (e) {
      debugPrint('Erreur getLesson: $e');
    }
    return null;
  }

  static Future<bool> updateLesson(
      String subjectId, String lessonId, String title, List<NotebookPageModel> pages) async {
    try {
      final url = Uri.parse('${EnvConfig.baseUrl}/courses/subjects/$subjectId/lessons/$lessonId');
      final pagePayload = pages.map((p) => {
        'id': p.id,
        'pageNumber': p.pageNumber,
        'strokes': p.strokes.map((s) => s.toJson()).toList(),
      }).toList();
      final response = await http.put(url, headers: _getHeaders(),
          body: jsonEncode({'title': title, 'pages': pagePayload, 'pageCount': pages.length}))
          .timeout(const Duration(seconds: 12));
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('Erreur updateLesson: $e');
      return false;
    }
  }

  static Future<List<SubjectModel>> fetchSubjects() async {
    try {
      final url = Uri.parse('${EnvConfig.baseUrl}/courses/subjects');
      final response = await http.get(url, headers: _getHeaders())
          .timeout(const Duration(seconds: 8));
      if (response.statusCode == 200) {
        final List list = jsonDecode(response.body);
        return list.map((item) => SubjectModel.fromJson(item as Map<String, dynamic>)).toList();
      }
    } catch (e) {
      debugPrint('Erreur fetchSubjects: $e');
    }
    return [];
  }

  static final List<Map<String, dynamic>> _offlineFeedbackQueue = [];

  static Future<bool> sendFeedback(Map<String, dynamic> feedbackData) async {
    try {
      final url = Uri.parse('${EnvConfig.baseUrl}/ocr/feedback');
      final response = await http
          .post(url, headers: _getHeaders(), body: jsonEncode(feedbackData))
          .timeout(const Duration(seconds: 8));
      if (response.statusCode == 200 || response.statusCode == 201) {
        // Envoi réussi, essayer de vider la file hors ligne
        flushOfflineFeedback();
        return true;
      }
    } catch (e) {
      debugPrint('[ApiClient] Échec envoi feedback: $e. Enfilé hors ligne.');
      _offlineFeedbackQueue.add(feedbackData);
    }
    return false;
  }

  static Future<void> flushOfflineFeedback() async {
    if (_offlineFeedbackQueue.isEmpty) return;
    final copy = List<Map<String, dynamic>>.from(_offlineFeedbackQueue);
    _offlineFeedbackQueue.clear();
    for (final item in copy) {
      try {
        final url = Uri.parse('${EnvConfig.baseUrl}/ocr/feedback');
        await http
            .post(url, headers: _getHeaders(), body: jsonEncode(item))
            .timeout(const Duration(seconds: 5));
      } catch (_) {
        _offlineFeedbackQueue.add(item);
        break;
      }
    }
  }

  static Future<Map<String, dynamic>> checkHealth() async {
    final url = Uri.parse('${EnvConfig.baseUrl}/health');
    final response = await http.get(url, headers: _getHeaders())
        .timeout(const Duration(seconds: 4));
    if (response.statusCode == 200) return jsonDecode(response.body);
    throw Exception('Backend inaccessible');
  }
}
