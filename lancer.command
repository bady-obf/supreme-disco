#!/bin/bash
# Raccourci de lancement (macOS) - double-cliquez sur ce fichier.
# (La premiere fois, il faut le rendre executable : voir le README.)
# Se place dans le dossier du script puis lance l'application.
cd "$(dirname "$0")" || exit 1

if command -v python3 >/dev/null 2>&1; then
    python3 main.py
else
    echo "Python 3 est introuvable. Installez-le depuis https://www.python.org/downloads/"
    read -r -p "Appuyez sur Entree pour fermer..."
fi
