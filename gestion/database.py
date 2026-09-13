"""Couche d'acces aux donnees (SQLite).

Ce module ne depend PAS de tkinter : il peut donc etre importe et teste
sans interface graphique. Toutes les operations metier (produits, clients,
ventes, statistiques) passent par la classe :class:`Database`.

Reference : bibliotheque standard Python ``sqlite3``
https://docs.python.org/3/library/sqlite3.html
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
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
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    date_vente TEXT NOT NULL,
    client_id  INTEGER,
    total      REAL NOT NULL DEFAULT 0,
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
"""


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
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def fermer(self) -> None:
        """Ferme la connexion a la base."""
        self.conn.close()

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
        self, client_id: int | None, lignes: list[dict]
    ) -> int:
        """Enregistre une vente et decremente le stock, en une transaction.

        ``lignes`` est une liste de dictionnaires :
        ``{"produit_id": int, "quantite": int}``.

        Leve :class:`StockInsuffisant` si un produit n'a pas assez de stock ;
        dans ce cas AUCUNE modification n'est appliquee (rollback).
        Retourne l'identifiant de la vente creee.
        """
        if not lignes:
            raise ValueError("Une vente doit contenir au moins une ligne.")

        try:
            # Verifie d'abord la disponibilite de tout le panier.
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
                if quantite > produit["quantite"]:
                    raise StockInsuffisant(
                        f"Stock insuffisant pour « {produit['designation']} » : "
                        f"demande {quantite}, disponible {produit['quantite']}."
                    )
                montant = quantite * produit["prix_vente"]
                total += montant
                details.append((produit, quantite, montant))

            # Enregistre l'entete de vente.
            cur = self.conn.execute(
                "INSERT INTO ventes (date_vente, client_id, total) VALUES (?, ?, ?)",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), client_id, total),
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
