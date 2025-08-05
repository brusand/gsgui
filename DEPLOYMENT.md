# 🚀 GSGUI - Guide de Déploiement Portable

Ce guide explique comment installer et déployer GSGUI sur différents systèmes d'exploitation.

## 📋 Prérequis

### Tous les systèmes
- **Git** : Pour cloner le dépôt
- **Python 3.8+** : Backend FastAPI
- **Node.js 16+** et **npm** : Frontend React
- **Connexion Internet** : Pour les API GuruShots

### Vérification rapide
```bash
git --version
python3 --version  # ou python --version sur Windows
node --version
npm --version
```

## 📦 Installation

### 1. Cloner le projet
```bash
git clone https://github.com/brusand/gsgui.git
cd gsgui
git checkout web-ui
```

### 2. Installation automatique des dépendances
```bash
# Utiliser le script d'installation portable
chmod +x install-dependencies.sh
./install-dependencies.sh
```

Ou manuellement :
```bash
# Backend
cd backend
pip install -r requirements.txt
cd ..

# Frontend  
cd web-ui
npm install
cd ..
```

## 🎯 Configuration

### 1. Fichier de configuration principal
Créer/modifier `data/gsgui.ini` :
```ini
player = votre_nom

[players]
[[votre_nom]]
xtoken = votre_token_gurushots_64_caracteres
turbo_algorithm = "[hybrid,position_aware,adaptive_time]"
auto_optimize_turbo = False
[[[scheduled_strategies]]]
```

### 2. Obtenir votre token GuruShots
1. Connectez-vous sur [GuruShots](https://gurushots.com)
2. Ouvrez les outils développeur (F12)
3. Onglet Network → Rechargez la page
4. Cherchez une requête vers l'API GuruShots
5. Copiez la valeur du header `x-token` (64 caractères)

## 🖥️ Lancement

### Script Portable (Recommandé)
```bash
# Démarrage simple
./process-manager-portable.sh start

# Démarrage avec surveillance automatique
./process-manager-portable.sh monitor

# Vérifier l'état
./process-manager-portable.sh status

# Arrêter
./process-manager-portable.sh stop
```

### Lancement Manuel
```bash
# Terminal 1 - Backend
cd backend
python3 gs_backend.py

# Terminal 2 - Frontend
cd web-ui
npm run dev
```

## 🌐 Accès

- **Local** : http://localhost:3000
- **Réseau local** : http://[IP-de-la-machine]:3000
- **Mobile/Externe** : Configurez votre routeur pour rediriger le port 80 vers 3000

## 🔧 Spécificités par OS

### 🐧 Linux (Ubuntu/Debian)
```bash
# Dépendances système
sudo apt update
sudo apt install python3 python3-pip nodejs npm git

# Si problème avec python3
sudo apt install python3-venv python3-dev
```

### 🍎 macOS
```bash
# Avec Homebrew
brew install python3 node npm git

# Ou utiliser Python système + Node.js depuis nodejs.org
```

### 🪟 Windows

#### Option 1: Git Bash (Recommandé)
1. Installer [Git for Windows](https://git-scm.com/download/win) (inclut Git Bash)
2. Installer [Python](https://python.org/downloads/) (cocher "Add to PATH")
3. Installer [Node.js](https://nodejs.org/) (inclut npm)
4. Utiliser Git Bash pour les commandes

#### Option 2: PowerShell/CMD
```cmd
# Vérifier les installations
python --version
npm --version

# Adapter les commandes :
# ./script.sh → .\script.sh ou bash script.sh
# python3 → python
```

#### Option 3: WSL (Windows Subsystem for Linux)
```bash
# Installer WSL2 avec Ubuntu
wsl --install -d Ubuntu

# Puis suivre les instructions Linux
```

## 🔍 Dépannage

### Problèmes courants

#### 1. "Command not found: python3"
```bash
# Linux/macOS: installer python3
# Windows: utiliser 'python' au lieu de 'python3'
```

#### 2. "Permission denied" sur les scripts
```bash
chmod +x *.sh
```

#### 3. Port 3000 déjà utilisé
```bash
# Le script trouve automatiquement un port libre
# Ou modifier vite.config.ts pour changer le port
```

#### 4. Problèmes npm
```bash
# Nettoyer le cache
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

#### 5. Backend ne démarre pas
```bash
# Vérifier les logs
cat logs/backend.log

# Vérifier la configuration
cat data/gsgui.ini
```

### Logs et Debug
```bash
# Voir tous les logs en temps réel
./process-manager-portable.sh logs

# Logs individuels
tail -f logs/backend.log
tail -f logs/frontend.log
tail -f logs/manager.log
```

## 📁 Structure du Projet
```
gsgui/
├── backend/              # Backend FastAPI
│   ├── gs_backend.py    # Point d'entrée principal
│   └── app/             # Code applicatif
├── web-ui/              # Frontend React
│   ├── src/             # Code source
│   └── package.json     # Dépendances npm
├── data/                # Fichiers de configuration
│   ├── gsgui.ini       # Configuration principale
│   └── strategies.ini   # Stratégies disponibles
├── logs/                # Logs d'exécution
├── pids/                # Fichiers PID des processus
├── install-dependencies.sh      # Installation auto
├── process-manager-portable.sh  # Gestionnaire portable
└── DEPLOYMENT.md        # Ce fichier
```

## 🔒 Sécurité

- **Tokens** : Ne jamais commiter les tokens dans Git
- **Accès réseau** : Le backend reste en local (127.0.0.1:8001)
- **Proxy** : Seul le frontend (port 3000) est exposé
- **Logs** : Les tokens sont partiellement masqués dans les logs

## 🆘 Support

En cas de problème :
1. Vérifiez les logs : `./process-manager-portable.sh logs`
2. Testez la connectivité GuruShots depuis le navigateur
3. Vérifiez que tous les prérequis sont installés
4. Consultez les issues GitHub du projet

---

**GSGUI Web Interface v2.0** - Interface web pour automatisation GuruShots