"""Onglet de gestion des utilisateurs (reserve aux administrateurs).

Permet de creer des comptes, changer le role, (des)activer, reinitialiser le
mot de passe et supprimer un utilisateur. La base empeche la suppression ou la
retrogradation du dernier administrateur actif.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from ..database import ROLES


class OngletUtilisateurs(ttk.Frame):
    def __init__(self, parent, db, on_change=None):
        super().__init__(parent, padding=10)
        self.db = db
        self.on_change = on_change
        self.utilisateur_selectionne = None

        self._construire_tableau()
        self._construire_formulaire()
        self.rafraichir()

    def _construire_tableau(self):
        cadre = ttk.Frame(self)
        cadre.pack(fill="both", expand=True)
        colonnes = ("identifiant", "nom", "role", "actif")
        self.tableau = ttk.Treeview(cadre, columns=colonnes, show="headings", height=10)
        for col, (titre, largeur) in {
            "identifiant": ("Identifiant", 160),
            "nom": ("Nom", 220),
            "role": ("Role", 120),
            "actif": ("Actif", 80),
        }.items():
            self.tableau.heading(col, text=titre)
            self.tableau.column(col, width=largeur, anchor="w")
        defilement = ttk.Scrollbar(cadre, orient="vertical", command=self.tableau.yview)
        self.tableau.configure(yscrollcommand=defilement.set)
        self.tableau.pack(side="left", fill="both", expand=True)
        defilement.pack(side="right", fill="y")
        self.tableau.bind("<<TreeviewSelect>>", self._au_choix_ligne)

    def _construire_formulaire(self):
        form = ttk.LabelFrame(self, text="Compte utilisateur", padding=10)
        form.pack(fill="x", pady=(10, 0))

        self.var_identifiant = tk.StringVar()
        self.var_nom = tk.StringVar()
        self.var_role = tk.StringVar(value="vendeur")
        self.var_mdp = tk.StringVar()

        ttk.Label(form, text="Identifiant *").grid(row=0, column=0, sticky="w", padx=5, pady=4)
        self.entree_identifiant = ttk.Entry(form, textvariable=self.var_identifiant, width=24)
        self.entree_identifiant.grid(row=0, column=1, sticky="w", padx=5, pady=4)

        ttk.Label(form, text="Nom").grid(row=0, column=2, sticky="w", padx=5, pady=4)
        ttk.Entry(form, textvariable=self.var_nom, width=24).grid(
            row=0, column=3, sticky="w", padx=5, pady=4)

        ttk.Label(form, text="Role").grid(row=1, column=0, sticky="w", padx=5, pady=4)
        ttk.Combobox(form, textvariable=self.var_role, state="readonly",
                     values=list(ROLES), width=21).grid(
            row=1, column=1, sticky="w", padx=5, pady=4)

        ttk.Label(form, text="Mot de passe").grid(row=1, column=2, sticky="w", padx=5, pady=4)
        ttk.Entry(form, textvariable=self.var_mdp, show="•", width=24).grid(
            row=1, column=3, sticky="w", padx=5, pady=4)

        boutons = ttk.Frame(form)
        boutons.grid(row=2, column=0, columnspan=4, pady=(10, 0), sticky="w")
        ttk.Button(boutons, text="Nouveau", command=self._nouveau).pack(side="left", padx=3)
        ttk.Button(boutons, text="Creer", command=self._creer).pack(side="left", padx=3)
        ttk.Button(boutons, text="Changer le role", command=self._changer_role).pack(side="left", padx=3)
        ttk.Button(boutons, text="Activer/Desactiver", command=self._basculer_actif).pack(side="left", padx=3)
        ttk.Button(boutons, text="Reinit. mot de passe", command=self._reinit_mdp).pack(side="left", padx=3)
        ttk.Button(boutons, text="Supprimer", command=self._supprimer).pack(side="left", padx=3)

        ttk.Label(
            self,
            text="Roles : « admin » accede a tout ; « vendeur » accede aux ventes, "
                 "produits, clients, historique et tableau de bord.",
            foreground="#666", wraplength=620, justify="left",
        ).pack(anchor="w", pady=(8, 0))

    # ------------------------------------------------------------------ #
    def rafraichir(self):
        for item in self.tableau.get_children():
            self.tableau.delete(item)
        for u in self.db.lister_utilisateurs():
            self.tableau.insert(
                "", "end", iid=str(u["id"]),
                values=(u["identifiant"], u["nom"] or "", u["role"],
                        "Oui" if u["actif"] else "Non"),
            )

    def _au_choix_ligne(self, _event=None):
        selection = self.tableau.selection()
        if not selection:
            return
        uid = int(selection[0])
        u = next((x for x in self.db.lister_utilisateurs() if x["id"] == uid), None)
        if u is None:
            return
        self.utilisateur_selectionne = uid
        self.var_identifiant.set(u["identifiant"])
        self.var_nom.set(u["nom"] or "")
        self.var_role.set(u["role"])
        self.var_mdp.set("")

    def _nouveau(self):
        self.utilisateur_selectionne = None
        self.var_identifiant.set("")
        self.var_nom.set("")
        self.var_role.set("vendeur")
        self.var_mdp.set("")
        if self.tableau.selection():
            self.tableau.selection_remove(self.tableau.selection())

    def _creer(self):
        try:
            self.db.creer_utilisateur(
                self.var_identifiant.get(), self.var_mdp.get(),
                role=self.var_role.get(), nom=self.var_nom.get())
        except ValueError as err:
            messagebox.showerror("Erreur", str(err))
            return
        self._nouveau()
        self.rafraichir()
        if self.on_change:
            self.on_change()
        messagebox.showinfo("Succes", "Utilisateur cree.")

    def _changer_role(self):
        if self.utilisateur_selectionne is None:
            messagebox.showinfo("Aucune selection", "Selectionnez un utilisateur.")
            return
        try:
            self.db.definir_role(self.utilisateur_selectionne, self.var_role.get())
        except ValueError as err:
            messagebox.showerror("Erreur", str(err))
            return
        self.rafraichir()
        messagebox.showinfo("Succes", "Role modifie.")

    def _basculer_actif(self):
        if self.utilisateur_selectionne is None:
            messagebox.showinfo("Aucune selection", "Selectionnez un utilisateur.")
            return
        u = next((x for x in self.db.lister_utilisateurs()
                  if x["id"] == self.utilisateur_selectionne), None)
        if u is None:
            return
        try:
            self.db.definir_actif(self.utilisateur_selectionne, not u["actif"])
        except ValueError as err:
            messagebox.showerror("Erreur", str(err))
            return
        self.rafraichir()

    def _reinit_mdp(self):
        if self.utilisateur_selectionne is None:
            messagebox.showinfo("Aucune selection", "Selectionnez un utilisateur.")
            return
        nouveau = self.var_mdp.get()
        if len(nouveau) < 4:
            messagebox.showwarning(
                "Mot de passe",
                "Saisissez le nouveau mot de passe (min. 4 caracteres) "
                "dans le champ « Mot de passe ».")
            return
        self.db.modifier_mot_de_passe(self.utilisateur_selectionne, nouveau)
        self.var_mdp.set("")
        messagebox.showinfo("Succes", "Mot de passe reinitialise.")

    def _supprimer(self):
        if self.utilisateur_selectionne is None:
            messagebox.showinfo("Aucune selection", "Selectionnez un utilisateur.")
            return
        if not messagebox.askyesno("Confirmation", "Supprimer ce compte ?"):
            return
        try:
            self.db.supprimer_utilisateur(self.utilisateur_selectionne)
        except ValueError as err:
            messagebox.showerror("Erreur", str(err))
            return
        self._nouveau()
        self.rafraichir()
