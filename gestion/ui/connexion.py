"""Fenetre de connexion et creation du premier administrateur.

Au tout premier lancement (aucun utilisateur en base), l'application demande
de creer le compte administrateur. Ensuite, un ecran de connexion classique
verifie identifiant + mot de passe.

``demander_connexion(db)`` retourne le dictionnaire de l'utilisateur connecte,
ou ``None`` si la fenetre est fermee sans connexion.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk


class FenetreConnexion(tk.Tk):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.utilisateur = None
        self.title("Connexion — Gestion Commerciale")
        self.resizable(False, False)

        self.premier_lancement = db.nombre_utilisateurs() == 0
        cadre = ttk.Frame(self, padding=20)
        cadre.pack()

        if self.premier_lancement:
            self._construire_creation(cadre)
        else:
            self._construire_connexion(cadre)

        self.bind("<Return>", lambda _e: self._valider())
        self._centrer()

    def _centrer(self):
        self.update_idletasks()
        largeur = self.winfo_width()
        hauteur = self.winfo_height()
        x = (self.winfo_screenwidth() - largeur) // 2
        y = (self.winfo_screenheight() - hauteur) // 3
        self.geometry(f"+{max(0, x)}+{max(0, y)}")

    # ------------------------------------------------------------------ #
    def _construire_connexion(self, cadre):
        ttk.Label(cadre, text="Connexion", font=("TkDefaultFont", 14, "bold")).grid(
            row=0, column=0, columnspan=2, pady=(0, 14))

        ttk.Label(cadre, text="Identifiant :").grid(row=1, column=0, sticky="w", pady=5)
        self.var_identifiant = tk.StringVar()
        entree_id = ttk.Entry(cadre, textvariable=self.var_identifiant, width=26)
        entree_id.grid(row=1, column=1, pady=5)

        ttk.Label(cadre, text="Mot de passe :").grid(row=2, column=0, sticky="w", pady=5)
        self.var_mdp = tk.StringVar()
        ttk.Entry(cadre, textvariable=self.var_mdp, show="•", width=26).grid(
            row=2, column=1, pady=5)

        ttk.Button(cadre, text="Se connecter", command=self._valider).grid(
            row=3, column=0, columnspan=2, pady=(14, 0))
        entree_id.focus_set()

    def _construire_creation(self, cadre):
        ttk.Label(cadre, text="Bienvenue !", font=("TkDefaultFont", 14, "bold")).grid(
            row=0, column=0, columnspan=2)
        ttk.Label(cadre, text="Creez le compte administrateur pour commencer.",
                  foreground="#555").grid(row=1, column=0, columnspan=2, pady=(2, 14))

        ttk.Label(cadre, text="Nom (optionnel) :").grid(row=2, column=0, sticky="w", pady=5)
        self.var_nom = tk.StringVar()
        entree_nom = ttk.Entry(cadre, textvariable=self.var_nom, width=26)
        entree_nom.grid(row=2, column=1, pady=5)

        ttk.Label(cadre, text="Identifiant :").grid(row=3, column=0, sticky="w", pady=5)
        self.var_identifiant = tk.StringVar(value="admin")
        ttk.Entry(cadre, textvariable=self.var_identifiant, width=26).grid(
            row=3, column=1, pady=5)

        ttk.Label(cadre, text="Mot de passe :").grid(row=4, column=0, sticky="w", pady=5)
        self.var_mdp = tk.StringVar()
        ttk.Entry(cadre, textvariable=self.var_mdp, show="•", width=26).grid(
            row=4, column=1, pady=5)

        ttk.Label(cadre, text="Confirmer :").grid(row=5, column=0, sticky="w", pady=5)
        self.var_mdp2 = tk.StringVar()
        ttk.Entry(cadre, textvariable=self.var_mdp2, show="•", width=26).grid(
            row=5, column=1, pady=5)

        ttk.Button(cadre, text="Creer et se connecter", command=self._valider).grid(
            row=6, column=0, columnspan=2, pady=(14, 0))
        entree_nom.focus_set()

    # ------------------------------------------------------------------ #
    def _valider(self):
        if self.premier_lancement:
            self._valider_creation()
        else:
            self._valider_connexion()

    def _valider_connexion(self):
        utilisateur = self.db.verifier_identifiants(
            self.var_identifiant.get(), self.var_mdp.get())
        if utilisateur is None:
            messagebox.showerror("Echec",
                                 "Identifiant ou mot de passe incorrect "
                                 "(ou compte desactive).")
            self.var_mdp.set("")
            return
        self.utilisateur = utilisateur
        self.destroy()

    def _valider_creation(self):
        identifiant = self.var_identifiant.get().strip()
        mdp = self.var_mdp.get()
        if not identifiant:
            messagebox.showwarning("Champ requis", "L'identifiant est obligatoire.")
            return
        if len(mdp) < 4:
            messagebox.showwarning("Mot de passe",
                                   "Le mot de passe doit contenir au moins 4 caracteres.")
            return
        if mdp != self.var_mdp2.get():
            messagebox.showwarning("Mot de passe",
                                   "Les deux mots de passe ne correspondent pas.")
            return
        try:
            self.db.creer_utilisateur(identifiant, mdp, role="admin",
                                      nom=self.var_nom.get())
        except ValueError as err:
            messagebox.showerror("Erreur", str(err))
            return
        self.utilisateur = self.db.verifier_identifiants(identifiant, mdp)
        self.destroy()


def demander_connexion(db):
    """Ouvre la fenetre de connexion et retourne l'utilisateur, ou ``None``."""
    fenetre = FenetreConnexion(db)
    fenetre.mainloop()
    return fenetre.utilisateur
