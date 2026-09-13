"""Onglet de gestion des clients (CRUD simple)."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk


class OngletClients(ttk.Frame):
    def __init__(self, parent, db, on_change=None):
        super().__init__(parent, padding=10)
        self.db = db
        self.on_change = on_change
        self.client_selectionne = None

        self._construire_barre_recherche()
        self._construire_tableau()
        self._construire_formulaire()
        self.rafraichir()

    def _construire_barre_recherche(self):
        barre = ttk.Frame(self)
        barre.pack(fill="x", pady=(0, 8))
        ttk.Label(barre, text="Rechercher :").pack(side="left")
        self.var_recherche = tk.StringVar()
        entree = ttk.Entry(barre, textvariable=self.var_recherche, width=30)
        entree.pack(side="left", padx=6)
        entree.bind("<KeyRelease>", lambda _e: self.rafraichir())
        ttk.Button(barre, text="Effacer",
                   command=lambda: (self.var_recherche.set(""), self.rafraichir())
                   ).pack(side="left")

    def _construire_tableau(self):
        cadre = ttk.Frame(self)
        cadre.pack(fill="both", expand=True)

        colonnes = ("nom", "telephone", "adresse")
        self.tableau = ttk.Treeview(cadre, columns=colonnes, show="headings", height=10)
        for col, (titre, largeur) in {
            "nom": ("Nom", 220),
            "telephone": ("Telephone", 140),
            "adresse": ("Adresse", 260),
        }.items():
            self.tableau.heading(col, text=titre)
            self.tableau.column(col, width=largeur, anchor="w")

        defilement = ttk.Scrollbar(cadre, orient="vertical", command=self.tableau.yview)
        self.tableau.configure(yscrollcommand=defilement.set)
        self.tableau.pack(side="left", fill="both", expand=True)
        defilement.pack(side="right", fill="y")
        self.tableau.bind("<<TreeviewSelect>>", self._au_choix_ligne)

    def _construire_formulaire(self):
        form = ttk.LabelFrame(self, text="Fiche client", padding=10)
        form.pack(fill="x", pady=(10, 0))

        self.var_nom = tk.StringVar()
        self.var_telephone = tk.StringVar()
        self.var_adresse = tk.StringVar()

        ttk.Label(form, text="Nom *").grid(row=0, column=0, sticky="w", padx=5, pady=4)
        ttk.Entry(form, textvariable=self.var_nom, width=30).grid(
            row=0, column=1, sticky="w", padx=5, pady=4)
        ttk.Label(form, text="Telephone").grid(row=0, column=2, sticky="w", padx=5, pady=4)
        ttk.Entry(form, textvariable=self.var_telephone, width=24).grid(
            row=0, column=3, sticky="w", padx=5, pady=4)
        ttk.Label(form, text="Adresse").grid(row=1, column=0, sticky="w", padx=5, pady=4)
        ttk.Entry(form, textvariable=self.var_adresse, width=60).grid(
            row=1, column=1, columnspan=3, sticky="w", padx=5, pady=4)

        boutons = ttk.Frame(form)
        boutons.grid(row=2, column=0, columnspan=4, pady=(10, 0), sticky="w")
        ttk.Button(boutons, text="Nouveau", command=self._nouveau).pack(side="left", padx=3)
        ttk.Button(boutons, text="Enregistrer", command=self._enregistrer).pack(side="left", padx=3)
        ttk.Button(boutons, text="Supprimer", command=self._supprimer).pack(side="left", padx=3)

    def rafraichir(self):
        for item in self.tableau.get_children():
            self.tableau.delete(item)
        for c in self.db.lister_clients(self.var_recherche.get()):
            self.tableau.insert(
                "", "end", iid=str(c["id"]),
                values=(c["nom"], c["telephone"] or "", c["adresse"] or ""),
            )

    def _au_choix_ligne(self, _event=None):
        selection = self.tableau.selection()
        if not selection:
            return
        cid = int(selection[0])
        client = next((c for c in self.db.lister_clients() if c["id"] == cid), None)
        if client is None:
            return
        self.client_selectionne = cid
        self.var_nom.set(client["nom"])
        self.var_telephone.set(client["telephone"] or "")
        self.var_adresse.set(client["adresse"] or "")

    def _nouveau(self):
        self.client_selectionne = None
        for var in (self.var_nom, self.var_telephone, self.var_adresse):
            var.set("")
        if self.tableau.selection():
            self.tableau.selection_remove(self.tableau.selection())

    def _enregistrer(self):
        nom = self.var_nom.get().strip()
        if not nom:
            messagebox.showwarning("Champ requis", "Le nom du client est obligatoire.")
            return
        telephone = self.var_telephone.get().strip()
        adresse = self.var_adresse.get().strip()
        if self.client_selectionne is None:
            self.db.ajouter_client(nom, telephone, adresse)
            message = "Client ajoute."
        else:
            self.db.modifier_client(self.client_selectionne, nom, telephone, adresse)
            message = "Client modifie."
        self._nouveau()
        self.rafraichir()
        if self.on_change:
            self.on_change()
        messagebox.showinfo("Succes", message)

    def _supprimer(self):
        if self.client_selectionne is None:
            messagebox.showinfo("Aucune selection", "Selectionnez d'abord un client.")
            return
        if not messagebox.askyesno("Confirmation", "Supprimer ce client ?"):
            return
        self.db.supprimer_client(self.client_selectionne)
        self._nouveau()
        self.rafraichir()
        if self.on_change:
            self.on_change()
