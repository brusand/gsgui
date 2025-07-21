# GSGUI Backend API

Backend FastAPI pour l'application GuruShots GUI, extrait et refactorisé du code `gsui.py`.

## 🚀 Quick Start

### Avec Docker (Recommandé)

```bash
# Cloner et aller dans le dossier backend
cd backend/

# Copier le fichier de configuration
cp .env.example .env

# Lancer avec Docker Compose
docker-compose up -d

# L'API sera disponible sur http://localhost:8000
```

### Installation locale

```bash
# Installer les dépendances
pip install -r requirements.txt

# Configurer les variables d'environnement
cp .env.example .env
# Éditer .env avec vos configurations

# Lancer le serveur
python -m uvicorn app.main:app --reload
```

## 📡 API Endpoints

### Documentation automatique
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Endpoints principaux

#### Challenges
- `GET /api/v1/challenges/` - Liste des challenges actifs
- `POST /api/v1/challenges/vote-panel` - Récupérer panel de vote
- `POST /api/v1/challenges/vote` - Soumettre des votes
- `POST /api/v1/challenges/simple-vote` - Vote simple automatique

#### WebSocket temps réel
- `WS /ws/{user_id}` - Connexion WebSocket pour updates temps réel

## 🏗️ Architecture

```
backend/
├── app/
│   ├── api/v1/           # Endpoints REST API
│   ├── core/             # Configuration
│   ├── models/           # Modèles de base de données
│   ├── schemas/          # Schémas Pydantic
│   ├── services/         # Services métier
│   │   ├── gurushots_api.py      # Client API GuruShots
│   │   └── strategy_scheduler.py # Scheduler de stratégies
│   ├── websockets/       # Gestion WebSocket temps réel
│   └── main.py          # Point d'entrée FastAPI
├── tests/               # Tests unitaires
├── Dockerfile          # Image Docker
├── docker-compose.yml  # Stack complète
└── requirements.txt    # Dépendances Python
```

## 🔄 Migration depuis gsui.py

Le backend extrait et refactorise les composants clés de `gsui.py` :

### Services extraits
- **`AsyncFetcher`** → `GuruShotsAPI` - Client API GuruShots
- **Scheduling logic** → `StrategyScheduler` - Gestionnaire de stratégies
- **Turbo algorithms** → `TurboEngine` (TODO)
- **Configuration** → Configuration centralisée

### Modèles de données
- **`GurushotChallenge`** → `Challenge` (SQLAlchemy)
- **Configuration .ini** → Modèles base de données
- **Historique turbo** → `TurboHistory`

### Fonctionnalités temps réel
- **WebSockets** pour updates instantanés
- **Events système** (challenges, votes, stratégies)
- **Notifications push**

## 🛠️ Développement

### Structure des services

#### GuruShotsAPI
```python
api_client = GuruShotsAPI(user_token)
challenges = await api_client.get_challenges()
vote_result = await api_client.execute_simple_vote(url, count)
```

#### Strategy Scheduler
```python
scheduler = StrategyScheduler()
await scheduler.schedule_strategy(
    strategy_id, user_id, user_token,
    challenge_id, challenge_url, end_time, config
)
```

#### WebSocket Events
```python
# Côté backend
await connection_manager.notify_vote_executed(user_id, challenge_id, count, success)

# Côté client
{
  "type": "vote_executed",
  "challenge_id": "12345",
  "vote_count": 10,
  "success": true
}
```

### Tests

```bash
# Lancer les tests
pytest tests/

# Avec couverture
pytest --cov=app tests/
```

### Base de données

```bash
# Migrations avec Alembic (TODO)
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

## 🔧 Configuration

Principales variables d'environnement dans `.env`:

- `DATABASE_URL` - URL PostgreSQL
- `REDIS_URL` - URL Redis
- `SECRET_KEY` - Clé de chiffrement
- `GURUSHOTS_API_BASE` - Base URL API GuruShots
- `DEBUG` - Mode debug

## 📊 Monitoring

### Logs
Les logs sont configurés avec le module `logging` standard Python.

### Métriques
- Connexions WebSocket actives
- Requêtes API par endpoint
- Stratégies en cours d'exécution

### Health Check
`GET /health` retourne l'état des services (API, DB, Redis).

## 🚦 Prochaines étapes

### Phase actuelle ✅
- [x] Structure backend FastAPI
- [x] Extraction logique gsui.py
- [x] API endpoints challenges
- [x] WebSocket temps réel
- [x] Strategy Scheduler

### Phase suivante 🔄
- [ ] Algorithmes Turbo
- [ ] Base de données PostgreSQL
- [ ] Tests unitaires
- [ ] Client desktop (migration gsui.py)
- [ ] Client mobile Flutter

### À venir 📋
- [ ] Authentification JWT
- [ ] Rate limiting
- [ ] Monitoring avancé
- [ ] Déploiement production