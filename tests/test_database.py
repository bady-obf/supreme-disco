"""Tests de la couche base de donnees.

Executable sans interface graphique :
    python3 -m unittest tests.test_database
"""

import unittest

from gestion.database import Database, StockInsuffisant


class TestDatabase(unittest.TestCase):
    def setUp(self):
        # Base en memoire : rapide et isolee entre chaque test.
        self.db = Database(":memory:")

    def tearDown(self):
        self.db.fermer()

    # ---- Produits ----
    def test_ajouter_et_lister_produit(self):
        pid = self.db.ajouter_produit("REF001", "Sac de riz 25kg", 12000, 15000, 40, 5)
        self.assertIsInstance(pid, int)
        produits = self.db.lister_produits()
        self.assertEqual(len(produits), 1)
        self.assertEqual(produits[0]["designation"], "Sac de riz 25kg")
        self.assertEqual(produits[0]["quantite"], 40)

    def test_reference_unique(self):
        self.db.ajouter_produit("REF001", "Produit A", 100, 150, 10)
        with self.assertRaises(Exception):
            self.db.ajouter_produit("REF001", "Produit B", 200, 250, 5)

    def test_modifier_produit(self):
        pid = self.db.ajouter_produit("REF001", "Ancien", 100, 150, 10, 2)
        self.db.modifier_produit(pid, "REF001", "Nouveau", 120, 180, 20, 3)
        p = self.db.obtenir_produit(pid)
        self.assertEqual(p["designation"], "Nouveau")
        self.assertEqual(p["prix_vente"], 180)
        self.assertEqual(p["quantite"], 20)

    def test_supprimer_produit(self):
        pid = self.db.ajouter_produit("REF001", "A supprimer", 100, 150, 10)
        self.db.supprimer_produit(pid)
        self.assertIsNone(self.db.obtenir_produit(pid))

    def test_recherche_produit(self):
        self.db.ajouter_produit("REF001", "Huile Aya 1L", 900, 1100, 30)
        self.db.ajouter_produit("REF002", "Savon Madar", 200, 300, 50)
        resultats = self.db.lister_produits("huile")
        self.assertEqual(len(resultats), 1)
        self.assertEqual(resultats[0]["reference"], "REF001")

    def test_produits_en_alerte(self):
        self.db.ajouter_produit("R1", "Stock bas", 100, 150, 2, 5)   # 2 <= 5
        self.db.ajouter_produit("R2", "Stock ok", 100, 150, 20, 5)   # 20 > 5
        self.db.ajouter_produit("R3", "Sans seuil", 100, 150, 0, 0)  # seuil 0 ignore
        alertes = self.db.produits_en_alerte()
        self.assertEqual(len(alertes), 1)
        self.assertEqual(alertes[0]["reference"], "R1")

    # ---- Clients ----
    def test_ajouter_et_lister_client(self):
        cid = self.db.ajouter_client("Boutique Fatou", "70000000", "Dakar")
        self.assertIsInstance(cid, int)
        clients = self.db.lister_clients()
        self.assertEqual(len(clients), 1)
        self.assertEqual(clients[0]["nom"], "Boutique Fatou")

    # ---- Ventes ----
    def test_enregistrer_vente_decremente_le_stock(self):
        pid = self.db.ajouter_produit("REF001", "Sac de ciment", 3500, 4200, 100, 10)
        cid = self.db.ajouter_client("Chantier Diallo", "76000000", "Thies")
        vid = self.db.enregistrer_vente(cid, [{"produit_id": pid, "quantite": 12}],
                                        taux_tva=0)
        self.assertIsInstance(vid, int)
        # Le stock doit avoir baisse de 12.
        self.assertEqual(self.db.obtenir_produit(pid)["quantite"], 88)
        # Le total (sans TVA) doit valoir 12 * 4200.
        ventes = self.db.lister_ventes()
        self.assertEqual(ventes[0]["total"], 12 * 4200)

    def test_vente_stock_insuffisant_rollback(self):
        pid = self.db.ajouter_produit("REF001", "Article rare", 100, 150, 5)
        with self.assertRaises(StockInsuffisant):
            self.db.enregistrer_vente(None, [{"produit_id": pid, "quantite": 10}])
        # Aucune vente enregistree, stock inchange.
        self.assertEqual(len(self.db.lister_ventes()), 0)
        self.assertEqual(self.db.obtenir_produit(pid)["quantite"], 5)

    def test_vente_multi_lignes_atomicite(self):
        p1 = self.db.ajouter_produit("R1", "Produit dispo", 100, 150, 10)
        p2 = self.db.ajouter_produit("R2", "Produit limite", 100, 150, 3)
        # La 2e ligne echoue -> toute la vente doit etre annulee.
        with self.assertRaises(StockInsuffisant):
            self.db.enregistrer_vente(
                None,
                [
                    {"produit_id": p1, "quantite": 5},
                    {"produit_id": p2, "quantite": 8},
                ],
            )
        # p1 ne doit PAS avoir ete decremente.
        self.assertEqual(self.db.obtenir_produit(p1)["quantite"], 10)
        self.assertEqual(len(self.db.lister_ventes()), 0)

    def test_statistiques(self):
        p1 = self.db.ajouter_produit("R1", "A", 1000, 1500, 10)  # valeur achat 10000
        p2 = self.db.ajouter_produit("R2", "B", 500, 800, 20)    # valeur achat 10000
        self.assertEqual(self.db.valeur_stock(), 20000)
        self.assertEqual(self.db.nombre_produits(), 2)
        self.db.enregistrer_vente(None, [{"produit_id": p1, "quantite": 2}],
                                  taux_tva=0)
        # CA du jour (sans TVA) = 2 * 1500 = 3000
        self.assertEqual(self.db.chiffre_affaires_jour(), 3000)
        self.assertEqual(self.db.nombre_ventes_jour(), 1)


if __name__ == "__main__":
    unittest.main()
