"""Onglet rapports : generation de rapports par periode en Excel (.xlsx) ou CSV."""

from __future__ import annotations

import tkinter as tk
import webbrowser
from datetime import date, datetime
from pathlib import Path
from tkinter import messagebox, ttk

from .. import rapports


class OngletRapports(ttk.Frame):
    def __init__(self, parent, db):
        super().__init__(parent, padding=15)
        self.db = db
        self._construire()

    def _construire(self):
        options = ttk.LabelFrame(self, text="Parametres du rapport", padding=12)
        options.pack(fill="x")

        ttk.Label(options, text="Type de rapport :").grid(row=0, column=0, sticky="w",
                                                          padx=5, pady=6)
        self.var_type = tk.StringVar()
        self.combo_type = ttk.Combobox(options, textvariable=self.var_type,
                                      state="readonly", width=32,
                                      values=list(rapports.RAPPORTS.keys()))
        self.combo_type.grid(row=0, column=1, sticky="w", padx=5, pady=6)
        self.combo_type.current(0)
        self.combo_type.bind("<<ComboboxSelected>>", lambda _e: self._maj_etat_dates())

        # Periode.
        premier_jour = date.today().replace(day=1).strftime("%Y-%m-%d")
        aujourdhui = date.today().strftime("%Y-%m-%d")
        ttk.Label(options, text="Du (AAAA-MM-JJ) :").grid(row=1, column=0, sticky="w",
                                                         padx=5, pady=6)
        self.var_debut = tk.StringVar(value=premier_jour)
        self.entree_debut = ttk.Entry(options, textvariable=self.var_debut, width=16)
        self.entree_debut.grid(row=1, column=1, sticky="w", padx=5, pady=6)

        ttk.Label(options, text="Au (AAAA-MM-JJ) :").grid(row=2, column=0, sticky="w",
                                                        padx=5, pady=6)
        self.var_fin = tk.StringVar(value=aujourdhui)
        self.entree_fin = ttk.Entry(options, textvariable=self.var_fin, width=16)
        self.entree_fin.grid(row=2, column=1, sticky="w", padx=5, pady=6)

        # Raccourcis de periode.
        raccourcis = ttk.Frame(options)
        raccourcis.grid(row=3, column=0, columnspan=2, sticky="w", padx=5, pady=6)
        ttk.Button(raccourcis, text="Aujourd'hui",
                   command=self._periode_aujourdhui).pack(side="left", padx=3)
        ttk.Button(raccourcis, text="Ce mois",
                   command=self._periode_mois).pack(side="left", padx=3)
        ttk.Button(raccourcis, text="Cette annee",
                   command=self._periode_annee).pack(side="left", padx=3)

        # Boutons d'export.
        boutons = ttk.Frame(self)
        boutons.pack(fill="x", pady=(14, 0))
        ttk.Button(boutons, text="Generer Excel (.xlsx)",
                   command=lambda: self._generer("xlsx")).pack(side="left", padx=4)
        ttk.Button(boutons, text="Generer CSV",
                   command=lambda: self._generer("csv")).pack(side="left", padx=4)

        # Apercu.
        cadre_apercu = ttk.LabelFrame(self, text="Apercu", padding=10)
        cadre_apercu.pack(fill="both", expand=True, pady=(14, 0))
        self.apercu = tk.Text(cadre_apercu, height=10, wrap="word", state="disabled")
        self.apercu.pack(fill="both", expand=True)

        self._maj_etat_dates()

    def _maj_etat_dates(self):
        """Active/desactive les champs date selon que le rapport a besoin d'une periode."""
        _fonction, besoin_periode = rapports.RAPPORTS[self.var_type.get()]
        etat = "normal" if besoin_periode else "disabled"
        self.entree_debut.configure(state=etat)
        self.entree_fin.configure(state=etat)

    def _periode_aujourdhui(self):
        j = date.today().strftime("%Y-%m-%d")
        self.var_debut.set(j)
        self.var_fin.set(j)

    def _periode_mois(self):
        self.var_debut.set(date.today().replace(day=1).strftime("%Y-%m-%d"))
        self.var_fin.set(date.today().strftime("%Y-%m-%d"))

    def _periode_annee(self):
        self.var_debut.set(date.today().replace(month=1, day=1).strftime("%Y-%m-%d"))
        self.var_fin.set(date.today().strftime("%Y-%m-%d"))

    def _valider_date(self, texte: str) -> bool:
        try:
            datetime.strptime(texte.strip(), "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def _generer(self, fmt: str):
        libelle = self.var_type.get()
        fonction, besoin_periode = rapports.RAPPORTS[libelle]

        d1 = self.var_debut.get().strip()
        d2 = self.var_fin.get().strip()
        if besoin_periode:
            if not self._valider_date(d1) or not self._valider_date(d2):
                messagebox.showwarning("Dates invalides",
                                       "Utilisez le format AAAA-MM-JJ (ex. 2026-09-13).")
                return
            if d1 > d2:
                messagebox.showwarning("Periode invalide",
                                       "La date de debut doit preceder la date de fin.")
                return

        base_nom, feuilles = fonction(self.db, d1, d2)
        try:
            if fmt == "xlsx":
                chemin = rapports.exporter_xlsx(feuilles, base_nom)
            else:
                chemin = rapports.exporter_csv(feuilles, base_nom)
        except Exception as err:
            messagebox.showerror("Erreur", f"Export impossible.\n\n{err}")
            return

        self._afficher_apercu(feuilles)
        chemin_abs = str(Path(chemin).resolve())
        if messagebox.askyesno(
            "Rapport genere",
            f"Fichier enregistre :\n{chemin_abs}\n\nOuvrir le fichier maintenant ?",
        ):
            try:
                webbrowser.open(Path(chemin_abs).as_uri())
            except Exception:
                pass

    def _afficher_apercu(self, feuilles: list[dict]):
        lignes = []
        for feuille in feuilles:
            lignes.append(f"=== {feuille['nom']} ===")
            if feuille["entetes"]:
                lignes.append(" | ".join(str(e) for e in feuille["entetes"]))
            for ligne in feuille["lignes"][:15]:
                lignes.append(" | ".join(str(c) for c in ligne))
            if len(feuille["lignes"]) > 15:
                lignes.append(f"... ({len(feuille['lignes']) - 15} lignes de plus)")
            lignes.append("")
        self.apercu.configure(state="normal")
        self.apercu.delete("1.0", "end")
        self.apercu.insert("1.0", "\n".join(lignes))
        self.apercu.configure(state="disabled")

    def rafraichir(self):
        # Rien a precharger : le rapport est genere a la demande.
        pass
