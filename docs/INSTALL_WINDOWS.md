# Windows Installation Guide

Complete guide to installing and running Walid AI Desktop on Windows 10/11.

## Prerequisites

- **Windows 10 version 1903+** or **Windows 11**
- **Python 3.11** (3.10 or 3.12 may work but not tested)
- **Git** (optional, for cloning the repository)
- **Ollama** (for local LLM inference)
- **8GB RAM minimum** (16GB recommended for larger models)
- **10GB free disk space**

## Step 1: Install Python

1. Download Python 3.11 from [python.org](https://www.python.org/downloads/release/python-31110/)
2. Run the installer
3. **Important:** Check "Add Python to PATH" during installation
4. Click "Install Now"

Verify installation:
```powershell
python --version
# Should output: Python 3.11.x
```

## Step 2: Install Ollama

1. Download Ollama for Windows from [ollama.com](https://ollama.com/download/windows)
2. Run the installer
3. Ollama will start automatically as a background service

Verify installation:
```powershell
ollama --version
```

### Recommended Models

Install one or more of these models based on your needs:

```powershell
# General purpose (balanced)
ollama pull llama3.2:3b

# Better reasoning (requires 8GB+ RAM)
ollama pull llama3.2

# Code-focused
ollama pull codellama:7b

# Small and fast
ollama pull phi3:mini
```

## Step 3: Clone or Download the Repository

### Option A: Using Git
```powershell
git clone https://github.com/walidddhony-rgb/walid_ai_desktop.git
cd walid_ai_desktop
```

### Option B: Manual Download
1. Go to [github.com/walidddhony-rgb/walid_ai_desktop](https://github.com/walidddhony-rgb/walid_ai_desktop)
2. Click "Code" → "Download ZIP"
3. Extract to a folder (e.g., `C:\Users\YourName\walid_ai_desktop`)
4. Open PowerShell in that folder

## Step 4: Create Virtual Environment

```powershell
# Create virtual environment
python -m venv venv

# Activate it
.\venv\Scripts\Activate.ps1
```

If you get a PowerShell execution policy error:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Step 5: Install Dependencies

```powershell
# Upgrade pip
python -m pip install --upgrade pip

# Install main requirements
pip install -r requirements.txt

# Install development requirements (optional, for testing)
pip install -r requirements-dev.txt
```

## Step 6: Configure Environment (Optional)

Create a `.env` file in the project root for custom settings:

```env
# Ollama configuration
OLLAMA_HOST=http://localhost:11434

# Default model
DEFAULT_MODEL=llama3.2:3b

# Database path
DATABASE_PATH=./data/walid_ai.db

# Knowledge base path
KNOWLEDGE_BASE_PATH=./data/knowledge
```

## Step 7: Run the Application

### Start Ollama Server (if not running)
```powershell
ollama serve
```

### Run Walid AI Desktop
```powershell
# Make sure you're in the project directory and venv is activated
python main.py
```

The application window should open within a few seconds.

## First Run Checklist

After launching, verify:

- [ ] Application window opens without errors
- [ ] Status bar shows model connection (green indicator)
- [ ] You can type a message and get a response
- [ ] Voice button appears (if microphone is available)
- [ ] Settings dialog opens and shows current configuration

## Common Issues and Solutions

### Issue: "ModuleNotFoundError: No module named 'PyQt6'"

**Solution:**
```powershell
pip install PyQt6
```

### Issue: "Ollama connection failed"

**Solutions:**
1. Make sure Ollama is running: `ollama serve`
2. Check if model is installed: `ollama list`
3. Pull a model if none installed: `ollama pull llama3.2:3b`

### Issue: "Permission denied" when running PowerShell scripts

**Solution:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Issue: Application crashes on startup

**Solutions:**
1. Check Python version: must be 3.10-3.12
2. Reinstall dependencies: `pip install -r requirements.txt --force-reinstall`
3. Check logs in `logs/app.log` for detailed error messages

### Issue: Voice features not working

**Solutions:**
1. Check microphone permissions in Windows Settings → Privacy → Microphone
2. Install additional TTS engine: `pip install edge-tts`
3. Test STT separately: run `voice/stt_engine.py` directly

### Issue: High memory usage

**Solutions:**
1. Use smaller models: `ollama pull phi3:mini`
2. Close other memory-intensive applications
3. Reduce context size in settings

## Performance Tips

1. **Use SSD storage** for faster model loading
2. **Close unnecessary applications** to free up RAM
3. **Use quantized models** (e.g., `llama3.2:3b` instead of `llama3.2:70b`)
4. **Keep Ollama updated** for performance improvements

## Uninstallation

To completely remove Walid AI Desktop:

1. Delete the project folder
2. Remove virtual environment (delete `venv` folder)
3. Remove Ollama models (optional):
   ```powershell
   ollama rm <model-name>
   ```
4. Uninstall Ollama from Windows Settings → Apps

## Getting Help

- **GitHub Issues:** [github.com/walidddhony-rgb/walid_ai_desktop/issues](https://github.com/walidddhony-rgb/walid_ai_desktop/issues)
- **Documentation:** Check `docs/` folder for additional guides
- **Logs:** Review `logs/app.log` for detailed error information

## Next Steps

After successful installation:

1. Read the [User Guide](USER_GUIDE.md) for usage instructions
2. Explore the [Features Overview](FEATURES.md)
3. Check out [Examples](examples/) for common workflows
4. Join discussions in GitHub Issues or Discussions

---

**Last updated:** September 2026  
**Tested on:** Windows 11 23H2, Python 3.11.10, Ollama 0.3.x
