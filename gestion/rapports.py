"""Construction et export des rapports par periode.

Chaque rapport est represente par une liste de "feuilles"
(``{"nom", "entetes", "lignes"}``) reutilisable pour l'export Excel (.xlsx)
comme pour l'export CSV.

Les exports Excel utilisent ``gestion.xlsx`` (bibliotheque standard uniquement).
Le CSV utilise le module standard ``csv`` avec le point-virgule comme
separateur et un BOM UTF-8, pour une ouverture correcte dans Excel francophone.
"""

from __future__ import annotations

import csv
from pathlib import Path

from .xlsx import ecrire_xlsx, horodatage


def _n(valeur: float) -> float:
    """Arrondit un montant a 2 decimales (pour l'ecriture numerique)."""
    return round(float(valeur), 2)


# ---------------------------------------------------------------------- #
# Constructeurs de rapports (retournent (titre_fichier, feuilles))
# ---------------------------------------------------------------------- #
def rapport_ventes(db, date_debut: str, date_fin: str):
    """Rapport des ventes sur une periode : synthese, detail, top produits."""
    ventes = db.ventes_periode(date_debut, date_fin)
    par_produit = db.ventes_par_produit_periode(date_debut, date_fin)
    totaux = db.totaux_ventes_periode(date_debut, date_fin)

    synthese = {
        "nom": "Synthèse",
        "entetes": ["Indicateur", "Valeur"],
        "lignes": [
            ["Période", f"{date_debut} au {date_fin}"],
            ["Nombre de ventes", totaux["nombre"]],
            ["Total brut (FCFA)", _n(totaux["brut"])],
            ["Remises (FCFA)", _n(totaux["remise"])],
            ["Chiffre d'affaires HT (FCFA)", _n(totaux["ht"])],
            ["TVA collectée (FCFA)", _n(totaux["tva"])],
            ["Chiffre d'affaires TTC (FCFA)", _n(totaux["ttc"])],
        ],
    }
    detail = {
        "nom": "Ventes",
        "entetes": ["N°", "Date", "Client", "Brut (FCFA)", "Remise (FCFA)",
                    "HT (FCFA)", "TVA (FCFA)", "TTC (FCFA)"],
        "lignes": [[v["id"], v["date_vente"], v["client_nom"],
                    _n(v["montant_brut"]), _n(v["remise"]),
                    _n(v["montant_brut"] - v["remise"]),
                    _n(v["montant_tva"]), _n(v["total"])]
                   for v in ventes],
    }
    produits = {
        "nom": "Top produits",
        "entetes": ["Produit", "Quantité vendue", "Montant (FCFA)"],
        "lignes": [[p["designation"], p["quantite"], _n(p["montant"])]
                   for p in par_produit],
    }
    return ("rapport_ventes", [synthese, detail, produits])


def rapport_approvisionnements(db, date_debut: str, date_fin: str):
    """Rapport des approvisionnements (depenses) sur une periode."""
    appros = db.approvisionnements_periode(date_debut, date_fin)
    depenses = db.depenses_periode(date_debut, date_fin)

    synthese = {
        "nom": "Synthèse",
        "entetes": ["Indicateur", "Valeur"],
        "lignes": [
            ["Période", f"{date_debut} au {date_fin}"],
            ["Nombre d'approvisionnements", len(appros)],
            ["Dépenses totales (FCFA)", _n(depenses)],
        ],
    }
    detail = {
        "nom": "Approvisionnements",
        "entetes": ["N°", "Date", "Fournisseur", "Total (FCFA)"],
        "lignes": [[a["id"], a["date_appro"], a["fournisseur_nom"], _n(a["total"])]
                   for a in appros],
    }
    return ("rapport_approvisionnements", [synthese, detail])


def rapport_stock(db, date_debut: str = "", date_fin: str = ""):
    """Etat du stock a l'instant present (les dates sont ignorees)."""
    produits = db.lister_produits()
    lignes = []
    for p in produits:
        valeur = p["quantite"] * p["prix_achat"]
        alerte = "OUI" if (p["seuil_alerte"] > 0 and p["quantite"] <= p["seuil_alerte"]) else ""
        lignes.append([p["reference"], p["designation"], p["quantite"],
                       _n(p["prix_achat"]), _n(p["prix_vente"]),
                       p["seuil_alerte"], _n(valeur), alerte])
    detail = {
        "nom": "Stock",
        "entetes": ["Référence", "Désignation", "Stock", "Prix achat",
                    "Prix vente", "Seuil", "Valeur stock (FCFA)", "Alerte"],
        "lignes": lignes,
    }
    return ("rapport_stock", [detail])


# Table des rapports disponibles : libelle -> (fonction, besoin_periode)
RAPPORTS = {
    "Ventes par période": (rapport_ventes, True),
    "Approvisionnements par période": (rapport_approvisionnements, True),
    "État du stock (à ce jour)": (rapport_stock, False),
}


# ---------------------------------------------------------------------- #
# Export
# ---------------------------------------------------------------------- #
def exporter_xlsx(feuilles: list[dict], base_nom: str, dossier: str = "rapports") -> str:
    """Ecrit les feuilles dans un fichier .xlsx horodate. Retourne le chemin."""
    Path(dossier).mkdir(parents=True, exist_ok=True)
    chemin = Path(dossier) / f"{base_nom}_{horodatage()}.xlsx"
    ecrire_xlsx(str(chemin), feuilles)
    return str(chemin)


def exporter_csv(feuilles: list[dict], base_nom: str, dossier: str = "rapports") -> str:
    """Ecrit la feuille de detail (la derniere) en CSV. Retourne le chemin.

    Point-virgule + BOM UTF-8 pour une ouverture propre dans Excel francophone.
    """
    Path(dossier).mkdir(parents=True, exist_ok=True)
    chemin = Path(dossier) / f"{base_nom}_{horodatage()}.csv"
    # Exporte la premiere feuille de detail (celle qui n'est pas la synthese).
    feuille = next((f for f in feuilles if f["nom"] != "Synthèse"), feuilles[0])
    with open(chemin, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        if feuille["entetes"]:
            writer.writerow(feuille["entetes"])
        writer.writerows(feuille["lignes"])
    return str(chemin)
