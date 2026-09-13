"""Tests des fonctionnalites avancees : fournisseurs, approvisionnements,
rapports, parametres, generation .xlsx et facture HTML.

Executable sans interface graphique :
    python3 -m unittest tests.test_fonctions_avancees
"""

import os
import tempfile
import unittest
import zipfile
from datetime import datetime

from gestion.database import Database
from gestion import rapports
from gestion.facture import generer_facture_html
from gestion.xlsx import ecrire_xlsx, _lettre_colonne


class TestFournisseursEtAppro(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:")

    def tearDown(self):
        self.db.fermer()

    def test_crud_fournisseur(self):
        fid = self.db.ajouter_fournisseur("Grossiste Diallo", "771", "Touba")
        self.assertEqual(self.db.nombre_fournisseurs(), 1)
        self.db.modifier_fournisseur(fid, "Grossiste D.", "772", "Mbour")
        f = self.db.lister_fournisseurs()[0]
        self.assertEqual(f["nom"], "Grossiste D.")
        self.db.supprimer_fournisseur(fid)
        self.assertEqual(self.db.nombre_fournisseurs(), 0)

    def test_appro_incremente_stock(self):
        pid = self.db.ajouter_produit("CIM50", "Ciment 50 kg", 3500, 4200, 8, 10)
        fid = self.db.ajouter_fournisseur("Grossiste", "771", "Touba")
        aid = self.db.enregistrer_approvisionnement(
            fid, [{"produit_id": pid, "quantite": 50, "prix_achat": 3600}])
        self.assertIsInstance(aid, int)
        produit = self.db.obtenir_produit(pid)
        self.assertEqual(produit["quantite"], 58)          # 8 + 50
        self.assertEqual(produit["prix_achat"], 3600)      # prix mis a jour

    def test_appro_sans_maj_prix(self):
        pid = self.db.ajouter_produit("CIM50", "Ciment", 3500, 4200, 8, 10)
        self.db.enregistrer_approvisionnement(
            None, [{"produit_id": pid, "quantite": 10, "prix_achat": 9999}],
            maj_prix_achat=False)
        produit = self.db.obtenir_produit(pid)
        self.assertEqual(produit["quantite"], 18)
        self.assertEqual(produit["prix_achat"], 3500)      # inchange

    def test_appro_vide_leve_erreur(self):
        with self.assertRaises(ValueError):
            self.db.enregistrer_approvisionnement(None, [])


class TestParametres(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:")

    def tearDown(self):
        self.db.fermer()

    def test_valeurs_par_defaut(self):
        infos = self.db.parametres_entreprise()
        self.assertIn("entreprise_nom", infos)

    def test_definir_et_relire(self):
        self.db.definir_parametre("entreprise_nom", "Ets Balde")
        self.assertEqual(self.db.obtenir_parametre("entreprise_nom"), "Ets Balde")

    def test_parametre_absent_retourne_defaut(self):
        self.assertEqual(self.db.obtenir_parametre("inexistant", "x"), "x")


class TestRapports(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:")
        self.jour = datetime.now().strftime("%Y-%m-%d")
        p = self.db.ajouter_produit("RIZ25", "Sac de riz 25 kg", 12000, 15000, 40, 5)
        c = self.db.ajouter_client("Boutique Fatou", "770", "Dakar")
        self.db.enregistrer_vente(c, [{"produit_id": p, "quantite": 3}])

    def tearDown(self):
        self.db.fermer()

    def test_ca_et_ventes_periode(self):
        self.assertEqual(self.db.ca_periode(self.jour, self.jour), 45000)
        self.assertEqual(len(self.db.ventes_periode(self.jour, self.jour)), 1)

    def test_ventes_par_produit(self):
        agg = self.db.ventes_par_produit_periode(self.jour, self.jour)
        self.assertEqual(agg[0]["designation"], "Sac de riz 25 kg")
        self.assertEqual(agg[0]["quantite"], 3)
        self.assertEqual(agg[0]["montant"], 45000)

    def test_construction_rapport_ventes(self):
        base, feuilles = rapports.rapport_ventes(self.db, self.jour, self.jour)
        self.assertEqual(base, "rapport_ventes")
        noms = [f["nom"] for f in feuilles]
        self.assertEqual(noms, ["Synthèse", "Ventes", "Top produits"])

    def test_export_xlsx(self):
        base, feuilles = rapports.rapport_ventes(self.db, self.jour, self.jour)
        with tempfile.TemporaryDirectory() as d:
            chemin = rapports.exporter_xlsx(feuilles, base, dossier=d)
            self.assertTrue(os.path.exists(chemin))
            self.assertTrue(chemin.endswith(".xlsx"))
            self.assertIsNone(zipfile.ZipFile(chemin).testzip())

    def test_export_csv(self):
        base, feuilles = rapports.rapport_ventes(self.db, self.jour, self.jour)
        with tempfile.TemporaryDirectory() as d:
            chemin = rapports.exporter_csv(feuilles, base, dossier=d)
            self.assertTrue(os.path.exists(chemin))
            with open(chemin, encoding="utf-8-sig") as fh:
                contenu = fh.read()
            self.assertIn("N°", contenu)          # entete de la feuille "Ventes"


class TestXlsx(unittest.TestCase):
    def test_lettre_colonne(self):
        self.assertEqual(_lettre_colonne(1), "A")
        self.assertEqual(_lettre_colonne(26), "Z")
        self.assertEqual(_lettre_colonne(27), "AA")

    def test_ecriture_valide(self):
        with tempfile.TemporaryDirectory() as d:
            chemin = os.path.join(d, "t.xlsx")
            ecrire_xlsx(chemin, [{"nom": "F", "entetes": ["A", "B"],
                                  "lignes": [["x", 1], ["y", 2.5]]}])
            z = zipfile.ZipFile(chemin)
            self.assertIsNone(z.testzip())
            self.assertIn("xl/worksheets/sheet1.xml", z.namelist())

    def test_echappement_caracteres_speciaux(self):
        with tempfile.TemporaryDirectory() as d:
            chemin = os.path.join(d, "t.xlsx")
            ecrire_xlsx(chemin, [{"nom": "F", "entetes": ["X"],
                                  "lignes": [["a & b < c"]]}])
            contenu = zipfile.ZipFile(chemin).read("xl/worksheets/sheet1.xml").decode()
            self.assertIn("a &amp; b &lt; c", contenu)


class TestFacture(unittest.TestCase):
    def test_generation_html(self):
        db = Database(":memory:")
        db.definir_parametre("entreprise_nom", "Ets Balde & Fils")
        p = db.ajouter_produit("RIZ25", "Sac de riz 25 kg", 12000, 15000, 40, 5)
        c = db.ajouter_client("Boutique Fatou", "770", "Dakar")
        vid = db.enregistrer_vente(c, [{"produit_id": p, "quantite": 3}])
        with tempfile.TemporaryDirectory() as d:
            chemin = generer_facture_html(db, vid, dossier=d)
            with open(chemin, encoding="utf-8") as fh:
                html = fh.read()
            self.assertIn("FACTURE", html)
            self.assertIn("Ets Balde &amp; Fils", html)   # echappement HTML
            self.assertIn("45 000 FCFA", html)
            self.assertIn("Boutique Fatou", html)
        db.fermer()

    def test_vente_introuvable(self):
        db = Database(":memory:")
        with self.assertRaises(ValueError):
            generer_facture_html(db, 999)
        db.fermer()


if __name__ == "__main__":
    unittest.main()
