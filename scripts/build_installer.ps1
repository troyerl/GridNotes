# Build a distributable GridNotes Windows app + installer.
$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir

$AppName = "GridNotes"
$BuildVenv = Join-Path $RootDir ".build-venv"
$DistDir = Join-Path $RootDir "dist"
$BuildDir = Join-Path $RootDir "build"
$AppDistDir = Join-Path $DistDir $AppName
$ZipPath = Join-Path $DistDir "GridNotes-Windows.zip"
$SetupPath = Join-Path $DistDir "GridNotes-Setup.exe"
$IssPath = Join-Path $RootDir "scripts\gridnotes.iss"

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

Write-Host "==> Generating icon.ico for Windows"
python (Join-Path $RootDir "scripts\generate_icon.py")

Write-Host "==> Generating Windows version info for GridNotes.exe"
python (Join-Path $RootDir "scripts\generate_win_version_info.py")

Write-Host "==> Running PyInstaller"
pyinstaller gridnotes.spec --noconfirm --clean

$ExePath = Join-Path $AppDistDir "GridNotes.exe"
if (-not (Test-Path $ExePath)) {
    throw "Error: expected executable at $ExePath"
}

$TestsDir = Join-Path $AppDistDir "tests"
if (Test-Path $TestsDir) {
    throw "Error: tests/ must not be included in the installer bundle"
}
$TestArtifacts = Get-ChildItem -Path $AppDistDir -Recurse -Include @(
    "test_*.py",
    "conftest.py",
    "pytest.ini"
) -ErrorAction SilentlyContinue
if ($TestArtifacts) {
    throw ("Error: test artifacts must not be bundled: " + ($TestArtifacts.FullName -join ", "))
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

    $AppVersion = python (Join-Path $RootDir "scripts\read_app_version.py")
    if (-not $AppVersion) {
        throw "Error: could not read app version from gridnotes/app/app_version.py"
    }
    Write-Host "==> Creating Windows installer with Inno Setup (v$AppVersion)"
    & $InnoCompiler "/DMyAppVersion=$AppVersion" $IssPath
    if (Test-Path $SetupPath) {
        $BuiltInstaller = $true
    }
    break
}

if (Test-Path $ZipPath) { Remove-Item -Force $ZipPath }
Write-Host "==> Creating GridNotes-Windows.zip (in-place updates)"
Compress-Archive -Path (Join-Path $AppDistDir "*") -DestinationPath $ZipPath

if (-not $BuiltInstaller) {
    Write-Host "==> Inno Setup not found; ZIP is the only Windows installer package"
    Write-Host "    Install Inno Setup 6 to produce GridNotes-Setup.exe:"
    Write-Host "    https://jrsoftware.org/isinfo.php"
}

Write-Host ""
Write-Host "Build complete."
Write-Host "  App folder: $AppDistDir"
if ($BuiltInstaller) {
    Write-Host "  Installer:  $SetupPath"
    Write-Host ""
    Write-Host "Share GridNotes-Setup.exe with others. They run it and follow the setup wizard."
} else {
    Write-Host "  Zip:        $ZipPath"
    Write-Host ""
    Write-Host "Share the zip with others. They unzip it and run GridNotes.exe."
}

Write-Host ""
Write-Host "User data is stored at:"
Write-Host "  %APPDATA%\GridNotes\driver_history.db"
