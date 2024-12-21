#!/bin/bash

if [ "$#" -lt 1 ]; then
    echo "Usage: newproject <app> [branch|workdir] [workdir]"
    exit 1
fi

app=$1
branch=${2:-main}
workdir=${3:-.}

PYTHON=3.13.1

if [ -d "$app" ]; then
  echo "[*] '$app' already exists. Please choose a different name."
  exit 0
fi

if [ "$#" -eq 2 ]; then
    second_param=$2
    if [[ "$second_param" == dev* || "$second_param" == main* ]]; then
        branch=$second_param
        workdir="."
    else
        branch="main"
        workdir=$second_param
    fi
else
    branch=${2:-main}
    workdir=${3:-.}
fi

echo "================================================================================"
echo "[*] Application name: $app"
echo "[*] Working directory: $workdir"
echo "[*] Base4 branch: $branch"
echo "[*] Python version: $PYTHON"
echo "================================================================================"

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


if [ "$workdir" != "." ]; then
    mkdir -p "$workdir"
fi

cd "$workdir" || exit
mkdir -p "$app"
cd "$app" || exit


# Function to install pyenv
install_pyenv() {
    curl https://pyenv.run | bash

    # Add pyenv to shell startup files
    echo -e '\n# pyenv initialization' >> ~/.zshrc
    echo 'export PATH="$HOME/.pyenv/bin:$PATH"' >> ~/.zshrc
    echo 'eval "$(pyenv init --path)"' >> ~/.zshrc
    echo 'eval "$(pyenv init -)"' >> ~/.zshrc
    echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.zshrc
    source ~/.zshrc
}

# Function to install pyenv-virtualenv
install_pyenv_virtualenv() {
    git clone https://github.com/pyenv/pyenv-virtualenv.git "$(pyenv root)"/plugins/pyenv-virtualenv
    echo -e '\n# pyenv-virtualenv initialization' >> ~/.zshrc
    echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.zshrc
    source ~/.zshrc
}

# Check if pyenv is installed
if ! command -v pyenv &> /dev/null; then
    echo "[*] pyenv is not installed. Installing..."
    install_pyenv
else
    echo ''
fi

# Check if pyenv-virtualenv is installed
if [ ! -d "$(pyenv root)/plugins/pyenv-virtualenv" ]; then
    echo "[*] pyenv-virtualenv is not installed. Installing..."
    install_pyenv_virtualenv
else
    echo ''
fi

if pyenv versions --bare | grep -q "^$PYTHON_VERSION$"; then
    echo ''
else
    pyenv install $PYTHON
fi
pyenv install $PYTHON
pyenv virtualenv $PYTHON dc.$app.$PYTHON
pyenv local dc.$app.$PYTHON
echo "[*] Installing virtual environment..."

#exec "$SHELL"

# Dodaj trenutni direktorijum u Python path
#current_folder=$(pwd)
#echo "$current_folder/src" >> "$current_folder/.venv/lib/$PYTHON/site-packages/pythonpaths.pth"

# Nadogradi pip
echo "[*] Upgrading pip..."
pip3 install --upgrade pip -q


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
  pip3 install -e . #-q
  cd ../../ || exit

elif [ "$install_type" == "venv" ]; then
  pip install git+https://github.com/base4services/base4.git@${branch} > /dev/null 2>&1;
fi

echo "[*] Cloning base4project repository..."
if ! git clone https://github.com/base4services/base4project.git > /dev/null 2>&1; then
  echo "check permissions or if the repository exists."
  exit 1
fi

cd base4project || exit
cd .. || exit
mv base4project/* base4project/.[^.]* ./
rm -rf  base4project
mv idea .idea
mv .idea/rename.iml .idea/$app.iml

# config files
sed -i '' "s/__PROJECT_NAME__/${app}/g" config/services.yaml config/env.yaml .idea/misc.xml .idea/modules.xml .idea/workspace.xml > /dev/null 2>&1;

# reinitialize git
rm -rf .git
git init > /dev/null 2>&1;
git add .  > /dev/null 2>&1;
git commit -m "initial commit" > /dev/null 2>&1;

# security keys
echo "[*] Generating security keys..."
cd security || exit
./mk_keys.sh > /dev/null 2>&1;
cd .. || exit

echo "[*] Generating env file..."
bmanager compile-env > /dev/null 2>&1;

echo "[*] Linking docker-compose.yaml..."
ln -sf infrastructure/docker-compose.yaml docker-compose.yaml

echo "[*] Allow direnv..."
direnv allow

echo "================================================================================"
echo "  ---  Project created successfully!   ---"
echo "  [*] Git repository initialized in $workdir/$app."
echo "  [*] 'bmanager' tool is for managing the project. Run 'bmanager -h' for help."
echo "================================================================================"
