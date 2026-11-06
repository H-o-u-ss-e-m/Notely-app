import 'package:flutter/material.dart';

enum SaveState { saved, saving, dirty, error }

class SaveStatusChip extends StatelessWidget {
  final SaveState status;
  final String? lastSavedTime;
  final String? errorMessage;

  const SaveStatusChip({
    super.key,
    required this.status,
    this.lastSavedTime,
    this.errorMessage,
  });

  @override
  Widget build(BuildContext context) {
    Color bg;
    Color border;
    Color fg;
    String text;
    String tooltip;

    switch (status) {
      case SaveState.saved:
        bg = const Color(0xFF16A34A).withValues(alpha: 0.15);
        border = const Color(0xFF16A34A).withValues(alpha: 0.4);
        fg = const Color(0xFF4ADE80);
        text = (lastSavedTime != null && lastSavedTime!.isNotEmpty)
            ? 'Enregistré ($lastSavedTime)'
            : 'Enregistré';
        tooltip = 'Toutes les modifications sont enregistrées sur le serveur.';
        break;

      case SaveState.saving:
        bg = const Color(0xFF2563EB).withValues(alpha: 0.15);
        border = const Color(0xFF3B82F6).withValues(alpha: 0.4);
        fg = const Color(0xFF60A5FA);
        text = 'Enregistrement…';
        tooltip = 'Synchronisation des modifications avec le serveur en cours…';
        break;

      case SaveState.dirty:
        bg = const Color(0xFFD97706).withValues(alpha: 0.15);
        border = const Color(0xFFF59E0B).withValues(alpha: 0.4);
        fg = const Color(0xFFFBBF24);
        text = 'Modifications non enregistrées';
        tooltip = 'Des tracés sont en mémoire locale et seront synchronisés automatiquement.';
        break;

      case SaveState.error:
        bg = const Color(0xFFDC2626).withValues(alpha: 0.15);
        border = const Color(0xFFEF4444).withValues(alpha: 0.4);
        fg = const Color(0xFFF87171);
        text = 'Échec de l\'enregistrement';
        tooltip = errorMessage ?? 'Impossible de contacter le serveur. Les données restent en local.';
        break;
    }

    return Tooltip(
      message: tooltip,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: bg,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: border, width: 1),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (status == SaveState.saving)
              SizedBox(
                width: 8,
                height: 8,
                child: CircularProgressIndicator(
                  strokeWidth: 1.5,
                  valueColor: AlwaysStoppedAnimation<Color>(fg),
                ),
              )
            else
              Container(
                width: 7,
                height: 7,
                decoration: BoxDecoration(color: fg, shape: BoxShape.circle),
              ),
            const SizedBox(width: 5),
            Text(
              text,
              style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w600,
                color: fg,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
