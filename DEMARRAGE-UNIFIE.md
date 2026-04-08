# Démarrage Automatique Unifié - GSGUI + Collector + Prévention Veille

**Date**: 4 avril 2026
**Projet**: GSGUI (GuruShots GUI & Collector)
**Architecture**: 3 services + prévention veille

---

## Vue d'Ensemble

Cette solution unifie le démarrage automatique de **tous les services** GuruShots au boot du Mac Mini:

| Service | Description | Port/Fonction |
|---------|-------------|---------------|
| **Backend API** | API FastAPI pour gsgui | Port 8001 |
| **Frontend Web** | Interface Vite/React | Port 5173 |
| **Collector** | Collecte de données GuruShots | Background daemon |
| **Caffeinate** | Prévention de mise en veille | Système |

**Une seule application** au démarrage lance tout! 🚀

---

## Architecture

### Structure du Projet

```
/Volumes/SSD/devs/gsgui/
├── backend/
│   ├── gs_backend.py          # Backend API (port 8001)
│   ├── gs_collector.py         # Collector GuruShots
│   └── app/                    # Modules backend
├── web-ui/                     # Frontend React/Vite
├── process-manager-portable.sh # Gestionnaire de 3 services
├── automator-launcher.sh       # Script de démarrage unifié
├── logs/
│   ├── backend.log
│   ├── frontend.log
│   ├── collector.log
│   └── manager.log
└── pids/
    ├── backend.pid
    ├── frontend.pid
    ├── collector.pid
    └── manager.pid
```

### Flux de Démarrage

```
1. Boot macOS
   ↓
2. ~/Applications/GSGUI Launcher.app démarre
   ↓
3. automator-launcher.sh lance:
   ├── caffeinate (prévention veille)
   ├── Attend montage du SSD (max 60s)
   ├── Vérifie Python et npm
   └── Lance process-manager-portable.sh start
   ↓
4. process-manager-portable.sh démarre:
   ├── Backend (gs_backend.py)
   ├── Frontend (npm run dev)
   └── Collector (gs_collector.py --daemon)
   ↓
5. ✅ Tout est opérationnel 24/7
```

---

## Installation

### Prérequis

- macOS (testé sur Mac Mini)
- Python 3.x + pip
- Node.js + npm
- Disque SSD monté sur `/Volumes/SSD`

### Étape 1: Vérifier la Migration du Collector

Le collector est maintenant dans `/Volumes/SSD/devs/gsgui/backend/gs_collector.py`

```bash
cd /Volumes/SSD/devs/gsgui
ls -la backend/gs_collector.py
```

Si le fichier n'existe pas:
```bash
# Le copier depuis l'ancien projet
cp /Volumes/SSD/devs/gurushots-collector/collector.py backend/gs_collector.py
```

### Étape 2: Configuration du Collector

Créer ou éditer `collector.env` (optionnel):

```bash
cd /Volumes/SSD/devs/gsgui
cp collector.env.example collector.env  # Si existe
# ou
nano collector.env
```

Configuration minimale:
```env
DATABASE_PATH=/Volumes/SSD/Data/gurushots_data.db
COLLECTION_INTERVAL_MINUTES=30
CHALLENGE_IDS=id1,id2,id3
LOG_LEVEL=INFO
```

### Étape 3: Vérifier l'Application de Démarrage

L'application existe déjà depuis votre configuration précédente de gsgui.

Vérifier:
```bash
ls -la ~/Applications/GSGUI\ Launcher.app
```

Si elle n'existe pas, la recréer:
```bash
cd /Volumes/SSD/devs/gsgui

# Créer le script AppleScript
cat > /tmp/gsgui-launcher-new.applescript <<'EOF'
on run
    display notification "Démarrage en cours..." with title "GSGUI Launcher"
    try
        set launchCommand to "/bin/bash /Volumes/SSD/devs/gsgui/automator-launcher.sh"
        do shell script launchCommand
    on error errMsg
        display notification "Erreur: " & errMsg with title "GSGUI Launcher" sound name "Basso"
    end try
end run
EOF

# Compiler en application
osacompile -o ~/Applications/"GSGUI Launcher.app" /tmp/gsgui-launcher-new.applescript

# Ajouter aux éléments de connexion
osascript -e 'tell application "System Events" to make login item at end with properties {path:"'$HOME'/Applications/GSGUI Launcher.app", hidden:true}'
```

### Étape 4: Vérification

```bash
# Vérifier que l'app est dans les éléments de connexion
osascript -e 'tell application "System Events" to get the name of every login item'
# Doit afficher: GSGUI Launcher

# Vérifier les scripts
ls -la /Volumes/SSD/devs/gsgui/automator-launcher.sh
ls -la /Volumes/SSD/devs/gsgui/process-manager-portable.sh
```

---

## Test sans Redémarrer

### Test Complet

```bash
cd /Volumes/SSD/devs/gsgui

# 1. Arrêter tout
./process-manager-portable.sh stop
killall caffeinate 2>/dev/null || true

# 2. Nettoyer les logs
rm -f /tmp/gsgui-launcher.log
rm -f logs/*.log

# 3. Lancer l'application comme au boot
open ~/Applications/"GSGUI Launcher.app"

# 4. Attendre 15-20 secondes
sleep 20

# 5. Vérifier le log de démarrage
cat /tmp/gsgui-launcher.log
```

**Résultat attendu dans le log**:
```
[2026-04-04 15:30:00] Démarrage de GSGUI Launcher
[2026-04-04 15:30:00] Attente du montage du disque SSD...
[2026-04-04 15:30:00] Disque SSD monté avec succès
[2026-04-04 15:30:01] npm trouvé: /opt/homebrew/bin/npm
[2026-04-04 15:30:01] python3 trouvé: /opt/homebrew/bin/python3
[2026-04-04 15:30:01] Lancement de caffeinate (prévention de veille)...
[2026-04-04 15:30:01] caffeinate lancé (PID: 12345)
[2026-04-04 15:30:01] Lancement du process-manager (backend + frontend + collector)...
[2026-04-04 15:30:15] GSGUI démarré avec succès (3 services + caffeinate)
```

### Vérifier les Services

```bash
# Vérifier le statut des 3 services
./process-manager-portable.sh status

# Résultat attendu:
# ✅ Backend actif (PID: XXXX)
# ✅ Frontend actif (PID: YYYY)
# ✅ Collector actif (PID: ZZZZ)
# ✅ Tous les services sont actifs
```

### Vérifier Caffeinate

```bash
# Processus caffeinate
ps aux | grep caffeinate | grep -v grep

# Assertions de veille
pmset -g assertions | grep caffeinate

# Fichier PID
cat /tmp/gsgui-caffeinate.pid
```

### Vérifier les Ports

```bash
# Backend (8001)
lsof -i:8001

# Frontend (5173)
lsof -i:5173

# Tester les URLs
curl http://localhost:8001/health    # Backend
curl http://localhost:5173           # Frontend
```

---

## Gestion des Services

### Commandes Principales

```bash
cd /Volumes/SSD/devs/gsgui

# Démarrer tous les services
./process-manager-portable.sh start

# Arrêter tous les services
./process-manager-portable.sh stop

# Redémarrer tous les services
./process-manager-portable.sh restart

# Vérifier le statut
./process-manager-portable.sh status

# Surveillance automatique avec redémarrage
./process-manager-portable.sh monitor
```

### Logs

```bash
# Logs individuels
tail -f logs/backend.log
tail -f logs/frontend.log
tail -f logs/collector.log

# Log du process manager
tail -f logs/manager.log

# Log de l'application de démarrage
tail -f /tmp/gsgui-launcher.log
```

### Arrêter Caffeinate

```bash
# Arrêter caffeinate (réactive la mise en veille)
kill $(cat /tmp/gsgui-caffeinate.pid)

# Ou
killall caffeinate
```

---

## Monitoring et Diagnostic

### Script de Statut Global

Créer un script pour tout vérifier:

```bash
cat > /Volumes/SSD/devs/gsgui/status-all.sh <<'EOF'
#!/bin/bash
echo "=== Statut Global GSGUI ==="
echo ""

# Services GSGUI
echo "📊 Services:"
cd /Volumes/SSD/devs/gsgui
./process-manager-portable.sh status
echo ""

# Caffeinate
echo "☕ Prévention de veille:"
if pgrep caffeinate > /dev/null; then
    echo "  ✅ caffeinate actif (PID: $(pgrep caffeinate))"
    pmset -g assertions | grep caffeinate | head -1
else
    echo "  ❌ caffeinate inactif"
fi
echo ""

# Ports
echo "🔌 Ports:"
if lsof -i:8001 > /dev/null 2>&1; then
    echo "  ✅ Backend port 8001"
else
    echo "  ❌ Backend port 8001 libre"
fi
if lsof -i:5173 > /dev/null 2>&1; then
    echo "  ✅ Frontend port 5173"
else
    echo "  ❌ Frontend port 5173 libre"
fi
echo ""

# Logs récents
echo "📝 Dernières lignes des logs:"
echo "--- Launcher ---"
tail -3 /tmp/gsgui-launcher.log 2>/dev/null || echo "  Pas de logs"
echo "--- Backend ---"
tail -3 /Volumes/SSD/devs/gsgui/logs/backend.log 2>/dev/null || echo "  Pas de logs"
echo "--- Collector ---"
tail -3 /Volumes/SSD/devs/gsgui/logs/collector.log 2>/dev/null || echo "  Pas de logs"
EOF

chmod +x /Volumes/SSD/devs/gsgui/status-all.sh
```

Utilisation:
```bash
cd /Volumes/SSD/devs/gsgui
./status-all.sh
```

### Diagnostic des Erreurs

#### Erreur: Un service ne démarre pas

```bash
# Voir les logs spécifiques
cat logs/backend.log      # Pour le backend
cat logs/frontend.log     # Pour le frontend
cat logs/collector.log    # Pour le collector

# Vérifier l'environnement Python
source venv/bin/activate
python3 --version
pip list
```

#### Erreur: Caffeinate ne démarre pas

```bash
# Vérifier le log
cat /tmp/gsgui-launcher.log | grep caffeinate

# Tester manuellement
caffeinate -dis &
echo $!
```

#### Erreur: Le disque SSD n'est pas monté

Le script attend 60 secondes le montage du SSD. Si ce n'est pas suffisant:

```bash
# Éditer automator-launcher.sh
nano /Volumes/SSD/devs/gsgui/automator-launcher.sh

# Modifier la ligne:
MAX_WAIT=60
# en:
MAX_WAIT=120  # 2 minutes
```

---

## Désinstallation / Désactivation

### Désactiver le Démarrage Automatique

```bash
# Retirer des éléments de connexion
osascript -e 'tell application "System Events" to delete login item "GSGUI Launcher"'

# Les services ne démarreront plus automatiquement au boot
# Mais peuvent toujours être lancés manuellement
```

### Désinstaller Complètement

```bash
# 1. Retirer des éléments de connexion
osascript -e 'tell application "System Events" to delete login item "GSGUI Launcher"'

# 2. Arrêter tous les services
cd /Volumes/SSD/devs/gsgui
./process-manager-portable.sh stop

# 3. Arrêter caffeinate
killall caffeinate

# 4. Supprimer l'application
rm -rf ~/Applications/"GSGUI Launcher.app"

# 5. Nettoyer les fichiers temporaires
rm -f /tmp/gsgui-launcher.log
rm -f /tmp/gsgui-caffeinate.pid
```

---

## Test Après Redémarrage

1. **Redémarrer le Mac Mini**

2. **Attendre 2-3 minutes** (montage SSD + démarrage services)

3. **Vérifier tout**:

```bash
cd /Volumes/SSD/devs/gsgui

# Status complet
./status-all.sh

# Ou manuellement
./process-manager-portable.sh status
ps aux | grep caffeinate | grep -v grep
lsof -i:8001
lsof -i:5173
cat /tmp/gsgui-launcher.log
```

4. **Tester les applications**:
   - Backend API: http://localhost:8001
   - Frontend Web: http://localhost:5173
   - Vérifier les logs du collector

---

## Résumé

### ✅ Ce qui a été fait

1. **Migration du Collector** dans le projet gsgui (`backend/gs_collector.py`)
2. **Extension du process-manager** pour gérer 3 services au lieu de 2
3. **Ajout de caffeinate** dans automator-launcher.sh
4. **Une seule application** au boot qui lance tout

### 🚀 Résultat Final

**Au démarrage du Mac Mini**:
- ✅ Disque SSD se monte automatiquement
- ✅ Application "GSGUI Launcher" démarre
- ✅ **caffeinate** empêche la mise en veille
- ✅ **Backend** API démarre (port 8001)
- ✅ **Frontend** Web démarre (port 5173)
- ✅ **Collector** démarre en background
- ✅ Le Mac reste actif 24/7 sans interruption

### 📁 Fichiers Clés

| Fichier | Rôle |
|---------|------|
| `~/Applications/GSGUI Launcher.app` | Application de démarrage |
| `/Volumes/SSD/devs/gsgui/automator-launcher.sh` | Script de lancement unifié |
| `/Volumes/SSD/devs/gsgui/process-manager-portable.sh` | Gestionnaire de 3 services |
| `/Volumes/SSD/devs/gsgui/backend/gs_collector.py` | Collector GuruShots |
| `/tmp/gsgui-launcher.log` | Log de démarrage |
| `/tmp/gsgui-caffeinate.pid` | PID de caffeinate |

### 🎯 Commandes Utiles

```bash
# Statut complet
cd /Volumes/SSD/devs/gsgui && ./status-all.sh

# Redémarrer tout
cd /Volumes/SSD/devs/gsgui && ./process-manager-portable.sh restart

# Voir les logs en temps réel
tail -f /tmp/gsgui-launcher.log logs/backend.log logs/collector.log

# Vérifier la veille
pmset -g assertions | grep caffeinate
```

---

## Support

### Problèmes Connus

1. **Le collector ne trouve pas sa config**: S'assurer que `collector.env` existe ou que les variables sont dans `.env`
2. **caffeinate s'arrête**: Normal si on arrête/redémarre manuellement, il redémarre au boot
3. **Un service ne démarre pas**: Vérifier les logs individuels dans `logs/`

### Logs à Consulter en Cas de Problème

```bash
# Par ordre d'importance
cat /tmp/gsgui-launcher.log           # Démarrage global
cat logs/manager.log                  # Process manager
cat logs/collector.log                # Collector spécifique
cat logs/backend.log                  # Backend API
cat logs/frontend.log                 # Frontend web
```

---

**Tout est maintenant unifié et géré par une seule application au démarrage! 🎉**
