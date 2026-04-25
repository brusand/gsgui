# Watchdog VNC pour Mac mini

Solution automatique pour redémarrer le service de partage d'écran (VNC) quand il se bloque.

## Le problème

Après plusieurs jours sans connexion, le service VNC de macOS peut se bloquer, rendant impossible la connexion via Partage d'écran ou VNC Viewer, même si le Mac mini fonctionne normalement (serveurs, disques accessibles).

## La solution

Un watchdog launchd qui :
- Vérifie toutes les **5 minutes** si le service VNC répond
- Redémarre automatiquement le service s'il est bloqué
- Logue toutes les actions dans `/tmp/vnc-watchdog.log`

## Installation

Depuis votre ordinateur local :

```bash
./install-vnc-watchdog.sh
```

Le script vous demandera :
- L'utilisateur du Mac mini
- L'IP du Mac mini

## Vérification

Pour vérifier que le watchdog fonctionne, connectez-vous au Mac mini :

```bash
ssh user@ip_mac_mini

# Vérifier que le service est actif
sudo launchctl list | grep vnc-watchdog

# Voir les logs
tail -f /tmp/vnc-watchdog.log
```

## Désinstallation

```bash
./uninstall-vnc-watchdog.sh
```

## Fichiers créés sur le Mac mini

- `/usr/local/bin/vnc-watchdog.sh` - Script de surveillance
- `/Library/LaunchDaemons/com.gsgui.vnc-watchdog.plist` - Configuration launchd
- `/tmp/vnc-watchdog.log` - Journal des actions
- `/tmp/vnc-watchdog-stdout.log` - Sortie standard
- `/tmp/vnc-watchdog-stderr.log` - Erreurs

## Notes

- Le watchdog s'exécute automatiquement au démarrage du Mac mini
- Aucun redémarrage du Mac mini n'est nécessaire après l'installation
- Les logs permettent de suivre les interventions automatiques
