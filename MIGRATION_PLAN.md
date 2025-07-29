# 🏗️ Plan de Migration Backend GSGUI

## 📋 **État Actuel Analysé**

### ✅ **Existant Backend**
- **FastAPI** avec structure complète
- **ConfigManager** avec locks et format .ini compatible
- **WebSockets** pour real-time
- **API endpoints** bases créés

### 🔍 **Stratégies Programmées Actuelles (gsui.py)**
```python
# Structure dans .ini :
scheduled_strategies = {
    'challenge_id': {
        'strategy_name': '4m',
        'challenge_title': 'Mon Challenge', 
        'scheduled_at': '2025-07-29T10:31:04.686123'
    }
}

# Logique de traitement :
1. save_scheduled_strategy()    # Sauve dans .ini
2. load_and_restore_scheduled_strategies()  # Restaure au démarrage
3. schedule_multiple_votes()    # Planifie les votes
4. remove_scheduled_strategy()  # Supprime
```

## 🎯 **Migration Priorisée - Phase 1 : Stratégies**

### **1. Endpoints API à créer**
```python
# Stratégies programmées
POST /api/v1/profiles/{profile_id}/strategies           # Programmer une stratégie
GET  /api/v1/profiles/{profile_id}/strategies           # Lister stratégies programmées  
GET  /api/v1/profiles/{profile_id}/strategies/{challenge_id}  # Détail stratégie
DELETE /api/v1/profiles/{profile_id}/strategies/{challenge_id} # Supprimer
PUT  /api/v1/profiles/{profile_id}/strategies/{challenge_id}   # Modifier

# Gestion profils mobile
POST /api/v1/profiles/register    # Créer/connecter profil avec gs_token
GET  /api/v1/profiles/{profile_id} # Info profil
GET  /api/v1/strategies           # Liste stratégies disponibles (4m, fill, etc.)
```

### **2. Modèles de données**
```python
class ProfileRegisterRequest:
    profile_name: str
    gs_token: Optional[str] = None  # Si None, cherche dans .ini existant

class ScheduledStrategy:
    challenge_id: str
    strategy_name: str
    challenge_title: str
    scheduled_at: datetime
    status: str  # 'pending', 'running', 'completed', 'failed'
```

### **3. Services à migrer**
- **StrategyScheduler** : Logique de programmation depuis gsui.py
- **ProfileManager** : Gestion des profils avec gs_token
- **GuruShotsAPI** : Intégration API GuruShots

## 🚀 **Questions avant implémentation :**

### **A. Architecture des stratégies**
1. **Exécution** : Garder l'exécution côté backend ou permettre déclenchement manuel depuis mobile ?
2. **Scheduler** : Utiliser APScheduler (comme actuellement) ou système de tâches (Celery) ?
3. **Real-time** : WebSockets pour notifier le mobile des changements de statut ?

### **B. Gestion des profils**
1. **Authentification** : Simple nom+token ou système plus sécurisé ?
2. **Validation gs_token** : Faire un appel test à GuruShots pour valider le token ?
3. **Multi-device** : Un profil peut-il être utilisé depuis plusieurs mobiles ?

### **C. Compatibilité**
1. **Migration douce** : Garder gsui.py fonctionnel pendant la transition ?
2. **Format données** : Maintenir exactement le même format .ini ou améliorer ?

## 💡 **Recommandation de démarrage :**

### **Phase 1a : API Profils (1-2h)**
- Endpoint register profil 
- Validation gs_token
- CRUD profils basique

### **Phase 1b : API Stratégies (2-3h)**  
- CRUD stratégies programmées
- Migration logique depuis gsui.py
- Tests avec profils existants

Ça te va comme plan ? Dis-moi tes priorités et on commence ! 🎯