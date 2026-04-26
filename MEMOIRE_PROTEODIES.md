# MÉMOIRE PROJET PROTÉODIES
## Pour Claude Code — Player web de sonification de protéines

---

## 1. CONTEXTE DU PROJET

**Propriétaire :** Bruno (guitariste jazz manouche, ingénieur logiciel, Évreux FR)
**Concept :** Les *protéodies* sont la sonification de séquences d'acides aminés en musique. Chaque acide aminé → une note (hauteur) + une durée (proportionnelle à sa masse moléculaire). Inspiré de la théorie de Joël Sternheimer.

**Règle fondamentale de sonification :**
- Hauteur = position de l'AA dans l'ordre alphabétique (`ACDEFGHIKLMNPQRSTVWY`) projetée sur une gamme musicale
- Durée = proportionnelle à la masse moléculaire en Daltons :
  - ≤ 100 Da → croche (0.5 beat)
  - 101–160 Da → noire (1 beat)
  - ≥ 161 Da → blanche (2 beats)
- Vélocité = proportionnelle à la masse : `vel = 0.45 + (mass-75)/(204-75) * 0.45`
- Référence diapason : La4 = **429.62 Hz** (Diapason de l'eau H₂O, Marc Henry) ou 440 Hz standard

---

## 2. FICHIER PRINCIPAL

**Player HTML autonome :**
```
web-ui/public/proteodies/index.html   ← Player web iPad autonome (Web Audio API)
```

**Accès via serveur web gsgui :**
```
http://localhost:3000/proteodies/   ← depuis le Mac mini
http://192.168.1.18:3000/proteodies/ ← depuis l'iPad (réseau local)
```

---

## 3. ARCHITECTURE DU PLAYER HTML (`web-ui/public/proteodies/index.html`)

### Structure HTML (dans l'ordre)
```
<head>
  CSS complet (dark theme, variables CSS --teal, --bg, etc.)
  CSS modal (.modal-overlay, .modal-box)
  CSS playlist (.pl-item, .pl-badge, .pl-info-btn)
  CSS instruments (.instr-btn)

<body>
  <!-- TRANSPORT STICKY (position:sticky top:0) -->
  4 boutons ronds 60×60px : ▶ ⏸ ■ ⏭
  + affichage nom/statut protéodie en cours

  <h1> titre + sous-titre

  <!-- .now-box (caché par défaut) -->
  Titre + meta de la protéodie en cours

  <!-- .card Séquence en cours -->
  canvas.wave (waveform décorative)
  .seq-wrap (cellules AA qui s'illuminent)
  .prog-wrap / .prog-bar (barre de progression)
  .prog-info (temps écoulé / boucle / temps restant)

  <!-- .card Instrument -->
  .instr-grid 2 colonnes :
    🪈 Flûte andine | 🎤 Voix femmes
    🎵 Voix hommes  | 🎶 Chœur mixte
    ✨ Cristal       | 🔔 Bol tibétain

  <!-- .card Réglages -->
  Sliders : Tempo (25-180 BPM) | Durée (1-30 min) | Reverb
  Select gamme : Mib Lydien / Sol majeur / La mineur / Ab majeur
  Select mode audio : Stéréo / Binaural 🎧 / Isochrone
  Checkbox boucle
  Checkbox diapason 429.62 Hz (COCHÉ PAR DÉFAUT)
  Avertissement battements binauraux/isochroniques

  <!-- .card Playlist -->
  div#playlist (généré par buildPlaylist())
  Boutons Tout cocher / Tout décocher

  <!-- Modal description (remonte depuis le bas) -->
  id="desc-modal" → showDesc(id) / closeModal()

<script>
  const PROTEODIES = [...]   ← tableau des 48 protéodies
  const DESCRIPTIONS = {...} ← descriptions détaillées
  const MASS = {...}          ← masses molaires 20 AA
  const ORD = 'ACDEFGHIKLMNPQRSTVWY'
  const SCALES = {mib, sol, la, ab}
  const CAT_COLORS = {...}

  // Fonctions audio (Web Audio API, pas de samples)
  playFlute / playVoixF / playVoixH / playChoeur / playCristal / playBol

  // Fonctions core
  getA4()        → 429.62 ou 440 Hz selon checkbox
  midiFor(aa)    → note MIDI depuis l'AA
  freqFor(midi)  → fréquence Hz
  massFor(aa)    → masse en Da
  velFor(aa)     → vélocité 0-0.9
  ticksFor(aa)   → durée en beats (0.5, 1, ou 2)

  // Session
  startSession() / endSession() / togglePause() / stopSession() / skipNext()

  // UI
  showSeq(prot) / drawWave(seq) / showDesc(id) / closeModal()
  buildPlaylist() / selectAll(v)
```

---

## 4. STRUCTURE D'UNE ENTRÉE PROTEODIES

```javascript
{
  id:   'piezo1',                              // identifiant unique (snake_case)
  name: 'PIEZO1 — GsMTx4',                    // affiché dans la playlist
  seq:  'GCLEFWWKCNPNDDKCCGPKLKCHAISYKECTK',  // séquence 1-lettre des AA
  cat:  '🧬',                                  // emoji catégorie
  desc: 'Inhibiteur canal mécano-sensible'     // courte description
}
```

Et dans `DESCRIPTIONS[id]` : description longue de 3-5 phrases (mécanisme biochimique, lien avec les bilans de Bruno si applicable).

---

## 5. CATÉGORIES ACTUELLES (56 protéodies)

| Emoji | Catégorie | Nb | IDs principaux |
|---|---|---|---|
| 🧬 | PIEZO1 | 1 | piezo1 |
| 🧠 | Neuro/Mémoire | 6 | tph1, th, dbh, semax, bdnf |
| 🦵 | Genou | 5 | bpc157, col2, pdgf, igf1, bmp7 |
| 😴 | Sommeil | 2 | dsip, oxy |
| 🍽️ | Boulimie | 1 | glp1 |
| ❤️ | Tension | 1 | apelin |
| 💧 | Eau/Pression | 1 | aqp1 |
| 🏔️ | Bolivie/Altitude | 2 | epo, hif |
| 🌵 | Pedro (cactus) | 3 | cry1, aqptip, pepc |
| 🌿 | Plantes | 7 | psk, clv3, systemin, ralf, rubisco, expansin, kin1 |
| 🥒 | Concombre | 7 | pr1, chi, npr1, pdf12, wrky30, flg22, csa |
| 🍅 | Tomates | 8 | t_pr1, t_rcr3, t_pto, t_i3, t_ver, t_syst, t_lox, t_cf9 |
| 😊 | Humeur | 5 | endorphin, ananda, galanin, vip, subp |
| 👁️ | Yeux/Cataracte | 6 | cryaa, cryab, crygd, gpx, lano, sod |
| 🌌 | Conscience | 2 | inmt, 5ht2a |

---

## 6. GAMMES DISPONIBLES

```javascript
SCALES = {
    'mib': [51,53,55,57,58,60,62,63,65,67,69,70,72,74,75,77,79,81,82,84],  // Eb Lydien (défaut)
    'sol': [43,45,47,48,50,52,54,55,57,59,60,62,64,67,69,71,72,74,76,79],  // G majeur (manouche)
    'la':  [45,48,50,52,53,55,57,60,62,65,67,69,72,74,77,79,81,84,86,89],  // La mineur (altitude)
    'ab':  [44,46,48,49,51,53,55,56,58,60,61,63,65,67,68,70,72,73,75,77],  // Ab majeur (sommeil)
}
```

---

## 7. MODES AUDIO (Battements binauraux et isochroniques)

Le player propose **3 modes de génération audio** :

### **Mode 1 : Stéréo** (classique - par défaut)
- Les deux oreilles reçoivent la même fréquence
- Utilise les instruments (Flûte, Voix, Cristal, etc.)
- Fonctionne avec haut-parleurs ou casque

### **Mode 2 : Binaural** 🎧
- Fréquence légèrement différente dans chaque oreille
- Ex: Oreille gauche = freq - (beatFreq/2), Oreille droite = freq + (beatFreq/2)
- Le cerveau perçoit un battement à la fréquence `beatFreq`
- **NÉCESSITE UN CASQUE** (ne fonctionne pas avec haut-parleurs)
- Induit des états de conscience spécifiques selon la fréquence de battement

### **Mode 3 : Isochrone**
- Pulsations régulières du volume (ON/OFF rapide)
- Même fréquence dans les deux oreilles
- Fonctionne avec **haut-parleurs ou casque**
- Plus efficace que binaural selon certaines études
- Utilisé pour méditation, concentration, sommeil

### **Fréquences de battement par catégorie**

```javascript
BEAT_FREQS = {
  '🧬': 10,   // PIEZO1 - Beta bas (concentration)
  '🧠': 14,   // Neuro - Beta (concentration active)
  '🦵': 10,   // Genou - Beta bas
  '😴': 4,    // Sommeil - Theta/Delta (sommeil profond)
  '🍽️': 10,   // Boulimie - Beta bas
  '❤️': 8,    // Tension - Alpha (relaxation)
  '💧': 10,   // Eau - Beta bas
  '🏔️': 12,   // Altitude - Beta
  '🌵': 10,   // Cactus - Beta bas
  '🌿': 10,   // Plantes - Beta bas
  '🥒': 10,   // Concombre - Beta bas
  '🍅': 10,   // Tomate - Beta bas
  '😊': 8,    // Humeur - Alpha (bien-être)
  '👁️': 10,   // Yeux - Beta bas
  '🌌': 6     // Conscience - Theta (états modifiés DMT)
}
```

### **Ondes cérébrales et effets**

| Onde | Fréquence | État de conscience | Catégories |
|------|-----------|-------------------|------------|
| **Delta** | 1-4 Hz | Sommeil profond, régénération | 😴 Sommeil |
| **Theta** | 4-8 Hz | Méditation profonde, créativité, rêves | 🌌 Conscience, 😴 Sommeil |
| **Alpha** | 8-13 Hz | Relaxation, calme, bien-être | ❤️ Tension, 😊 Humeur |
| **Beta** | 13-30 Hz | Concentration, vigilance, cognition | 🧠 Neuro, 🏔️ Altitude |

### **Précautions d'usage**

⚠️ **Avertissement** : Modes Binaural et Isochrone déconseillés en cas d'épilepsie photosensible ou troubles neurologiques.

- **Binaural** : Casque obligatoire
- **Isochrone** : Fonctionne sans casque
- **Volume modéré** : Les battements peuvent être intenses
- **Durée progressive** : Commencer par 5-10 minutes

---

## 8. STRATÉGIE DE MISE À JOUR DU PLAYER HTML

### RÈGLE ABSOLUE : ne jamais patcher incrementalement
Les patches successifs corrompent le fichier. Toujours éditer directement le fichier `web-ui/public/proteodies/index.html`.

### Workflow pour ajouter une protéodie au player :

1. Éditer `web-ui/public/proteodies/index.html`
2. Ajouter l'entrée dans le tableau `PROTEODIES` (id, name, seq, cat, desc)
3. Ajouter la description longue dans l'objet `DESCRIPTIONS`
4. Vérifier que la couleur cat existe dans `CAT_COLORS`
5. Tester dans le navigateur

---

## 9. BILANS NEUROTRANSMETTEURS DE BRUNO (contexte protéodies santé)

**Bilan 2017 :** DOPA=85%, 34DOPAC=14%🔴, HVA=43%🔴, NORADRE=59%🟡, SEROT=54%🟡, 5HIAA=54%
**Bilan 2018 (après Wim Hof) :** DOPA=72%, 34DOPAC=25%🟡, HVA=61%✅, NORADRE=128%🔴, SEROT=40%🔴, 5HIAA=91%✅

**Déficits cibles :**
- SEROT bas → protéodies TPH1 (Tryptophane Hydroxylase), Galanine, β-Endorphine
- 34DOPAC bas → TH (Tyrosine Hydroxylase), Sémax
- NORADRE élevé → DBH en modération, Apelin-13

---

## 10. HISTORIQUE DES ERREURS À ÉVITER

1. **Ne pas patcher le HTML incrementalement avec des regex** → corruption du fichier JS
2. **Toujours éditer directement le fichier HTML** avec les outils Read/Edit
3. **Ne jamais insérer du code JS dans le milieu d'une fonction** → risque de corruption
4. **Vérifier la syntaxe JavaScript** après chaque modification

---

## 11. PISTES D'EXTENSION FUTURES

- Ajouter des protéodies pour d'autres légumes/fruits (poivron, courge...)
- Protéodies de relaxation cardiaque (ANP, BNP)
- Combo "Pedro la nuit" (PEPC + AQP TIP en Ab majeur 28 BPM)
- Export WAV depuis Logic Pro des sessions clés
- Version avec accord de base répété en boucle plutôt que bourdon changeant
- Ajout de la propriété `bpm` par protéodie pour des tempos spécifiques (ex: DSIP = 28 BPM)
- Interface de création de protéodie custom depuis le player (saisie séquence AA)
