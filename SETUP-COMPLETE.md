# Setup Complet - GSGUI Unifié ✅

**Date**: 4 avril 2026
**Status**: ✅ Opérationnel

---

## Résumé

Tous les services GuruShots sont maintenant unifiés dans le projet `/Volumes/SSD/devs/gsgui` avec démarrage automatique au boot.

### Services Actifs

| Service | Status | PID | Port/Type |
|---------|--------|-----|-----------|
| Backend API | ✅ Actif | 6689 | 8001 |
| Frontend Web | ✅ Actif | 6704 | 5173 |
| Collector | ✅ Actif | 6731 | Daemon |
| Caffeinate | ⚠️ À configurer | - | Système |

---

## Corrections Appliquées

### 1. Installation de la Dépendance `schedule`

**Problème**: `ModuleNotFoundError: No module named 'schedule'`

**Solution**:
```bash
cd /Volumes/SSD/devs/gsgui
source venv/bin/activate
pip install schedule
```

✅ **Résolu**: Le module `schedule` est maintenant installé dans l'environnement virtuel.

### 2. Configuration du Collector

**Problème**: Le collector ne trouvait pas son fichier de configuration

**Solution**: Modification de `backend/gs_collector.py` pour chercher automatiquement `collector.env` dans le répertoire parent:

```python
# Chercher collector.env dans le répertoire parent (gsgui/)
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
collector_env = os.path.join(parent_dir, 'collector.env')

if os.path.exists(collector_env):
    load_dotenv(collector_env)
```

✅ **Résolu**: Le collector charge maintenant `/Volumes/SSD/devs/gsgui/collector.env`

### 3. Création des Répertoires

**Problème**: Répertoires manquants pour les logs et exports

**Solution**:
```bash
mkdir -p /Volumes/SSD/Data/GuruShots/logs
mkdir -p /Volumes/SSD/Data/GuruShots/exports
mkdir -p /Volumes/SSD/Data/GuruShots/visualizations
```

✅ **Résolu**: Tous les répertoires nécessaires existent.

---

## État Actuel

### Services

```bash
cd /Volumes/SSD/devs/gsgui
./process-manager-portable.sh status
```

**Résultat**:
```
✅ Backend actif (PID: 6689)
✅ Frontend actif (PID: 6704)
✅ Collector actif (PID: 6731)
✅ Tous les services sont actifs
```

### Logs Collector

Dernière collecte (voir `/Volumes/SSD/devs/gsgui/logs/collector.log`):

```
2026-04-04 14:53:47 - INFO - Traitement de 5 challenges
2026-04-04 14:53:47 - INFO - Snapshot sauvegardé avec 5 challenges
2026-04-04 14:53:47 - INFO - Collecte terminée avec succès
```

✅ Le collector fonctionne et collecte les données toutes les 30 minutes.

---

## Configuration au Boot

### Application de Démarrage

**Status**: ✅ Déjà configurée (depuis votre setup précédent de gsgui)

**Application**: `~/Applications/GSGUI Launcher.app`

**Vérification**:
```bash
osascript -e 'tell application "System Events" to get the name of every login item'
# Doit afficher: GSGUI Launcher
```

### Prévention de Veille (Caffeinate)

**Status**: ⚠️ Intégré dans automator-launcher.sh mais à tester au prochain boot

Le script `automator-launcher.sh` a été modifié pour lancer automatiquement `caffeinate -dis` au démarrage.

**Test manuel**:
```bash
# Tester le launcher complet
open ~/Applications/"GSGUI Launcher.app"

# Vérifier caffeinate après
ps aux | grep caffeinate | grep -v grep
```

---

## Commandes Utiles

### Gestion des Services

```bash
cd /Volumes/SSD/devs/gsgui

# Démarrer tout
./process-manager-portable.sh start

# Arrêter tout
./process-manager-portable.sh stop

# Redémarrer
./process-manager-portable.sh restart

# Statut détaillé
./process-manager-portable.sh status

# Statut global (incluant caffeinate)
./status-all.sh
```

### Logs

```bash
# Logs individuels
tail -f logs/backend.log
tail -f logs/frontend.log
tail -f logs/collector.log

# Log de démarrage
tail -f /tmp/gsgui-launcher.log

# Toutes les collectes du collector
grep "Collecte terminée" logs/collector.log
```

### Base de Données

Le collector sauvegarde dans:
```
/Volumes/SSD/Data/GuruShots/gurushots_data.db
```

Vérifier:
```bash
ls -lh /Volumes/SSD/Data/GuruShots/gurushots_data.db
sqlite3 /Volumes/SSD/Data/GuruShots/gurushots_data.db "SELECT COUNT(*) FROM snapshots;"
```

---

## Test de Démarrage Automatique

### Sans Redémarrer

```bash
cd /Volumes/SSD/devs/gsgui

# 1. Arrêter tout
./process-manager-portable.sh stop
killall caffeinate 2>/dev/null || true

# 2. Nettoyer les logs
rm -f /tmp/gsgui-launcher.log

# 3. Lancer comme au boot
open ~/Applications/"GSGUI Launcher.app"

# 4. Attendre 20 secondes
sleep 20

# 5. Vérifier
./status-all.sh
cat /tmp/gsgui-launcher.log
```

### Avec Redémarrage Complet

1. **Redémarrer le Mac Mini**
2. **Attendre 2-3 minutes** (temps de montage du SSD + démarrage)
3. **Vérifier**:
```bash
cd /Volumes/SSD/devs/gsgui
./status-all.sh
```

**Résultat attendu**:
- ✅ Backend actif (port 8001)
- ✅ Frontend actif (port 5173)
- ✅ Collector actif (daemon)
- ✅ Caffeinate actif (prévention veille)

---

## URLs et Accès

### Backend API
- **URL**: http://localhost:8001
- **Health Check**: http://localhost:8001/health
- **Docs**: http://localhost:8001/docs

### Frontend Web
- **URL**: http://localhost:5173
- **Interface**: Interface web complète de gestion

### Collector
- **Mode**: Daemon background
- **Intervalle**: 30 minutes
- **Challenges**: 22 challenges configurés dans `collector.env`
- **Base de données**: `/Volumes/SSD/Data/GuruShots/gurushots_data.db`

---

## Fichiers Importants

| Fichier | Description |
|---------|-------------|
| `~/Applications/GSGUI Launcher.app` | Application de démarrage |
| `/Volumes/SSD/devs/gsgui/automator-launcher.sh` | Script de lancement unifié |
| `/Volumes/SSD/devs/gsgui/process-manager-portable.sh` | Gestionnaire de 3 services |
| `/Volumes/SSD/devs/gsgui/backend/gs_collector.py` | Collector migré |
| `/Volumes/SSD/devs/gsgui/collector.env` | Configuration du collector |
| `/Volumes/SSD/devs/gsgui/status-all.sh` | Script de statut global |
| `/tmp/gsgui-launcher.log` | Log de démarrage |
| `/tmp/gsgui-caffeinate.pid` | PID de caffeinate |

---

## Prochaines Étapes

### Recommandé

1. ✅ **Tester le démarrage automatique** avec un redémarrage complet du Mac
2. ⚠️ **Vérifier caffeinate** après le boot
3. ✅ **Surveiller les logs du collector** pour s'assurer qu'il collecte bien toutes les 30 minutes

### Optionnel

- Configurer des alertes Telegram (variables dans `collector.env`)
- Ajouter un monitoring externe des services
- Créer un dashboard pour visualiser les données collectées

---

## Support

### Logs à Vérifier en Cas de Problème

1. `/tmp/gsgui-launcher.log` - Démarrage global
2. `logs/manager.log` - Process manager
3. `logs/collector.log` - Collecteur spécifique
4. `logs/backend.log` - API backend
5. `logs/frontend.log` - Interface web

### Commandes de Diagnostic

```bash
# Statut global
cd /Volumes/SSD/devs/gsgui && ./status-all.sh

# Processus Python actifs
ps aux | grep python | grep -v grep

# Ports occupés
lsof -i:8001
lsof -i:5173

# Assertions de veille
pmset -g assertions | grep caffeinate
```

---

## Conclusion

✅ **Tous les services sont opérationnels**
✅ **Le collector collecte les données avec succès**
✅ **Architecture unifiée fonctionnelle**
⚠️ **Démarrage automatique à tester au prochain reboot**

Le système est prêt pour fonctionner 24/7! 🚀
