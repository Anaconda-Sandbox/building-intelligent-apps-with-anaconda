# Installing Conda: Quick Start Guide

This guide provides cross-platform instructions for installing conda using command-line methods (no GUI required) that work on **Windows PowerShell**, **WSL2**, **macOS**, and **Linux**.

**Estimated time: 5-10 minutes**

## 🚀 Quick Install (Choose One)

### Option 1: conda-express (Modern & Fast) ⭐ Recommended

**conda-express** (`cx`) is a lightweight, single-binary bootstrapper for conda. It's the fastest way to get started with modern tooling:

#### macOS / Linux / WSL2:

```bash
curl -fsSL https://jezdez.github.io/conda-express/get-cx.sh | sh
```

#### Windows PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://jezdez.github.io/conda-express/get-cx.ps1 | iex"
```

**What it does:**
- ✅ Downloads a 7-11 MB static binary (vs 500+ MB for traditional conda)
- ✅ Detects your platform automatically
- ✅ Verifies checksums for security
- ✅ Updates your PATH automatically
- ✅ Bootstraps conda in ~3-5 seconds
- ✅ Ready to use immediately

**After installation:**
```bash
cx bootstrap                    # First run only
cx create -n myenv python=3.12  # Create environments
cx shell myenv                  # Activate environments
```

**Customize installation with environment variables:**
```bash
# Choose installation directory
CX_INSTALL_DIR=~/.local/bin curl -fsSL https://jezdez.github.io/conda-express/get-cx.sh | sh

# Skip PATH updates
CX_NO_PATH_UPDATE=1 curl -fsSL https://jezdez.github.io/conda-express/get-cx.sh | sh

# Skip auto-bootstrap
CX_NO_BOOTSTRAP=1 curl -fsSL https://jezdez.github.io/conda-express/get-cx.sh | sh
```

---

### Option 2: Traditional Miniconda (Standard)

Use this if you prefer the traditional conda experience or need conda-mamba-solver.

#### macOS / Linux / WSL2:

```bash
curl -fsSL https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -o ~/miniconda.sh && bash ~/miniconda.sh -b -p ~/miniconda && rm ~/miniconda.sh
```

**For macOS (Intel):**
```bash
curl -fsSL https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh -o ~/miniconda.sh && bash ~/miniconda.sh -b -p ~/miniconda && rm ~/miniconda.sh
```

**For macOS (Apple Silicon):**
```bash
curl -fsSL https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.sh -o ~/miniconda.sh && bash ~/miniconda.sh -b -p ~/miniconda && rm ~/miniconda.sh
```

#### Windows PowerShell:

```powershell
$url = "https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe"
$path = "$env:USERPROFILE\miniconda_installer.exe"
(New-Object System.Net.ServicePointManager).SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
Invoke-WebRequest -Uri $url -OutFile $path
& $path /S /D=%USERPROFILE%\miniconda
Remove-Item $path
```

**Initialize shell (required for traditional Miniconda):**
```bash
# Bash
~/miniconda/bin/conda init bash
source ~/.bashrc

# Zsh
~/miniconda/bin/conda init zsh
source ~/.zshrc

# PowerShell
~/miniconda/Scripts/conda init powershell
```

---

### Option 3: Anaconda Distribution (Full Suite)

Anaconda is the full distribution including GUI, Conda Navigator, and pre-installed packages. This is ideal if you want a complete data science environment with visual tools.

#### Step 1: Download via Command Line

**macOS / Linux / WSL2:**

```bash
# Download the latest Anaconda installer
curl -fsSL https://www.anaconda.com/download/success -o anaconda_download.html

# For automated download (using direct URL):
# macOS (Intel)
curl -fsSL https://repo.anaconda.com/archive/Anaconda3-latest-MacOSX-x86_64.sh -o ~/anaconda.sh

# macOS (Apple Silicon)
curl -fsSL https://repo.anaconda.com/archive/Anaconda3-latest-MacOSX-arm64.sh -o ~/anaconda.sh

# Linux
curl -fsSL https://repo.anaconda.com/archive/Anaconda3-latest-Linux-x86_64.sh -o ~/anaconda.sh

# Install
bash ~/anaconda.sh -b -p ~/anaconda
rm ~/anaconda.sh
```

**Windows PowerShell:**

```powershell
$url = "https://repo.anaconda.com/archive/Anaconda3-latest-Windows-x86_64.exe"
$path = "$env:USERPROFILE\anaconda_installer.exe"
(New-Object System.Net.ServicePointManager).SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
Invoke-WebRequest -Uri $url -OutFile $path
& $path /S /D=%USERPROFILE%\anaconda
Remove-Item $path
```

**Alternative: Download via GUI (if preferred)**
1. Visit [Anaconda Downloads](https://www.anaconda.com/download)
2. Select your operating system
3. Download the installer
4. Run the installer and follow the prompts
5. Continue to Step 2 below

#### Step 2: Initialize Conda

```bash
# Bash
~/anaconda/bin/conda init bash
source ~/.bashrc

# Zsh
~/anaconda/bin/conda init zsh
source ~/.zshrc

# PowerShell
~/anaconda/Scripts/conda init powershell
```

#### Step 3: Register with Anaconda (Optional but Recommended)

Create a free account at [anaconda.com](https://www.anaconda.com/account) to:
- Access Anaconda Cloud for sharing packages
- Use Anaconda Nucleus for AI tools
- Get community support
- Track your environments

**From command line (after account creation):**
```bash
# Login to your Anaconda account
anaconda login

# You'll be prompted to enter your credentials
# Username: [your-username]
# Password: [your-password]

# Verify login
anaconda whoami

# Logout when done
anaconda logout
```

**What's included in full Anaconda:**
- ✅ 250+ pre-installed packages
- ✅ Conda Navigator (GUI)
- ✅ Jupyter Notebook & JupyterLab
- ✅ Spyder IDE
- ✅ Data science libraries (NumPy, Pandas, Matplotlib, Scikit-learn, etc.)
- ✅ R integration
- ✅ Anaconda Cloud access
- ✅ Full documentation

**Initialize shell after Anaconda installation:**
```bash
# Bash
~/anaconda/bin/conda init bash
source ~/.bashrc

# Zsh
~/anaconda/bin/conda init zsh
source ~/.zshrc

# PowerShell
~/anaconda/Scripts/conda init powershell
```

---

## 📋 Comparison: All Options

| Feature | conda-express | Miniconda | Anaconda Full |
|---------|---------------|----------|--------------|
| **Binary Size** | 7-11 MB | 50-100 MB | 700-900 MB |
| **Initial Setup** | ~3-5 sec | ~30-60 sec | ~2-5 min |
| **Shell Init Required** | ❌ No | ✅ Yes | ✅ Yes |
| **Modern Solver** | ✅ Rattler | ⚠️ Libmamba | ⚠️ Libmamba |
| **PyPI Support** | ✅ Included | ❌ Separate | ❌ Separate |
| **Pre-installed Packages** | Minimal | Minimal | 250+ packages |
| **Conda Navigator GUI** | ❌ No | ❌ No | ✅ Yes |
| **JupyterLab** | ❌ No | ❌ No | ✅ Yes |
| **Anaconda Cloud Access** | ❌ No | ❌ No | ✅ Yes |
| **Shell Activation** | conda-spawn | conda activate | conda activate |
| **File Size on Disk** | ~200 MB | ~2-3 GB | ~8-15 GB |
| **Maturity** | ⭐ Newer | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ Stable |
| **Best For** | Fast setup, CLI | Lightweight apps | Full data science |

---

## 🔍 Verify Installation

### For conda-express:
```bash
cx --version
cx bootstrap  # If not already done
cx list       # Verify installation
```

### For Miniconda or Anaconda:
```bash
conda --version
conda list    # Verify installation
conda config --show # Check configuration
```

### Verify Anaconda Account (if registered):
```bash
anaconda whoami
```

---

## 🚀 Next Steps

After installation, you can create the Foundation environment:

```bash
# Navigate to the foundation directory
cd 00-foundation

# Create the environment
conda env create --file environment.yml

# Activate it
conda activate foundation

# (Optional) Run the setup script
bash setup.sh
```

---

## ❓ Troubleshooting

### "curl: command not found"
**Solution:** Install curl first
```bash
# macOS (Homebrew)
brew install curl

# Ubuntu/Debian
sudo apt-get install curl

# CentOS/RHEL
sudo yum install curl

# Windows: Use PowerShell method (curl alias included)
```

### "Permission denied" on macOS/Linux
**Solution:** Make the installer executable
```bash
chmod +x ~/miniconda.sh
bash ~/miniconda.sh -b -p ~/miniconda
```

### Windows PowerShell execution policy error
**Solution:** Run with bypass
```powershell
powershell -ExecutionPolicy Bypass
# Then paste the conda-express or Miniconda PowerShell command
```

### "conda: command not found" after installation
**Solution:** Add conda to PATH
```bash
# Bash
echo 'export PATH="$HOME/miniconda/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Zsh
echo 'export PATH="$HOME/miniconda/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### WSL2 Integration
For Windows users with WSL2:
```bash
# Install in WSL terminal (not PowerShell)
curl -fsSL https://jezdez.github.io/conda-express/get-cx.sh | sh

# Or use traditional Miniconda
curl -fsSL https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -o ~/miniconda.sh && bash ~/miniconda.sh -b -p ~/miniconda
```

### Anaconda Login Issues
**Solution:** Clear credentials and try again
```bash
# Clear cached credentials
conda config --remove-key channels

# Login again
anaconda login

# If issues persist, check network connectivity
anaconda config get url
```

---

## 📚 Additional Resources

- **conda-express Documentation:** https://jezdez.github.io/conda-express/
- **Miniconda Documentation:** https://docs.conda.io/projects/miniconda/
- **Anaconda Distribution:** https://www.anaconda.com/download
- **Anaconda Cloud:** https://anaconda.cloud/
- **Conda User Guide:** https://docs.conda.io/projects/conda/en/latest/
- **Mamba Solver:** https://conda.incubator.org/

---

## 🎯 Recommended Path

**For this repository (Building Intelligent Apps):**

**Fastest path:**
1. ✅ Use **conda-express** for fastest setup
2. ✅ Run `bash 00-foundation/setup.sh` for configuration
3. ✅ Create environments with `cx create -n myenv python=3.12`
4. ✅ Activate with `cx shell myenv`

**Full data science setup:**
1. ✅ Install **Anaconda Full** for complete environment
2. ✅ (Optional) Register with Anaconda account
3. ✅ Run `bash 00-foundation/setup.sh` for configuration
4. ✅ Use JupyterLab for interactive development

**Light weight CLI approach:**
1. ✅ Use **Miniconda** for traditional conda experience
2. ✅ Run `bash 00-foundation/setup.sh` for configuration
3. ✅ Activate with `conda activate foundation`

**Happy coding! 🚀**
