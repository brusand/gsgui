# Correction des Chemins Absolus - GSGUI

## Problème Identifié

### Symptômes
- Deux répertoires `data/` causant de la confusion :
  - `/Volumes/SSD/devs/gsgui/data/` (racine - le BON)
  - `/Volumes/SSD/devs/gsgui/backend/data/` (symlink)

- Les boutons "Stratégie" et "Édition" ne pointaient pas vers les mêmes fichiers selon le contexte de démarrage
- Au démarrage au boot, le CWD (current working directory) était différent, causant des erreurs de résolution de chemins

### Cause Racine
Tous les fichiers Python utilisaient des **chemins relatifs** :
- `'./data/gsgui.ini'`
- `'./data/strategies.ini'`
- `'data/strategies.ini'`

Ces chemins ne fonctionnent que si le CWD est exactement `/Volumes/SSD/devs/gsgui/`. Au démarrage au boot, le CWD peut être différent (`/`, `/Users/bruno`, etc.), causant des erreurs.

## Solution Mise en Place

### 1. Module Centralisé pour les Chemins
**Nouveau fichier** : `backend/app/utils/paths.py`

Ce module :
- Calcule `PROJECT_ROOT` depuis `__file__` (absolu, indépendant du CWD)
- Définit tous les chemins critiques comme constantes absolues
- Assure que les chemins fonctionnent **depuis n'importe quel CWD**

```python
PROJECT_ROOT = /Volumes/SSD/devs/gsgui
GSGUI_INI_PATH = /Volumes/SSD/devs/gsgui/data/gsgui.ini
STRATEGIES_INI_PATH = /Volumes/SSD/devs/gsgui/data/strategies.ini
```

### 2. Fichiers Corrigés

| Fichier | Changement | Ligne |
|---------|-----------|-------|
| `backend/app/utils/paths.py` | **CRÉÉ** - Module centralisé | N/A |
| `backend/app/services/config_manager.py` | Import + utilisation chemins absolus | 18-19 |
| `backend/app/services/extended_strategy_executor.py` | Import + utilisation chemins absolus | 75, 82 |
| `backend/app/services/enhanced_strategy_engine.py` | Import + utilisation chemins absolus | 38 |
| `backend/gs_backend.py` | Import + remplacement 6 occurrences | 30, 124, 1701, 2344, 2371, 2392, 3194 |

### 3. Vérifications Effectuées

✅ **Test 1** : Démarrage depuis `/Volumes/SSD/devs/gsgui/` (normal)
```bash
./process-manager-portable.sh start
# → Backend et Frontend démarrent correctement
```

✅ **Test 2** : Test chemins depuis `/tmp` (CWD différent)
```python
CWD: /private/tmp
PROJECT_ROOT: /Volumes/SSD/devs/gsgui
GSGUI_INI_PATH: /Volumes/SSD/devs/gsgui/data/gsgui.ini
STRATEGIES_INI_PATH: /Volumes/SSD/devs/gsgui/data/strategies.ini
Files exist: gsgui.ini=True, strategies.ini=True
```

✅ **Test 3** : API retourne le bon fichier
```bash
curl http://localhost:8001/api/v1/strategies/config
# Path: /Volumes/SSD/devs/gsgui/data/strategies.ini ✓
# Content length: 7689 chars ✓
```

✅ **Test 4** : Frontend utilise l'API (pas de fichiers locaux)
- Bouton "Édition" → `apiClient.getStrategiesConfig()` → `/api/v1/strategies/config`
- Bouton "Sauvegarder" → `apiClient.saveStrategiesConfig()` → `/api/v1/strategies/save`

## Résultat

### Avant
- ❌ Chemins relatifs cassés selon le CWD
- ❌ Confusion entre 2 répertoires `data/`
- ❌ Bugs au démarrage au boot

### Après
- ✅ Chemins absolus calculés depuis `__file__`
- ✅ Un seul répertoire `data/` de référence (racine)
- ✅ Fonctionne depuis **n'importe quel CWD**
- ✅ Compatible démarrage au boot via launchd

## Fichiers Toujours Utilisés

| Fichier | Usage |
|---------|-------|
| `/Volumes/SSD/devs/gsgui/data/gsgui.ini` | Configuration principale (profils, challenges) |
| `/Volumes/SSD/devs/gsgui/data/strategies.ini` | Définitions des stratégies |
| `/Volumes/SSD/devs/gsgui/data/challenges.db` | Base de données des challenges |

## Prochaines Étapes (Optionnel)

1. **Tester le démarrage au boot** :
   ```bash
   launchctl load ~/Library/LaunchAgents/com.user.gsgui.plist
   ```

2. **Vérifier les logs** :
   ```bash
   tail -f /Volumes/SSD/devs/gsgui/logs/backend.log
   ```

3. **Supprimer l'ancien symlink** (si non utilisé) :
   ```bash
   # Vérifier d'abord qu'il n'est plus référencé
   grep -r "backend/data" /Volumes/SSD/devs/gsgui/backend/
   # Si rien trouvé, supprimer le symlink
   rm /Volumes/SSD/devs/gsgui/backend/data/gsgui.ini
   ```

## Notes Techniques

- **Threading Safety** : Les locks existants (`gsgui_ini_lock`, `strategies_ini_lock`) sont préservés
- **Rétrocompatibilité** : Aucun changement d'API ou de format de fichier
- **Performance** : Aucun impact (chemins calculés une seule fois à l'import)
- **Portabilité** : Utilise `pathlib.Path` (cross-platform)

---

**Date de correction** : 2026-04-06
**Testés** : macOS, démarrage manuel + simulation CWD différent
**Statut** : ✅ Production Ready
