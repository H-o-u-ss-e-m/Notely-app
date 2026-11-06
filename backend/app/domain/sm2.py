"""
Algorithme de répétition espacée SM-2 (SuperMemo-2) et génération de cartes
à partir des éléments structurés issus de l'OCR (Chantier 9 / fonctionnalité « Cartes de révision »).

Fonctions pures, sans accès base de données : faciles à tester.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Tuple

MIN_EASE = 1.3
DEFAULT_EASE = 2.5


@dataclass(frozen=True)
class CardState:
    ease_factor: float = DEFAULT_EASE
    interval_days: int = 0
    repetitions: int = 0


def sm2_update(state: CardState, quality: int) -> CardState:
    """
    Applique une révision de qualité `quality` (0 = trou noir … 5 = parfait).

    - qualité < 3 : échec → répétitions remises à 0, intervalle = 1 jour (facteur de facilité inchangé,
      conformément à l'algorithme SM-2 d'origine) ;
    - qualité ≥ 3 : 1re réussite → 1 jour, 2e → 6 jours, ensuite intervalle × facteur de facilité ;
      le facteur est mis à jour puis borné à 1,3 minimum.
    """
    if not 0 <= quality <= 5:
        raise ValueError("quality doit être compris entre 0 et 5")

    if quality < 3:
        return CardState(ease_factor=state.ease_factor, interval_days=1, repetitions=0)

    if state.repetitions == 0:
        interval = 1
    elif state.repetitions == 1:
        interval = 6
    else:
        interval = max(1, round(state.interval_days * state.ease_factor))

    ease = state.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    ease = max(MIN_EASE, round(ease, 4))
    return CardState(ease_factor=ease, interval_days=interval, repetitions=state.repetitions + 1)


def next_due(now: datetime, interval_days: int) -> datetime:
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now + timedelta(days=interval_days)


_HEADING_TYPES = {"h1", "h2", "h3", "h4", "h5", "h6"}


def generate_cards_from_elements(elements: Iterable[dict], max_back_chars: int = 600) -> List[Tuple[str, str]]:
    """
    Transforme la structure d'un cours en paires (question, réponse) :
    chaque titre (h1–h6) devient la face avant, les paragraphes qui le suivent
    (jusqu'au titre suivant) forment la face arrière. Les schémas sont ignorés ;
    un titre sans contenu ne produit aucune carte.
    """
    cards: List[Tuple[str, str]] = []
    front = None
    body: List[str] = []

    def flush():
        if front and body:
            back = " ".join(body).strip()
            if back:
                cards.append((front, back[:max_back_chars]))

    for el in elements:
        etype = (el.get("type") or "").lower()
        text = (el.get("text") or "").strip()
        if etype in _HEADING_TYPES:
            flush()
            front, body = (text or None), []
        elif etype == "paragraph" and front and text:
            body.append(text)
    flush()
    return cards
