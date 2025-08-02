# Test du Changement de Profil

## Fonctionnalités Corrigées

✅ **Bouton Déconnexion** : Remplace l'ancien bouton "Changer Profil"  
✅ **Filtrage WebSocket** : Seuls les logs du profil connecté s'affichent  
✅ **Reconnexion Propre** : Plus de plantage lors du changement de profil  
✅ **Jobs Maintenus** : Les stratégies programmées continuent en arrière-plan  

## Comment Tester

1. **Démarrer le backend** :
   ```bash
   python backend_real.py
   ```

2. **Démarrer le frontend** :
   ```bash
   cd src/gs
   python gsui_enhanced.py
   ```

3. **Test de changement de profil** :
   - Se connecter avec le profil "bruno"
   - Programmer quelques stratégies pour générer des logs
   - Cliquer sur le bouton rouge "🚪 Déconnexion"
   - Sélectionner le profil "caloune" 
   - Vérifier que l'application ne plante pas
   - Vérifier que les logs ne montrent que les messages de "caloune"

4. **Test de filtrage** :
   - Garder le backend actif avec des stratégies pour les deux profils
   - Basculer entre "bruno" et "caloune"  
   - Vérifier que chaque profil ne voit que ses propres logs

## Corrections Apportées

- **Gestion WebSocket** : Thread proprement fermé avec `join(timeout=2.0)`
- **Flag d'arrêt** : `websocket_should_stop` pour éviter les conflits
- **Erreurs gérées** : Try-catch dans `logout()` pour éviter les crashes
- **Délai de reconnexion** : 1 seconde de délai pour stabiliser la connexion
- **Filtrage profil** : Messages WebSocket filtrés par `profile_id`

## Backend Continue

Les jobs programmés sur le backend continuent à s'exécuter même quand :
- Le frontend est fermé
- On change de profil  
- On se déconnecte temporairement

La programmation des stratégies est indépendante du frontend connecté.