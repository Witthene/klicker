# Gera dist\Klicker.exe (um único arquivo, sem console).
Set-Location $PSScriptRoot

function Step($description, [scriptblock]$command) {
    & $command
    if ($LASTEXITCODE -ne 0) { throw "Falhou: $description" }
}

if (-not (Test-Path .venv)) { Step "criar venv" { python -m venv .venv } }
Step "instalar dependências" { .\.venv\Scripts\python -m pip install -q -r requirements.txt pyinstaller }
Step "testes" { .\.venv\Scripts\python -m unittest discover -s tests 2>$null }
Step "exportar ícone" { .\.venv\Scripts\python -m klicker --export-icon assets\icon.ico }
Step "pyinstaller" {
    .\.venv\Scripts\pyinstaller --noconfirm --clean --onefile --windowed `
        --name Klicker --icon assets\icon.ico --log-level WARN run.py
}

Write-Host "`nPronto: $PSScriptRoot\dist\Klicker.exe"
