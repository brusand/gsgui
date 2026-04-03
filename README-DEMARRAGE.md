# Configuration du Démarrage Automatique - GSGUI

## ✅ Installation Terminée!

L'application **GSGUI Launcher** a été créée et configurée avec succès!

### Fichiers créés

- **`~/Applications/GSGUI Launcher.app`** - Application de lancement automatique
- Cette application démarre automatiquement avec votre session macOS

### Fonctionnement

L'application fait ce qui suit au démarrage:

1. **Attend le montage du disque SSD** (max 60 secondes)
2. **Lance le process-manager** en mode start
3. **Démarre le backend** et le **frontend**
4. **Affiche une notification** de succès

### Vérifier le démarrage automatique

L'application a été ajoutée aux **Éléments de connexion**. Pour vérifier:

1. Ouvrir **Réglages Système**
2. Aller dans **Général** > **Éléments de connexion**
3. Vous devriez voir **GSGUI Launcher** dans la liste "Ouvrir à l'ouverture de session"

### Test

Vous pouvez tester l'application maintenant:

```bash
# Arrêter les services actuels
cd /Volumes/SSD/devs/gsgui
./process-manager-portable.sh stop

# Double-cliquer sur l'application dans ~/Applications
# ou lancer depuis le terminal:
open ~/Applications/"GSGUI Launcher.app"

# Vérifier que les services démarrent
./process-manager-portable.sh status
```

### Notifications

Vous recevrez des notifications macOS:
- **"Démarrage de GSGUI..."** - Au lancement de l'application
- **"GSGUI est démarré!"** - Quand tous les services sont actifs
- **"Le disque SSD n'est pas monté!"** - Si le disque n'est pas disponible

### Gestion des services

```bash
# Vérifier l'état
./process-manager-portable.sh status

# Arrêter les services
./process-manager-portable.sh stop

# Redémarrer
./process-manager-portable.sh restart

# Voir les logs
./process-manager-portable.sh logs
```

### Désactiver le démarrage automatique

Si vous ne voulez plus que GSGUI démarre automatiquement:

1. **Réglages Système** > **Général** > **Éléments de connexion**
2. Sélectionner **GSGUI Launcher**
3. Cliquer sur le bouton **"-"** pour le retirer

Ou via le terminal:

```bash
osascript -e 'tell application "System Events" to delete login item "GSGUI Launcher"'
```

### Logs

Les logs sont disponibles dans:
- `logs/backend.log` - Backend Python
- `logs/frontend.log` - Frontend Vite
- `logs/manager.log` - Gestionnaire de processus
- `/tmp/gsgui-launcher.log` - Application de lancement

### En cas de problème

Si les services ne démarrent pas automatiquement:

1. Vérifier les logs: `cat /tmp/gsgui-launcher.log`
2. Vérifier que le disque SSD est bien monté: `ls /Volumes/SSD/devs/gsgui`
3. Tester manuellement: `open ~/Applications/"GSGUI Launcher.app"`
4. Lancer manuellement les services: `./process-manager-portable.sh start`

### Suppression complète

Pour supprimer complètement la configuration:

```bash
# Retirer des éléments de connexion
osascript -e 'tell application "System Events" to delete login item "GSGUI Launcher"'

# Supprimer l'application
rm -rf ~/Applications/"GSGUI Launcher.app"

# Nettoyer les fichiers temporaires
rm -f /tmp/gsgui-launcher.log
rm -rf ~/bin/gsgui-launcher.*
rm -rf ~/Library/Logs/GSGUI/
```

## Prochaines étapes

Au prochain redémarrage de votre Mac:
1. Le disque SSD sera monté automatiquement
2. L'application GSGUI Launcher se lancera
3. Les services backend et frontend démarreront
4. Vous recevrez une notification de confirmation

**C'est tout! Votre système est maintenant configuré pour le démarrage automatique.** 🎉
