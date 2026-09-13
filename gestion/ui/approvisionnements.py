"""Onglet de saisie d'un approvisionnement (entree de stock).

Fonctionnement (symetrique de la vente, mais le stock AUGMENTE) :
1. On choisit un fournisseur.
2. On ajoute des produits (produit + quantite + prix d'achat).
3. On valide : l'approvisionnement est enregistre et le stock est incremente.
   Le prix d'achat du produit peut etre mis a jour (case a cocher).
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from .widgets import format_montant, lire_float, lire_int


class OngletApprovisionnements(ttk.Frame):
    def __init__(self, parent, db, on_change=None):
        super().__init__(parent, padding=10)
        self.db = db
        self.on_change = on_change
        # Panier : {produit_id, designation, prix_achat, quantite}.
        self.panier = []
        self._map_fournisseurs = {}
        self._map_produits = {}

        self._construire_entete()
        self._construire_ligne_ajout()
        self._construire_panier()
        self._construire_pied()
        self.rafraichir()

    def _construire_entete(self):
        entete = ttk.Frame(self)
        entete.pack(fill="x", pady=(0, 10))
        ttk.Label(entete, text="Fournisseur :").pack(side="left")
        self.var_fournisseur = tk.StringVar()
        self.combo_fournisseur = ttk.Combobox(entete, textvariable=self.var_fournisseur,
                                             state="readonly", width=35)
        self.combo_fournisseur.pack(side="left", padx=6)

        self.var_maj_prix = tk.BooleanVar(value=True)
        ttk.Checkbutton(entete, text="Mettre a jour le prix d'achat des produits",
                        variable=self.var_maj_prix).pack(side="left", padx=12)

    def _construire_ligne_ajout(self):
        cadre = ttk.LabelFrame(self, text="Ajouter un article", padding=10)
        cadre.pack(fill="x")

        ttk.Label(cadre, text="Produit :").grid(row=0, column=0, padx=5, pady=4, sticky="w")
        self.var_produit = tk.StringVar()
        self.combo_produit = ttk.Combobox(cadre, textvariable=self.var_produit,
                                          state="readonly", width=38)
        self.combo_produit.grid(row=0, column=1, padx=5, pady=4, sticky="w")
        self.combo_produit.bind("<<ComboboxSelected>>", self._prefill_prix)

        ttk.Label(cadre, text="Quantite :").grid(row=0, column=2, padx=5, pady=4, sticky="w")
        self.var_quantite = tk.StringVar(value="1")
        ttk.Entry(cadre, textvariable=self.var_quantite, width=8).grid(
            row=0, column=3, padx=5, pady=4, sticky="w")

        ttk.Label(cadre, text="Prix d'achat :").grid(row=0, column=4, padx=5, pady=4, sticky="w")
        self.var_prix = tk.StringVar()
        ttk.Entry(cadre, textvariable=self.var_prix, width=10).grid(
            row=0, column=5, padx=5, pady=4, sticky="w")

        ttk.Button(cadre, text="Ajouter", command=self._ajouter_au_panier).grid(
            row=0, column=6, padx=8, pady=4)

    def _construire_panier(self):
        cadre = ttk.Frame(self)
        cadre.pack(fill="both", expand=True, pady=(10, 0))
        colonnes = ("designation", "prix", "quantite", "montant")
        self.tableau = ttk.Treeview(cadre, columns=colonnes, show="headings", height=8)
        for col, (titre, largeur, ancre) in {
            "designation": ("Designation", 260, "w"),
            "prix": ("Prix d'achat", 130, "e"),
            "quantite": ("Quantite", 90, "e"),
            "montant": ("Montant", 140, "e"),
        }.items():
            self.tableau.heading(col, text=titre)
            self.tableau.column(col, width=largeur, anchor=ancre)
        defilement = ttk.Scrollbar(cadre, orient="vertical", command=self.tableau.yview)
        self.tableau.configure(yscrollcommand=defilement.set)
        self.tableau.pack(side="left", fill="both", expand=True)
        defilement.pack(side="right", fill="y")

    def _construire_pied(self):
        pied = ttk.Frame(self)
        pied.pack(fill="x", pady=(10, 0))
        ttk.Button(pied, text="Retirer la ligne", command=self._retirer_ligne).pack(side="left")
        ttk.Button(pied, text="Vider", command=self._vider_panier).pack(side="left", padx=6)

        self.var_total = tk.StringVar(value=format_montant(0))
        ttk.Label(pied, textvariable=self.var_total,
                  font=("TkDefaultFont", 12, "bold")).pack(side="right", padx=10)
        ttk.Label(pied, text="TOTAL :").pack(side="right")
        ttk.Button(pied, text="Valider l'approvisionnement",
                   command=self._valider).pack(side="right", padx=20)

    # ------------------------------------------------------------------ #
    def rafraichir(self):
        fournisseurs = self.db.lister_fournisseurs()
        self._map_fournisseurs = {"Fournisseur inconnu": None}
        for f in fournisseurs:
            self._map_fournisseurs[f["nom"]] = f["id"]
        self.combo_fournisseur["values"] = list(self._map_fournisseurs.keys())
        if not self.var_fournisseur.get():
            self.var_fournisseur.set("Fournisseur inconnu")

        produits = self.db.lister_produits()
        self._map_produits = {}
        libelles = []
        for p in produits:
            libelle = f"{p['designation']} (stock: {p['quantite']})"
            self._map_produits[libelle] = p["id"]
            libelles.append(libelle)
        self.combo_produit["values"] = libelles

    def _prefill_prix(self, _event=None):
        """Pre-remplit le prix d'achat avec celui du produit choisi."""
        libelle = self.var_produit.get()
        pid = self._map_produits.get(libelle)
        if pid is not None:
            produit = self.db.obtenir_produit(pid)
            if produit is not None:
                self.var_prix.set(str(produit["prix_achat"]))

    def _ajouter_au_panier(self):
        libelle = self.var_produit.get()
        if not libelle or libelle not in self._map_produits:
            messagebox.showwarning("Produit", "Choisissez un produit dans la liste.")
            return
        quantite = lire_int(self.var_quantite.get())
        if quantite <= 0:
            messagebox.showwarning("Quantite", "La quantite doit etre superieure a zero.")
            return
        produit_id = self._map_produits[libelle]
        produit = self.db.obtenir_produit(produit_id)
        if produit is None:
            messagebox.showerror("Erreur", "Produit introuvable.")
            self.rafraichir()
            return
        prix_achat = lire_float(self.var_prix.get(), produit["prix_achat"])

        for ligne in self.panier:
            if ligne["produit_id"] == produit_id:
                ligne["quantite"] += quantite
                ligne["prix_achat"] = prix_achat
                break
        else:
            self.panier.append({
                "produit_id": produit_id,
                "designation": produit["designation"],
                "prix_achat": prix_achat,
                "quantite": quantite,
            })
        self.var_quantite.set("1")
        self.var_prix.set("")
        self.var_produit.set("")
        self._afficher_panier()

    def _afficher_panier(self):
        for item in self.tableau.get_children():
            self.tableau.delete(item)
        total = 0.0
        for i, ligne in enumerate(self.panier):
            montant = ligne["prix_achat"] * ligne["quantite"]
            total += montant
            self.tableau.insert(
                "", "end", iid=str(i),
                values=(ligne["designation"], format_montant(ligne["prix_achat"]),
                        ligne["quantite"], format_montant(montant)),
            )
        self.var_total.set(format_montant(total))

    def _retirer_ligne(self):
        selection = self.tableau.selection()
        if not selection:
            messagebox.showinfo("Aucune selection", "Selectionnez une ligne.")
            return
        index = int(selection[0])
        if 0 <= index < len(self.panier):
            del self.panier[index]
        self._afficher_panier()

    def _vider_panier(self):
        self.panier = []
        self._afficher_panier()

    def _valider(self):
        if not self.panier:
            messagebox.showwarning("Panier vide", "Ajoutez au moins un article.")
            return
        fournisseur_id = self._map_fournisseurs.get(self.var_fournisseur.get())
        lignes = [{"produit_id": l["produit_id"], "quantite": l["quantite"],
                   "prix_achat": l["prix_achat"]} for l in self.panier]
        try:
            appro_id = self.db.enregistrer_approvisionnement(
                fournisseur_id, lignes, maj_prix_achat=self.var_maj_prix.get())
        except Exception as err:
            messagebox.showerror("Erreur", f"Approvisionnement non enregistre.\n\n{err}")
            return
        messagebox.showinfo("Enregistre",
                            f"Approvisionnement n°{appro_id} enregistre. Stock mis a jour.")
        self._vider_panier()
        self.var_fournisseur.set("Fournisseur inconnu")
        self.rafraichir()
        if self.on_change:
            self.on_change()
