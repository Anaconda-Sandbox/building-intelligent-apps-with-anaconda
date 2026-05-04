# Foundation: AI Python Development Environment Setup

Welcome to the Foundation demo! This section sets up a complete environment for building intelligent applications with Python, including LLM frameworks, MCP servers, and agent orchestration tools.

## 🎯 What You'll Learn

- Setting up a conda environment with modern Python package management
- Configuring conda-pypi for PyPI wheel support
- Initializing MCP (Model Context Protocol) servers
- Working with LangChain, LlamaIndex, and LangGraph frameworks
- Managing environment variables and configurations

**Estimated completion time: 5-7 minutes**

## 📋 Prerequisites

- Conda with Anaconda Ditro or Miniconda Distro 
    - Wizard download: ([Miniconda download here](https://www.anaconda.com/docs/getting-started/miniconda/install/overview)) | ([Anaonda download here](https://www.anaconda.com/docs/getting-started/miniconda/install/overview))
    - Jump to [Installing Conda from the command line](#installing-miniconda-from-the-command-line)
- ~2GB disk space for dependencies
- Python 3.10+

## 🚀 Quick Start

### Step 1: Create the Environment

```bash
# Navigate to the foundation directory
cd 00-foundation

# Accept Anaconda terms of service
# Learn more about (Anaconda ToS - Explain Like I'm Five)[101-reference-library/terms-of-service-ELI5.md]
conda init
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r

# Update to the latest conda
conda install -n base -c defaults "conda>=26.3.2" anaconda-anon-usage

# Install experimental plugins in base
# Learn more about conda-rattler-solver: https://github.com/conda-incubator/conda-rattler-solver 
# Learn more about conda-pypi: https://github.com/conda-incubator/conda-pypi-test
# Learn more about conda-workspaces: https://github.com/conda-incubator/conda-workspaces
# Learn more about conda-lockfiles: https://github.com/conda-incubator/conda-lockfiles

conda install -n base conda-rattler-solver "conda-pypi>=0.8.0" conda-workspaces conda-lockfiles

# Create the conda environment from the environment.yml file
conda env create --file environment.yml
```

This will:
- Install Python 3.10+
- Install LLM frameworks (LangChain, LlamaIndex, LangGraph)
- Set up MCP ecosystem (mcp, fastmcp)
- Configure conda-pypi for PyPI wheel support
- Install database and async utilities
- Enable the Anaconda CLI tools

If you're starting from an [Anaconda Cloud notebook](https://nb.anaconda.com), you can use [Quick Start Environments](https://www.anaconda.com/products/navigator/quick-start-environments).

### Step 2: Activate the Environment

```bash
conda activate foundation
```

### Step 3: Run the Setup Script

```bash
# Make the setup script executable (if needed)
chmod +x setup.sh

# Run the setup script
bash setup.sh
```

The setup script will:
- ✅ Configure conda to use the rattler solver for wheel installation
- ✅ Add the conda-pypi-test channel for PyPI wheel indexing
- ✅ Create required directories for MCP configurations
- ✅ Set environment variables for proper module discovery
- ✅ Display verification information

## 📦 What's Installed

### Core AI/LLM Frameworks
- **LangChain** - LLM orchestration and agent frameworks
- **LlamaIndex** - Data indexing and retrieval-augmented generation (RAG)
- **LangGraph** - Stateful, multi-step agent workflows

### MCP (Model Context Protocol)
- **mcp** - Official MCP SDK for Python
- **fastmcp** - Fast MCP server framework
- **mcp-servers** - Pre-built MCP server implementations

### Data & Infrastructure
- **pgvector** - PostgreSQL vector database support
- **Pydantic** (v2+) - Data validation and settings management
- **aiohttp** - Async HTTP client/server
- **python-dotenv** - Environment variable management

### Package Management
- **conda-pypi** (≥0.8.0) - PyPI wheel support in conda
- **conda-rattler-solver** - Modern dependency resolver
- **conda-lock** - Lock file generation for reproducibility
- **Anaconda CLI** - Command-line tools for environment management

## ⚙️ Configuration

### Setting Environment Variables

The setup script creates a configuration directory. You can add a `.env` file:

```bash
# Create a .env file in your project root
cat > .env << 'EOF'
PYTHONPATH=${CONDA_PREFIX}/lib:$PYTHONPATH
MCP_CONFIG=${CONDA_PREFIX}/etc/mcp
LOG_LEVEL=INFO
EOF

# Load it in your Python code with python-dotenv
from dotenv import load_dotenv
load_dotenv()
```

### Configuring the Rattler Solver

The setup script automatically configures the rattler solver. To verify:

```bash
conda config --show solver
```

You should see: `solver: rattler`

### Adding the conda-pypi-test Channel

The setup script adds the test channel. To verify:

```bash
conda config --show channels
```

You should see the conda-pypi-test channel listed.

## 🧪 Verify Installation

Test that everything is installed correctly:

```bash
# Check Python version
python --version

# Check key packages
python -c "import langchain; print(f'LangChain: {langchain.__version__}')"
python -c "import llama_index; print(f'LlamaIndex: {llama_index.__version__}')"
python -c "import langgraph; print('LangGraph: OK')"
python -c "import mcp; print('MCP: OK')"
python -c "import pydantic; print(f'Pydantic: {pydantic.__version__}')"

# Check MCP version
mcp --version

# List all packages
conda list
```

## 📁 Directory Structure

```
00-foundation/
├── README.md           # This file
├── environment.yml     # Conda environment specification
├── setup.sh           # Setup and configuration script
└── notebooks/         # Example notebooks (add your demos here)
```

## 🔧 Manual Configuration (Optional)

If you prefer to configure manually without running the setup script:

```bash
# 1. Configure the solver
conda config --set solver rattler

# 2. Add the conda-pypi-test channel
conda config --append channels https://github.com/conda-incubator/conda-pypi-test/releases/download

# 3. Set environment variables (add to ~/.bashrc or ~/.zshrc)
export PYTHONPATH="${CONDA_PREFIX}/lib:$PYTHONPATH"
export MCP_CONFIG="${CONDA_PREFIX}/etc/mcp"

# 4. Create required directories
mkdir -p "${CONDA_PREFIX}/etc/mcp"
mkdir -p "${CONDA_PREFIX}/var/log"
```

## 🧹 Cleaning Up

To remove the environment:

```bash
# Deactivate first
conda deactivate

# Remove the environment
conda env remove --name foundation

# (Optional) Remove the channels and revert solver
conda config --remove channels https://github.com/conda-incubator/conda-pypi-test/releases/download
conda config --remove-key solver
```

## 📚 Next Steps

After completing this foundation setup, you'll be ready for:
- **01-data-sources** - Working with data ingestion and RAG
- **02-your-first-agent** - Building your first AI agent
- **03-your-first-and-second-apps** - Creating production applications
- **04-deploying-cloud-and-inference** - Deploying to cloud platforms

## ❓ Troubleshooting

### Issue: "solver: rattler" not found
**Solution:** Ensure `conda-rattler-solver` is installed and run `conda config --set solver rattler`

### Issue: ModuleNotFoundError for LangChain or LlamaIndex
**Solution:** Verify the environment is activated: `conda activate foundation`

### Issue: MCP command not found
**Solution:** Reinstall the mcp package: `conda install mcp -y`

### Issue: pgvector not installing
**Solution:** pgvector requires PostgreSQL dev headers. Install with: `conda install libpq -y`

## Installing Miniconda from the Command Line
### Linux & [macOS](https://docs.conda.io/projects/conda/en/stable/user-guide/install/macos.html) (Terminal): 
The process for Linux and macOS is nearly identical. You download a .sh shell script and run it using bash. 

- **Download:** Use curl or wget to fetch the installer for your architecture (e.g., x86_64 for Intel or arm64 for Apple Silicon).
- **Run Installer:** Execute the script using bash. Use the -b flag for a "batch" install to skip interactive prompts.
- **Initialize:** Run conda init to set up your shell. 

```bash
# Example for Linux and Mac
# Replace url for macOS Apple Silicon: https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.sh
# Replace url for macOS Intel: https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh
# Download the installer
curl -sL https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh > Miniconda3.sh
# Run the installer
bash Miniconda3.sh
# Respond to terms of service and auto activate base
# Initialization targets are listed in the final step of install
source /home/codespace/miniconda3/bin/activate
conda init
```

### Windows (PowerShell)
While Windows often uses a graphical .exe, you can perform a "silent" command-line installation using PowerShell. 

- **Download:** Use Invoke-WebRequest to download the .exe installer.
- **Silent Install:** Run the installer with the /S flag. You must specify the destination path with /D=.
- **Initialize:** After installation, you may need to update the PowerShell Execution Policy to allow Conda scripts to run. 

```powershell
# Download and install silently
Invoke-WebRequest -Uri "https://anaconda.com" -OutFile "miniconda.exe"
Start-Process -FilePath .\miniconda.exe -ArgumentList "/S", "/D=$Env:UserProfile\Miniconda3" -Wait

# Initialize PowerShell (Run as Administrator if needed)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
& "$Env:UserProfile\Miniconda3\Scripts\conda.exe" init powershell
```
### After Installation
After installation, restart your terminal or run `source ~/.bashrc` (Linux) or `source ~/.zshrc` (Mac) to finalize the setup. You can verify the installation by running `conda --version`.

## 📖 Resources

- [Conda Documentation](https://docs.conda.io/)
- [conda-pypi GitHub](https://github.com/conda-incubator/conda-pypi)
- [LangChain Documentation](https://python.langchain.com/)
- [LlamaIndex Documentation](https://docs.llamaindex.ai/)
- [MCP Specification](https://modelcontextprotocol.io/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)

## 🤝 Contributing

Have suggestions or improvements? We'd love to hear from you! Check out the main repository's contributing guidelines.

---

**Happy coding! 🚀 Let's build intelligent applications together.**
