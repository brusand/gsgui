# 🎯 GSGUI Desktop Simple - Guide d'Utilisation

## ✅ Démarrage

### **Méthode 1: Script Bash (Simple)**
```bash
cd ~/gsgui
./run_simple.sh
```

### **Méthode 2: Script Python (Robuste)**
```bash
cd ~/gsgui
python run_gsgui.py
```

### **Méthode 3: Manuel (Debug)**
```bash
# Terminal 1 - Backend
cd ~/gsgui
python backend_simple.py

# Terminal 2 - Interface
cd ~/gsgui/src/gs
python gsui_simple.py
```

---

## 🎨 Interface

### **Démarrage Automatique**
- Les challenges se chargent **automatiquement** au démarrage
- Format unifié : `⚪ Titre... | 🗳️Votes | 🏆Rang | ⏰Temps | 📅Stratégie`

### **6 Boutons Essentiels**
1. **🔄 Refresh** - Recharge les challenges 
2. **✅ All** - Sélectionne tout
3. **❌ None** - Efface sélection
4. **⚡ Fill** - Vote immédiat 80 votes
5. **📅 Stratégie** - Programme avec nettoyage auto
6. **🚀 Turbo** - Active turbo système

---

## 🔧 Fonctionnalité Critique

### **Nettoyage Automatique des Stratégies** ✅
Quand vous appliquez une **nouvelle stratégie** :
1. Les stratégies existantes sont **automatiquement annulées**
2. La nouvelle stratégie est **programmée**
3. **1 seule stratégie active** par challenge

**Validé et testé** - Fonctionne parfaitement !

---

## 📋 Workflow

1. **Démarrer** avec un des scripts
2. **Interface s'ouvre** avec 3 challenges chargés automatiquement
3. **Sélectionner** challenges (clic multiple)
4. **Utiliser les 6 boutons** selon besoin
5. **Fermer** l'interface pour arrêter

---

## 🎉 Système 100% Fonctionnel

✅ Backend API stable sur port 8001  
✅ Interface esthétique dark theme  
✅ 6 boutons uniquement comme demandé  
✅ Colonnes identiques aux 2 interfaces  
✅ Auto-refresh au démarrage  
✅ Nettoyage automatique stratégies  
✅ Scripts de démarrage qui marchent  

**GSGUI Desktop Simple est prêt !** 🚀