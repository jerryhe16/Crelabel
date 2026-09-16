$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$OutputDir = Join-Path $ProjectDir "dist"
$ReleaseDir = Join-Path $ProjectDir "release\Crelabel_v0.8.14"
$InstallerDir = Join-Path $ProjectDir "release"

Set-Location -LiteralPath $ProjectDir
python -m PyInstaller --noconfirm --clean --onefile --windowed --name "Crelabel" --icon "crelabel.ico" `
    --add-data "fonts/led_board-7.ttf;fonts" `
    --add-data "assets/prime-logo.png;assets" `
    --add-data "assets/prime-logo.svg;assets" `
    --exclude-module numpy `
    --exclude-module tkinter `
    --exclude-module PIL.ImageTk `
    --exclude-module PySide6.QtNetwork `
    --exclude-module PySide6.QtOpenGL `
    --exclude-module PySide6.QtQml `
    --exclude-module PySide6.QtQuick `
    crelabel.py

New-Item -ItemType Directory -Path $ReleaseDir -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $ReleaseDir "drivers") -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $ProjectDir "drivers\NiimbotPrinterDriverInstaller-3.0.2.1.exe") -Destination (Join-Path $ReleaseDir "drivers") -Force
Copy-Item -LiteralPath (Join-Path $OutputDir "Crelabel.exe") -Destination (Join-Path $ReleaseDir "Crelabel.exe") -Force
New-Item -ItemType Directory -Path (Join-Path $ReleaseDir "fonts") -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $ProjectDir "fonts\led_board-7.ttf") -Destination (Join-Path $ReleaseDir "fonts") -Force
New-Item -ItemType Directory -Path (Join-Path $ReleaseDir "assets") -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $ProjectDir "assets\prime-logo.png") -Destination (Join-Path $ReleaseDir "assets") -Force
Copy-Item -LiteralPath (Join-Path $ProjectDir "assets\prime-logo.svg") -Destination (Join-Path $ReleaseDir "assets") -Force
Copy-Item -LiteralPath (Join-Path $ProjectDir "Crelabel-Quick-Guide.txt") -Destination $ReleaseDir -Force
Copy-Item -LiteralPath (Join-Path $ProjectDir "THIRD_PARTY_NOTICES.txt") -Destination $ReleaseDir -Force
$RuntimeDir = Join-Path $ReleaseDir "runtime"
New-Item -ItemType Directory -Path $RuntimeDir -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $ProjectDir "vendor\lark-cli\lark-cli.exe") -Destination $RuntimeDir -Force
Copy-Item -LiteralPath (Join-Path $ProjectDir "vendor\lark-cli\LICENSE") -Destination (Join-Path $RuntimeDir "LARK_CLI_LICENSE.txt") -Force

$IsccCandidates = @(
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
)
$Iscc = $IsccCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if ($Iscc) {
    & $Iscc (Join-Path $ProjectDir "Crelabel.iss")
} else {
    Write-Warning "Inno Setup not found. Crelabel.exe was built, but the setup package was skipped."
}

Write-Host ""
Write-Host "Build complete: $(Join-Path $OutputDir 'Crelabel.exe')"
Write-Host "Installer output: $InstallerDir"
