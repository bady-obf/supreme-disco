@echo off
REM Raccourci de lancement (Windows) - double-cliquez sur ce fichier.
REM Se place dans le dossier du script puis lance l'application.
cd /d "%~dp0"

REM Essaie le lanceur "py" (recommande sur Windows), sinon "python".
py main.py 2>nul || python main.py

REM En cas d'erreur, garde la fenetre ouverte pour lire le message.
if errorlevel 1 (
    echo.
    echo Impossible de lancer l'application.
    echo Verifiez que Python 3 est installe : https://www.python.org/downloads/
    echo ^(Cochez "tcl/tk and IDLE" pendant l'installation.^)
    echo.
    pause
)
