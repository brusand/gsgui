# Solution de Démarrage Automatique GSGUI - RÉSOLU ✅

**Date**: 3 avril 2026
**Problème**: Le démarrage automatique via Automator ne fonctionnait pas
**Cause**: npm n'était pas dans le PATH au démarrage
**Solution**: Script shell avec PATH explicite + Application AppleScript

---

## Historique du Problème

### Tentatives précédentes (NON FONCTIONNELLES)
1. ❌ **LaunchAgent** (`com.gsgui.manager.plist`) - Ne fonctionne pas avec disques externes montés avec `nosuid`/`nodev`
2. ❌ **Application Automator v1** - PATH incomplet, npm non trouvé

### Solution Actuelle (FONCTIONNELLE) ✅
- **Script shell**: `automator-launcher.sh` - Définit le PATH explicite
- **Application**: `~/Applications/GSGUI Launcher.app` - Lance le script shell
- **Statut**: Ajoutée aux Éléments de connexion macOS

---

## Architecture de la Solution

### 1. Script Shell Principal: `automator-launcher.sh`
**Localisation**: `/Volumes/SSD/devs/gsgui/automator-launcher.sh`

**Fonction**:
- Définit le PATH complet: `/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin`
- Attend le montage du disque SSD (max 60 secondes)
- Vérifie la présence de npm et python3
- Lance `process-manager-portable.sh start`
- Affiche des notifications macOS
- Log tout dans `/tmp/gsgui-launcher.log`

**Points clés**:
```bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
```
Cette ligne est CRITIQUE car au démarrage macOS, le PATH est minimal.

### 2. Application AppleScript: `GSGUI Launcher.app`
**Localisation**: `~/Applications/GSGUI Launcher.app`

**Fonction**:
- Application macOS lancée au démarrage
- Exécute simplement: `/bin/bash /Volumes/SSD/devs/gsgui/automator-launcher.sh`
- Affiche notifications de succès/erreur

**Code source**: `/tmp/gsgui-launcher.applescript` (pour référence)

### 3. Script Process Manager: `process-manager-portable.sh`
**Localisation**: `/Volumes/SSD/devs/gsgui/process-manager-portable.sh`

**Fonction**: (inchangé)
- Gère le backend Python (port 8001)
- Gère le frontend Vite (port 5173)
- Utilise l'environnement virtuel: `/Volumes/SSD/devs/gsgui/venv`

---

## Configuration Actuelle

### Éléments de Connexion macOS
```
Réglages Système > Général > Éléments de connexion
✅ GSGUI Launcher (masqué)
```

### Chemins Importants
- **npm**: `/opt/homebrew/bin/npm`
- **python3**: `/opt/homebrew/bin/python3` (mais utilise le venv)
- **venv**: `/Volumes/SSD/devs/gsgui/venv/bin/python`

---

## Vérification et Diagnostic

### Vérifier que tout fonctionne
```bash
# 1. Vérifier l'état des services
cd /Volumes/SSD/devs/gsgui
./process-manager-portable.sh status

# 2. Voir le log de l'application
cat /tmp/gsgui-launcher.log

# 3. Vérifier les éléments de connexion
osascript -e 'tell application "System Events" to get the name of every login item'
```

### Si les services ne démarrent PAS automatiquement

#### Étape 1: Vérifier le log
```bash
cat /tmp/gsgui-launcher.log
```

Chercher:
- `npm n'est pas installé ou pas dans le PATH` → Problème de PATH
- `Le disque SSD n'est pas monté` → Disque non monté après 60s
- `Échec du démarrage` → Erreur dans process-manager

#### Étape 2: Tester manuellement l'application
```bash
# Arrêter les services actuels
./process-manager-portable.sh stop

# Nettoyer le log
rm -f /tmp/gsgui-launcher.log

# Lancer l'application
open ~/Applications/"GSGUI Launcher.app"

# Attendre 10 secondes puis vérifier
sleep 10
cat /tmp/gsgui-launcher.log
./process-manager-portable.sh status
```

#### Étape 3: Vérifier le PATH dans le script
```bash
# Vérifier que npm est bien là
which npm
# Doit retourner: /opt/homebrew/bin/npm

# Si npm est ailleurs, éditer automator-launcher.sh
# et ajuster la ligne: export PATH="..."
```

#### Étape 4: Recréer l'application si nécessaire
Si le script shell a été modifié, recréer l'application:
```bash
cd /Volumes/SSD/devs/gsgui

# Retirer l'ancienne des éléments de connexion
osascript -e 'tell application "System Events" to delete login item "GSGUI Launcher"'

# Supprimer l'ancienne application
rm -rf ~/Applications/"GSGUI Launcher.app"

# Recréer avec osacompile
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

osacompile -o ~/Applications/"GSGUI Launcher.app" /tmp/gsgui-launcher-new.applescript

# Rajouter aux éléments de connexion
osascript -e 'tell application "System Events" to make login item at end with properties {path:"'$HOME'/Applications/GSGUI Launcher.app", hidden:true}'
```

---

## Test de Démarrage Automatique

### Test Complet (sans redémarrer le Mac)
```bash
# 1. Arrêter tous les services
./process-manager-portable.sh stop

# 2. Nettoyer les logs
rm -f /tmp/gsgui-launcher.log
rm -f logs/*.log

# 3. Simuler le démarrage
open ~/Applications/"GSGUI Launcher.app"

# 4. Attendre et vérifier
sleep 10
echo "=== Status ==="
./process-manager-portable.sh status
echo ""
echo "=== Log Launcher ==="
cat /tmp/gsgui-launcher.log
```

**Résultat attendu**:
```
✅ Backend actif (PID: XXXX)
✅ Frontend actif (PID: XXXX)
✅ Tous les services sont actifs
```

---

## Gestion des Services

### Démarrage manuel
```bash
./process-manager-portable.sh start
```

### Arrêt
```bash
./process-manager-portable.sh stop
```

### Surveillance continue (redémarre automatiquement en cas d'arrêt)
```bash
./process-manager-portable.sh monitor
```

### Voir les logs en temps réel
```bash
./process-manager-portable.sh logs
```

---

## Désactivation du Démarrage Automatique

Si vous voulez désactiver le démarrage automatique:

```bash
# Retirer des éléments de connexion
osascript -e 'tell application "System Events" to delete login item "GSGUI Launcher"'

# Optionnel: supprimer l'application
rm -rf ~/Applications/"GSGUI Launcher.app"
```

---

## Fichiers Créés

### Fichiers Actifs (NE PAS SUPPRIMER)
- ✅ `/Volumes/SSD/devs/gsgui/automator-launcher.sh` - Script de démarrage avec PATH
- ✅ `~/Applications/GSGUI Launcher.app` - Application de démarrage
- ✅ `/Volumes/SSD/devs/gsgui/process-manager-portable.sh` - Gestionnaire de processus

### Fichiers de Log
- `/tmp/gsgui-launcher.log` - Log de l'application (nettoyé à chaque lancement)
- `/Volumes/SSD/devs/gsgui/logs/backend.log` - Log du backend
- `/Volumes/SSD/devs/gsgui/logs/frontend.log` - Log du frontend
- `/Volumes/SSD/devs/gsgui/logs/manager.log` - Log du process manager

### Fichiers Obsolètes (Peuvent être supprimés)
- ❌ `com.gsgui.manager.plist` - LaunchAgent non fonctionnel
- ❌ `install-launchd.sh` - Script d'installation LaunchAgent
- ❌ `uninstall-launchd.sh` - Script de désinstallation LaunchAgent
- ❌ `launchd-wrapper.sh` - Wrapper LaunchAgent
- ❌ `create-automator-app.sh` - Ancien script de création
- ❌ `recreate-automator-app.sh` - Ancien script de recréation
- ❌ `DEMARRAGE-AUTOMATIQUE.md` - Documentation de l'ancienne méthode
- ❌ `README-DEMARRAGE.md` - Ancien README

```bash
# Pour nettoyer les fichiers obsolètes
cd /Volumes/SSD/devs/gsgui
rm -f com.gsgui.manager.plist install-launchd.sh uninstall-launchd.sh
rm -f launchd-wrapper.sh create-automator-app.sh recreate-automator-app.sh
rm -f test-launchd.sh
# Garder les anciens MD comme référence historique
```

---

## Points Techniques Importants

### Pourquoi cette solution fonctionne

1. **PATH Explicite**: Au démarrage macOS, seul `/usr/bin:/bin:/usr/sbin:/sbin` est dans le PATH. Homebrew (`/opt/homebrew/bin`) n'est pas inclus. Le script définit explicitement le PATH complet.

2. **Attente du Montage**: Les disques externes peuvent prendre quelques secondes à être montés. Le script attend jusqu'à 60 secondes.

3. **Logs Détaillés**: Tout est loggé dans `/tmp/gsgui-launcher.log` pour diagnostic.

4. **Notifications**: L'utilisateur est informé visuellement du succès/échec.

5. **AppleScript Simple**: L'application ne fait qu'exécuter le script bash, toute la logique est dans le shell.

### Pourquoi LaunchAgent ne fonctionne pas

Les disques externes montés automatiquement par macOS ont les options de sécurité:
- `nosuid` - Pas d'exécution SUID
- `nodev` - Pas d'accès aux devices
- `noexec` (parfois) - Pas d'exécution

`launchd` refuse d'exécuter des scripts depuis ces volumes par sécurité.

---

## Résumé pour Redémarrage Rapide

**Tout fonctionne actuellement ✅**

**Pour vérifier rapidement après un reboot**:
```bash
cd /Volumes/SSD/devs/gsgui
./process-manager-portable.sh status
cat /tmp/gsgui-launcher.log
```

**Si rien ne démarre**:
```bash
# Lancer manuellement
open ~/Applications/"GSGUI Launcher.app"
```

**Fichier clé**: `automator-launcher.sh` contient toute la logique avec le PATH correct.
