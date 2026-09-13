"""Ecriture de fichiers Excel (.xlsx) SANS dependance externe.

Un fichier .xlsx est une archive ZIP contenant des documents XML au format
Office Open XML (ECMA-376). Ce module en genere une version minimale mais
valide (plusieurs feuilles, chaines et nombres, entetes en gras), en
n'utilisant que la bibliotheque standard (``zipfile`` + ``xml``).

Reference du format : ECMA-376 / documentation Microsoft
https://learn.microsoft.com/openspecs/office_standards/ms-xlsx

API :
    ecrire_xlsx("rapport.xlsx", [
        {"nom": "Ventes",
         "entetes": ["Date", "Client", "Total"],
         "lignes": [["2026-09-13", "Fatou", 15000], ...]},
    ])
"""

from __future__ import annotations

import zipfile
from datetime import datetime
from xml.sax.saxutils import escape


def _lettre_colonne(index: int) -> str:
    """Convertit un index de colonne 1-base en lettres Excel (1->A, 27->AA)."""
    lettres = ""
    while index > 0:
        index, reste = divmod(index - 1, 26)
        lettres = chr(65 + reste) + lettres
    return lettres


def _est_nombre(valeur) -> bool:
    """Vrai si la valeur doit etre ecrite comme un nombre (pas un booleen)."""
    return isinstance(valeur, (int, float)) and not isinstance(valeur, bool)


def _cellule(ref: str, valeur, style: int = 0) -> str:
    """Genere le XML d'une cellule (nombre ou chaine en ligne)."""
    attr_style = f' s="{style}"' if style else ""
    if valeur is None or valeur == "":
        return f'<c r="{ref}"{attr_style}/>'
    if _est_nombre(valeur):
        return f'<c r="{ref}"{attr_style}><v>{valeur}</v></c>'
    texte = escape(str(valeur))
    # xml:space="preserve" conserve les espaces de debut/fin.
    return (f'<c r="{ref}"{attr_style} t="inlineStr">'
            f'<is><t xml:space="preserve">{texte}</t></is></c>')


def _feuille_xml(entetes: list, lignes: list) -> str:
    """Genere le XML d'une feuille (entetes en gras = style 1)."""
    parties = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
        '<sheetData>',
    ]
    numero_ligne = 1
    if entetes:
        cellules = "".join(
            _cellule(f"{_lettre_colonne(i + 1)}{numero_ligne}", val, style=1)
            for i, val in enumerate(entetes)
        )
        parties.append(f'<row r="{numero_ligne}">{cellules}</row>')
        numero_ligne += 1
    for ligne in lignes:
        cellules = "".join(
            _cellule(f"{_lettre_colonne(i + 1)}{numero_ligne}", val)
            for i, val in enumerate(ligne)
        )
        parties.append(f'<row r="{numero_ligne}">{cellules}</row>')
        numero_ligne += 1
    parties.append('</sheetData></worksheet>')
    return "".join(parties)


_STYLES_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    '<fonts count="2">'
    '<font><sz val="11"/><name val="Calibri"/></font>'
    '<font><b/><sz val="11"/><name val="Calibri"/></font>'
    '</fonts>'
    '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
    '<borders count="1"><border/></borders>'
    '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
    '<cellXfs count="2">'
    '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
    '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
    '</cellXfs>'
    '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
    '</styleSheet>'
)


def _nettoyer_nom_feuille(nom: str, defaut: str) -> str:
    """Excel interdit \\ / ? * [ ] : et limite a 31 caracteres."""
    nom = (nom or defaut).strip()
    for interdit in '\\/?*[]:':
        nom = nom.replace(interdit, " ")
    return nom[:31] or defaut


def ecrire_xlsx(chemin: str, feuilles: list[dict]) -> str:
    """Ecrit un classeur .xlsx a l'emplacement ``chemin``.

    ``feuilles`` : liste de dicts ``{"nom", "entetes", "lignes"}``.
    Retourne le chemin du fichier ecrit.
    """
    if not feuilles:
        feuilles = [{"nom": "Feuille1", "entetes": [], "lignes": []}]

    noms = [_nettoyer_nom_feuille(f.get("nom"), f"Feuille{i+1}")
            for i, f in enumerate(feuilles)]

    # [Content_Types].xml
    overrides = "".join(
        f'<Override PartName="/xl/worksheets/sheet{i+1}.xml" '
        f'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for i in range(len(feuilles))
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/styles.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        f'{overrides}'
        '</Types>'
    )

    # _rels/.rels
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        '</Relationships>'
    )

    # xl/workbook.xml
    sheets_xml = "".join(
        f'<sheet name="{escape(noms[i])}" sheetId="{i+1}" r:id="rId{i+1}"/>'
        for i in range(len(feuilles))
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets>{sheets_xml}</sheets>'
        '</workbook>'
    )

    # xl/_rels/workbook.xml.rels (feuilles rId1..N, styles rId(N+1))
    id_styles = len(feuilles) + 1
    rel_feuilles = "".join(
        f'<Relationship Id="rId{i+1}" '
        f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        f'Target="worksheets/sheet{i+1}.xml"/>'
        for i in range(len(feuilles))
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'{rel_feuilles}'
        f'<Relationship Id="rId{id_styles}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
        '</Relationships>'
    )

    with zipfile.ZipFile(chemin, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        z.writestr("xl/styles.xml", _STYLES_XML)
        for i, feuille in enumerate(feuilles):
            z.writestr(
                f"xl/worksheets/sheet{i+1}.xml",
                _feuille_xml(feuille.get("entetes", []), feuille.get("lignes", [])),
            )
    return chemin


def horodatage() -> str:
    """Retourne un horodatage utilisable dans un nom de fichier."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")
