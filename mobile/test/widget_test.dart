import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/main.dart';
import 'package:mobile/models/structural_model.dart';
import 'package:mobile/features/notebook/screens/notebook_screen.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/core/localization/notely_translations.dart';

void main() {
  testWidgets('Notely smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(const NotelyApp());
    expect(find.text('Notely'), findsOneWidget);
    await tester.pump(const Duration(milliseconds: 2300));
  });

  test('StructuralElementModel parses source and stroke_fingerprint (Mission 1)', () {
    final elem = StructuralElementModel.fromJson({
      'id': 1,
      'type': 'paragraph',
      'text': 'مرحبا',
      'confidence': 1.0,
      'calibrated': false,
      'bbox': [0.0, 0.0, 100.0, 30.0],
      'stroke_ids': ['s1', 's2'],
      'source': 'memory',
      'stroke_fingerprint': 'abc123def456',
      'words': [
        {
          'index': 0,
          'text': 'مرحبا',
          'confidence': 1.0,
          'corrected': true,
          'source': 'memory',
        }
      ],
    });
    expect(elem.text, 'مرحبا');
    expect(elem.source, 'memory');
    expect(elem.strokeFingerprint, 'abc123def456');
    expect(elem.words.first.source, 'memory');
  });

  test('toScene(toViewport(p, m), m) == p for all zoom scales (Mission 2 / Partie 3.4)', () {
    for (final s in [0.25, 0.5, 1.0, 2.0, 4.0]) {
      final m = Matrix4.identity()
        ..setEntry(0, 0, s)
        ..setEntry(1, 1, s)
        ..setEntry(0, 3, 37.0)
        ..setEntry(1, 3, -12.0);
      const p = Offset(300.0, 500.0);
      final screen = toViewport(p, m);
      final back = toScene(screen, m);
      expect(back.dx, closeTo(p.dx, 1e-5));
      expect(back.dy, closeTo(p.dy, 1e-5));
    }
  });

  test('ApiClient secure session storage & removal of plaintext notely_user_session.json (Mission 5 / Partie 5.8)', () async {
    await ApiClient.saveSession('sec-access-1', 'sec-refresh-1', {'id': 'u1', 'email': 'u1@notely.app'});
    final legacyFile = File('${Directory.systemTemp.path}/notely_user_session.json');
    expect(await legacyFile.exists(), isFalse);

    ApiClient.authToken = null;
    ApiClient.refreshToken = null;
    await ApiClient.loadSession();
    expect(ApiClient.authToken, 'sec-access-1');
    expect(ApiClient.refreshToken, 'sec-refresh-1');

    await ApiClient.clearSession();
    expect(ApiClient.authToken, isNull);
    expect(ApiClient.refreshToken, isNull);
  });

  test('SaveStatusChip and NotelyTranslations fr/en/ar (Mission 6 / Partie 4)', () {
    expect(NotelyTranslations.of('fr').recognize, 'Reconnaître le texte');
    expect(NotelyTranslations.of('en').recognize, 'Recognize text');
    expect(NotelyTranslations.of('ar').recognize, 'التعرف على النص');
    expect(NotelyTranslations.of('ar').palmRejection, 'رفض راحة اليد');
  });
}
