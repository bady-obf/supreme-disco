"""Onglet parametres : infos entreprise, TVA, et sauvegarde/restauration."""

from __future__ import annotations

import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


class OngletParametres(ttk.Frame):
    def __init__(self, parent, db, on_change=None, on_restore=None):
        super().__init__(parent, padding=15)
        self.db = db
        self.on_change = on_change
        # Callback appele apres une restauration (rafraichit TOUS les ecrans).
        self.on_restore = on_restore
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

        # --- Sauvegarde / restauration ---
        cadre_sauv = ttk.LabelFrame(self, text="Sauvegarde et restauration",
                                    padding=12)
        cadre_sauv.pack(fill="x", pady=(16, 0))
        ttk.Button(cadre_sauv, text="Sauvegarder la base...",
                   command=self._sauvegarder).pack(side="left", padx=4)
        ttk.Button(cadre_sauv, text="Restaurer une sauvegarde...",
                   command=self._restaurer).pack(side="left", padx=4)
        ttk.Label(
            self,
            text="La sauvegarde copie toutes vos donnees dans un fichier .db. "
                 "La restauration remplace les donnees actuelles par celles du fichier choisi.",
            foreground="#666", wraplength=560, justify="left",
        ).pack(anchor="w", pady=(8, 0))

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

    def _sauvegarder(self):
        nom_defaut = "gestion_sauvegarde_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".db"
        chemin = filedialog.asksaveasfilename(
            title="Enregistrer la sauvegarde",
            defaultextension=".db",
            initialfile=nom_defaut,
            filetypes=[("Base de donnees", "*.db"), ("Tous les fichiers", "*.*")],
        )
        if not chemin:
            return
        try:
            self.db.sauvegarder(chemin)
        except Exception as err:
            messagebox.showerror("Erreur", f"Sauvegarde impossible.\n\n{err}")
            return
        messagebox.showinfo("Sauvegarde",
                            f"Sauvegarde enregistree :\n{Path(chemin).resolve()}")

    def _restaurer(self):
        chemin = filedialog.askopenfilename(
            title="Choisir une sauvegarde a restaurer",
            filetypes=[("Base de donnees", "*.db"), ("Tous les fichiers", "*.*")],
        )
        if not chemin:
            return
        if not messagebox.askyesno(
            "Confirmation",
            "La restauration va REMPLACER toutes les donnees actuelles par "
            "celles de la sauvegarde choisie.\n\nContinuer ?",
        ):
            return
        try:
            self.db.restaurer(chemin)
        except Exception as err:
            messagebox.showerror("Erreur", f"Restauration impossible.\n\n{err}")
            return
        self.rafraichir()
        if self.on_restore:
            self.on_restore()
        messagebox.showinfo("Restauration",
                            "Donnees restaurees avec succes.")
