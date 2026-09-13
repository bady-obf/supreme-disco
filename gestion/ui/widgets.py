"""Fonctions utilitaires partagees par les onglets de l'interface.

Ne contient volontairement que des aides simples (formatage, validation)
pour eviter la duplication de code entre les differents ecrans.
"""

from __future__ import annotations

# Devise affichee. Changez cette valeur pour adapter l'application
# (ex. "EUR", "MAD", "USD"). La zone OHADA utilise le franc CFA.
DEVISE = "FCFA"


def format_montant(valeur: float) -> str:
    """Formate un montant avec separateur de milliers et la devise.

    >>> format_montant(1250000)
    '1 250 000 FCFA'
    """
    try:
        nombre = f"{float(valeur):,.0f}".replace(",", " ")
    except (TypeError, ValueError):
        nombre = "0"
    return f"{nombre} {DEVISE}"


def lire_float(valeur: str, defaut: float = 0.0) -> float:
    """Convertit une chaine en nombre decimal, en tolerant la virgule.

    Retourne ``defaut`` si la conversion echoue (champ vide, texte invalide).
    """
    texte = str(valeur).strip().replace(" ", "").replace(",", ".")
    if not texte:
        return defaut
    try:
        return float(texte)
    except ValueError:
        return defaut


def lire_int(valeur: str, defaut: int = 0) -> int:
    """Convertit une chaine en entier. Retourne ``defaut`` si invalide."""
    texte = str(valeur).strip().replace(" ", "")
    if not texte:
        return defaut
    try:
        return int(float(texte))
    except ValueError:
        return defaut
