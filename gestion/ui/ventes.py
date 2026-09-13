"""Onglet de saisie d'une nouvelle vente.

Fonctionnement :
1. On choisit un client (ou « Client de passage »).
2. On ajoute des produits au panier (produit + quantite).
3. On valide : la vente est enregistree et le stock est decremente
   (operation atomique cote base de donnees).
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from ..database import StockInsuffisant
from .widgets import format_montant, lire_int


class OngletVentes(ttk.Frame):
    def __init__(self, parent, db, on_change=None):
        super().__init__(parent, padding=10)
        self.db = db
        self.on_change = on_change
        # Panier en memoire : liste de dicts {produit_id, designation, prix, quantite}.
        self.panier = []
        # Correspondance libelle affiche -> identifiant (produits / clients).
        self._map_produits = {}
        self._map_clients = {}

        self._construire_entete()
        self._construire_ligne_ajout()
        self._construire_panier()
        self._construire_pied()
        self.rafraichir()

    def _construire_entete(self):
        entete = ttk.Frame(self)
        entete.pack(fill="x", pady=(0, 10))
        ttk.Label(entete, text="Client :").pack(side="left")
        self.var_client = tk.StringVar()
        self.combo_client = ttk.Combobox(entete, textvariable=self.var_client,
                                         state="readonly", width=35)
        self.combo_client.pack(side="left", padx=6)

    def _construire_ligne_ajout(self):
        cadre = ttk.LabelFrame(self, text="Ajouter un article", padding=10)
        cadre.pack(fill="x")

        ttk.Label(cadre, text="Produit :").grid(row=0, column=0, padx=5, pady=4, sticky="w")
        self.var_produit = tk.StringVar()
        self.combo_produit = ttk.Combobox(cadre, textvariable=self.var_produit,
                                          state="readonly", width=40)
        self.combo_produit.grid(row=0, column=1, padx=5, pady=4, sticky="w")

        ttk.Label(cadre, text="Quantite :").grid(row=0, column=2, padx=5, pady=4, sticky="w")
        self.var_quantite = tk.StringVar(value="1")
        ttk.Entry(cadre, textvariable=self.var_quantite, width=8).grid(
            row=0, column=3, padx=5, pady=4, sticky="w")

        ttk.Button(cadre, text="Ajouter au panier", command=self._ajouter_au_panier).grid(
            row=0, column=4, padx=8, pady=4)

    def _construire_panier(self):
        cadre = ttk.Frame(self)
        cadre.pack(fill="both", expand=True, pady=(10, 0))

        colonnes = ("designation", "prix", "quantite", "montant")
        self.tableau = ttk.Treeview(cadre, columns=colonnes, show="headings", height=8)
        for col, (titre, largeur, ancre) in {
            "designation": ("Designation", 260, "w"),
            "prix": ("Prix unitaire", 130, "e"),
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
        ttk.Button(pied, text="Vider le panier", command=self._vider_panier).pack(side="left", padx=6)

        self.var_total = tk.StringVar(value=format_montant(0))
        ttk.Label(pied, textvariable=self.var_total, font=("TkDefaultFont", 12, "bold")
                  ).pack(side="right", padx=10)
        ttk.Label(pied, text="TOTAL :").pack(side="right")

        ttk.Button(pied, text="Valider la vente", command=self._valider_vente).pack(
            side="right", padx=20)

    # ------------------------------------------------------------------ #
    # Logique
    # ------------------------------------------------------------------ #
    def rafraichir(self):
        """Recharge les listes deroulantes clients/produits."""
        clients = self.db.lister_clients()
        self._map_clients = {"Client de passage": None}
        for c in clients:
            self._map_clients[f"{c['nom']}"] = c["id"]
        self.combo_client["values"] = list(self._map_clients.keys())
        if not self.var_client.get():
            self.var_client.set("Client de passage")

        produits = self.db.lister_produits()
        self._map_produits = {}
        libelles = []
        for p in produits:
            libelle = f"{p['designation']} (stock: {p['quantite']}) - {format_montant(p['prix_vente'])}"
            self._map_produits[libelle] = p["id"]
            libelles.append(libelle)
        self.combo_produit["values"] = libelles

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

        # Quantite deja presente dans le panier pour ce produit.
        deja = sum(l["quantite"] for l in self.panier if l["produit_id"] == produit_id)
        if quantite + deja > produit["quantite"]:
            messagebox.showwarning(
                "Stock insuffisant",
                f"Stock disponible pour « {produit['designation']} » : "
                f"{produit['quantite']} (deja {deja} au panier).",
            )
            return

        # Fusionne avec une ligne existante du meme produit, sinon ajoute.
        for ligne in self.panier:
            if ligne["produit_id"] == produit_id:
                ligne["quantite"] += quantite
                break
        else:
            self.panier.append({
                "produit_id": produit_id,
                "designation": produit["designation"],
                "prix": produit["prix_vente"],
                "quantite": quantite,
            })

        self.var_quantite.set("1")
        self._afficher_panier()

    def _afficher_panier(self):
        for item in self.tableau.get_children():
            self.tableau.delete(item)
        total = 0.0
        for i, ligne in enumerate(self.panier):
            montant = ligne["prix"] * ligne["quantite"]
            total += montant
            self.tableau.insert(
                "", "end", iid=str(i),
                values=(ligne["designation"], format_montant(ligne["prix"]),
                        ligne["quantite"], format_montant(montant)),
            )
        self.var_total.set(format_montant(total))

    def _retirer_ligne(self):
        selection = self.tableau.selection()
        if not selection:
            messagebox.showinfo("Aucune selection", "Selectionnez une ligne du panier.")
            return
        index = int(selection[0])
        if 0 <= index < len(self.panier):
            del self.panier[index]
        self._afficher_panier()

    def _vider_panier(self):
        self.panier = []
        self._afficher_panier()

    def _valider_vente(self):
        if not self.panier:
            messagebox.showwarning("Panier vide", "Ajoutez au moins un article.")
            return
        client_id = self._map_clients.get(self.var_client.get())
        lignes = [{"produit_id": l["produit_id"], "quantite": l["quantite"]}
                  for l in self.panier]
        try:
            vente_id = self.db.enregistrer_vente(client_id, lignes)
        except StockInsuffisant as err:
            messagebox.showerror("Stock insuffisant", str(err))
            return
        except Exception as err:
            messagebox.showerror("Erreur", f"Vente non enregistree.\n\n{err}")
            return

        messagebox.showinfo("Vente enregistree", f"Vente n°{vente_id} enregistree avec succes.")
        self._vider_panier()
        self.var_client.set("Client de passage")
        self.rafraichir()
        if self.on_change:
            self.on_change()
