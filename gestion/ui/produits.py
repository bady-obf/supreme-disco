"""Onglet de gestion des produits (stock).

CRUD complet : ajouter, modifier, supprimer, rechercher.
Les lignes dont le stock est <= au seuil d'alerte sont mises en evidence.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from .widgets import format_montant, lire_float, lire_int


class OngletProduits(ttk.Frame):
    def __init__(self, parent, db, on_change=None):
        super().__init__(parent, padding=10)
        self.db = db
        # Callback appele apres toute modification (pour rafraichir le tableau de bord).
        self.on_change = on_change
        self.produit_selectionne = None

        self._construire_barre_recherche()
        self._construire_tableau()
        self._construire_formulaire()
        self.rafraichir()

    # ------------------------------------------------------------------ #
    # Construction de l'interface
    # ------------------------------------------------------------------ #
    def _construire_barre_recherche(self):
        barre = ttk.Frame(self)
        barre.pack(fill="x", pady=(0, 8))
        ttk.Label(barre, text="Rechercher :").pack(side="left")
        self.var_recherche = tk.StringVar()
        entree = ttk.Entry(barre, textvariable=self.var_recherche, width=30)
        entree.pack(side="left", padx=6)
        entree.bind("<KeyRelease>", lambda _e: self.rafraichir())
        ttk.Button(barre, text="Effacer", command=self._effacer_recherche).pack(side="left")

    def _construire_tableau(self):
        cadre = ttk.Frame(self)
        cadre.pack(fill="both", expand=True)

        colonnes = ("reference", "designation", "prix_achat", "prix_vente",
                    "quantite", "seuil_alerte")
        self.tableau = ttk.Treeview(cadre, columns=colonnes, show="headings", height=10)

        entetes = {
            "reference": ("Reference", 100),
            "designation": ("Designation", 220),
            "prix_achat": ("Prix achat", 110),
            "prix_vente": ("Prix vente", 110),
            "quantite": ("Stock", 70),
            "seuil_alerte": ("Seuil", 70),
        }
        for col, (titre, largeur) in entetes.items():
            self.tableau.heading(col, text=titre)
            ancre = "e" if col in ("prix_achat", "prix_vente", "quantite", "seuil_alerte") else "w"
            self.tableau.column(col, width=largeur, anchor=ancre)

        # Ligne en rouge clair lorsque le stock est en alerte.
        self.tableau.tag_configure("alerte", background="#ffd6d6")

        defilement = ttk.Scrollbar(cadre, orient="vertical", command=self.tableau.yview)
        self.tableau.configure(yscrollcommand=defilement.set)
        self.tableau.pack(side="left", fill="both", expand=True)
        defilement.pack(side="right", fill="y")

        self.tableau.bind("<<TreeviewSelect>>", self._au_choix_ligne)

    def _construire_formulaire(self):
        form = ttk.LabelFrame(self, text="Fiche produit", padding=10)
        form.pack(fill="x", pady=(10, 0))

        self.var_reference = tk.StringVar()
        self.var_designation = tk.StringVar()
        self.var_prix_achat = tk.StringVar()
        self.var_prix_vente = tk.StringVar()
        self.var_quantite = tk.StringVar()
        self.var_seuil = tk.StringVar()

        champs = [
            ("Reference *", self.var_reference, 0, 0),
            ("Designation *", self.var_designation, 0, 2),
            ("Prix d'achat", self.var_prix_achat, 1, 0),
            ("Prix de vente *", self.var_prix_vente, 1, 2),
            ("Quantite en stock", self.var_quantite, 2, 0),
            ("Seuil d'alerte", self.var_seuil, 2, 2),
        ]
        for libelle, var, ligne, col in champs:
            ttk.Label(form, text=libelle).grid(row=ligne, column=col, sticky="w",
                                               padx=5, pady=4)
            ttk.Entry(form, textvariable=var, width=24).grid(
                row=ligne, column=col + 1, sticky="w", padx=5, pady=4)

        boutons = ttk.Frame(form)
        boutons.grid(row=3, column=0, columnspan=4, pady=(10, 0), sticky="w")
        ttk.Button(boutons, text="Nouveau", command=self._nouveau).pack(side="left", padx=3)
        ttk.Button(boutons, text="Enregistrer", command=self._enregistrer).pack(side="left", padx=3)
        ttk.Button(boutons, text="Supprimer", command=self._supprimer).pack(side="left", padx=3)

    # ------------------------------------------------------------------ #
    # Logique
    # ------------------------------------------------------------------ #
    def rafraichir(self):
        """Recharge le tableau depuis la base."""
        for item in self.tableau.get_children():
            self.tableau.delete(item)
        for p in self.db.lister_produits(self.var_recherche.get()):
            tags = ()
            if p["seuil_alerte"] > 0 and p["quantite"] <= p["seuil_alerte"]:
                tags = ("alerte",)
            self.tableau.insert(
                "", "end", iid=str(p["id"]),
                values=(
                    p["reference"], p["designation"],
                    format_montant(p["prix_achat"]),
                    format_montant(p["prix_vente"]),
                    p["quantite"], p["seuil_alerte"],
                ),
                tags=tags,
            )

    def _effacer_recherche(self):
        self.var_recherche.set("")
        self.rafraichir()

    def _au_choix_ligne(self, _event=None):
        selection = self.tableau.selection()
        if not selection:
            return
        produit = self.db.obtenir_produit(int(selection[0]))
        if produit is None:
            return
        self.produit_selectionne = produit["id"]
        self.var_reference.set(produit["reference"])
        self.var_designation.set(produit["designation"])
        self.var_prix_achat.set(str(produit["prix_achat"]))
        self.var_prix_vente.set(str(produit["prix_vente"]))
        self.var_quantite.set(str(produit["quantite"]))
        self.var_seuil.set(str(produit["seuil_alerte"]))

    def _nouveau(self):
        self.produit_selectionne = None
        for var in (self.var_reference, self.var_designation, self.var_prix_achat,
                    self.var_prix_vente, self.var_quantite, self.var_seuil):
            var.set("")
        if self.tableau.selection():
            self.tableau.selection_remove(self.tableau.selection())

    def _enregistrer(self):
        reference = self.var_reference.get().strip()
        designation = self.var_designation.get().strip()
        if not reference or not designation:
            messagebox.showwarning(
                "Champs requis",
                "La reference et la designation sont obligatoires.",
            )
            return

        prix_achat = lire_float(self.var_prix_achat.get())
        prix_vente = lire_float(self.var_prix_vente.get())
        quantite = lire_int(self.var_quantite.get())
        seuil = lire_int(self.var_seuil.get())

        try:
            if self.produit_selectionne is None:
                self.db.ajouter_produit(reference, designation, prix_achat,
                                        prix_vente, quantite, seuil)
                message = "Produit ajoute."
            else:
                self.db.modifier_produit(self.produit_selectionne, reference,
                                         designation, prix_achat, prix_vente,
                                         quantite, seuil)
                message = "Produit modifie."
        except Exception as err:  # ex. reference deja utilisee
            messagebox.showerror(
                "Erreur",
                f"Impossible d'enregistrer le produit.\n\n{err}\n\n"
                "Astuce : la reference doit etre unique.",
            )
            return

        self._nouveau()
        self.rafraichir()
        if self.on_change:
            self.on_change()
        messagebox.showinfo("Succes", message)

    def _supprimer(self):
        if self.produit_selectionne is None:
            messagebox.showinfo("Aucune selection", "Selectionnez d'abord un produit.")
            return
        if not messagebox.askyesno("Confirmation", "Supprimer ce produit ?"):
            return
        self.db.supprimer_produit(self.produit_selectionne)
        self._nouveau()
        self.rafraichir()
        if self.on_change:
            self.on_change()
