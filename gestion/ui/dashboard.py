"""Onglet tableau de bord : indicateurs cles et alertes de stock."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .widgets import format_montant


class OngletDashboard(ttk.Frame):
    def __init__(self, parent, db):
        super().__init__(parent, padding=15)
        self.db = db
        self._construire_cartes()
        self._construire_alertes()
        self.rafraichir()

    def _construire_cartes(self):
        cadre = ttk.Frame(self)
        cadre.pack(fill="x")

        # Chaque carte est un LabelFrame contenant une grande valeur.
        self._valeurs = {}
        cartes = [
            ("ca_jour", "Chiffre d'affaires du jour"),
            ("ventes_jour", "Ventes du jour"),
            ("valeur_stock", "Valeur du stock"),
            ("nb_produits", "Produits references"),
            ("nb_clients", "Clients"),
        ]
        for i, (cle, titre) in enumerate(cartes):
            carte = ttk.LabelFrame(cadre, text=titre, padding=12)
            carte.grid(row=i // 3, column=i % 3, padx=8, pady=8, sticky="nsew")
            cadre.columnconfigure(i % 3, weight=1)
            valeur = ttk.Label(carte, text="-", font=("TkDefaultFont", 16, "bold"))
            valeur.pack()
            self._valeurs[cle] = valeur

    def _construire_alertes(self):
        cadre = ttk.LabelFrame(self, text="Alertes de stock (a reapprovisionner)", padding=10)
        cadre.pack(fill="both", expand=True, pady=(12, 0))

        colonnes = ("reference", "designation", "quantite", "seuil")
        self.tableau = ttk.Treeview(cadre, columns=colonnes, show="headings", height=8)
        for col, (titre, largeur, ancre) in {
            "reference": ("Reference", 120, "w"),
            "designation": ("Designation", 300, "w"),
            "quantite": ("Stock actuel", 110, "e"),
            "seuil": ("Seuil d'alerte", 110, "e"),
        }.items():
            self.tableau.heading(col, text=titre)
            self.tableau.column(col, width=largeur, anchor=ancre)
        self.tableau.tag_configure("alerte", background="#ffd6d6")

        defilement = ttk.Scrollbar(cadre, orient="vertical", command=self.tableau.yview)
        self.tableau.configure(yscrollcommand=defilement.set)
        self.tableau.pack(side="left", fill="both", expand=True)
        defilement.pack(side="right", fill="y")

        self.label_aucune = ttk.Label(self, text="")
        self.label_aucune.pack(anchor="w", pady=(6, 0))

    def rafraichir(self):
        """Recalcule tous les indicateurs et la liste d'alertes."""
        self._valeurs["ca_jour"].config(text=format_montant(self.db.chiffre_affaires_jour()))
        self._valeurs["ventes_jour"].config(text=str(self.db.nombre_ventes_jour()))
        self._valeurs["valeur_stock"].config(text=format_montant(self.db.valeur_stock()))
        self._valeurs["nb_produits"].config(text=str(self.db.nombre_produits()))
        self._valeurs["nb_clients"].config(text=str(self.db.nombre_clients()))

        for item in self.tableau.get_children():
            self.tableau.delete(item)
        alertes = self.db.produits_en_alerte()
        for p in alertes:
            self.tableau.insert(
                "", "end",
                values=(p["reference"], p["designation"], p["quantite"], p["seuil_alerte"]),
                tags=("alerte",),
            )
        if alertes:
            self.label_aucune.config(text=f"{len(alertes)} produit(s) a reapprovisionner.")
        else:
            self.label_aucune.config(text="Aucune alerte : tous les stocks sont au-dessus du seuil.")
