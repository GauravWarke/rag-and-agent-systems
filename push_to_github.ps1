# One-shot (Windows PowerShell): create the GitHub repo and push this monorepo.
# Requires GitHub CLI (winget install GitHub.cli). Run from inside this folder.
$ErrorActionPreference = "Stop"
$Repo = "ai-engineering-projects"
$Visibility = "private"   # or "public"

gh auth status 2>$null; if ($LASTEXITCODE -ne 0) { gh auth login }

if (-not (Test-Path ".git")) { git init; git branch -M main }
git add .
git commit -m "Initial commit: 15-project AI engineering monorepo + P1 Support Knowledge Copilot scaffold"
gh repo create $Repo --$Visibility --source=. --remote=origin --push
$me = gh api user -q .login
Write-Host "Done -> https://github.com/$me/$Repo"
