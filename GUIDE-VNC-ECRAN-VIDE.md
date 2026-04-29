# Guide de résolution : Écran VNC vide après reconnexion

## Symptôme

Après une première connexion VNC réussie, quand vous vous déconnectez puis reconnectez :
- ✅ La connexion VNC s'établit (pas d'erreur réseau)
- ❌ L'écran est vide/noir, sans prompt de mot de passe
- ❌ Obligé de redémarrer le Mac mini pour retrouver l'écran de connexion

## Cause

Ce problème est causé par des sessions VNC "fantômes" qui restent actives en mémoire après déconnexion. Le `loginwindow` (écran de connexion macOS) ne se rafraîchit pas correctement.

## Solutions

### Solution immédiate (via SSH)

Connectez-vous en SSH au Mac mini et exécutez :

```bash
sudo ./fix-vnc-blank-screen.sh
```

Ce script va :
1. Fermer les sessions utilisateur actives
2. Réinitialiser le `loginwindow`
3. Rafraîchir le `WindowServer`
4. Nettoyer les connexions VNC zombies
5. Redémarrer le service VNC si nécessaire

**Note:** Nécessite sudo (mot de passe admin)

### Solution préventive (automatisation)

Pour éviter que ce problème se reproduise, installez le nettoyage automatique :

```bash
# Installer le LaunchDaemon qui nettoie les sessions toutes les 5 minutes
sudo ./install-vnc-session-cleanup.sh
```

Cela va créer un service qui :
- Détecte quand vous vous déconnectez de VNC
- Nettoie automatiquement les sessions zombies
- Rafraîchit l'écran de connexion
- Redémarre VNC si trop de connexions zombies

### Vérification des logs

Pour voir ce qui se passe :

```bash
# Logs du nettoyage automatique
tail -f /tmp/vnc-session-cleanup.log

# Logs du watchdog VNC
tail -f /tmp/vnc-watchdog.log
```

## Scripts disponibles

| Script | Usage | Description |
|--------|-------|-------------|
| `fix-vnc-blank-screen.sh` | Immédiat | Corrige l'écran vide maintenant |
| `vnc-session-cleanup.sh` | Automatique | Nettoie les sessions (appelé par cron) |
| `force-restart-vnc.sh` | Dépannage | Redémarrage complet du VNC |
| `fix-vnc-zombie-connections.sh` | Dépannage | Nettoie les connexions zombies |

## Pourquoi ça arrive ?

macOS gère mal les déconnexions VNC multiples :
1. Vous vous connectez → session VNC créée
2. Vous vous déconnectez → session reste en mémoire (CLOSE_WAIT)
3. Vous reconnectez → nouvelle session créée, mais l'ancienne bloque le loginwindow
4. Résultat : écran noir car loginwindow pense qu'une session est encore active

## Prévention

### Bonne pratique de déconnexion

Au lieu de fermer brutalement VNC Viewer, faites :
1. Menu Pomme > Fermer la session (si connecté)
2. Attendre 5 secondes
3. Fermer VNC Viewer

### Monitoring

Vérifiez régulièrement les connexions zombies :

```bash
# Voir le nombre de connexions zombies
netstat -an | grep 5900 | grep CLOSE_WAIT | wc -l
```

Si > 50 connexions zombies → redémarrez VNC avec `./fix-vnc-blank-screen.sh`

## Troubleshooting

### Si le problème persiste après fix-vnc-blank-screen.sh

1. Vérifier qu'aucun utilisateur n'est connecté physiquement au Mac mini :
   ```bash
   who
   ```

2. Forcer le logout de tous les utilisateurs :
   ```bash
   sudo pkill -KILL -u votre_username
   ```

3. Redémarrer complètement le service VNC :
   ```bash
   sudo ./force-restart-vnc.sh
   ```

4. En dernier recours, redémarrer le Mac mini :
   ```bash
   sudo shutdown -r now
   ```

### Si vous ne pouvez pas vous connecter en SSH

Vous devrez redémarrer le Mac mini physiquement :
- Débrancher/rebrancher l'alimentation
- Ou appuyer brièvement sur le bouton power (si accessible)

## Automatisation complète

Pour une tranquillité totale, installez tous les services :

```bash
# 1. Nettoyage automatique des sessions
sudo ./install-vnc-session-cleanup.sh

# 2. Watchdog VNC (redémarre si planté)
sudo ./install-vnc-watchdog.sh

# 3. Vérifier que tout fonctionne
launchctl list | grep vnc
```

Vous devriez voir :
- `com.gsgui.vnc.session-cleanup` (nettoyage toutes les 5min)
- `com.gsgui.vnc.watchdog` (surveillance continue)

## Accès à distance de secours

Si VNC et SSH sont bloqués, vous pouvez :

1. **Tailscale** (si installé) : connexion via VPN privé
2. **Port forwarding SSH** : plus sécurisé que VNC direct
3. **TeamViewer** : solution de secours (installer avant problème)

## Sécurité

⚠️ **Important** : Le port VNC 5900 ne devrait PAS être exposé directement sur Internet.

Solutions sécurisées :
- Utiliser un tunnel SSH : `ssh -L 5900:localhost:5900 user@mac-mini`
- Configurer Tailscale : VPN privé point-à-point
- Firewall : bloquer port 5900 depuis l'extérieur

Voir aussi : `SECURITE-VNC.md`
