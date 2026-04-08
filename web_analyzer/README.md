# 🌐 GuruShots Web Analyzer

Application web révolutionnaire pour l'analyse interactive des stratégies GuruShots par entries.

## 🎯 Fonctionnalités

### ✨ Innovation Clé
- **Visualisation par Entries** : Affichage révolutionnaire avec 4 lignes (Entry_0, Entry_1, Entry_2, Entry_3)
- **Couleurs Photo ID** : Chaque photo obtient une couleur unique pour tracker les swaps
- **Temps Lisible** : Format heures:minutes au lieu des valeurs incompréhensibles
- **Détection Swaps** : Visualisation des changements de photos via couleurs

### 🎨 Interface Web
- Design moderne et responsive
- Sélection interactive des challenges et membres
- Contrôles entry avec checkboxes colorées
- Génération d'analyse en temps réel
- Compatible mobile et desktop

## 🚀 Installation et Démarrage

### Prérequis
```bash
pip install -r requirements.txt
```

### Démarrage Rapide
```bash
# Démarrer l'application web
./start_web_analyzer.sh start

# Ouvrir dans le navigateur
./start_web_analyzer.sh open
```

### Commandes Disponibles
```bash
./start_web_analyzer.sh start      # Démarrer le serveur
./start_web_analyzer.sh stop       # Arrêter le serveur  
./start_web_analyzer.sh restart    # Redémarrer
./start_web_analyzer.sh status     # Vérifier le statut
./start_web_analyzer.sh logs       # Afficher les logs
./start_web_analyzer.sh open       # Ouvrir le navigateur
```

## 🌐 Interface Web

### URL d'accès
- Local: http://localhost:5001
- Réseau: http://[VOTRE_IP]:5001

### Utilisation
1. **Sélectionner un Challenge** : Liste des challenges avec nombre de participants
2. **Choisir un Membre** : Top membres avec statistiques (rang, votes, apparitions)
3. **Configurer l'Affichage** : Cocher/décocher les entries à visualiser
4. **Analyser** : Cliquer sur "Analyser" pour générer le graphique

### Contrôles Interactifs
- **Entry 0** (rouge) : Première position
- **Entry 1** (vert) : Deuxième position  
- **Entry 2** (bleu) : Troisième position
- **Entry 3** (orange) : Quatrième position

## 📊 API Endpoints

### GET /api/challenges
Récupère la liste des challenges disponibles
```json
{
  "success": true,
  "challenges": [
    {
      "id": "105594",
      "title": "By the Waterside",
      "status": "ongoing",
      "snapshots": 1543,
      "members": 23
    }
  ]
}
```

### GET /api/members/{challenge_id}
Récupère les top membres d'un challenge
```json
{
  "success": true,
  "members": [
    {
      "id": "member123",
      "name": "Anca the vampire",
      "appearances": 45,
      "vote_range": [1200, 5670],
      "rank_range": [12, 89],
      "vote_gain": 4470
    }
  ]
}
```

### POST /api/analyze
Génère l'analyse graphique
```json
{
  "challenge_id": "105594",
  "member_id": "member123", 
  "visible_entries": ["Entry_0", "Entry_1", "Entry_2"]
}
```

Réponse:
```json
{
  "success": true,
  "image": "data:image/png;base64,..."
}
```

## 🎨 Architecture Technique

### Backend Flask
- **PhotoColorManager** : Gestion des couleurs uniques par photo ID
- **WebGuruShotsAnalyzer** : Logique d'analyse et génération graphique
- **Base de données** : SQLite avec structure optimisée
- **Matplotlib Web** : Backend non-interactif pour génération PNG

### Frontend JavaScript
- **GuruShotsAnalyzer Class** : Gestion de l'interface
- **API Integration** : Calls AJAX vers les endpoints Flask
- **Responsive Design** : CSS Grid et Flexbox
- **State Management** : Synchronisation challenges/membres/entries

### Visualisation Innovation
```python
# Couleurs photo ID avec distribution golden ratio
hue = (color_index * 137.508) % 360
rgb = colorsys.hsv_to_rgb(hue/360, saturation, value)

# Temps formaté lisible  
if hours > 0:
    label = f"{hours}h{minutes:02d}"
else:
    label = f"{minutes}min"

# Segments colorés pour tracker les swaps
for i in range(len(entry_times) - 1):
    color = color_manager.get_color_for_photo(photo_id)
    ax.plot([x1, x2], [y1, y2], color=color, linewidth=3)
```

## 🗄️ Base de Données

### Structure Optimisée
- **snapshots** : Collections temporelles
- **participant_snapshots** : Données des participants
- **photo_snapshots** : Détail des photos par entry
- **members** : Informations des membres

### Requêtes Clés
```sql
-- Récupération données par entry avec positions
SELECT s.timestamp, ps.total_votes, ph.photo_id, ph.votes,
       ROW_NUMBER() OVER (PARTITION BY s.timestamp ORDER BY ph.votes DESC) - 1 as entry_position
FROM snapshots s
JOIN participant_snapshots ps ON s.id = ps.snapshot_id  
JOIN photo_snapshots ph ON ps.id = ph.participant_snapshot_id
WHERE s.challenge_id = ? AND ps.member_id = ?
ORDER BY s.timestamp, ph.votes DESC
```

## 📈 Avantages Révolutionnaires

### vs Ancienne Interface
- ❌ **Avant** : Interfaces "inexploitables", éléments qui se chevauchent
- ✅ **Maintenant** : Interface web moderne, responsive, utilisable

### vs Temps Incompréhensible  
- ❌ **Avant** : "1000 à -1000" incompréhensible
- ✅ **Maintenant** : "2h30", "45min", "10s" lisibles

### vs Swaps Invisibles
- ❌ **Avant** : "je ne vois pas les swaps sur les graphiques"
- ✅ **Maintenant** : Couleurs photo ID révèlent tous les swaps

## 🤝 Partage avec Amis

### Accès Réseau
1. Démarrer le serveur : `./start_web_analyzer.sh start`
2. Trouver votre IP : `ifconfig` ou `ipconfig`
3. Partager l'URL : `http://[VOTRE_IP]:5001`

### Exemple
```bash
# Votre IP locale
ip addr show | grep "inet 192"
# Partager: http://192.168.1.100:5001
```

## 🔧 Configuration Avancée

### Port Personnalisé
Modifier dans `app.py`:
```python
app.run(debug=True, host='0.0.0.0', port=VOTRE_PORT)
```

### Base de Données
Par défaut cherche dans:
- `/Volumes/SSD/Data/GuruShots/gurushots_enhanced.db`
- `./gurushots_enhanced.db`

### Production
Pour production, utiliser un serveur WSGI:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5001 app:app
```

## 🎉 Révolution Accomplie

Cette application web révolutionne l'analyse GuruShots en permettant:
- 🌐 **Partage** avec vos amis via interface web
- 🎨 **Visualisation** révolutionnaire par couleurs photo ID  
- ⏰ **Temps** enfin lisible en heures:minutes
- 🔄 **Swaps** visibles via changements couleur
- 📱 **Mobile** responsive design
- ⚡ **Temps réel** analyse interactive

*Fini les interfaces "inexploitables" et les timestamps incompréhensibles !*