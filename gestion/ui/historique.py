"""Onglet historique : liste des ventes et detail de la vente selectionnee."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .widgets import format_montant


class OngletHistorique(ttk.Frame):
    def __init__(self, parent, db):
        super().__init__(parent, padding=10)
        self.db = db
        self._construire()
        self.rafraichir()

    def _construire(self):
        ttk.Button(self, text="Rafraichir", command=self.rafraichir).pack(anchor="w", pady=(0, 8))

        panneaux = ttk.Panedwindow(self, orient="horizontal")
        panneaux.pack(fill="both", expand=True)

        # Gauche : liste des ventes.
        cadre_ventes = ttk.LabelFrame(panneaux, text="Ventes", padding=6)
        colonnes = ("id", "date", "client", "total")
        self.table_ventes = ttk.Treeview(cadre_ventes, columns=colonnes,
                                         show="headings", height=15)
        for col, (titre, largeur, ancre) in {
            "id": ("N°", 50, "e"),
            "date": ("Date", 150, "w"),
            "client": ("Client", 180, "w"),
            "total": ("Total", 130, "e"),
        }.items():
            self.table_ventes.heading(col, text=titre)
            self.table_ventes.column(col, width=largeur, anchor=ancre)
        self.table_ventes.pack(fill="both", expand=True)
        self.table_ventes.bind("<<TreeviewSelect>>", self._au_choix_vente)
        panneaux.add(cadre_ventes, weight=3)

        # Droite : detail de la vente.
        cadre_detail = ttk.LabelFrame(panneaux, text="Detail de la vente", padding=6)
        colonnes_d = ("designation", "prix", "quantite", "montant")
        self.table_detail = ttk.Treeview(cadre_detail, columns=colonnes_d,
                                        show="headings", height=15)
        for col, (titre, largeur, ancre) in {
            "designation": ("Designation", 200, "w"),
            "prix": ("Prix unit.", 110, "e"),
            "quantite": ("Qte", 60, "e"),
            "montant": ("Montant", 120, "e"),
        }.items():
            self.table_detail.heading(col, text=titre)
            self.table_detail.column(col, width=largeur, anchor=ancre)
        self.table_detail.pack(fill="both", expand=True)
        panneaux.add(cadre_detail, weight=2)

    def rafraichir(self):
        for item in self.table_ventes.get_children():
            self.table_ventes.delete(item)
        for v in self.db.lister_ventes():
            self.table_ventes.insert(
                "", "end", iid=str(v["id"]),
                values=(v["id"], v["date_vente"], v["client_nom"],
                        format_montant(v["total"])),
            )
        for item in self.table_detail.get_children():
            self.table_detail.delete(item)

    def _au_choix_vente(self, _event=None):
        selection = self.table_ventes.selection()
        if not selection:
            return
        vente_id = int(selection[0])
        for item in self.table_detail.get_children():
            self.table_detail.delete(item)
        for ligne in self.db.lignes_de_vente(vente_id):
            self.table_detail.insert(
                "", "end",
                values=(ligne["designation"], format_montant(ligne["prix_unitaire"]),
                        ligne["quantite"], format_montant(ligne["montant"])),
            )
