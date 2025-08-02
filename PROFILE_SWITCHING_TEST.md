# Test du Changement de Profil

## Fonctionnalités Corrigées

✅ **Bouton Déconnexion** : Remplace l'ancien bouton "Changer Profil"  
✅ **Filtrage WebSocket** : Seuls les logs du profil connecté s'affichent  
✅ **Reconnexion Propre** : Plus de plantage lors du changement de profil  
✅ **Jobs Maintenus** : Les stratégies programmées continuent en arrière-plan  
🔍 **Debug Complet** : Logs détaillés pour diagnostiquer les problèmes

## Comment Tester

### Option 1: Test Manuel

1. **Démarrer le backend** :
   ```bash
   python backend_real.py
   ```

2. **Démarrer le frontend avec debug** :
   ```bash
   cd src/gs
   python gsui_enhanced.py
   ```

3. **Test de changement de profil** :
   - Se connecter avec le profil "bruno"
   - Programmer quelques stratégies pour générer des logs
   - Cliquer sur le bouton rouge "🚪 Déconnexion"
   - **Observer les messages [DEBUG] dans le terminal**
   - Sélectionner le profil "caloune" 
   - Vérifier que l'application ne plante pas
   - Vérifier que les logs ne montrent que les messages de "caloune"

### Option 2: Script de Test Automatisé

```bash
python test_profile_switching.py
```

Ce script lance l'application avec des instructions détaillées.

## Debugging de la "Sortie Violente"

Quand vous testez le changement de profil, surveillez dans le terminal les messages :

```
🚪 [DEBUG] Début logout()
🔌 [DEBUG] Appel disconnect_websocket()
🔌 [DEBUG] Début disconnect_websocket()
🔌 [DEBUG] Flag d'arrêt activé
🔌 [DEBUG] Fermeture WebSocket client
✅ [DEBUG] WebSocket client fermé
🔌 [DEBUG] Attente fin thread WebSocket
✅ [DEBUG] Thread WebSocket terminé
🔌 [DEBUG] Nettoyage références
✅ [DEBUG] disconnect_websocket terminé
👁️ [DEBUG] Masquage fenêtre
📋 [DEBUG] Création dialog ProfileSelectionDialog
📋 [DEBUG] Exécution dialog
```

**Si l'application plante, regardez :**
- À quelle étape [DEBUG] s'arrêtent les messages
- S'il y a des messages d'erreur avec stack trace
- Si le thread WebSocket se termine proprement

## Signaler un Problème

Si vous observez une sortie violente, notez :
1. **Dernier message [DEBUG]** affiché
2. **Messages d'erreur** éventuels 
3. **Profil de départ** et **profil de destination**
4. **Actions effectuées** avant la déconnexion

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