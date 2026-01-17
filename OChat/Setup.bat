@echo off
echo Installation des modules Python...

:: Vérifie si Python est installé
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Python n'est pas installé. Installez-le avant de continuer.
    pause
    exit /b
)

:: Vérifie si le fichier modules.txt existe
if not exist modules.txt (
    echo ❌ Le fichier modules.txt est introuvable !
    pause
    exit /b
)

:: Installation des modules
echo 📦 Installation des modules depuis modules.txt...
pip install -r modules.txt

echo ✅ Tous les modules ont été installés !