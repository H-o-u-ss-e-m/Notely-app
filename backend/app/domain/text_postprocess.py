"""
Module de post-traitement de texte par langue (ML-10 / §8.10).
Normalisation Unicode NFC, typographie, suggestions de lexique et restauration d'accents.
"""
import re
import unicodedata
from typing import List, Optional, Dict, Any
from app.ml.engines.base import LineOut, WordOut

# Dictionnaire de référence des mots français fréquemment privés d'accents par TrOCR
FRENCH_ACCENTS_MAP: Dict[str, str] = {
    "derivable": "dérivable",
    "derivables": "dérivables",
    "derivee": "dérivée",
    "derivees": "dérivées",
    "theoreme": "théorème",
    "theoremes": "théorèmes",
    "egal": "égal",
    "egale": "égale",
    "egaux": "égaux",
    "egalite": "égalité",
    "equation": "équation",
    "equations": "équations",
    "propriete": "propriété",
    "proprietes": "propriétés",
    "geometrie": "géométrie",
    "geometrique": "géométrique",
    "premiere": "première",
    "deuxieme": "deuxième",
    "troisieme": "troisième",
    "enonce": "énoncé",
    "enonces": "énoncés",
    "definition": "définition",
    "definitions": "définitions",
    "general": "général",
    "generale": "générale",
    "generaux": "généraux",
    "reel": "réel",
    "reelle": "réelle",
    "reels": "réels",
    "element": "élément",
    "elements": "éléments",
    "lineaire": "linéaire",
    "lineaires": "linéaires",
    "methode": "méthode",
    "methodes": "méthodes",
    "systeme": "système",
    "systemes": "systèmes",
    "periode": "période",
    "periodique": "périodique",
    "integral": "intégral",
    "integrale": "intégrale",
    "integrales": "intégrales",
    "numerique": "numérique",
    "numeriques": "numériques",
    "hypothese": "hypothèse",
    "hypotheses": "hypothèses",
    "abscisse": "abscisse",
    "verifie": "vérifie",
    "verifient": "vérifient",
    "considere": "considère",
    "apres": "après",
    "tres": "très",
    "deja": "déjà",
    "ou": "ou",  # ou / où ambigu, ne pas forcer
    "meme": "même",
    "memes": "mêmes",
    "etre": "être",
    "resume": "résumé",
    "etude": "étude",
    "etudes": "études",
}

# Ligatures courantes en français
FRENCH_LIGATURES: Dict[str, str] = {
    "coeur": "cœur",
    "soeur": "sœur",
    "noeud": "nœud",
    "voeu": "vœu",
    "oeuvre": "œuvre",
    "oeuf": "œuf",
}


def normalize_unicode(text: str) -> str:
    """Normalise en forme canonique NFC et uniformise les espaces."""
    text = unicodedata.normalize("NFC", text)
    # Remplacer espaces insécables multiples par espace simple
    text = re.sub(r"[\u00A0\u200B\u202F]", " ", text)
    # Réduire espaces multiples
    text = re.sub(r" +", " ", text)
    return text.strip()


def apply_french_typography(text: str) -> str:
    """Applique les règles typographiques françaises (espaces avant ponctuation haute, etc.)."""
    # Espace fine/insécable avant : ; ! ?
    text = re.sub(r"\s*([:;!?])", r" \1", text)
    # Guillemets français « mot »
    text = re.sub(r'"\s*([^"]+?)\s*"', r"« \1 »", text)
    # Ligatures
    for unlig, lig in FRENCH_LIGATURES.items():
        text = re.sub(rf"\b{unlig}\b", lig, text, flags=re.IGNORECASE)
    return text


def match_case(target: str, source: str) -> str:
    """Conserve la casse du mot d'origine pour le remplacement."""
    if source.isupper():
        return target.upper()
    if source.istitle():
        return target.capitalize()
    return target


def postprocess_line(
    line: LineOut,
    lang: str = "fr",
    user_subs: Optional[Dict[str, Any]] = None,
    auto_correct_accents: bool = True,
) -> LineOut:
    """
    Pipeline de post-traitement complet :
    1. Normalisation Unicode
    2. Remplacement par dictionnaire utilisateur calibré (ML-5 / §8.5.b)
    3. Restauration d'accents / suggestions
    4. Typographie par langue
    """
    # 1. Normalisation Unicode du texte global
    raw_text = normalize_unicode(line.text)

    # 2. Traitement des mots
    for word in line.words:
        w_clean = normalize_unicode(word.text)
        w_lower = w_clean.lower()

        # Dictionnaire utilisateur (ML-5 / §8.5.b)
        if user_subs and w_lower in user_subs:
            val = user_subs[w_lower]
            target_text = val[0] if isinstance(val, (tuple, list)) else val
            count = val[1] if isinstance(val, (tuple, list)) else 1
            conf_ceiling = 0.85
            # Appliquer si le modèle n'est pas déjà très confiant et si récurrent ou confiance basse
            if word.confidence < conf_ceiling and (count >= 2 or word.confidence < 0.6):
                word.original = word.text
                word.text = match_case(target_text, word.text)
                word.corrected = True
                continue

        # Français : détection et suggestions d'accents
        if lang == "fr":
            if w_lower in FRENCH_ACCENTS_MAP:
                accented = FRENCH_ACCENTS_MAP[w_lower]
                # Conserver la casse (majuscule initiale si présente)
                if w_clean.istitle():
                    accented = accented.capitalize()
                elif w_clean.isupper():
                    accented = accented.upper()

                if accented not in word.alternatives:
                    word.alternatives.insert(0, accented)

                # Si le mot courant est dépourvu d'accents et que auto_correct_accents est actif
                if auto_correct_accents and accented != w_clean:
                    word.original = word.text
                    word.text = accented
                    word.corrected = True

    # 3. Typographie selon la langue
    if lang == "fr":
        # Si des mots ont été corrigés, reconstruire le texte
        if any(w.corrected for w in line.words):
            raw_text = " ".join(w.text for w in line.words)
        raw_text = apply_french_typography(raw_text)
    elif lang == "ar":
        # Ponctuation arabe
        raw_text = raw_text.replace("?", "؟").replace(",", "،").replace(";", "؛")
    elif lang == "de":
        # Typographie allemande (guillemets „ “)
        raw_text = re.sub(r'"\s*([^"]+?)\s*"', r"„\1“", raw_text)

    line.text = raw_text
    return line
