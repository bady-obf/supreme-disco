"""Graphique (histogramme) du chiffre d'affaires par jour.

Dessine directement sur un ``tkinter.Canvas`` : aucune dependance externe
(pas de matplotlib). Le graphique s'adapte a la taille disponible et se
redessine lors du redimensionnement.

Reference : ``tkinter.Canvas``
https://docs.python.org/3/library/tkinter.html
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .widgets import format_montant

COULEUR_BARRE = "#3b7dd8"
COULEUR_BARRE_JOUR = "#f5a623"   # met en avant le dernier jour (aujourd'hui)
COULEUR_AXE = "#999999"
COULEUR_TEXTE = "#444444"


class GraphiqueVentes(ttk.Frame):
    def __init__(self, parent, db, nb_jours: int = 14):
        super().__init__(parent)
        self.db = db
        self.nb_jours = nb_jours
        self.donnees: list[tuple[str, float]] = []

        titre = f"Chiffre d'affaires des {nb_jours} derniers jours"
        ttk.Label(self, text=titre, font=("TkDefaultFont", 10, "bold")).pack(anchor="w")

        self.canvas = tk.Canvas(self, height=200, background="white",
                                highlightthickness=1, highlightbackground="#ddd")
        self.canvas.pack(fill="both", expand=True)
        # Redessine quand la taille change.
        self.canvas.bind("<Configure>", lambda _e: self._dessiner())

    def rafraichir(self):
        """Recharge les donnees et redessine."""
        self.donnees = self.db.ca_par_jour(self.nb_jours)
        self._dessiner()

    def _dessiner(self):
        c = self.canvas
        c.delete("all")
        largeur = c.winfo_width()
        hauteur = c.winfo_height()
        if largeur < 20 or hauteur < 20:
            return  # canvas pas encore dimensionne

        if not self.donnees:
            self.donnees = self.db.ca_par_jour(self.nb_jours)

        marge_g, marge_d, marge_h, marge_b = 60, 12, 14, 26
        aire_l = largeur - marge_g - marge_d
        aire_h = hauteur - marge_h - marge_b
        base_y = marge_h + aire_h

        valeurs = [v for _, v in self.donnees]
        maxi = max(valeurs) if valeurs else 0

        # Axe horizontal (base).
        c.create_line(marge_g, base_y, largeur - marge_d, base_y, fill=COULEUR_AXE)

        if maxi <= 0:
            c.create_text(largeur / 2, hauteur / 2,
                          text="Aucune vente sur la periode",
                          fill=COULEUR_TEXTE)
            return

        # Ligne et etiquette du maximum.
        c.create_line(marge_g, marge_h, largeur - marge_d, marge_h,
                      fill="#eeeeee")
        c.create_text(marge_g - 6, marge_h, anchor="e",
                      text=format_montant(maxi), fill=COULEUR_TEXTE,
                      font=("TkDefaultFont", 8))
        c.create_text(marge_g - 6, base_y, anchor="e", text="0",
                      fill=COULEUR_TEXTE, font=("TkDefaultFont", 8))

        n = len(self.donnees)
        pas = aire_l / n
        largeur_barre = max(4, pas * 0.6)

        for i, (jour, valeur) in enumerate(self.donnees):
            centre_x = marge_g + pas * (i + 0.5)
            hauteur_barre = (valeur / maxi) * aire_h if maxi else 0
            x0 = centre_x - largeur_barre / 2
            x1 = centre_x + largeur_barre / 2
            y0 = base_y - hauteur_barre
            couleur = COULEUR_BARRE_JOUR if i == n - 1 else COULEUR_BARRE
            if hauteur_barre > 0:
                c.create_rectangle(x0, y0, x1, base_y, fill=couleur, outline="")
            # Etiquette du jour (JJ) sous la barre.
            c.create_text(centre_x, base_y + 12, text=jour[-2:],
                          fill=COULEUR_TEXTE, font=("TkDefaultFont", 8))
