# Installing Conda: Quick Start Guide

This guide provides cross-platform instructions for installing conda using command-line methods (no GUI required) that work on **Windows PowerShell**, **WSL2**, **macOS**, and **Linux**.

**Estimated time: 5-10 minutes**

## 🚀 Quick Install (Recommended)

### Option 1: conda-express (Modern & Fast)

**conda-express** (`cx`) is a lightweight, single-binary bootstrapper for conda. It's the fastest way to get started:

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

## 📋 Comparison: conda-express vs Traditional Miniconda

| Feature | conda-express | Miniconda |
|---------|---------------|----------|
| **Binary Size** | 7-11 MB | 50-100 MB |
| **Initial Setup** | ~3-5 seconds | ~30-60 seconds |
| **Shell Init Required** | ❌ No | ✅ Yes (conda init) |
| **Modern Solver** | ✅ Rattler (default) | ⚠️ Libmamba (optional) |
| **PyPI Support** | ✅ conda-pypi included | ❌ Separate install |
| **Traditional Activation** | ❌ conda-spawn only | ✅ conda activate |
| **File Size on Disk** | ~200 MB | ~2-3 GB |
| **Maturity** | ⭐ Newer (experimental) | ⭐⭐⭐⭐ Stable |

---

## 🔍 Verify Installation

### For conda-express:
```bash
cx --version
cx bootstrap  # If not already done
cx list       # Verify installation
```

### For Miniconda:
```bash
conda --version
conda list    # Verify installation
conda config --show # Check configuration
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

---

## 📚 Additional Resources

- **conda-express Documentation:** https://jezdez.github.io/conda-express/
- **Miniconda Documentation:** https://docs.conda.io/projects/miniconda/
- **Conda User Guide:** https://docs.conda.io/projects/conda/en/latest/
- **Mamba Solver:** https://conda.incubator.org/

---

## 🎯 Recommended Path

**For this repository (Building Intelligent Apps):**
1. ✅ Use **conda-express** for fastest setup
2. ✅ Run `bash 00-foundation/setup.sh` for configuration
3. ✅ Create environments with `conda create -n myenv python=3.12`
4. ✅ Activate with `cx shell myenv` or `conda activate myenv`

**Happy coding! 🚀**
