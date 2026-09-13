"""Fenetre principale de l'application (assemble les onglets)."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .database import Database
from .ui.approvisionnements import OngletApprovisionnements
from .ui.clients import OngletClients
from .ui.connexion import demander_connexion
from .ui.dashboard import OngletDashboard
from .ui.fournisseurs import OngletFournisseurs
from .ui.historique import OngletHistorique
from .ui.parametres import OngletParametres
from .ui.produits import OngletProduits
from .ui.rapports import OngletRapports
from .ui.utilisateurs import OngletUtilisateurs
from .ui.ventes import OngletVentes

# Administrateur par defaut lorsque l'application est lancee sans connexion
# (par exemple dans les tests) : acces complet.
ADMIN_PAR_DEFAUT = {"identifiant": "admin", "nom": "Administrateur", "role": "admin"}


class Application(tk.Tk):
    def __init__(self, chemin_db: str = "data/gestion.db", db=None, utilisateur=None):
        super().__init__()
        self.title("Gestion Commerciale & Stock")
        self.geometry("980x660")
        self.minsize(820, 580)

        # La base peut etre fournie (boucle de connexion) ou creee ici (tests).
        self._db_appartient = db is None
        self.db = db if db is not None else Database(chemin_db)
        self.utilisateur = utilisateur or ADMIN_PAR_DEFAUT
        self.deconnexion_demandee = False

        # Un peu de style pour les entetes de tableaux.
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass  # theme indisponible sur certaines plateformes : on garde le defaut
        style.configure("Treeview.Heading", font=("TkDefaultFont", 9, "bold"))

        self._construire_barre()
        self._construire_onglets()
        # Ferme proprement la base a la fermeture de la fenetre.
        self.protocol("WM_DELETE_WINDOW", self._quitter)

    def _construire_barre(self):
        barre = ttk.Frame(self, padding=(10, 6))
        barre.pack(fill="x")
        texte = f"Connecte : {self.utilisateur['nom']} ({self.utilisateur['role']})"
        ttk.Label(barre, text=texte, font=("TkDefaultFont", 9, "bold")).pack(side="left")
        ttk.Button(barre, text="Deconnexion", command=self._deconnecter).pack(side="right")

    def _construire_onglets(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # Tous les onglets sont construits ; l'affichage depend du role.
        self.dashboard = OngletDashboard(self.notebook, self.db)
        self.produits = OngletProduits(self.notebook, self.db, on_change=self._maj_globale)
        self.clients = OngletClients(self.notebook, self.db, on_change=self._maj_globale)
        self.fournisseurs = OngletFournisseurs(self.notebook, self.db, on_change=self._maj_globale)
        self.ventes = OngletVentes(self.notebook, self.db, on_change=self._maj_globale)
        self.approvisionnements = OngletApprovisionnements(
            self.notebook, self.db, on_change=self._maj_globale)
        self.historique = OngletHistorique(self.notebook, self.db)
        self.rapports = OngletRapports(self.notebook, self.db)
        self.parametres = OngletParametres(
            self.notebook, self.db,
            on_change=self._maj_globale, on_restore=self._maj_totale)
        self.utilisateurs = OngletUtilisateurs(self.notebook, self.db)

        # (onglet, libelle, roles autorises)
        definitions = [
            (self.dashboard, "  Tableau de bord  ", ("admin", "vendeur")),
            (self.produits, "  Produits  ", ("admin", "vendeur")),
            (self.clients, "  Clients  ", ("admin", "vendeur")),
            (self.fournisseurs, "  Fournisseurs  ", ("admin",)),
            (self.ventes, "  Nouvelle vente  ", ("admin", "vendeur")),
            (self.approvisionnements, "  Approvisionnement  ", ("admin",)),
            (self.historique, "  Historique  ", ("admin", "vendeur")),
            (self.rapports, "  Rapports  ", ("admin",)),
            (self.parametres, "  Parametres  ", ("admin",)),
            (self.utilisateurs, "  Utilisateurs  ", ("admin",)),
        ]
        role = self.utilisateur.get("role", "admin")
        for widget, titre, roles in definitions:
            if role in roles:
                self.notebook.add(widget, text=titre)

        # Rafraichit l'onglet affiche quand on change d'onglet.
        self.notebook.bind("<<NotebookTabChanged>>", self._au_changement_onglet)

    def _maj_globale(self):
        """Rafraichit les ecrans dependant des donnees partagees."""
        self.dashboard.rafraichir()
        self.ventes.rafraichir()
        self.approvisionnements.rafraichir()
        self.historique.rafraichir()

    def _maj_totale(self):
        """Rafraichit TOUS les onglets (utilise apres une restauration)."""
        for onglet in (self.dashboard, self.produits, self.clients,
                       self.fournisseurs, self.ventes, self.approvisionnements,
                       self.historique, self.rapports, self.parametres,
                       self.utilisateurs):
            if hasattr(onglet, "rafraichir"):
                onglet.rafraichir()

    def _au_changement_onglet(self, _event=None):
        onglet = self.notebook.nametowidget(self.notebook.select())
        if hasattr(onglet, "rafraichir"):
            onglet.rafraichir()

    def _deconnecter(self):
        """Ferme la fenetre en demandant le retour a l'ecran de connexion."""
        self.deconnexion_demandee = True
        # La base est partagee avec la boucle de connexion : on ne la ferme pas ici.
        self.destroy()

    def _quitter(self):
        if self._db_appartient:
            self.db.fermer()
        self.destroy()


def main():
    """Point d'entree : connexion puis lancement de l'application.

    Boucle : connexion -> application -> (deconnexion) -> connexion...
    """
    db = Database()
    try:
        while True:
            utilisateur = demander_connexion(db)
            if utilisateur is None:
                break  # fenetre de connexion fermee
            app = Application(db=db, utilisateur=utilisateur)
            app.mainloop()
            if not app.deconnexion_demandee:
                break  # fermeture normale de l'application
    finally:
        db.fermer()


if __name__ == "__main__":
    main()
