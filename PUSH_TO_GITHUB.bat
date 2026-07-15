@echo off
REM ============================================================
REM  One-click push of this folder to GitHub.
REM  Just double-click this file. It will:
REM    1. Make sure Git and the GitHub CLI are installed
REM    2. Sign you into GitHub (a browser window opens once)
REM    3. Push every file to your ai-engineering-projects repo
REM ============================================================
setlocal
cd /d "%~dp0"

echo.
echo === Step 1: checking tools ===
where git >nul 2>&1 || (echo Installing Git... & winget install --id Git.Git -e --source winget)
where gh  >nul 2>&1 || (echo Installing GitHub CLI... & winget install --id GitHub.cli -e --source winget)

echo.
echo === Step 2: signing in to GitHub (browser opens the first time) ===
gh auth status >nul 2>&1 || gh auth login

echo.
echo === Step 3: pushing all files ===
if not exist ".git" (
  git init
  git branch -M main
)
git add .
git commit -m "Initial commit: 15-project AI engineering monorepo + P1 Support Knowledge Copilot"
git remote remove origin >nul 2>&1
git remote add origin https://github.com/GauravWarke/ai-engineering-projects.git
git push -u origin main

echo.
echo === DONE ===
echo Your code is at: https://github.com/GauravWarke/ai-engineering-projects
echo.
pause
