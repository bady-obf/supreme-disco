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
        self.db.enregistrer_vente(c, [{"produit_id": p, "quantite": 3}], taux_tva=0)

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

    def test_facture_avec_tva_et_remise(self):
        db = Database(":memory:")
        p = db.ajouter_produit("RIZ25", "Sac de riz 25 kg", 12000, 15000, 40, 5)
        c = db.ajouter_client("Fatou", "770", "Dakar")
        vid = db.enregistrer_vente(c, [{"produit_id": p, "quantite": 4}],
                                   remise=5000, taux_tva=18)
        with tempfile.TemporaryDirectory() as d:
            with open(generer_facture_html(db, vid, dossier=d), encoding="utf-8") as fh:
                html = fh.read()
        for attendu in ["Sous-total", "Remise", "Total HT", "TVA (18%)",
                        "9 900 FCFA", "TOTAL TTC", "64 900 FCFA"]:
            self.assertIn(attendu, html)
        db.fermer()


class TestTVAEtRemise(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:")
        self.pid = self.db.ajouter_produit("RIZ25", "Sac de riz 25 kg",
                                           12000, 15000, 40, 5)
        self.cid = self.db.ajouter_client("Fatou", "770", "Dakar")

    def tearDown(self):
        self.db.fermer()

    def test_calcul_tva_et_remise(self):
        vid = self.db.enregistrer_vente(
            self.cid, [{"produit_id": self.pid, "quantite": 4}],
            remise=5000, taux_tva=18)
        v = self.db.obtenir_vente(vid)
        self.assertEqual(v["montant_brut"], 60000)   # 4 * 15000
        self.assertEqual(v["remise"], 5000)
        self.assertEqual(v["montant_tva"], 9900)      # (60000-5000) * 18%
        self.assertEqual(v["total"], 64900)           # 55000 + 9900

    def test_tva_par_defaut_depuis_parametre(self):
        # Parametre par defaut = 18.
        vid = self.db.enregistrer_vente(
            self.cid, [{"produit_id": self.pid, "quantite": 1}])
        v = self.db.obtenir_vente(vid)
        self.assertEqual(v["taux_tva"], 18.0)
        self.assertEqual(v["total"], 17700.0)         # 15000 * 1.18

    def test_remise_bornee_au_brut(self):
        # Une remise superieure au brut est plafonnee.
        vid = self.db.enregistrer_vente(
            self.cid, [{"produit_id": self.pid, "quantite": 1}],
            remise=999999, taux_tva=0)
        v = self.db.obtenir_vente(vid)
        self.assertEqual(v["remise"], 15000)          # plafonnee au brut
        self.assertEqual(v["total"], 0)

    def test_totaux_periode(self):
        jour = datetime.now().strftime("%Y-%m-%d")
        self.db.enregistrer_vente(
            self.cid, [{"produit_id": self.pid, "quantite": 4}],
            remise=5000, taux_tva=18)
        t = self.db.totaux_ventes_periode(jour, jour)
        self.assertEqual(t["nombre"], 1)
        self.assertEqual(t["brut"], 60000)
        self.assertEqual(t["remise"], 5000)
        self.assertEqual(t["ht"], 55000)
        self.assertEqual(t["tva"], 9900)
        self.assertEqual(t["ttc"], 64900)

    def test_ca_par_jour_longueur_et_ordre(self):
        serie = self.db.ca_par_jour(10)
        self.assertEqual(len(serie), 10)
        # Les jours sont ordonnes croissants et le dernier est aujourd'hui.
        jours = [j for j, _ in serie]
        self.assertEqual(jours, sorted(jours))
        self.assertEqual(jours[-1], datetime.now().strftime("%Y-%m-%d"))


class TestUtilisateurs(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:")

    def tearDown(self):
        self.db.fermer()

    def test_creation_et_verification(self):
        self.assertEqual(self.db.nombre_utilisateurs(), 0)
        self.db.creer_utilisateur("admin", "secret123", role="admin", nom="Patron")
        self.assertEqual(self.db.nombre_utilisateurs(), 1)
        u = self.db.verifier_identifiants("admin", "secret123")
        self.assertIsNotNone(u)
        self.assertEqual(u["role"], "admin")
        self.assertIsNone(self.db.verifier_identifiants("admin", "mauvais"))
        self.assertIsNone(self.db.verifier_identifiants("inconnu", "x"))

    def test_mot_de_passe_jamais_en_clair(self):
        self.db.creer_utilisateur("u", "monMotDePasse")
        row = self.db.conn.execute(
            "SELECT mot_de_passe_hash FROM utilisateurs WHERE identifiant='u'").fetchone()
        self.assertNotIn("monMotDePasse", row["mot_de_passe_hash"])

    def test_identifiant_unique(self):
        self.db.creer_utilisateur("admin", "x", role="admin")
        with self.assertRaises(ValueError):
            self.db.creer_utilisateur("admin", "y")

    def test_role_invalide(self):
        with self.assertRaises(ValueError):
            self.db.creer_utilisateur("u", "x", role="superman")

    def test_compte_desactive_refuse(self):
        uid = self.db.creer_utilisateur("admin", "x", role="admin")
        self.db.creer_utilisateur("v", "y", role="vendeur")
        vid = [u["id"] for u in self.db.lister_utilisateurs() if u["identifiant"] == "v"][0]
        self.db.definir_actif(vid, False)
        self.assertIsNone(self.db.verifier_identifiants("v", "y"))

    def test_dernier_admin_protege(self):
        uid = self.db.creer_utilisateur("admin", "x", role="admin")
        # Ni retrograder, ni desactiver, ni supprimer le dernier admin.
        with self.assertRaises(ValueError):
            self.db.definir_role(uid, "vendeur")
        with self.assertRaises(ValueError):
            self.db.definir_actif(uid, False)
        with self.assertRaises(ValueError):
            self.db.supprimer_utilisateur(uid)

    def test_changement_mot_de_passe(self):
        uid = self.db.creer_utilisateur("u", "ancien")
        self.db.modifier_mot_de_passe(uid, "nouveau")
        self.assertIsNone(self.db.verifier_identifiants("u", "ancien"))
        self.assertIsNotNone(self.db.verifier_identifiants("u", "nouveau"))


class TestSauvegardeRestauration(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.mkdtemp()
        self.base = os.path.join(self.dossier, "gestion.db")
        self.sauv = os.path.join(self.dossier, "sauvegarde.db")

    def test_sauvegarde_puis_restauration(self):
        db = Database(self.base)
        db.ajouter_produit("RIZ25", "Sac de riz 25 kg", 12000, 15000, 40, 5)
        db.sauvegarder(self.sauv)
        self.assertTrue(os.path.exists(self.sauv))
        # Modifie puis restaure.
        db.ajouter_produit("SAV", "Savon", 100, 200, 10, 0)
        self.assertEqual(db.nombre_produits(), 2)
        db.restaurer(self.sauv)
        self.assertEqual(db.nombre_produits(), 1)
        # La connexion reste utilisable apres restauration.
        db.ajouter_produit("NEW", "Nouveau", 1, 2, 3, 0)
        self.assertEqual(db.nombre_produits(), 2)
        db.fermer()

    def test_restauration_fichier_invalide(self):
        db = Database(self.base)
        mauvais = os.path.join(self.dossier, "pasunebase.db")
        with open(mauvais, "w") as f:
            f.write("ceci n'est pas une base sqlite")
        with self.assertRaises(ValueError):
            db.restaurer(mauvais)
        db.fermer()

    def test_restauration_remet_schema_a_niveau(self):
        # Cree une "ancienne" sauvegarde sans les colonnes TVA.
        import sqlite3
        vieux = os.path.join(self.dossier, "ancienne.db")
        con = sqlite3.connect(vieux)
        con.executescript(
            "CREATE TABLE produits (id INTEGER PRIMARY KEY, reference TEXT, "
            "designation TEXT, prix_achat REAL, prix_vente REAL, quantite INTEGER, "
            "seuil_alerte INTEGER);"
            "CREATE TABLE ventes (id INTEGER PRIMARY KEY, date_vente TEXT, "
            "client_id INTEGER, total REAL);")
        con.commit()
        con.close()
        db = Database(self.base)
        db.restaurer(vieux)
        # Apres restauration, les colonnes TVA doivent exister (migration relancee).
        cols = {r["name"] for r in
                db.conn.execute("PRAGMA table_info(ventes)").fetchall()}
        self.assertIn("montant_tva", cols)
        db.fermer()


if __name__ == "__main__":
    unittest.main()
