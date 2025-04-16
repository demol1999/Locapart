@echo off
echo 🚀 Lancement du backend FastAPI...
start cmd /k "cd /d C:\Script\locappart\Locapart\backend && uvicorn main:app --reload"

timeout /t 2

echo 🚀 Lancement du frontend React...
start cmd /k "cd /d C:\Script\locappart\Locapart\frontend && npm run dev"

echo ✅ Tout est lancé ! Appuie sur une touche pour fermer ce terminal...
pause > nul
