"""Fenetre principale de l'application (assemble les onglets)."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .database import Database
from .ui.approvisionnements import OngletApprovisionnements
from .ui.clients import OngletClients
from .ui.dashboard import OngletDashboard
from .ui.fournisseurs import OngletFournisseurs
from .ui.historique import OngletHistorique
from .ui.parametres import OngletParametres
from .ui.produits import OngletProduits
from .ui.rapports import OngletRapports
from .ui.ventes import OngletVentes


class Application(tk.Tk):
    def __init__(self, chemin_db: str = "data/gestion.db"):
        super().__init__()
        self.title("Gestion Commerciale & Stock")
        self.geometry("980x640")
        self.minsize(820, 560)

        self.db = Database(chemin_db)

        # Un peu de style pour les entetes de tableaux.
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass  # theme indisponible sur certaines plateformes : on garde le defaut
        style.configure("Treeview.Heading", font=("TkDefaultFont", 9, "bold"))

        self._construire_onglets()
        # Ferme proprement la base a la fermeture de la fenetre.
        self.protocol("WM_DELETE_WINDOW", self._quitter)

    def _construire_onglets(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=8)

        # Le tableau de bord se rafraichit apres toute modification metier.
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

        self.notebook.add(self.dashboard, text="  Tableau de bord  ")
        self.notebook.add(self.produits, text="  Produits  ")
        self.notebook.add(self.clients, text="  Clients  ")
        self.notebook.add(self.fournisseurs, text="  Fournisseurs  ")
        self.notebook.add(self.ventes, text="  Nouvelle vente  ")
        self.notebook.add(self.approvisionnements, text="  Approvisionnement  ")
        self.notebook.add(self.historique, text="  Historique  ")
        self.notebook.add(self.rapports, text="  Rapports  ")
        self.notebook.add(self.parametres, text="  Parametres  ")

        # Rafraichit l'onglet affiche quand on change d'onglet
        # (utile pour la vente qui depend des produits/clients a jour).
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
                       self.historique, self.rapports, self.parametres):
            if hasattr(onglet, "rafraichir"):
                onglet.rafraichir()

    def _au_changement_onglet(self, _event=None):
        onglet = self.notebook.nametowidget(self.notebook.select())
        if hasattr(onglet, "rafraichir"):
            onglet.rafraichir()

    def _quitter(self):
        self.db.fermer()
        self.destroy()


def main():
    """Point d'entree : lance l'application."""
    app = Application()
    app.mainloop()


if __name__ == "__main__":
    main()
