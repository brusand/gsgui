# 🛩️ Mode Avion - Guide Complet

Le Proteodies Player fonctionne **100% hors ligne** en mode avion sur iPad. Voici comment procéder :

## ✅ Préparation (une seule fois, AVEC connexion)

### 1. Installer l'app sur l'écran d'accueil
1. Sur iPad, ouvre **Safari** (obligatoire)
2. Va sur `http://[IP-MAC-MINI]:3000/proteodies/`
3. Attends que la page charge complètement (5-10 secondes)
4. Touche le bouton **Partage** 📤
5. Touche **"Sur l'écran d'accueil"**
6. Touche **"Ajouter"**

### 2. Vérifier que tout est en cache
1. Ouvre l'app depuis l'icône sur l'écran d'accueil
2. Attends 5-10 secondes que tout se charge
3. Fais défiler pour voir les 64 protéodies
4. Vérifie que le bol tibétain 🔔 est sélectionné
5. Ferme l'app (swipe up)

### 3. Test hors ligne
1. Active le **mode avion** ✈️ sur l'iPad
   - Réglages → Mode Avion → ON
2. Touche l'icône **Protéodies** 🧬 sur l'écran d'accueil
3. L'app devrait se lancer **instantanément** et fonctionner normalement

## 🎵 Utilisation en mode avion

**Tout fonctionne normalement :**
- ✅ Les 64 protéodies (y compris Mianne 💚)
- ✅ Tous les instruments (Bol tibétain par défaut)
- ✅ Modes audio (Stéréo, Binaural, Isochrone)
- ✅ Minuterie décompte
- ✅ Filtres par catégorie
- ✅ Descriptions complètes (bouton ⓘ)
- ✅ Diapason de l'eau H2O

**Aucune connexion nécessaire !**

## 🔄 Mise à jour (quand tu ajoutes de nouvelles protéodies)

1. Désactive le mode avion
2. Connecte-toi au réseau local
3. Ouvre l'app
4. Tire vers le bas pour recharger
5. Attends quelques secondes
6. Réactive le mode avion
7. Teste → tout fonctionne !

## 🛠️ Dépannage

### L'app ne se lance pas en mode avion
**Solution :**
1. Désactive le mode avion
2. Ouvre Safari et va sur l'URL d'origine
3. Laisse la page chargée pendant 30 secondes
4. Ferme Safari
5. Ouvre l'app depuis l'écran d'accueil (AVEC connexion)
6. Attends 10 secondes
7. Ferme l'app
8. Active le mode avion
9. Relance l'app → devrait fonctionner

### L'app affiche une page blanche en mode avion
**Cause :** Le Service Worker n'est pas installé
**Solution :**
1. Désactive le mode avion
2. Supprime l'app de l'écran d'accueil (maintenir l'icône → Supprimer)
3. Dans Safari : Réglages → Safari → Effacer historique et données
4. Recommence l'installation depuis l'étape 1

### L'app se lance mais n'a que les anciennes protéodies
**Cause :** Ancien cache actif
**Solution :**
1. Le cache se mettra à jour automatiquement la prochaine fois que tu ouvres l'app AVEC connexion
2. Version du cache actuel : **proteodies-v2-64p** (64 protéodies)
3. Ouvre l'app avec connexion, attends 10 secondes, recharge une fois

## 📊 Technique

**Service Worker :** Cache-First Strategy
- Cache `index.html`, `manifest.json`
- Tout le CSS, JavaScript et données sont inline dans le HTML
- Taille totale : ~75 Ko compressés
- Fonctionne même si le serveur est éteint

**Stockage iPad :**
- Cache persistent dans Safari
- Environ 500 Ko total
- Pas de limite de temps

## 🎯 Utilisation typique

**À la maison (avec Mac Mini allumé) :**
- Connexion normale
- Mises à jour automatiques

**En voyage / en vol ✈️ :**
- Mode avion activé
- Lancement depuis l'icône
- Fonctionne exactement pareil
- Batteries illimitées de protéodies !

**En randonnée / bivouac 🏕️ :**
- Aucun réseau nécessaire
- iPad en mode avion pour économiser la batterie
- Player Proteodies actif
- Parfait pour méditation / sommeil en nature
