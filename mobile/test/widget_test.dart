import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/main.dart';
import 'package:mobile/models/structural_model.dart';

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
}
