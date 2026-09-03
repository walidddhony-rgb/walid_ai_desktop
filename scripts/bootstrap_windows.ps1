# Walid AI Desktop - Windows Bootstrap Script
# Automates installation and setup on Windows 10/11

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Walid AI Desktop - Setup Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$PYTHON_MIN_VERSION = "3.10"
$PYTHON_MAX_VERSION = "3.12"
$REQUIRED_FILES = @("requirements.txt", "main.py", "pyproject.toml")

# Colors
$Success = "Green"
$Error = "Red"
$Warning = "Yellow"
$Info = "Cyan"

# Helper functions
function Test-Python {
    try {
        $pythonVersion = python --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] Python found: $pythonVersion" -ForegroundColor $Success
            return $true
        }
    } catch {
        Write-Host "[ERROR] Python not found in PATH" -ForegroundColor $Error
        return $false
    }
    return $false
}

function Test-Ollama {
    try {
        $ollamaVersion = ollama --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] Ollama found: $ollamaVersion" -ForegroundColor $Success
            return $true
        }
    } catch {
        Write-Host "[WARNING] Ollama not found in PATH" -ForegroundColor $Warning
        return $false
    }
    return $false
}

function Test-RequiredFiles {
    $allPresent = $true
    foreach ($file in $REQUIRED_FILES) {
        if (Test-Path $file) {
            Write-Host "[OK] Found: $file" -ForegroundColor $Success
        } else {
            Write-Host "[ERROR] Missing: $file" -ForegroundColor $Error
            $allPresent = $false
        }
    }
    return $allPresent
}

function Create-VEnv {
    Write-Host "" -ForegroundColor $Info
    Write-Host "Creating virtual environment..." -ForegroundColor $Info
    
    if (Test-Path "venv") {
        Write-Host "[INFO] Virtual environment already exists" -ForegroundColor $Warning
        return $true
    }
    
    try {
        python -m venv venv
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] Virtual environment created" -ForegroundColor $Success
            return $true
        }
    } catch {
        Write-Host "[ERROR] Failed to create virtual environment" -ForegroundColor $Error
        return $false
    }
    return $false
}

function Activate-VEnv {
    Write-Host "" -ForegroundColor $Info
    Write-Host "Activating virtual environment..." -ForegroundColor $Info
    
    $activateScript = ".\venv\Scripts\Activate.ps1"
    if (Test-Path $activateScript) {
        & $activateScript
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] Virtual environment activated" -ForegroundColor $Success
            return $true
        }
    } else {
        Write-Host "[ERROR] Activation script not found" -ForegroundColor $Error
        return $false
    }
    return $false
}

function Install-Dependencies {
    Write-Host "" -ForegroundColor $Info
    Write-Host "Installing dependencies..." -ForegroundColor $Info
    
    try {
        # Upgrade pip first
        Write-Host "Upgrading pip..." -ForegroundColor $Info
        python -m pip install --upgrade pip --quiet
        
        # Install requirements
        Write-Host "Installing requirements.txt..." -ForegroundColor $Info
        pip install -r requirements.txt --quiet
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] Dependencies installed successfully" -ForegroundColor $Success
            return $true
        }
    } catch {
        Write-Host "[ERROR] Failed to install dependencies" -ForegroundColor $Error
        return $false
    }
    return $false
}

function Install-DevDependencies {
    Write-Host "" -ForegroundColor $Info
    Write-Host "Installing development dependencies (optional)..." -ForegroundColor $Info
    
    if (Test-Path "requirements-dev.txt") {
        try {
            pip install -r requirements-dev.txt --quiet
            Write-Host "[OK] Development dependencies installed" -ForegroundColor $Success
            return $true
        } catch {
            Write-Host "[WARNING] Failed to install dev dependencies (continuing...)" -ForegroundColor $Warning
            return $false
        }
    } else {
        Write-Host "[INFO] requirements-dev.txt not found, skipping" -ForegroundColor $Warning
        return $true
    }
}

function Check-Ollama-Models {
    Write-Host "" -ForegroundColor $Info
    Write-Host "Checking Ollama models..." -ForegroundColor $Info
    
    try {
        $models = ollama list 2>&1
        if ($models -match "No models found") {
            Write-Host "[WARNING] No Ollama models installed" -ForegroundColor $Warning
            Write-Host "Recommended: ollama pull llama3.2:3b" -ForegroundColor $Info
            return $false
        } else {
            Write-Host "[OK] Ollama models found:" -ForegroundColor $Success
            Write-Host $models -ForegroundColor $Info
            return $true
        }
    } catch {
        Write-Host "[WARNING] Could not check Ollama models" -ForegroundColor $Warning
        return $false
    }
}

function Create-EnvFile {
    Write-Host "" -ForegroundColor $Info
    Write-Host "Creating .env file (if not exists)..." -ForegroundColor $Info
    
    if (-not (Test-Path ".env")) {
        $envContent = @"
# Ollama configuration
OLLAMA_HOST=http://localhost:11434

# Default model
DEFAULT_MODEL=llama3.2:3b

# Database path
DATABASE_PATH=./data/walid_ai.db

# Knowledge base path
KNOWLEDGE_BASE_PATH=./data/knowledge
"@
        $envContent | Out-File -FilePath ".env" -Encoding UTF8
        Write-Host "[OK] .env file created" -ForegroundColor $Success
    } else {
        Write-Host "[INFO] .env file already exists" -ForegroundColor $Warning
    }
}

function Launch-Application {
    Write-Host "" -ForegroundColor $Info
    Write-Host "Launching Walid AI Desktop..." -ForegroundColor $Info
    
    try {
        python main.py
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] Application launched successfully" -ForegroundColor $Success
            return $true
        }
    } catch {
        Write-Host "[ERROR] Failed to launch application" -ForegroundColor $Error
        return $false
    }
    return $false
}

# Main installation flow
Write-Host "Step 1: Checking prerequisites..." -ForegroundColor $Info
Write-Host "" -ForegroundColor $Info

$pythonOk = Test-Python
$ollamaOk = Test-Ollama
$filesOk = Test-RequiredFiles

if (-not $pythonOk) {
    Write-Host "" -ForegroundColor $Error
    Write-Host "ERROR: Python is not installed or not in PATH" -ForegroundColor $Error
    Write-Host "Please install Python 3.11 from https://www.python.org/downloads/" -ForegroundColor $Error
    Write-Host "Make sure to check 'Add Python to PATH' during installation" -ForegroundColor $Error
    exit 1
}

if (-not $filesOk) {
    Write-Host "" -ForegroundColor $Error
    Write-Host "ERROR: Required files are missing" -ForegroundColor $Error
    Write-Host "Make sure you're running this script from the project root directory" -ForegroundColor $Error
    exit 1
}

Write-Host "" -ForegroundColor $Info
Write-Host "Step 2: Setting up virtual environment..." -ForegroundColor $Info
Write-Host "" -ForegroundColor $Info

if (-not (Create-VEnv)) {
    Write-Host "ERROR: Failed to create virtual environment" -ForegroundColor $Error
    exit 1
}

if (-not (Activate-VEnv)) {
    Write-Host "ERROR: Failed to activate virtual environment" -ForegroundColor $Error
    exit 1
}

Write-Host "" -ForegroundColor $Info
Write-Host "Step 3: Installing dependencies..." -ForegroundColor $Info
Write-Host "" -ForegroundColor $Info

if (-not (Install-Dependencies)) {
    Write-Host "ERROR: Failed to install dependencies" -ForegroundColor $Error
    exit 1
}

Install-DevDependencies

Write-Host "" -ForegroundColor $Info
Write-Host "Step 4: Configuration..." -ForegroundColor $Info
Write-Host "" -ForegroundColor $Info

Create-EnvFile
Check-Ollama-Models

Write-Host "" -ForegroundColor $Success
Write-Host "========================================" -ForegroundColor $Success
Write-Host "  Setup completed successfully!" -ForegroundColor $Success
Write-Host "========================================" -ForegroundColor $Success
Write-Host ""

Write-Host "Next steps:" -ForegroundColor $Info
Write-Host "1. Make sure Ollama is running: ollama serve" -ForegroundColor $Info
Write-Host "2. Install a model if needed: ollama pull llama3.2:3b" -ForegroundColor $Info
Write-Host "3. Run the application: python main.py" -ForegroundColor $Info
Write-Host ""

# Ask user if they want to launch now
$response = Read-Host "Launch Walid AI Desktop now? (y/n)"
if ($response -eq "y" -or $response -eq "Y") {
    Launch-Application
} else {
    Write-Host "You can launch it later with: python main.py" -ForegroundColor $Info
}

Write-Host ""
Write-Host "For more information, see: docs/INSTALL_WINDOWS.md" -ForegroundColor $Info
Write-Host ""
