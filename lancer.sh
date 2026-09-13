#!/bin/bash
# Raccourci de lancement (Linux) - executez ./lancer.sh, ou double-cliquez
# si votre gestionnaire de fichiers autorise l'execution des scripts.
# Se place dans le dossier du script puis lance l'application.
cd "$(dirname "$0")" || exit 1

if command -v python3 >/dev/null 2>&1; then
    python3 main.py
else
    echo "Python 3 est introuvable."
    echo "Installez-le (ex. : sudo apt install python3 python3-tk)."
    read -r -p "Appuyez sur Entree pour fermer..."
fi
