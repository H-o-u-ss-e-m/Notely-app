"""Constantes de limites (anti-DoS). Valeurs issues du plan SEC-5."""

MAX_STROKES_PER_REQUEST = 5_000
MAX_POINTS_PER_STROKE = 10_000  # plan: 2_000 ; relevé tant que le client Flutter ne simplifie pas (RDP)
MAX_TOTAL_POINTS = 200_000
MAX_PAGES_PER_LESSON = 300
MAX_PAGES_PER_REQUEST = 300
MAX_CANVAS_DIM = 4_000
MAX_TEXT_CORRECTION_LEN = 2_000
MAX_ID_LEN = 255  # = taille de la colonne strokes.id
