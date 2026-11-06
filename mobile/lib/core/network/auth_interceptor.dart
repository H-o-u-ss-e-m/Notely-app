import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../config/env_config.dart';

/// Stockage sécurisé (Keystore Android / Keychain iOS) avec repli mémoire
/// automatique pour les tests unitaires sans canal natif (Plan v2 §5.8 — FLT-2).
class SecureTokenStore {
  final FlutterSecureStorage _secureStorage;
  final Map<String, String> _memoryFallback = {};

  SecureTokenStore([FlutterSecureStorage? storage])
      : _secureStorage = storage ?? const FlutterSecureStorage();

  Future<String?> read({required String key}) async {
    try {
      final val = await _secureStorage.read(key: key);
      if (val != null) return val;
    } catch (_) {}
    return _memoryFallback[key];
  }

  Future<void> write({required String key, required String? value}) async {
    if (value == null) {
      await delete(key: key);
      return;
    }
    _memoryFallback[key] = value;
    try {
      await _secureStorage.write(key: key, value: value);
    } catch (_) {}
  }

  Future<void> delete({required String key}) async {
    _memoryFallback.remove(key);
    try {
      await _secureStorage.delete(key: key);
    } catch (_) {}
  }

  Future<void> deleteAll() async {
    _memoryFallback.clear();
    try {
      await _secureStorage.deleteAll();
    } catch (_) {}
  }
}

/// Intercepteur Dio sérialisé (`QueuedInterceptorsWrapper`) qui rafraîchit
/// automatiquement l'access token sur HTTP 401 et rejoue la requête (Plan v2 §5.8).
class AuthInterceptor extends QueuedInterceptorsWrapper {
  final Dio dio;
  final SecureTokenStore storage;
  final Future<void> Function() onLogout;
  final void Function(String access, String? refresh)? onTokensUpdated;

  AuthInterceptor({
    required this.dio,
    required this.storage,
    required this.onLogout,
    this.onTokensUpdated,
  });

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) async {
    if (!options.path.contains('/auth/login') &&
        !options.path.contains('/auth/register') &&
        !options.path.contains('/auth/refresh')) {
      final access = await storage.read(key: 'access');
      if (access != null && access.isNotEmpty) {
        options.headers['Authorization'] = 'Bearer $access';
      }
    }
    handler.next(options);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) async {
    if (err.response?.statusCode == 401 && !err.requestOptions.path.contains('/auth/')) {
      try {
        final refresh = await storage.read(key: 'refresh');
        if (refresh == null || refresh.isEmpty) {
          await onLogout();
          return handler.next(err);
        }

        // Requête de refresh dédiée (sans repasser dans l'intercepteur d'erreur)
        final refreshDio = Dio(BaseOptions(baseUrl: EnvConfig.baseUrl));
        refreshDio.httpClientAdapter = dio.httpClientAdapter;
        final r = await refreshDio.post(
          '${EnvConfig.baseUrl}/auth/refresh',
          data: {'refresh_token': refresh, 'refreshToken': refresh},
        );

        final data = r.data is Map ? Map<String, dynamic>.from(r.data as Map) : <String, dynamic>{};
        final newAccess = (data['access_token'] ?? data['accessToken']) as String?;
        final newRefresh = (data['refresh_token'] ?? data['refreshToken']) as String?;

        if (newAccess != null && newAccess.isNotEmpty) {
          await storage.write(key: 'access', value: newAccess);
          if (newRefresh != null && newRefresh.isNotEmpty) {
            await storage.write(key: 'refresh', value: newRefresh);
          }
          onTokensUpdated?.call(newAccess, newRefresh);
          err.requestOptions.headers['Authorization'] = 'Bearer $newAccess';
          return handler.resolve(await dio.fetch(err.requestOptions));
        }
      } catch (_) {
        await onLogout();
      }
    }
    handler.next(err);
  }
}
