# Démarrage Automatique de GSGUI

## Problème rencontré avec LaunchAgent

La méthode LaunchAgent (via `launchd`) **ne fonctionne PAS** avec ce projet car il se trouve sur un disque externe monté avec les options `nosuid` et `nodev`. Ces restrictions de sécurité de macOS empêchent launchd d'exécuter des scripts depuis des volumes externes.

## Solution recommandée: Application Automator + Éléments de connexion

### Création de l'application (à faire une seule fois)

1. **Ouvrir Automator** (dans /Applications)

2. **Choisir "Application"** comme type de document

3. **Chercher "Exécuter un script shell"** dans la barre de recherche

4. **Glisser "Exécuter un script shell"** dans la zone de droite

5. **Coller ce script** dans la zone de texte:

```bash
# Attendre que le disque SSD soit monté
MAX_WAIT=60
waited=0

while [[ ! -d "/Volumes/SSD/devs/gsgui" ]] && [[ $waited -lt $MAX_WAIT ]]; do
    sleep 5
    waited=$((waited + 5))
done

if [[ ! -d "/Volumes/SSD/devs/gsgui" ]]; then
    osascript -e 'display notification "Le disque SSD n'\''est pas monté" with title "GSGUI Launcher" sound name "Basso"'
    exit 1
fi

# Lancer le process-manager en mode monitor
cd "/Volumes/SSD/devs/gsgui"
/bin/bash ./process-manager-portable.sh monitor > /dev/null 2>&1 &

# Attendre 5 secondes et vérifier que les services démarrent
sleep 5

# Notification de succès
osascript -e 'display notification "GSGUI a démarré avec succès" with title "GSGUI Launcher" sound name "Glass"'
```

6. **Enregistrer l'application**:
   - Fichier > Enregistrer
   - Nom: `GSGUI Launcher`
   - Emplacement: `~/Applications`
   - Format: Application

### Ajout aux éléments de connexion

1. **Ouvrir Réglages Système**

2. **Aller dans "Général" > "Éléments de connexion"**

3. **Cliquer sur "+"** sous "Ouvrir à l'ouverture de session"

4. **Sélectionner** l'application `GSGUI Launcher` dans ~/Applications

5. **Cocher "Masquer"** pour qu'elle se lance discrètement en arrière-plan

### Test de l'application

Double-cliquez sur l'application `GSGUI Launcher` pour tester. Vous devriez:
- Recevoir une notification quand GSGUI démarre
- Voir les services backend et frontend démarrer

Vérifier avec:
```bash
cd /Volumes/SSD/devs/gsgui
./process-manager-portable.sh status
```

## Alternative: Démarrage manuel

Si vous préférez un contrôle manuel, lancez simplement au démarrage:

```bash
cd /Volumes/SSD/devs/gsgui
./process-manager-portable.sh monitor
```

Le mode monitor s'occupera de:
- Démarrer le backend et le frontend
- Les surveiller en continu
- Les redémarrer automatiquement en cas d'arrêt

## Arrêt du service

Pour arrêter GSGUI:

```bash
cd /Volumes/SSD/devs/gsgui
./process-manager-portable.sh stop
```

Pour arrêter aussi le processus de surveillance:

```bash
./process-manager-portable.sh stop_monitor
```

## Logs

Les logs sont disponibles dans:
- `logs/backend.log` - Logs du backend Python
- `logs/frontend.log` - Logs du frontend Vite
- `logs/manager.log` - Logs du gestionnaire de processus

## Fichiers créés

Les fichiers suivants ont été créés mais ne sont plus utilisés (vous pouvez les supprimer):
- `~/bin/gsgui-launcher.sh` - Tentative de launcher bash
- `~/bin/gsgui-launcher.py` - Tentative de launcher Python
- `~/bin/process-manager-portable.sh` - Copie du script
- `~/Library/Logs/GSGUI/` - Logs du LaunchAgent (non fonctionnel)
- `com.gsgui.manager.plist` - Configuration LaunchAgent (non fonctionnelle)
- `install-launchd.sh` - Script d'installation LaunchAgent
- `uninstall-launchd.sh` - Script de désinstallation LaunchAgent
- `launchd-wrapper.sh` - Wrapper pour LaunchAgent

Vous pouvez nettoyer ces fichiers avec:
```bash
rm -rf ~/bin/gsgui-launcher.* ~/bin/process-manager-portable.sh
rm -rf ~/Library/Logs/GSGUI/
```
