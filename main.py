"""Point d'entree de l'application de gestion commerciale.

Lancez simplement :
    python3 main.py

La base de donnees est creee automatiquement dans ``data/gestion.db``
au premier demarrage.
"""

from gestion.app import main

if __name__ == "__main__":
    main()
