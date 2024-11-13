#!/bin/bash

# Proverite da li su prosleđena dva argumenta
if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <app> [workdir]"
    exit 1
fi

# Ulazni parametri
app=$1
workdir=${2:-.} 

GITHUB_HOST=github2
#GITHUB_HOST=github.com

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
        echo "Line successfully added to $config_file"
    fi
}


echo "[*] installing direnv..."
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
        echo "[*] brew not found. Installing Homebrew..."
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

# Idi u radni direktorijum i napravi folder za aplikaciju
cd "$workdir" || exit
mkdir -p "$app"
cd "$app" || exit

# Postavi verziju Python-a
PYTHON=python3.12

# Kreiraj virtualno okruženje
$PYTHON -m venv .venv
source .venv/bin/activate

# Dodaj trenutni direktorijum u Python path
current_folder=$(pwd)
echo "$current_folder/src" >> "$current_folder/.venv/lib/$PYTHON/site-packages/pythonpaths.pth"

# Nadogradi pip
echo "[*] upgrading pip..."
pip3 install --upgrade pip -q

# Napravi i pređi u folder lib
mkdir lib
cd lib || exit


echo "[*] cloning base4 repository..."
if ! git clone git+ssh://git@$GITHUB_HOST/base4services/base4.git > /dev/null 2>&1; then
  echo "check permissions or if the repository exists."
  exit 1
fi
cd base4 || exit
echo "[*] installing base4 dependencies..."
pip3 install -e . -q
rm -rf .git
cd ../../ || exit


echo "[*] cloning base4project repository..."
if ! git clone git+ssh://git@$GITHUB_HOST/base4services/base4project.git > /dev/null 2>&1; then
  echo "check permissions or if the repository exists."
  exit 1

fi
mv base4project/* base4project/.[^.]* ./
rm -rf  base4project


# config files
sed -i '' "s/__PROJECT_NAME__/${app}/g" config/services.yaml config/env.yaml

# reinitialize git
rm -rf .git
git init
git add .  > /dev/null 2>&1;
git commit -m "initial commit" > /dev/null 2>&1;

# todo, sredi ovo
cp lib/base4/base4/scripts/testall .venv/bin/testall

# security keys
echo "[*] generating security keys..."
cd security || exit
./mk_keys.sh > /dev/null 2>&1;
cd .. || exit

echo "[*] generating env file..."
bmanager -e > /dev/null 2>&1;

echo "[*] generating schemas..."
bmanager -g models,schemas > /dev/null 2>&1;

echo "[*] allow direnv..."
direnv allow

echo "================================================================================"
echo "  ---  Project created successfully!   ---"
echo "  [*] Git repository initialized in $workdir/$app."
echo "  [*] 'bmanager' tool is for managing the project. Run 'bmanager -h' for help."
echo "================================================================================"
