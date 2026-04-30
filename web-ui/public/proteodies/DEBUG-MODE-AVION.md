# 🛩️ Debug Mode Avion - Procédure de Réparation

Le mode avion ne fonctionne plus ? Voici comment réparer le cache.

## 🔍 Diagnostic Rapide

### Sur iPad - Vérifier le Service Worker

1. **Ouvre Safari sur l'iPad**
2. Va sur `http://[IP-MAC-MINI]:3000/proteodies/`
3. **Ouvre la Console Web** :
   - Connecte l'iPad au Mac via USB
   - Sur le Mac : Safari → Développement → [Nom iPad] → proteodies
4. **Regarde les logs** :
   - `[App] ✅ Service Worker enregistré` → ✅ Bon signe
   - `[App] 💾 Caches disponibles: ["proteodies-v7-offline-fix"]` → ✅ Cache présent
   - `[SW] ✅ Cache hit` → ✅ Cache fonctionne

### Vérifier sans console

1. Ouvre l'app avec connexion
2. Attends 10 secondes
3. Regarde en bas : nombre de protéodies doit être **64**
4. Ferme l'app
5. Active le mode avion
6. Relance l'app → Doit fonctionner

## 🔧 Solution 1 : Réinstallation Propre

**Cette solution fonctionne dans 95% des cas**

### Étapes :

1. **Supprime l'app de l'écran d'accueil**
   - Maintiens l'icône 🧬
   - Touche "Supprimer"

2. **Vide le cache Safari**
   - Réglages → Safari
   - Effacer historique et données de sites web
   - Confirme

3. **Redémarre l'iPad**
   - Tiens Power + Volume Down
   - Éteins complètement
   - Rallume

4. **Réinstalle l'app**
   - Ouvre Safari
   - Va sur `http://[IP]:3000/proteodies/`
   - **Attends 30 secondes** (important !)
   - Partage → Sur l'écran d'accueil → Ajouter

5. **Premier lancement**
   - Ouvre l'app depuis l'icône (AVEC connexion)
   - **Attends 20 secondes**
   - Fais défiler jusqu'en bas
   - Vérifie : **64 protéodies affichées**
   - Ferme l'app

6. **Test mode avion**
   - Active le mode avion ✈️
   - Ouvre l'app
   - **Doit fonctionner** !

## 🔧 Solution 2 : Force le Cache Manuellement

Si la solution 1 ne fonctionne pas :

1. **Sur le Mac Mini**, vérifie que le serveur tourne :
   ```bash
   cd /Volumes/SSD/devs/gsgui
   ./start-webui.sh
   ```

2. **Sur iPad**, ouvre Safari (pas l'app)

3. **Va sur** : `http://[IP]:3000/proteodies/index.html`
   - URL complète avec `index.html` à la fin

4. **Attends que ça charge complètement** (30 secondes)

5. **Force le rechargement** :
   - Tire la page vers le bas
   - Recharge 3 fois de suite

6. **Ferme Safari**

7. **Ouvre l'app depuis l'icône** (AVEC connexion encore)

8. **Attends 20 secondes**

9. **Teste en mode avion**

## 🔧 Solution 3 : Debug avec Console

Si rien ne fonctionne, active les logs :

1. **Connecte l'iPad au Mac via USB**

2. **Sur le Mac** :
   - Safari → Préférences → Avancées
   - Coche "Afficher le menu Développement"

3. **Sur l'iPad**, ouvre l'app

4. **Sur le Mac** :
   - Safari → Développement → [Nom iPad] → [proteodies]
   - La console s'ouvre

5. **Recharge l'app sur iPad**

6. **Cherche dans les logs** :
   - ✅ `[SW] ✅ Cache hit` → Le cache fonctionne
   - ❌ `[SW] ⚠️ Cache miss` → Le cache ne contient pas la page
   - 🛩️ `[SW] 🛩️ Fetch failed (mode avion?)` → Mode avion détecté

7. **Si tu vois plein de "Cache miss"** :
   - Le cache n'est pas rempli
   - Retourne à la Solution 1

8. **Si tu vois "Service Worker enregistré"** mais pas de cache :
   - Le SW est installé mais le cache est vide
   - Force un rechargement : CMD+R
   - Attends 20 secondes
   - Recharge encore

## 🔧 Solution 4 : Version Simplifiée (Fallback)

Si vraiment rien ne fonctionne, il y a un problème de Service Worker.

**Diagnostic** :
```bash
# Sur le Mac, vérifie que le fichier sw.js existe
ls -la /Volumes/SSD/devs/gsgui/web-ui/public/proteodies/sw.js
```

**Vérifie la version du cache** :
- Ouvre `/Volumes/SSD/devs/gsgui/web-ui/public/proteodies/sw.js`
- Ligne 2 doit contenir : `const CACHE_NAME = 'proteodies-v7-offline-fix';`
- Si c'est une autre version, c'est normal (cache pas encore mis à jour)

**Force la mise à jour** :
1. Sur iPad, supprime l'app
2. Sur iPad, dans Safari :
   - Réglages → Safari → Avancées → Données de sites web
   - Cherche "proteodies"
   - Supprime tout
3. Réinstalle l'app

## 📊 Checklist Complète

Avant de déclarer que "ça ne marche pas", vérifie :

- [ ] Le serveur est lancé sur le Mac (`./start-webui.sh`)
- [ ] L'iPad et le Mac sont sur le même réseau
- [ ] L'app a été ouverte AU MOINS UNE FOIS avec connexion
- [ ] On a attendu au moins 20 secondes lors du premier lancement
- [ ] Les 64 protéodies sont visibles (pas 56 ou 59)
- [ ] L'app a été fermée complètement avant d'activer le mode avion
- [ ] Le mode avion est bien activé (pas juste WiFi off)

## 🎯 Test de Validation

**Pour confirmer que le mode avion fonctionne** :

1. **Avec connexion** :
   - Ouvre l'app
   - Vérifie : 64 protéodies + catégorie 💚 Mianne visible
   - Vérifie : Timer affiche "0:00 / 10:00"
   - Vérifie : Bouton boucle ∞ présent
   - Ferme l'app

2. **Active le mode avion** ✈️

3. **Ouvre l'app**
   - Doit se lancer instantanément
   - Toutes les 64 protéodies présentes
   - Tout fonctionne exactement pareil

4. **Lance une session** :
   - Coche quelques protéodies
   - Appuie sur Play ▶️
   - Doit jouer normalement
   - Le bol tibétain 🔔 doit sonner

5. **Si tout ça fonctionne** → ✅ Mode avion opérationnel !

## 🆘 Dernière Solution : Reset Total

Si VRAIMENT rien ne fonctionne :

1. Sur Mac :
   ```bash
   cd /Volumes/SSD/devs/gsgui
   ./stop-webui.sh
   ./start-webui.sh
   ```

2. Sur iPad :
   - Supprime l'app
   - Réglages → Safari → Effacer tout
   - Réglages → Général → Stockage iPad → Safari → Supprimer
   - Redémarre l'iPad
   - Réinstalle l'app
   - Attends 30 secondes au premier lancement

Ça DOIT fonctionner maintenant !

## 📞 Contact

Si après tout ça, le mode avion ne fonctionne toujours pas, il y a probablement un problème réseau ou de certificat SSL sur le réseau local.

Version du cache actuelle : **proteodies-v7-offline-fix**
Date : 30 avril 2026
