# Installation sur iPad - Mode Hors Ligne

Le Protéodies Player est maintenant une **Progressive Web App (PWA)** qui fonctionne **100% hors ligne** sur iPad.

## 📱 Installation (une seule fois)

### Étape 1 : Première visite
1. Sur l'iPad, ouvrez **Safari** (obligatoire, pas Chrome)
2. Allez sur : `http://192.168.1.18:3000/proteodies/`
3. Attendez quelques secondes que la page se charge complètement

### Étape 2 : Ajouter à l'écran d'accueil
1. Touchez le bouton **Partage** (carré avec flèche vers le haut)
2. Faites défiler et touchez **"Sur l'écran d'accueil"**
3. Modifiez le nom si vous voulez (par défaut : "Protéodies")
4. Touchez **"Ajouter"**

### Étape 3 : C'est fini !
- Une icône 🧬 **"Protéodies"** apparaît sur l'écran d'accueil
- Touchez l'icône pour lancer l'app
- **Fonctionne hors ligne** : pas besoin du Mac mini ni de connexion réseau
- **Plein écran** : pas de barre Safari, comme une vraie app

## 🔄 Mise à jour

Si vous ajoutez de nouvelles protéodies plus tard :
1. Ouvrez l'app sur l'iPad (même hors ligne)
2. Reconnectez-vous au réseau local une fois
3. Rechargez la page (tirer vers le bas)
4. La nouvelle version se télécharge automatiquement
5. Vous pouvez à nouveau utiliser hors ligne

## 🛠️ Dépannage

**L'app ne s'installe pas ?**
- Utilisez **Safari**, pas Chrome
- Vérifiez que JavaScript est activé dans Safari
- Essayez de vider le cache : Réglages → Safari → Effacer historique et données

**L'app ne fonctionne pas hors ligne ?**
- Ouvrez l'app une première fois avec connexion
- Attendez quelques secondes que le cache se remplisse
- Vérifiez dans la console (Développement Web) que le Service Worker est enregistré

**Icône blanche au lieu de 🧬 ?**
- Normal sur certaines versions iOS
- L'app fonctionne quand même parfaitement

## 📊 Stockage

L'app utilise environ **500 Ko** de cache sur l'iPad :
- Fichier HTML (complet avec CSS/JS inline)
- Service Worker
- Manifest

Pas de fichiers externes, pas de dépendances, **100% autonome**.
