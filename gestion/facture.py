"""Generation de factures / tickets imprimables.

Approche sans dependance externe : on genere un fichier HTML propre puis on
l'ouvre dans le navigateur par defaut, ou l'utilisateur peut l'imprimer
(Ctrl+P) ou l'enregistrer en PDF via la fonction d'impression du navigateur.

Reference : module standard ``webbrowser``
https://docs.python.org/3/library/webbrowser.html
"""

from __future__ import annotations

import webbrowser
from html import escape
from pathlib import Path

from .ui.widgets import format_montant

MODELE = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>Facture n°{numero}</title>
<style>
  body {{ font-family: Arial, Helvetica, sans-serif; color: #222; margin: 30px; }}
  .entete {{ display: flex; justify-content: space-between; align-items: flex-start; }}
  .entreprise {{ font-size: 14px; }}
  .entreprise h1 {{ margin: 0 0 4px; font-size: 22px; }}
  .facture-info {{ text-align: right; font-size: 14px; }}
  .facture-info h2 {{ margin: 0 0 6px; font-size: 20px; color: #444; }}
  .bloc-client {{ margin: 24px 0 10px; font-size: 14px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px; }}
  th, td {{ border: 1px solid #ccc; padding: 8px 10px; }}
  th {{ background: #f0f0f0; text-align: left; }}
  td.nombre, th.nombre {{ text-align: right; }}
  tfoot td {{ font-weight: bold; }}
  tfoot .total-final td {{ font-size: 16px; border-top: 2px solid #999; }}
  .merci {{ margin-top: 30px; font-size: 13px; color: #666; }}
  @media print {{ .noprint {{ display: none; }} body {{ margin: 10mm; }} }}
  .noprint {{ margin-bottom: 18px; }}
  .btn {{ padding: 8px 16px; font-size: 14px; cursor: pointer; }}
</style>
</head>
<body>
<div class="noprint">
  <button class="btn" onclick="window.print()">Imprimer / Enregistrer en PDF</button>
</div>

<div class="entete">
  <div class="entreprise">
    <h1>{entreprise_nom}</h1>
    <div>{entreprise_adresse}</div>
    <div>{entreprise_telephone}</div>
    <div>{entreprise_email}</div>
  </div>
  <div class="facture-info">
    <h2>FACTURE</h2>
    <div>N° {numero}</div>
    <div>Date : {date}</div>
  </div>
</div>

<div class="bloc-client">
  <strong>Client :</strong> {client_nom}<br>
  {client_contact}
</div>

<table>
  <thead>
    <tr>
      <th>Désignation</th>
      <th class="nombre">Prix unitaire</th>
      <th class="nombre">Quantité</th>
      <th class="nombre">Montant</th>
    </tr>
  </thead>
  <tbody>
    {lignes}
  </tbody>
  <tfoot>
    {totaux}
  </tfoot>
</table>

<p class="merci">Merci de votre confiance.</p>
</body>
</html>
"""


def _ligne_total(libelle: str, valeur: str, classe: str = "") -> str:
    """Genere une ligne de total du pied de facture."""
    attr = f' class="{classe}"' if classe else ""
    return (f'<tr{attr}><td colspan="3" class="nombre">{escape(libelle)}</td>'
            f'<td class="nombre">{escape(valeur)}</td></tr>')


def _construire_totaux(vente) -> str:
    """Construit les lignes de totaux d'une facture (remise/TVA affichees si utiles)."""
    brut = vente["montant_brut"] or 0
    remise = vente["remise"] or 0
    taux_tva = vente["taux_tva"] or 0
    montant_tva = vente["montant_tva"] or 0
    total = vente["total"] or 0
    base_ht = brut - remise

    lignes = []
    # Detaille seulement si une remise ou une TVA s'applique.
    if remise > 0 or taux_tva > 0 or montant_tva > 0:
        lignes.append(_ligne_total("Sous-total", format_montant(brut)))
        if remise > 0:
            lignes.append(_ligne_total("Remise", "- " + format_montant(remise)))
        lignes.append(_ligne_total("Total HT", format_montant(base_ht)))
        lignes.append(_ligne_total(f"TVA ({taux_tva:g}%)", format_montant(montant_tva)))
        lignes.append(_ligne_total("TOTAL TTC", format_montant(total), "total-final"))
    else:
        lignes.append(_ligne_total("TOTAL", format_montant(total), "total-final"))
    return "".join(lignes)


def generer_facture_html(db, vente_id: int, dossier: str = "factures") -> str:
    """Genere le fichier HTML de la facture d'une vente. Retourne son chemin.

    Leve ``ValueError`` si la vente n'existe pas.
    """
    vente = db.obtenir_vente(vente_id)
    if vente is None:
        raise ValueError(f"Vente introuvable (n°{vente_id}).")
    lignes = db.lignes_de_vente(vente_id)
    infos = db.parametres_entreprise()

    lignes_html = "".join(
        "<tr>"
        f"<td>{escape(l['designation'])}</td>"
        f"<td class='nombre'>{escape(format_montant(l['prix_unitaire']))}</td>"
        f"<td class='nombre'>{l['quantite']}</td>"
        f"<td class='nombre'>{escape(format_montant(l['montant']))}</td>"
        "</tr>"
        for l in lignes
    )

    client_nom = vente["client_nom"] or "Client de passage"
    contact = " ".join(
        p for p in [vente["client_telephone"] or "", vente["client_adresse"] or ""]
        if p
    )

    totaux_html = _construire_totaux(vente)

    html = MODELE.format(
        numero=vente["id"],
        date=escape(vente["date_vente"]),
        entreprise_nom=escape(infos["entreprise_nom"]),
        entreprise_adresse=escape(infos["entreprise_adresse"]),
        entreprise_telephone=escape(infos["entreprise_telephone"]),
        entreprise_email=escape(infos["entreprise_email"]),
        client_nom=escape(client_nom),
        client_contact=escape(contact),
        lignes=lignes_html,
        totaux=totaux_html,
    )

    Path(dossier).mkdir(parents=True, exist_ok=True)
    chemin = Path(dossier) / f"facture_{vente['id']}.html"
    chemin.write_text(html, encoding="utf-8")
    return str(chemin)


def imprimer_facture(db, vente_id: int, dossier: str = "factures") -> str:
    """Genere la facture puis l'ouvre dans le navigateur pour impression.

    Retourne le chemin du fichier genere.
    """
    chemin = generer_facture_html(db, vente_id, dossier)
    webbrowser.open(Path(chemin).resolve().as_uri())
    return chemin
