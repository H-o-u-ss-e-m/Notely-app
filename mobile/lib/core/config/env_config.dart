import 'package:flutter/foundation.dart';

class EnvConfig {
  /// URL définie au build via --dart-define=API_URL=https://...
  static const String _customUrl = String.fromEnvironment('API_URL', defaultValue: '');

  /// URL choisie dynamiquement depuis l'écran de paramètres ou ngrok
  static String? _runtimeUrl;

  /// URL de base calculée automatiquement selon la plateforme
  static String get baseUrl {
    // 1. Priorité : URL définie au runtime (paramètres de l'app)
    if (_runtimeUrl != null && _runtimeUrl!.isNotEmpty) {
      return _runtimeUrl!;
    }

    // 2. URL fournie au build via --dart-define
    if (_customUrl.isNotEmpty) {
      final url = _customUrl.endsWith('/api/v1') ? _customUrl : '$_customUrl/api/v1';
      return url;
    }

    // 3. Auto-détection selon la plateforme
    if (kIsWeb) {
      // Flutter Web (Edge, Chrome) → le backend tourne sur la même machine
      return 'http://127.0.0.1:8000/api/v1';
    }

    // Flutter natif (Android, iOS)
    if (defaultTargetPlatform == TargetPlatform.android) {
      // Émulateur Android : 10.0.2.2 = localhost du PC
      // Téléphone physique : nécessite l'IP du PC ou ngrok
      return 'http://10.0.2.2:8000/api/v1';
    }

    // iOS Simulator / Desktop
    return 'http://127.0.0.1:8000/api/v1';
  }

  /// Permet de changer l'URL dynamiquement (paramètres de l'app, URL ngrok, IP locale)
  static void setRuntimeUrl(String url) {
    if (url.trim().isEmpty) {
      _runtimeUrl = null;
      return;
    }
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      url = 'http://$url';
    }
    if (!url.endsWith('/api/v1')) {
      url = '$url/api/v1';
    }
    _runtimeUrl = url;
  }

  /// Réinitialise l'URL runtime (retour à l'auto-détection)
  static void clearRuntimeUrl() {
    _runtimeUrl = null;
  }

  /// URL effective (pour compatibilité)
  static String get effectiveBaseUrl => baseUrl;
}
