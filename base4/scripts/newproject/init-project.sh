#!/usr/bin/env bash

# Default values
branch="main"
workdir="."

rm -rf lib .venv

# Function to display help
usage() {
    echo "Usage: newproject --app <app_name> [--branch <branch_name>] [--workdir <workdir>]"
    echo "       --branch    Branch name (default: main)."
    echo "       --workdir   Working directo:qry (default: .)."
    exit 1
}

# If no arguments are provided, print usage and exit
[[ $# -eq 0 ]] && usage

# Argument parsing
while [[ $# -gt 0 ]]; do
    case "$1" in
        --branch)
            branch="$2"
            shift 2
            ;;
        --workdir)
            workdir="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            echo
            usage
            ;;
    esac
done

cd "$workdir" || exit

# Prompt for installation type with a default option
echo "Choose installation type (default is 'lib'):"
echo "1. lib"
echo "2. venv"

# Read user input with a default value
read -p "[*] Enter 1 or 2 (press enter to use 'lib'): " choice </dev/tty

# Determine the installation type
case "$choice" in
    1|"") # Empty input defaults to 'lib'
        install_type="lib"
        ;;
    2)
        install_type="venv"
        ;;
    *)
        echo "[*] Invalid choice. Defaulting to 'lib'."
        install_type="lib"
        ;;
esac
echo "[*] Installation type selected: $install_type"

# Function to check for the presence of the line in the configuration file
check_and_add_line() {
    local config_file=$1
    local line='eval "$(direnv hook bash)"'

    # Check if the line already exists in the configuration file
    if grep -Fxq "$line" "$config_file"; then
        :
    else
        echo "$line not found in $config_file. Adding it..."
        echo "$line" >> "$config_file"
    fi
}

echo "[*] Installing direnv..."
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
      # Add the line to the appropriate configuration file (.bashrc or .zshrc)
    if [[ -f "$HOME/.bashrc" ]]; then
        check_and_add_line "$HOME/.bashrc"
    fi

    # Check if the system has apt (assumes Debian/Ubuntu)
    if command -v apt &> /dev/null; then
        sudo apt update > /dev/null 2>&1
    else
        echo "apt package manager not found. Please install direnv manually."
        exit 1
    fi

    if dpkg -l | grep -q direnv; then
        :
    else
        sudo apt install -y direnv > /dev/null 2>&1
    fi

elif [[ "$OSTYPE" == "darwin"* ]]; then
    if ! command -v brew &>/dev/null; then
        echo "[*] Brew not found. Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi

    if [[ -f "$HOME/.zshrc" ]]; then
      check_and_add_line "$HOME/.zshrc"
    fi

    if brew list | grep -q direnv; then
:
    else
        brew install direnv > /dev/null 2>&1
    fi

else
    echo "unsupported OS type: $OSTYPE. Please install direnv manually."
    exit 1
fi

PYTHON=python3
$PYTHON -m venv .venv
source .venv/bin/activate

current_folder=$(pwd)
site_packages="$current_folder/.venv/lib/$(python3 -c "import sys; print('python' + sys.version[:4])")/site-packages"
echo "$current_folder/src" >> "$site_packages/pythonpaths.pth"


# Nadogradi pip
echo "[*] Upgrading pip..."
pip3 install --upgrade pip -q
echo "[*] Installing project requirements.txt..."
pip3 install -r requirements.txt -q


if [ "$install_type" == "lib" ]; then
  mkdir lib
  cd lib || exit

  echo "[*] Cloning base4 repository..."
  if ! git clone https://github.com/base4services/base4.git > /dev/null 2>&1; then
    echo "Check permissions or if the repository exists."
    exit 1
  fi
  cd base4 || exit
  git checkout "${branch}" > /dev/null 2>&1;
  echo "[*] Installing base4 dependencies..."
  pip3 install -e . -q
  cd ../../ || exit

elif [ "$install_type" == "venv" ]; then
  pip install git+https://github.com/base4services/base4.git > /dev/null 2>&1;
fi

# security keys
echo "[*] Generating security keys..."
cd security || exit
bash mk_keys.sh > /dev/null 2>&1;
cd .. || exit

echo "[*] Generating environment files..."
bmanager compile-env > /dev/null 2>&1;
bmanager compile-yaml > /dev/null 2>&1;
bmanager compile-ac > /dev/null 2>&1;

echo "[*] Allow direnv..."
direnv allow

testall

