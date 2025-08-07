# ANCA Surveillance & Extended Strategies - Usage Guide

## 🔍 ANCA Surveillance Simple

### Configuration Cron MCP
Ajoutez dans votre configuration cron MCP :

```python
# Surveillance ANCA toutes les 10 minutes
@cron("*/10 * * * *")
async def anca_surveillance_job():
    """Surveille ANCA toutes les 10 minutes"""
    import requests
    
    try:
        response = requests.post("http://localhost:8000/api/v1/simple/cron/anca-surveillance")
        if response.status_code == 200:
            results = response.json()
            print(f"✅ ANCA surveillance: {results['results']}")
        else:
            print(f"❌ ANCA surveillance failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error in ANCA surveillance: {e}")

# Surveillance plus fréquente dernière heure (facultatif)
@cron("*/2 * * * *")  # Toutes les 2 minutes
async def anca_surveillance_intensive():
    """Surveillance intensive ANCA (à activer seulement si nécessaire)"""
    # Logique pour surveiller plus intensivement
    pass
```

### Méthodes Utilisées
- ✅ **get_top_photographer()** - Récupération classement challenge
- ✅ **get_challenges()** - Liste challenges actifs  
- ✅ **Comparaison états** - Détection événements ANCA
- ✅ **Stockage JSON** - Persistance événements

### Événements Détectés
- 🔥 **new_entry** - ANCA poste nouvelle photo
- 🔄 **swap_out** - ANCA retire photo (swap)
- 📈 **rank_change** - Changement rang significatif (±10)
- 👁️ **first_detection** - Première apparition dans challenge

## 🚀 Stratégies Étendues [4photos]

### Format strategies.ini Supporté
```ini
[4photos]
description="Stratégie 4 photos ANCA-style"
0=submit, end-120m0s, 83a85db59ad25b9e9171781de48d123b
1=vote, end-120m0s, 80
2=swap, end-90m0s, 83a85db59ad25b9e9171781de48d123b, 83a85db59ad25b9e9171781de48d134332
3=swap, end-60m0s, 83a85db59ad25b9e9171781de48d134332, 83a85db59ad25b9e9171781de48d123b
4=submit, end-60m0s, 83a85db59ad25b9e9171781de48d122323, 83a85db59ad25b9e9171781de48d12324, 83a85db59ad25b9e9171781de48d12325
5=vote, end-60m0s, 80
6=boost, end-50m0s, 0
7=turbo, end-50m0s, 1
8=vote, end-2m0s, 80
9=vote, end-0m45s, 20
```

### Actions Supportées
- **vote** - Vote sur photos (existant)
- **submit** - Soumettre photo(s) au challenge
- **swap** - Échanger deux photos  
- **boost** - Booster photo (index [0] = plus de votes)
- **turbo** - Débloquer turbo (set_turbo de l'API)

### Timing Supporté
- **end-120m0s** - 120 minutes avant fin challenge
- **end-90m0s** - 90 minutes avant fin
- **end-2m0s** - 2 minutes avant fin
- **now** - Immédiatement

## 📡 API Endpoints

### ANCA Surveillance
```bash
# Exécuter surveillance manuellement
POST /api/v1/simple/anca/surveillance/run

# Récupérer événements ANCA
GET /api/v1/simple/anca/events?limit=50

# Statistiques surveillance
GET /api/v1/simple/anca/stats
```

### Stratégies Étendues
```bash
# Exécuter stratégie [4photos]
POST /api/v1/simple/strategies/extended/execute
{
  "profile_id": "user1",
  "challenge_id": "12345", 
  "challenge_url": "my-challenge",
  "strategy_name": "4photos"
}

# Statut exécution
GET /api/v1/simple/strategies/extended/{execution_id}/status

# Annuler exécution
POST /api/v1/simple/strategies/extended/{execution_id}/cancel

# Liste stratégies disponibles
GET /api/v1/simple/strategies/available
```

## 🔧 Intégration avec l'Existant

### Méthodes API Requises
Ces méthodes doivent être présentes dans GuruShotsAPI :

```python
# Nouvelles méthodes que vous avez ajoutées
await api_client.submit_to_challenge(challenge_id, image_id)
await api_client.boost_photo(challenge_id, image_id) 
await api_client.set_turbo(challenge_id)  # Débloquer turbo

# Existantes utilisées
await api_client.swap_photo(challenge_id, current_id, new_id)
await api_client.execute_simple_vote(challenge_url, count)
await api_client.get_challenge_followings(challenge_id)  # Pour classement
```

### Fichiers de Données
- **strategies.ini** - Configuration stratégies (lecture seule)
- **anca_surveillance_data.json** - Événements ANCA persistés
- **Logs** - Events WebSocket pour interface temps réel

## 🎯 Exemple d'Usage Complet

### 1. Démarrer Surveillance ANCA
```bash
# Via cron MCP automatique toutes les 10min
# OU manuellement :
curl -X POST http://localhost:8000/api/v1/simple/anca/surveillance/run
```

### 2. Exécuter Stratégie [4photos]
```bash
curl -X POST http://localhost:8000/api/v1/simple/strategies/extended/execute \
  -H "Content-Type: application/json" \
  -d '{
    "profile_id": "bruno",
    "challenge_id": "12345",
    "challenge_url": "nature-photography-challenge", 
    "strategy_name": "4photos"
  }'
```

### 3. Surveiller via WebSocket
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/your_user_id');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  // Événements ANCA
  if (data.data.type === 'anca_surveillance_event') {
    console.log('🚨 ANCA Event:', data.data.event);
  }
  
  // Actions stratégie étendue
  if (data.data.type === 'extended_strategy_action') {
    console.log('🎯 Strategy Action:', data.data.action);
  }
};
```

## 🎛️ Configuration Recommandée

### Fréquence Surveillance
- **Normal** : 10-15 minutes (challenges > 6h restantes)
- **Intensif** : 5 minutes (challenges < 6h restantes)
- **Critique** : 2 minutes (challenges < 1h restantes)

### Filtrage Challenges
Le système surveille automatiquement max 5 challenges pour éviter rate limits.

## 🚀 Prochaines Améliorations

### Index Photos [0], [1]
Actuellement les index comme `boost, end-50m0s, 0` ne sont pas résolus.
Il faut implémenter `_resolve_photo_by_index()` pour :
- [0] = Photo avec le plus de votes
- [1] = Deuxième photo par votes
- etc.

### Machine Learning
Les données ANCA collectées peuvent alimenter :
- Prédiction des moments de swap
- Analyse patterns de succès
- Génération automatique de stratégies