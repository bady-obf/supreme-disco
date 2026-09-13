"""Couche d'acces aux donnees (SQLite).

Ce module ne depend PAS de tkinter : il peut donc etre importe et teste
sans interface graphique. Toutes les operations metier (produits, clients,
ventes, statistiques) passent par la classe :class:`Database`.

Reference : bibliotheque standard Python ``sqlite3``
https://docs.python.org/3/library/sqlite3.html
"""

from __future__ import annotations

import binascii
import hashlib
import hmac
import os
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path


class StockInsuffisant(Exception):
    """Levee lorsqu'une vente demande plus d'unites que le stock disponible."""


# Schema de la base. ``IF NOT EXISTS`` rend la creation idempotente.
SCHEMA = """
CREATE TABLE IF NOT EXISTS produits (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    reference     TEXT    NOT NULL UNIQUE,
    designation   TEXT    NOT NULL,
    prix_achat    REAL    NOT NULL DEFAULT 0,
    prix_vente    REAL    NOT NULL DEFAULT 0,
    quantite      INTEGER NOT NULL DEFAULT 0,
    seuil_alerte  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS clients (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    nom        TEXT NOT NULL,
    telephone  TEXT,
    adresse    TEXT
);

CREATE TABLE IF NOT EXISTS ventes (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    date_vente   TEXT NOT NULL,
    client_id    INTEGER,
    montant_brut REAL NOT NULL DEFAULT 0,
    remise       REAL NOT NULL DEFAULT 0,
    taux_tva     REAL NOT NULL DEFAULT 0,
    montant_tva  REAL NOT NULL DEFAULT 0,
    total        REAL NOT NULL DEFAULT 0,
    FOREIGN KEY (client_id) REFERENCES clients (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS lignes_vente (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    vente_id      INTEGER NOT NULL,
    produit_id    INTEGER,
    designation   TEXT    NOT NULL,
    prix_unitaire REAL    NOT NULL,
    quantite      INTEGER NOT NULL,
    montant       REAL    NOT NULL,
    FOREIGN KEY (vente_id)   REFERENCES ventes (id)   ON DELETE CASCADE,
    FOREIGN KEY (produit_id) REFERENCES produits (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS parametres (
    cle    TEXT PRIMARY KEY,
    valeur TEXT
);

CREATE TABLE IF NOT EXISTS fournisseurs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    nom        TEXT NOT NULL,
    telephone  TEXT,
    adresse    TEXT
);

CREATE TABLE IF NOT EXISTS approvisionnements (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    date_appro     TEXT NOT NULL,
    fournisseur_id INTEGER,
    total          REAL NOT NULL DEFAULT 0,
    FOREIGN KEY (fournisseur_id) REFERENCES fournisseurs (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS lignes_appro (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    appro_id    INTEGER NOT NULL,
    produit_id  INTEGER,
    designation TEXT    NOT NULL,
    prix_achat  REAL    NOT NULL,
    quantite    INTEGER NOT NULL,
    montant     REAL    NOT NULL,
    FOREIGN KEY (appro_id)   REFERENCES approvisionnements (id) ON DELETE CASCADE,
    FOREIGN KEY (produit_id) REFERENCES produits (id)          ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS utilisateurs (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    identifiant       TEXT    NOT NULL UNIQUE,
    nom               TEXT,
    role              TEXT    NOT NULL DEFAULT 'vendeur',
    sel               TEXT    NOT NULL,
    mot_de_passe_hash TEXT    NOT NULL,
    actif             INTEGER NOT NULL DEFAULT 1
);
"""

# Roles disponibles.
ROLES = ("admin", "vendeur")

# Nombre d'iterations PBKDF2 (compromis securite / rapidite pour une appli locale).
_PBKDF2_ITERATIONS = 200_000


def _hacher_mot_de_passe(mot_de_passe: str, sel: str | None = None) -> tuple[str, str]:
    """Retourne (sel, hash hexadecimal) pour un mot de passe via PBKDF2-HMAC-SHA256.

    Si ``sel`` est fourni, il est reutilise (pour verifier un mot de passe) ;
    sinon un sel aleatoire est genere (pour en enregistrer un nouveau).

    Reference : ``hashlib.pbkdf2_hmac``
    https://docs.python.org/3/library/hashlib.html#hashlib.pbkdf2_hmac
    """
    if sel is None:
        sel = binascii.hexlify(os.urandom(16)).decode()
    empreinte = hashlib.pbkdf2_hmac(
        "sha256", mot_de_passe.encode("utf-8"), sel.encode("utf-8"),
        _PBKDF2_ITERATIONS)
    return sel, binascii.hexlify(empreinte).decode()

# Valeurs par defaut des parametres de l'entreprise (utilisees sur les factures).
# taux_tva : taux de TVA par defaut (Senegal / zone OHADA : 18 %).
PARAMETRES_DEFAUT = {
    "entreprise_nom": "Mon Entreprise",
    "entreprise_adresse": "",
    "entreprise_telephone": "",
    "entreprise_email": "",
    "taux_tva": "18",
}


class Database:
    """Point d'entree unique pour toutes les operations sur les donnees."""

    def __init__(self, chemin: str | Path = "data/gestion.db") -> None:
        self.chemin = str(chemin)
        # Cree le dossier parent si besoin (sauf pour la base en memoire).
        if self.chemin != ":memory:":
            Path(self.chemin).parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False : pratique pour une petite appli Tkinter.
        self.conn = sqlite3.connect(self.chemin, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        # Active le respect des cles etrangeres (desactive par defaut en SQLite).
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._preparer_schema()

    def _preparer_schema(self) -> None:
        """Cree/complete le schema et insere les parametres par defaut.

        Idempotent : peut etre relance (notamment apres une restauration de
        sauvegarde, pour remettre a niveau une base plus ancienne).
        """
        self.conn.executescript(SCHEMA)
        self._migrer()
        for cle, valeur in PARAMETRES_DEFAUT.items():
            self.conn.execute(
                "INSERT OR IGNORE INTO parametres (cle, valeur) VALUES (?, ?)",
                (cle, valeur),
            )
        self.conn.commit()

    def _migrer(self) -> None:
        """Ajoute les colonnes manquantes aux bases creees par une version anterieure.

        SQLite ne recree pas une table existante (``IF NOT EXISTS``) : on ajoute
        donc les nouvelles colonnes de ``ventes`` (TVA, remise) au besoin.
        """
        colonnes = {r["name"] for r in
                    self.conn.execute("PRAGMA table_info(ventes)").fetchall()}
        ajouts = {
            "montant_brut": "REAL NOT NULL DEFAULT 0",
            "remise": "REAL NOT NULL DEFAULT 0",
            "taux_tva": "REAL NOT NULL DEFAULT 0",
            "montant_tva": "REAL NOT NULL DEFAULT 0",
        }
        for colonne, declaration in ajouts.items():
            if colonne not in colonnes:
                self.conn.execute(
                    f"ALTER TABLE ventes ADD COLUMN {colonne} {declaration}")
        # Pour les anciennes ventes (sans detail TVA), aligne le brut sur le total.
        self.conn.execute(
            "UPDATE ventes SET montant_brut = total "
            "WHERE montant_brut = 0 AND total <> 0")

    def fermer(self) -> None:
        """Ferme la connexion a la base."""
        self.conn.close()

    # ------------------------------------------------------------------ #
    # Sauvegarde / restauration
    # ------------------------------------------------------------------ #
    def sauvegarder(self, chemin_destination: str) -> str:
        """Copie la base courante vers ``chemin_destination`` (fichier .db).

        Utilise l'API de sauvegarde en ligne de SQLite : fonctionne meme
        pendant que l'application utilise la base. Retourne le chemin ecrit.

        Reference : ``sqlite3.Connection.backup``
        https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.backup
        """
        self.conn.commit()
        destination = sqlite3.connect(chemin_destination)
        try:
            with destination:
                self.conn.backup(destination)
        finally:
            destination.close()
        return chemin_destination

    def restaurer(self, chemin_source: str) -> None:
        """Remplace le contenu de la base courante par celui de ``chemin_source``.

        Le fichier source est d'abord valide (il doit contenir les tables de
        l'application). La connexion courante reste ouverte : les ecrans doivent
        simplement etre rafraichis apres l'appel. Le schema est remis a niveau
        (migration) au cas ou la sauvegarde proviendrait d'une version anterieure.

        Leve ``ValueError`` si le fichier n'est pas une base valide de l'appli.
        """
        source = sqlite3.connect(chemin_source)
        try:
            try:
                tables = {r[0] for r in source.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()}
            except sqlite3.DatabaseError as err:
                raise ValueError(
                    "Ce fichier n'est pas une base de donnees valide de l'application."
                ) from err
            if "produits" not in tables or "ventes" not in tables:
                raise ValueError(
                    "Ce fichier n'est pas une base de donnees valide de l'application.")
            source.backup(self.conn)
        finally:
            source.close()
        self.conn.commit()
        self._preparer_schema()

    # ------------------------------------------------------------------ #
    # Parametres (informations de l'entreprise, affichees sur les factures)
    # ------------------------------------------------------------------ #
    def obtenir_parametre(self, cle: str, defaut: str = "") -> str:
        """Retourne la valeur d'un parametre, ou ``defaut`` s'il est absent."""
        row = self.conn.execute(
            "SELECT valeur FROM parametres WHERE cle = ?", (cle,)
        ).fetchone()
        return row["valeur"] if row and row["valeur"] is not None else defaut

    def definir_parametre(self, cle: str, valeur: str) -> None:
        """Cree ou met a jour un parametre."""
        self.conn.execute(
            "INSERT INTO parametres (cle, valeur) VALUES (?, ?) "
            "ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur",
            (cle, valeur),
        )
        self.conn.commit()

    def parametres_entreprise(self) -> dict:
        """Retourne les informations de l'entreprise sous forme de dictionnaire."""
        return {cle: self.obtenir_parametre(cle, defaut)
                for cle, defaut in PARAMETRES_DEFAUT.items()}

    # ------------------------------------------------------------------ #
    # Produits
    # ------------------------------------------------------------------ #
    def ajouter_produit(
        self,
        reference: str,
        designation: str,
        prix_achat: float,
        prix_vente: float,
        quantite: int,
        seuil_alerte: int = 0,
    ) -> int:
        """Cree un produit et retourne son identifiant."""
        cur = self.conn.execute(
            """INSERT INTO produits
               (reference, designation, prix_achat, prix_vente, quantite, seuil_alerte)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (reference.strip(), designation.strip(), prix_achat, prix_vente,
             quantite, seuil_alerte),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def modifier_produit(
        self,
        produit_id: int,
        reference: str,
        designation: str,
        prix_achat: float,
        prix_vente: float,
        quantite: int,
        seuil_alerte: int,
    ) -> None:
        """Met a jour un produit existant."""
        self.conn.execute(
            """UPDATE produits
               SET reference = ?, designation = ?, prix_achat = ?,
                   prix_vente = ?, quantite = ?, seuil_alerte = ?
               WHERE id = ?""",
            (reference.strip(), designation.strip(), prix_achat, prix_vente,
             quantite, seuil_alerte, produit_id),
        )
        self.conn.commit()

    def supprimer_produit(self, produit_id: int) -> None:
        """Supprime un produit par son identifiant."""
        self.conn.execute("DELETE FROM produits WHERE id = ?", (produit_id,))
        self.conn.commit()

    def lister_produits(self, recherche: str = "") -> list[sqlite3.Row]:
        """Liste les produits, avec filtre optionnel sur reference/designation."""
        if recherche:
            motif = f"%{recherche.strip()}%"
            return self.conn.execute(
                """SELECT * FROM produits
                   WHERE reference LIKE ? OR designation LIKE ?
                   ORDER BY designation""",
                (motif, motif),
            ).fetchall()
        return self.conn.execute(
            "SELECT * FROM produits ORDER BY designation"
        ).fetchall()

    def obtenir_produit(self, produit_id: int) -> sqlite3.Row | None:
        """Retourne un produit par son identifiant, ou ``None``."""
        return self.conn.execute(
            "SELECT * FROM produits WHERE id = ?", (produit_id,)
        ).fetchone()

    def produits_en_alerte(self) -> list[sqlite3.Row]:
        """Produits dont le stock est <= au seuil d'alerte (seuil > 0)."""
        return self.conn.execute(
            """SELECT * FROM produits
               WHERE seuil_alerte > 0 AND quantite <= seuil_alerte
               ORDER BY quantite""",
        ).fetchall()

    # ------------------------------------------------------------------ #
    # Clients
    # ------------------------------------------------------------------ #
    def ajouter_client(self, nom: str, telephone: str = "", adresse: str = "") -> int:
        """Cree un client et retourne son identifiant."""
        cur = self.conn.execute(
            "INSERT INTO clients (nom, telephone, adresse) VALUES (?, ?, ?)",
            (nom.strip(), telephone.strip(), adresse.strip()),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def modifier_client(
        self, client_id: int, nom: str, telephone: str, adresse: str
    ) -> None:
        """Met a jour un client existant."""
        self.conn.execute(
            "UPDATE clients SET nom = ?, telephone = ?, adresse = ? WHERE id = ?",
            (nom.strip(), telephone.strip(), adresse.strip(), client_id),
        )
        self.conn.commit()

    def supprimer_client(self, client_id: int) -> None:
        """Supprime un client par son identifiant."""
        self.conn.execute("DELETE FROM clients WHERE id = ?", (client_id,))
        self.conn.commit()

    def lister_clients(self, recherche: str = "") -> list[sqlite3.Row]:
        """Liste les clients, avec filtre optionnel sur le nom."""
        if recherche:
            motif = f"%{recherche.strip()}%"
            return self.conn.execute(
                "SELECT * FROM clients WHERE nom LIKE ? ORDER BY nom", (motif,)
            ).fetchall()
        return self.conn.execute("SELECT * FROM clients ORDER BY nom").fetchall()

    # ------------------------------------------------------------------ #
    # Ventes
    # ------------------------------------------------------------------ #
    def enregistrer_vente(
        self,
        client_id: int | None,
        lignes: list[dict],
        remise: float = 0.0,
        taux_tva: float | None = None,
    ) -> int:
        """Enregistre une vente et decremente le stock, en une transaction.

        ``lignes`` est une liste de dictionnaires :
        ``{"produit_id": int, "quantite": int}``.

        ``remise`` : montant de remise (en FCFA) applique sur le total brut.
        ``taux_tva`` : taux de TVA en pourcentage ; si ``None``, le parametre
        ``taux_tva`` de la base est utilise. Le total enregistre est TTC :
        ``total = (brut - remise) + TVA``.

        Leve :class:`StockInsuffisant` si un produit n'a pas assez de stock ;
        dans ce cas AUCUNE modification n'est appliquee (rollback).
        Retourne l'identifiant de la vente creee.
        """
        if not lignes:
            raise ValueError("Une vente doit contenir au moins une ligne.")

        if taux_tva is None:
            try:
                taux_tva = float(self.obtenir_parametre("taux_tva", "0") or 0)
            except ValueError:
                taux_tva = 0.0

        try:
            # Verifie d'abord la disponibilite de tout le panier.
            details = []
            montant_brut = 0.0
            for ligne in lignes:
                produit = self.obtenir_produit(ligne["produit_id"])
                if produit is None:
                    raise ValueError(
                        f"Produit introuvable (id={ligne['produit_id']})."
                    )
                quantite = int(ligne["quantite"])
                if quantite <= 0:
                    raise ValueError("La quantite doit etre superieure a zero.")
                if quantite > produit["quantite"]:
                    raise StockInsuffisant(
                        f"Stock insuffisant pour « {produit['designation']} » : "
                        f"demande {quantite}, disponible {produit['quantite']}."
                    )
                montant = quantite * produit["prix_vente"]
                montant_brut += montant
                details.append((produit, quantite, montant))

            # Calcule remise (bornee), base HT, TVA et total TTC.
            remise = max(0.0, min(float(remise), montant_brut))
            taux_tva = max(0.0, float(taux_tva))
            base_ht = montant_brut - remise
            montant_tva = round(base_ht * taux_tva / 100.0, 2)
            total = round(base_ht + montant_tva, 2)

            # Enregistre l'entete de vente.
            cur = self.conn.execute(
                "INSERT INTO ventes "
                "(date_vente, client_id, montant_brut, remise, taux_tva, montant_tva, total) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), client_id,
                 montant_brut, remise, taux_tva, montant_tva, total),
            )
            vente_id = int(cur.lastrowid)

            # Enregistre les lignes et decremente le stock.
            for produit, quantite, montant in details:
                self.conn.execute(
                    """INSERT INTO lignes_vente
                       (vente_id, produit_id, designation, prix_unitaire, quantite, montant)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (vente_id, produit["id"], produit["designation"],
                     produit["prix_vente"], quantite, montant),
                )
                self.conn.execute(
                    "UPDATE produits SET quantite = quantite - ? WHERE id = ?",
                    (quantite, produit["id"]),
                )

            self.conn.commit()
            return vente_id
        except Exception:
            self.conn.rollback()
            raise

    def lister_ventes(self, limite: int = 100) -> list[sqlite3.Row]:
        """Liste les ventes recentes avec le nom du client."""
        return self.conn.execute(
            """SELECT v.id, v.date_vente, v.total,
                      COALESCE(c.nom, 'Client de passage') AS client_nom
               FROM ventes v
               LEFT JOIN clients c ON c.id = v.client_id
               ORDER BY v.id DESC
               LIMIT ?""",
            (limite,),
        ).fetchall()

    def lignes_de_vente(self, vente_id: int) -> list[sqlite3.Row]:
        """Retourne le detail (lignes) d'une vente."""
        return self.conn.execute(
            "SELECT * FROM lignes_vente WHERE vente_id = ? ORDER BY id",
            (vente_id,),
        ).fetchall()

    def obtenir_vente(self, vente_id: int) -> sqlite3.Row | None:
        """Retourne l'entete d'une vente (avec detail TVA) et les infos client."""
        return self.conn.execute(
            """SELECT v.id, v.date_vente, v.montant_brut, v.remise,
                      v.taux_tva, v.montant_tva, v.total,
                      c.nom AS client_nom, c.telephone AS client_telephone,
                      c.adresse AS client_adresse
               FROM ventes v
               LEFT JOIN clients c ON c.id = v.client_id
               WHERE v.id = ?""",
            (vente_id,),
        ).fetchone()

    # ------------------------------------------------------------------ #
    # Statistiques (tableau de bord)
    # ------------------------------------------------------------------ #
    def valeur_stock(self) -> float:
        """Valeur totale du stock au prix d'achat."""
        row = self.conn.execute(
            "SELECT COALESCE(SUM(quantite * prix_achat), 0) AS v FROM produits"
        ).fetchone()
        return float(row["v"])

    def nombre_produits(self) -> int:
        """Nombre de references produits enregistrees."""
        row = self.conn.execute("SELECT COUNT(*) AS n FROM produits").fetchone()
        return int(row["n"])

    def nombre_clients(self) -> int:
        """Nombre de clients enregistres."""
        row = self.conn.execute("SELECT COUNT(*) AS n FROM clients").fetchone()
        return int(row["n"])

    def chiffre_affaires_jour(self, jour: str | None = None) -> float:
        """Chiffre d'affaires d'une journee (par defaut aujourd'hui)."""
        if jour is None:
            jour = datetime.now().strftime("%Y-%m-%d")
        row = self.conn.execute(
            "SELECT COALESCE(SUM(total), 0) AS ca FROM ventes "
            "WHERE date_vente LIKE ?",
            (f"{jour}%",),
        ).fetchone()
        return float(row["ca"])

    def nombre_ventes_jour(self, jour: str | None = None) -> int:
        """Nombre de ventes d'une journee (par defaut aujourd'hui)."""
        if jour is None:
            jour = datetime.now().strftime("%Y-%m-%d")
        row = self.conn.execute(
            "SELECT COUNT(*) AS n FROM ventes WHERE date_vente LIKE ?",
            (f"{jour}%",),
        ).fetchone()
        return int(row["n"])

    def ca_par_jour(self, nb_jours: int = 14) -> list[tuple[str, float]]:
        """Chiffre d'affaires (TTC) par jour sur les ``nb_jours`` derniers jours.

        Retourne une liste ordonnee ``[(jour 'AAAA-MM-JJ', ca), ...]``, avec les
        jours sans vente a 0 (pour un graphique continu).
        """
        nb_jours = max(1, int(nb_jours))
        debut = date.today() - timedelta(days=nb_jours - 1)
        rows = self.conn.execute(
            "SELECT substr(date_vente, 1, 10) AS jour, COALESCE(SUM(total), 0) AS ca "
            "FROM ventes WHERE substr(date_vente, 1, 10) >= ? GROUP BY jour",
            (debut.strftime("%Y-%m-%d"),),
        ).fetchall()
        par_jour = {r["jour"]: float(r["ca"]) for r in rows}
        resultat = []
        for i in range(nb_jours):
            cle = (debut + timedelta(days=i)).strftime("%Y-%m-%d")
            resultat.append((cle, par_jour.get(cle, 0.0)))
        return resultat

    def totaux_ventes_periode(self, date_debut: str, date_fin: str) -> dict:
        """Totaux agreges des ventes sur une periode (brut, remise, HT, TVA, TTC)."""
        row = self.conn.execute(
            "SELECT COUNT(*) AS n, "
            "COALESCE(SUM(montant_brut), 0) AS brut, "
            "COALESCE(SUM(remise), 0) AS remise, "
            "COALESCE(SUM(montant_tva), 0) AS tva, "
            "COALESCE(SUM(total), 0) AS ttc "
            "FROM ventes WHERE substr(date_vente, 1, 10) BETWEEN ? AND ?",
            (date_debut, date_fin),
        ).fetchone()
        brut = float(row["brut"])
        remise = float(row["remise"])
        return {
            "nombre": int(row["n"]),
            "brut": brut,
            "remise": remise,
            "ht": brut - remise,
            "tva": float(row["tva"]),
            "ttc": float(row["ttc"]),
        }

    # ------------------------------------------------------------------ #
    # Fournisseurs
    # ------------------------------------------------------------------ #
    def ajouter_fournisseur(self, nom: str, telephone: str = "",
                            adresse: str = "") -> int:
        """Cree un fournisseur et retourne son identifiant."""
        cur = self.conn.execute(
            "INSERT INTO fournisseurs (nom, telephone, adresse) VALUES (?, ?, ?)",
            (nom.strip(), telephone.strip(), adresse.strip()),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def modifier_fournisseur(self, fournisseur_id: int, nom: str,
                             telephone: str, adresse: str) -> None:
        """Met a jour un fournisseur existant."""
        self.conn.execute(
            "UPDATE fournisseurs SET nom = ?, telephone = ?, adresse = ? WHERE id = ?",
            (nom.strip(), telephone.strip(), adresse.strip(), fournisseur_id),
        )
        self.conn.commit()

    def supprimer_fournisseur(self, fournisseur_id: int) -> None:
        """Supprime un fournisseur par son identifiant."""
        self.conn.execute("DELETE FROM fournisseurs WHERE id = ?", (fournisseur_id,))
        self.conn.commit()

    def lister_fournisseurs(self, recherche: str = "") -> list[sqlite3.Row]:
        """Liste les fournisseurs, avec filtre optionnel sur le nom."""
        if recherche:
            motif = f"%{recherche.strip()}%"
            return self.conn.execute(
                "SELECT * FROM fournisseurs WHERE nom LIKE ? ORDER BY nom", (motif,)
            ).fetchall()
        return self.conn.execute(
            "SELECT * FROM fournisseurs ORDER BY nom"
        ).fetchall()

    def nombre_fournisseurs(self) -> int:
        """Nombre de fournisseurs enregistres."""
        row = self.conn.execute("SELECT COUNT(*) AS n FROM fournisseurs").fetchone()
        return int(row["n"])

    # ------------------------------------------------------------------ #
    # Approvisionnements (entrees de stock)
    # ------------------------------------------------------------------ #
    def enregistrer_approvisionnement(
        self,
        fournisseur_id: int | None,
        lignes: list[dict],
        maj_prix_achat: bool = True,
    ) -> int:
        """Enregistre un approvisionnement et INCREMENTE le stock (transaction).

        ``lignes`` : liste de dicts
        ``{"produit_id": int, "quantite": int, "prix_achat": float}``.
        Si ``maj_prix_achat`` est vrai, le prix d'achat du produit est mis a jour
        avec celui de la ligne. Retourne l'identifiant de l'approvisionnement.
        """
        if not lignes:
            raise ValueError("Un approvisionnement doit contenir au moins une ligne.")
        try:
            details = []
            total = 0.0
            for ligne in lignes:
                produit = self.obtenir_produit(ligne["produit_id"])
                if produit is None:
                    raise ValueError(
                        f"Produit introuvable (id={ligne['produit_id']})."
                    )
                quantite = int(ligne["quantite"])
                if quantite <= 0:
                    raise ValueError("La quantite doit etre superieure a zero.")
                prix_achat = float(ligne.get("prix_achat", produit["prix_achat"]))
                montant = quantite * prix_achat
                total += montant
                details.append((produit, quantite, prix_achat, montant))

            cur = self.conn.execute(
                "INSERT INTO approvisionnements (date_appro, fournisseur_id, total) "
                "VALUES (?, ?, ?)",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), fournisseur_id, total),
            )
            appro_id = int(cur.lastrowid)

            for produit, quantite, prix_achat, montant in details:
                self.conn.execute(
                    """INSERT INTO lignes_appro
                       (appro_id, produit_id, designation, prix_achat, quantite, montant)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (appro_id, produit["id"], produit["designation"],
                     prix_achat, quantite, montant),
                )
                if maj_prix_achat:
                    self.conn.execute(
                        "UPDATE produits SET quantite = quantite + ?, prix_achat = ? "
                        "WHERE id = ?",
                        (quantite, prix_achat, produit["id"]),
                    )
                else:
                    self.conn.execute(
                        "UPDATE produits SET quantite = quantite + ? WHERE id = ?",
                        (quantite, produit["id"]),
                    )

            self.conn.commit()
            return appro_id
        except Exception:
            self.conn.rollback()
            raise

    def lister_approvisionnements(self, limite: int = 100) -> list[sqlite3.Row]:
        """Liste les approvisionnements recents avec le nom du fournisseur."""
        return self.conn.execute(
            """SELECT a.id, a.date_appro, a.total,
                      COALESCE(f.nom, 'Fournisseur inconnu') AS fournisseur_nom
               FROM approvisionnements a
               LEFT JOIN fournisseurs f ON f.id = a.fournisseur_id
               ORDER BY a.id DESC
               LIMIT ?""",
            (limite,),
        ).fetchall()

    def lignes_approvisionnement(self, appro_id: int) -> list[sqlite3.Row]:
        """Retourne le detail (lignes) d'un approvisionnement."""
        return self.conn.execute(
            "SELECT * FROM lignes_appro WHERE appro_id = ? ORDER BY id",
            (appro_id,),
        ).fetchall()

    # ------------------------------------------------------------------ #
    # Rapports par periode (dates au format 'AAAA-MM-JJ')
    # ------------------------------------------------------------------ #
    def ventes_periode(self, date_debut: str, date_fin: str) -> list[sqlite3.Row]:
        """Ventes dont la date est comprise entre date_debut et date_fin (inclus)."""
        return self.conn.execute(
            """SELECT v.id, v.date_vente, v.montant_brut, v.remise,
                      v.taux_tva, v.montant_tva, v.total,
                      COALESCE(c.nom, 'Client de passage') AS client_nom
               FROM ventes v
               LEFT JOIN clients c ON c.id = v.client_id
               WHERE substr(v.date_vente, 1, 10) BETWEEN ? AND ?
               ORDER BY v.date_vente""",
            (date_debut, date_fin),
        ).fetchall()

    def ca_periode(self, date_debut: str, date_fin: str) -> float:
        """Chiffre d'affaires total sur la periode."""
        row = self.conn.execute(
            "SELECT COALESCE(SUM(total), 0) AS ca FROM ventes "
            "WHERE substr(date_vente, 1, 10) BETWEEN ? AND ?",
            (date_debut, date_fin),
        ).fetchone()
        return float(row["ca"])

    def ventes_par_produit_periode(self, date_debut: str,
                                   date_fin: str) -> list[sqlite3.Row]:
        """Quantites et montants vendus par produit sur la periode."""
        return self.conn.execute(
            """SELECT lv.designation AS designation,
                      SUM(lv.quantite) AS quantite,
                      SUM(lv.montant)  AS montant
               FROM lignes_vente lv
               JOIN ventes v ON v.id = lv.vente_id
               WHERE substr(v.date_vente, 1, 10) BETWEEN ? AND ?
               GROUP BY lv.designation
               ORDER BY montant DESC""",
            (date_debut, date_fin),
        ).fetchall()

    def approvisionnements_periode(self, date_debut: str,
                                   date_fin: str) -> list[sqlite3.Row]:
        """Approvisionnements dont la date est comprise dans la periode."""
        return self.conn.execute(
            """SELECT a.id, a.date_appro, a.total,
                      COALESCE(f.nom, 'Fournisseur inconnu') AS fournisseur_nom
               FROM approvisionnements a
               LEFT JOIN fournisseurs f ON f.id = a.fournisseur_id
               WHERE substr(a.date_appro, 1, 10) BETWEEN ? AND ?
               ORDER BY a.date_appro""",
            (date_debut, date_fin),
        ).fetchall()

    def depenses_periode(self, date_debut: str, date_fin: str) -> float:
        """Total des approvisionnements (depenses) sur la periode."""
        row = self.conn.execute(
            "SELECT COALESCE(SUM(total), 0) AS d FROM approvisionnements "
            "WHERE substr(date_appro, 1, 10) BETWEEN ? AND ?",
            (date_debut, date_fin),
        ).fetchone()
        return float(row["d"])

    # ------------------------------------------------------------------ #
    # Utilisateurs (authentification)
    # ------------------------------------------------------------------ #
    def nombre_utilisateurs(self) -> int:
        """Nombre de comptes utilisateurs enregistres."""
        row = self.conn.execute("SELECT COUNT(*) AS n FROM utilisateurs").fetchone()
        return int(row["n"])

    def creer_utilisateur(self, identifiant: str, mot_de_passe: str,
                          role: str = "vendeur", nom: str = "") -> int:
        """Cree un utilisateur (mot de passe hache). Retourne son identifiant.

        Leve ``ValueError`` si l'identifiant/mot de passe est vide, si le role
        est inconnu, ou si l'identifiant existe deja.
        """
        identifiant = identifiant.strip()
        if not identifiant:
            raise ValueError("L'identifiant est obligatoire.")
        if not mot_de_passe:
            raise ValueError("Le mot de passe est obligatoire.")
        if role not in ROLES:
            raise ValueError(f"Role invalide : {role}.")
        sel, empreinte = _hacher_mot_de_passe(mot_de_passe)
        try:
            cur = self.conn.execute(
                "INSERT INTO utilisateurs (identifiant, nom, role, sel, mot_de_passe_hash) "
                "VALUES (?, ?, ?, ?, ?)",
                (identifiant, nom.strip(), role, sel, empreinte),
            )
        except sqlite3.IntegrityError as err:
            raise ValueError(f"L'identifiant « {identifiant} » existe deja.") from err
        self.conn.commit()
        return int(cur.lastrowid)

    def verifier_identifiants(self, identifiant: str, mot_de_passe: str) -> dict | None:
        """Retourne les infos de l'utilisateur si les identifiants sont valides.

        Ne retourne un utilisateur que s'il est actif et que le mot de passe
        correspond. Sinon retourne ``None``. La comparaison du hash est faite en
        temps constant (``hmac.compare_digest``).
        """
        row = self.conn.execute(
            "SELECT * FROM utilisateurs WHERE identifiant = ?",
            (identifiant.strip(),),
        ).fetchone()
        if row is None or not row["actif"]:
            return None
        _sel, empreinte = _hacher_mot_de_passe(mot_de_passe, row["sel"])
        if not hmac.compare_digest(empreinte, row["mot_de_passe_hash"]):
            return None
        return {"id": row["id"], "identifiant": row["identifiant"],
                "nom": row["nom"] or row["identifiant"], "role": row["role"]}

    def lister_utilisateurs(self) -> list[sqlite3.Row]:
        """Liste les utilisateurs (sans les donnees de mot de passe)."""
        return self.conn.execute(
            "SELECT id, identifiant, nom, role, actif FROM utilisateurs "
            "ORDER BY identifiant"
        ).fetchall()

    def modifier_mot_de_passe(self, utilisateur_id: int, nouveau: str) -> None:
        """Remplace le mot de passe d'un utilisateur (nouveau sel + hash)."""
        if not nouveau:
            raise ValueError("Le mot de passe est obligatoire.")
        sel, empreinte = _hacher_mot_de_passe(nouveau)
        self.conn.execute(
            "UPDATE utilisateurs SET sel = ?, mot_de_passe_hash = ? WHERE id = ?",
            (sel, empreinte, utilisateur_id),
        )
        self.conn.commit()

    def _nombre_admins_actifs(self) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) AS n FROM utilisateurs WHERE role = 'admin' AND actif = 1"
        ).fetchone()
        return int(row["n"])

    def definir_role(self, utilisateur_id: int, role: str) -> None:
        """Change le role d'un utilisateur, sans supprimer le dernier admin actif."""
        if role not in ROLES:
            raise ValueError(f"Role invalide : {role}.")
        actuel = self.conn.execute(
            "SELECT role, actif FROM utilisateurs WHERE id = ?", (utilisateur_id,)
        ).fetchone()
        if (actuel and actuel["role"] == "admin" and actuel["actif"]
                and role != "admin" and self._nombre_admins_actifs() <= 1):
            raise ValueError("Impossible : il doit rester au moins un administrateur actif.")
        self.conn.execute(
            "UPDATE utilisateurs SET role = ? WHERE id = ?", (role, utilisateur_id))
        self.conn.commit()

    def definir_actif(self, utilisateur_id: int, actif: bool) -> None:
        """Active ou desactive un compte, sans desactiver le dernier admin actif."""
        actuel = self.conn.execute(
            "SELECT role, actif FROM utilisateurs WHERE id = ?", (utilisateur_id,)
        ).fetchone()
        if (not actif and actuel and actuel["role"] == "admin" and actuel["actif"]
                and self._nombre_admins_actifs() <= 1):
            raise ValueError("Impossible : il doit rester au moins un administrateur actif.")
        self.conn.execute(
            "UPDATE utilisateurs SET actif = ? WHERE id = ?",
            (1 if actif else 0, utilisateur_id))
        self.conn.commit()

    def supprimer_utilisateur(self, utilisateur_id: int) -> None:
        """Supprime un utilisateur, sans supprimer le dernier admin actif."""
        actuel = self.conn.execute(
            "SELECT role, actif FROM utilisateurs WHERE id = ?", (utilisateur_id,)
        ).fetchone()
        if (actuel and actuel["role"] == "admin" and actuel["actif"]
                and self._nombre_admins_actifs() <= 1):
            raise ValueError("Impossible : il doit rester au moins un administrateur actif.")
        self.conn.execute("DELETE FROM utilisateurs WHERE id = ?", (utilisateur_id,))
        self.conn.commit()
