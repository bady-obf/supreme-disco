"""Remplit la base avec des donnees de demonstration.

Utile pour tester l'application rapidement :
    python3 seed_demo.py

Cree/complete ``data/gestion.db`` avec quelques produits, clients et une vente.
"""

from gestion.database import Database


def main():
    db = Database("data/gestion.db")

    produits = [
        # reference, designation, prix_achat, prix_vente, quantite, seuil_alerte
        ("RIZ25", "Sac de riz 25 kg", 12000, 15000, 40, 5),
        ("CIM50", "Sac de ciment 50 kg", 3500, 4200, 8, 10),
        ("HUI1L", "Huile vegetale 1 L", 900, 1100, 120, 20),
        ("SUC1K", "Sucre 1 kg", 600, 800, 60, 15),
        ("SAV01", "Savon de menage", 200, 300, 4, 12),
    ]
    ids = {}
    for ref, des, pa, pv, q, s in produits:
        try:
            ids[ref] = db.ajouter_produit(ref, des, pa, pv, q, s)
        except Exception:
            print(f"Produit {ref} deja present, ignore.")

    clients = [
        ("Boutique Fatou", "770000001", "Marche Sandaga, Dakar"),
        ("Restaurant Teranga", "770000002", "Plateau, Dakar"),
        ("Chantier Diallo", "770000003", "Thies"),
    ]
    for nom, tel, adr in clients:
        db.ajouter_client(nom, tel, adr)

    fournisseurs = [
        ("Grossiste Central", "780000001", "Zone industrielle, Dakar"),
        ("Import Sahel", "780000002", "Kaolack"),
    ]
    fids = {}
    for nom, tel, adr in fournisseurs:
        fids[nom] = db.ajouter_fournisseur(nom, tel, adr)

    # Informations de l'entreprise (en-tete des factures).
    db.definir_parametre("entreprise_nom", "Ma Boutique")
    db.definir_parametre("entreprise_adresse", "Marche central, Dakar")
    db.definir_parametre("entreprise_telephone", "+221 33 000 00 00")

    # Un approvisionnement d'exemple (entree de stock).
    if "CIM50" in ids:
        db.enregistrer_approvisionnement(
            fids["Grossiste Central"],
            [{"produit_id": ids["CIM50"], "quantite": 50, "prix_achat": 3600}],
        )

    # Une vente d'exemple si le riz existe.
    if "RIZ25" in ids:
        cid = db.lister_clients()[0]["id"]
        db.enregistrer_vente(cid, [{"produit_id": ids["RIZ25"], "quantite": 3}])

    print("Donnees de demonstration inserees dans data/gestion.db")
    print(f"- Produits      : {db.nombre_produits()}")
    print(f"- Clients       : {db.nombre_clients()}")
    print(f"- Fournisseurs  : {db.nombre_fournisseurs()}")
    print(f"- Valeur du stock : {db.valeur_stock():,.0f} FCFA".replace(",", " "))
    db.fermer()


if __name__ == "__main__":
    main()
