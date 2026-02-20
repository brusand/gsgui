# Mémo Session - 5 Décembre 2025

## 🎯 Résumé des corrections effectuées

### 1. ✅ Fix chemins de configuration (gsgui.ini introuvable)

**Problème:** Le backend s'exécutait dans `/backend/` mais cherchait `./data/gsgui.ini` qui n'existait pas à cet emplacement.

**Solution:**
- Ajout de constantes pour chemins absolus dans `backend/gs_backend.py`:
  ```python
  BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
  PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
  GSGUI_INI_PATH = os.path.join(PROJECT_ROOT, 'data', 'gsgui.ini')
  ```
- Remplacement de tous les `'./data/gsgui.ini'` par `GSGUI_INI_PATH`
- Idem dans `backend/app/services/config_manager.py` avec `DEFAULT_GSGUI_INI` et `DEFAULT_STRATEGIES_INI`

**Fichiers modifiés:**
- `backend/gs_backend.py`
- `backend/app/services/config_manager.py`

---

### 2. ✅ Fix proxy Vite pour bouton "Boost detector"

**Problème:** Le frontend appelait directement `http://localhost:8001/api/v1/...` au lieu d'utiliser le proxy Vite, causant des erreurs CORS/connexion.

**Solution:**
- Changement de 3 URLs dans `web-ui/src/components/MainInterface.tsx`:
  - `http://localhost:8001/api/v1/...` → `/api/v1/...`
  - Pour: auto-refresh toggle, auto-refresh status, deep-purge

**Fichiers modifiés:**
- `web-ui/src/components/MainInterface.tsx` (lignes 461, 502, 541)

---

### 3. ✅ Fix auto-refresh qui efface les stratégies

**Problème:** Lors de l'auto-refresh, les stratégies de fin de challenge disparaissaient de l'affichage frontend.

**Solution:**
- Ajout du merge des `scheduled_strategies` avec les challenges avant envoi WebSocket
- Dans `backend/app/services/auto_refresh_scheduler.py` (lignes 251-262):
  ```python
  # Récupérer les stratégies schedulées pour ce profil
  user_data = config_manager.get_user(profile_id)
  scheduled_strategies = user_data.get('scheduled_strategies', {}) if user_data else {}

  # Merger les informations de stratégie avec les challenges
  for challenge_dict in challenges_dict:
      challenge_id = str(challenge_dict.get('id'))
      if challenge_id in scheduled_strategies:
          strategy_info = scheduled_strategies[challenge_id]
          challenge_dict['selected_strategy'] = strategy_info.get('strategy_name', '')
          challenge_dict['strategy_status'] = strategy_info.get('strategy_status', '')
  ```

**Fichiers modifiés:**
- `backend/app/services/auto_refresh_scheduler.py`

---

### 4. ✅ Fix race condition multi-profils (le bug principal !)

**Problème:** Les 4 auto-refresh (bruno, caloune, alain, maryse) s'exécutaient EXACTEMENT au même moment et s'écrasaient mutuellement dans `gsgui.ini`. Le dernier profil écrasait les modifications des autres, d'où `strategy_name = ""`.

**Solution:**
- **RLock** au lieu de Lock (évite deadlocks)
- **Lock global** sur TOUTE l'opération `save_user_challenge()` (load + modify + save atomique)
- **Reload du config** avant chaque save pour avoir les dernières `scheduled_strategies`

**Changements dans `backend/app/services/config_manager.py`:**
```python
from threading import RLock  # Ligne 11

def __init__(self, ...):
    self._lock = RLock()  # Ligne 32

def save_user_challenge(self, user_id: str, challenge_id: str, challenge_data: Dict[str, Any]) -> bool:
    # LOCK GLOBAL pour éviter race condition
    with self._lock:  # Ligne 200
        try:
            # Recharger le config depuis le fichier
            self._load_configs()  # Ligne 204

            # Logique de priorité pour strategy_name (lignes 212-232):
            # 1. scheduled_strategies (priorité haute)
            # 2. strategy_name existant (préservation)
            # 3. challenge_data fourni
            # 4. vide par défaut
```

**Fichiers modifiés:**
- `backend/app/services/config_manager.py`

---

### 5. ✅ Changement intervalle auto-refresh: 10min → 5min

**Modification:**
- Changé la valeur par défaut de 10 à 5 minutes dans 4 fichiers
- Modifié `data/gsgui.ini` directement pour tous les profils

**Fichiers modifiés:**
- `backend/gs_backend.py` (ligne 1009)
- `backend/app/services/auto_refresh_scheduler.py` (lignes 26, 90)
- `web-ui/src/components/MainInterface.tsx` (ligne 31)
- `data/gsgui.ini` (auto_refresh_interval = 5 pour tous)

---

## 🐛 Bug identifié (non corrigé) - Boost raté

**Challenge:** "Made For GuruShots" (ID: 114812) - Profil bruno

**Analyse:**
1. **09:37:20** - ✅ Boost activé avec succès (photo: 45c024483d089bc42376fefcaa1e24ec)
2. **10:52 à 11:02** - ❌ 3 tentatives échouées avec error_code=1002

**Problèmes:**
1. **Log trompeur** (ligne 343 de `gurushots_api.py`):
   - Affiche "Photo boost successfully" même si GuruShots retourne `{success: false, error_code: 1002}`

2. **Détection défaillante**:
   - L'auto-refresh continue à détecter le boost comme `AVAILABLE` après activation
   - Ne détecte pas le passage à l'état `USED`

**Error_code 1002** = Probablement "Boost already used" ou "Boost not available"

**À corriger:**
- Améliorer le log de `boost_photo()` pour afficher le vrai statut de la réponse
- Améliorer la détection d'état du boost pour éviter les tentatives inutiles

---

## 📊 État actuel du système

**Backend:** ✅ Opérationnel (PID: 31948/31952)
**Frontend:** ✅ Opérationnel (PID: 31965)
**Auto-refresh:** ✅ Actif toutes les 5 minutes pour les 4 profils

**Prochains refresh:**
- bruno: 17:02:19
- caloune: 17:02:19
- alain: 17:02:19
- maryse: 17:02:19

---

## 🔧 Fichiers modifiés (à commiter)

1. `backend/gs_backend.py` - Chemins absolus + intervalle 5min
2. `backend/app/services/config_manager.py` - RLock + reload + logique priorité strategy_name
3. `backend/app/services/auto_refresh_scheduler.py` - Merge strategies + intervalle 5min
4. `web-ui/src/components/MainInterface.tsx` - Proxy Vite + intervalle 5min
5. `data/gsgui.ini` - auto_refresh_interval = 5

**Logs de debug ajoutés** (à retirer avant commit final):
- `config_manager.py` lignes 216-220, 225, 228, 232, 239, 247

---

## 📝 À faire après reboot

1. **Vérifier** que le système redémarre correctement
2. **Décider** si on commit tous ces changements
3. **Corriger** le bug des boosts (logs trompeurs + détection état)
4. **Nettoyer** les logs de debug si pas utiles

---

*Session terminée le 5 décembre 2025 à 17:00 environ*
*Backend/Frontend opérationnels*
*Tous les bugs de race condition et chemins résolus ✅*
