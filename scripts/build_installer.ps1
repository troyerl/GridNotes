# Build a distributable Racing Book Windows app + installer.
$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir

$AppName = "Racing Book"
$BuildVenv = Join-Path $RootDir ".build-venv"
$DistDir = Join-Path $RootDir "dist"
$BuildDir = Join-Path $RootDir "build"
$AppDistDir = Join-Path $DistDir $AppName
$ZipPath = Join-Path $DistDir "RacingBook-Windows.zip"
$SetupPath = Join-Path $DistDir "RacingBook-Setup.exe"
$IssPath = Join-Path $RootDir "scripts\racing_book.iss"

Write-Host "==> Building $AppName from $RootDir"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Error: python is required on PATH."
}

Write-Host "==> Creating build virtual environment"
if (Test-Path $BuildVenv) {
    Remove-Item -Recurse -Force $BuildVenv
}
python -m venv $BuildVenv
& (Join-Path $BuildVenv "Scripts\Activate.ps1")

Write-Host "==> Installing dependencies"
python -m pip install --upgrade pip
python -m pip install -r requirements-build.txt

Write-Host "==> Cleaning previous build artifacts"
if (Test-Path $BuildDir) { Remove-Item -Recurse -Force $BuildDir }
if (Test-Path $DistDir) { Remove-Item -Recurse -Force $DistDir }

Write-Host "==> Running PyInstaller"
pyinstaller racing_book.spec --noconfirm --clean

$ExePath = Join-Path $AppDistDir "Racing Book.exe"
if (-not (Test-Path $ExePath)) {
    throw "Error: expected executable at $ExePath"
}

$BuiltInstaller = $false
$InnoCandidates = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
)

foreach ($InnoCompiler in $InnoCandidates) {
    if (-not (Test-Path $InnoCompiler)) {
        continue
    }

    Write-Host "==> Creating Windows installer with Inno Setup"
    & $InnoCompiler $IssPath
    if (Test-Path $SetupPath) {
        $BuiltInstaller = $true
    }
    break
}

if (-not $BuiltInstaller) {
    Write-Host "==> Inno Setup not found; creating ZIP package instead"
    Write-Host "    Install Inno Setup 6 to produce RacingBook-Setup.exe:"
    Write-Host "    https://jrsoftware.org/isinfo.php"
    if (Test-Path $ZipPath) { Remove-Item -Force $ZipPath }
    Compress-Archive -Path (Join-Path $AppDistDir "*") -DestinationPath $ZipPath
}

Write-Host ""
Write-Host "Build complete."
Write-Host "  App folder: $AppDistDir"
if ($BuiltInstaller) {
    Write-Host "  Installer:  $SetupPath"
    Write-Host ""
    Write-Host "Share RacingBook-Setup.exe with others. They run it and follow the setup wizard."
} else {
    Write-Host "  Zip:        $ZipPath"
    Write-Host ""
    Write-Host "Share the zip with others. They unzip it and run Racing Book.exe."
}

Write-Host ""
Write-Host "User data is stored at:"
Write-Host "  %APPDATA%\RacingBook\driver_history.db"
