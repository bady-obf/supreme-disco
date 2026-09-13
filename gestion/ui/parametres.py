"""Onglet parametres : informations de l'entreprise imprimees sur les factures."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk


class OngletParametres(ttk.Frame):
    def __init__(self, parent, db, on_change=None):
        super().__init__(parent, padding=15)
        self.db = db
        self.on_change = on_change
        self._construire()
        self.rafraichir()

    def _construire(self):
        cadre = ttk.LabelFrame(self, text="Informations de l'entreprise (factures)",
                               padding=12)
        cadre.pack(fill="x")

        self.var_nom = tk.StringVar()
        self.var_adresse = tk.StringVar()
        self.var_telephone = tk.StringVar()
        self.var_email = tk.StringVar()
        self.var_tva = tk.StringVar()

        champs = [
            ("Nom de l'entreprise", self.var_nom),
            ("Adresse", self.var_adresse),
            ("Telephone", self.var_telephone),
            ("Email", self.var_email),
            ("Taux de TVA par defaut (%)", self.var_tva),
        ]
        for i, (libelle, var) in enumerate(champs):
            ttk.Label(cadre, text=libelle).grid(row=i, column=0, sticky="w", padx=5, pady=6)
            ttk.Entry(cadre, textvariable=var, width=45).grid(
                row=i, column=1, sticky="w", padx=5, pady=6)

        ttk.Button(cadre, text="Enregistrer", command=self._enregistrer).grid(
            row=len(champs), column=1, sticky="w", padx=5, pady=(10, 0))

        ttk.Label(
            self,
            text="Ces informations apparaissent en en-tete des factures imprimees.",
            foreground="#666",
        ).pack(anchor="w", pady=(10, 0))

    def rafraichir(self):
        infos = self.db.parametres_entreprise()
        self.var_nom.set(infos["entreprise_nom"])
        self.var_adresse.set(infos["entreprise_adresse"])
        self.var_telephone.set(infos["entreprise_telephone"])
        self.var_email.set(infos["entreprise_email"])
        self.var_tva.set(infos.get("taux_tva", "0"))

    def _enregistrer(self):
        self.db.definir_parametre("entreprise_nom", self.var_nom.get().strip())
        self.db.definir_parametre("entreprise_adresse", self.var_adresse.get().strip())
        self.db.definir_parametre("entreprise_telephone", self.var_telephone.get().strip())
        self.db.definir_parametre("entreprise_email", self.var_email.get().strip())
        # Valide le taux de TVA (nombre >= 0).
        taux = self.var_tva.get().strip().replace(",", ".")
        try:
            valeur = float(taux) if taux else 0.0
            if valeur < 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("TVA invalide",
                                   "Le taux de TVA doit etre un nombre positif (ex. 18).")
            return
        self.db.definir_parametre("taux_tva", str(valeur))
        if self.on_change:
            self.on_change()
        messagebox.showinfo("Succes", "Parametres enregistres.")
