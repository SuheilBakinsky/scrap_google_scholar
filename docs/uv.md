# Install uv
See https://docs.astral.sh/uv/getting-started/installation/

## 1. Execute this command in Terminal
### macOS and Linux
```console
curl -LsSf https://astral.sh/uv/install.sh | sh
```
### Windows
```console
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## 2. Start a new Terminal

## 3. Check if `uv` is installed properly
```console
uv --version
```

## 4. Go to project folder and run the application
```console
uv run main.py
```

# Installing and Syncing with other dependencies
## 1. Install
```console
uv add <dependency-name>==<version> 
```
(e.g. `uv add holidays==0.64`)

## 2. Sync
```console
uv sync
```

# Removing and Syncing with other dependencies
## 1. Remove
```console
uv remove <dependency-name>
```
(e.g. `uv remove holidays`)

## 2. Sync
```console
uv sync
```

# Upgrading and Syncing with other dependencies
## 1. Upgrade
```console
uv lock --upgrade-package <dependency-name>==<version>
```
(e.g. `uv lock --upgrade-package holidays==0.64`)

## 2. Sync
```console
uv sync
```

# List all dependencies
```console
uv tree
```

# List all outdated dependencies with a depth of 1
```console
uv tree --outdated --depth=1
```

# List installed python versions on system
```console
uv python list
```

# Set python version and create new .venv on the fly
## 1. Set python version
```console
uv python pin 3.12
```

## 2. Sync
```console
uv sync
```