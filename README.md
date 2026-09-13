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

- **Tableau de bord** : chiffre d'affaires du jour, nombre de ventes, valeur du
  stock, nombre de produits/clients, et **alertes de stock** (produits sous le seuil).
- **Produits** : ajouter / modifier / supprimer / rechercher, avec prix d'achat,
  prix de vente, quantité en stock et seuil d'alerte. Les lignes en rupture proche
  sont surlignées.
- **Clients** : fiche client (nom, téléphone, adresse) avec recherche.
- **Nouvelle vente** : panier multi-produits, choix du client (ou « client de
  passage »), contrôle du stock disponible, validation qui **décrémente le stock
  automatiquement** (opération atomique : tout ou rien).
- **Historique** : liste des ventes et détail ligne par ligne.

> Devise par défaut : **FCFA**. Modifiable dans `gestion/ui/widgets.py`
> (constante `DEVISE`).

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
  app.py                Fenêtre principale + assemblage des onglets
  ui/
    dashboard.py        Onglet tableau de bord
    produits.py         Onglet produits (stock)
    clients.py          Onglet clients
    ventes.py           Onglet nouvelle vente
    historique.py       Onglet historique des ventes
    widgets.py          Utilitaires partagés (formatage, devise)
tests/
  test_database.py      Tests de la couche base de données
data/                   Base SQLite locale (générée, ignorée par git)
```

---

## Pistes d'évolution

Ce prototype est volontairement simple. Prochaines étapes possibles :

- Impression / export PDF des factures et tickets de vente.
- Gestion des fournisseurs et des entrées de stock (approvisionnements).
- Rapports par période (jour / semaine / mois) et export Excel.
- Authentification (plusieurs utilisateurs, droits d'accès).
- Sauvegarde/restauration de la base de données.
