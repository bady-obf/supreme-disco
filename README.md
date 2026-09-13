# Gestion Commerciale & Stock

Application de bureau (prototype) pour gérer les **produits, le stock, les clients
et les ventes** d'une petite entreprise. Fonctionne **hors-ligne**, sur
Windows, macOS et Linux.

Construite avec la **bibliothèque standard de Python** uniquement :
[`tkinter`](https://docs.python.org/3/library/tkinter.html) pour l'interface
et [`sqlite3`](https://docs.python.org/3/library/sqlite3.html) pour la base de
données locale — **aucune dépendance externe à installer**.

---

## Fonctionnalités

- **Authentification** : écran de connexion, comptes multi-utilisateurs avec
  **rôles** (`admin` / `vendeur`). Au premier lancement, l'application invite à
  créer le compte administrateur. Les mots de passe sont **hachés** (PBKDF2), jamais
  stockés en clair. Un onglet **Utilisateurs** (admin) permet de gérer les comptes.
- **Tableau de bord** : chiffre d'affaires du jour, nombre de ventes, valeur du
  stock, nombre de produits/clients, **graphique du CA des 14 derniers jours**
  (dessiné sans dépendance externe) et **alertes de stock** (produits sous le seuil).
- **Produits** : ajouter / modifier / supprimer / rechercher, avec prix d'achat,
  prix de vente, quantité en stock et seuil d'alerte. Les lignes en rupture proche
  sont surlignées.
- **Clients** : fiche client (nom, téléphone, adresse) avec recherche.
- **Fournisseurs** : fiche fournisseur (nom, téléphone, adresse) avec recherche.
- **Nouvelle vente** : panier multi-produits, choix du client (ou « client de
  passage »), **remise** (en montant ou en %) et **TVA** (taux par défaut
  paramétrable, 18 % pour le Sénégal / zone OHADA), avec récapitulatif
  Sous-total / Remise / HT / TVA / TTC en direct. La validation **décrémente le
  stock automatiquement** (opération atomique : tout ou rien).
- **Facture imprimable** : après une vente (ou depuis l'historique), génération
  d'une **facture HTML** ouverte dans le navigateur, prête à imprimer ou à
  **enregistrer en PDF** (Ctrl+P). L'en-tête reprend les informations de
  l'entreprise et le pied détaille **Sous-total, remise, HT, TVA et TTC**.
- **Approvisionnement** : entrée de stock depuis un fournisseur (panier avec prix
  d'achat), qui **incrémente le stock** et peut mettre à jour le prix d'achat.
- **Historique** : liste des ventes et détail ligne par ligne.
- **Rapports par période** : ventes, approvisionnements ou état du stock, exportés
  en **Excel (`.xlsx`)** ou **CSV**. Le `.xlsx` est généré avec la bibliothèque
  standard uniquement (aucune dépendance type `openpyxl` requise).
- **Paramètres** : informations de l'entreprise imprimées sur les factures,
  **taux de TVA par défaut**, et **sauvegarde / restauration** de la base de
  données (copie fiable via l'API de sauvegarde SQLite ; la restauration remet
  automatiquement le schéma à niveau).

> Devise par défaut : **FCFA**. Modifiable dans `gestion/ui/widgets.py`
> (constante `DEVISE`).
>
> Les factures sont enregistrées dans `factures/` et les rapports dans
> `rapports/` (dossiers créés automatiquement, ignorés par git).

---

## Prérequis

- **Python 3.10 ou plus récent**.
- Le module `tkinter` :
  - **Windows / macOS** : inclus avec l'installateur officiel de
    [python.org](https://www.python.org/downloads/). Rien à faire.
  - **Linux (Debian/Ubuntu)** : `sudo apt install python3-tk`
  - **Linux (Fedora)** : `sudo dnf install python3-tkinter`

Vérifier que tout est prêt :

```bash
python3 -c "import tkinter, sqlite3; print('OK')"
```

---

## Lancer l'application

Depuis le dossier du projet :

```bash
python3 main.py
```

La base de données est créée automatiquement dans `data/gestion.db` au premier
démarrage.

Au **premier lancement**, l'application demande de créer le **compte
administrateur**. Ensuite, chaque démarrage passe par l'écran de connexion.

**Rôles** :
- `admin` : accès à tout (y compris fournisseurs, approvisionnements, rapports,
  paramètres et gestion des utilisateurs) ;
- `vendeur` : tableau de bord, produits, clients, nouvelle vente et historique.

Si vous chargez les données de démonstration (`seed_demo.py`), deux comptes
sont créés : `admin` / `admin` et `vendeur` / `vendeur` — **pensez à changer ces
mots de passe**.

### (Optionnel) Charger des données de démonstration

```bash
python3 seed_demo.py
```

Cela insère quelques produits, clients et une vente d'exemple pour découvrir
l'application immédiatement.

---

## Lancer les tests

La logique métier (stock, ventes, statistiques) est couverte par des tests qui
s'exécutent **sans interface graphique** :

```bash
python3 -m unittest discover -s tests -v
```

---

## Structure du projet

```
main.py                 Point d'entrée (lance l'application)
seed_demo.py            Insère des données de démonstration
gestion/
  database.py           Couche base de données SQLite (logique métier, testée)
  facture.py            Génération des factures HTML imprimables
  xlsx.py               Écriture de fichiers Excel (.xlsx) sans dépendance
  rapports.py           Construction et export des rapports (.xlsx / .csv)
  app.py                Fenêtre principale + assemblage des onglets
  ui/
    connexion.py        Écran de connexion / création du 1er admin
    dashboard.py        Onglet tableau de bord
    produits.py         Onglet produits (stock)
    clients.py          Onglet clients
    fournisseurs.py     Onglet fournisseurs
    utilisateurs.py     Onglet utilisateurs (admin)
    ventes.py           Onglet nouvelle vente (remise + TVA)
    approvisionnements.py  Onglet approvisionnement (entrées de stock)
    historique.py       Onglet historique des ventes
    rapports.py         Onglet rapports (export Excel / CSV)
    parametres.py       Onglet paramètres (infos entreprise, TVA)
    graphique.py        Histogramme du CA par jour (Canvas, sans dépendance)
    widgets.py          Utilitaires partagés (formatage, devise)
tests/
  test_database.py            Tests de la couche base de données
  test_fonctions_avancees.py  Tests fournisseurs, appro, rapports, xlsx, facture
data/                   Base SQLite locale (générée, ignorée par git)
factures/               Factures HTML générées (ignoré par git)
rapports/               Rapports Excel/CSV générés (ignoré par git)
```

---

## Pistes d'évolution

Prochaines étapes possibles :

- Numérotation personnalisée des factures.
- Gestion de plusieurs taux de TVA par produit.
- Sauvegarde automatique planifiée.
- Journal d'activité par utilisateur.
