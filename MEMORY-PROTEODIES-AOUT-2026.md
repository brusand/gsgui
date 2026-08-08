# 🧬 MÉMOIRE - Protéodies Août 2026

**Date:** 2026-08-08
**Branche:** `gsgui-v2-protéodies`
**Commit:** `e39da99` - "Add Proteodies V2 with audio samples and simplified interface"
**Total protéodies:** 185 organisées en 34 packs
**Versions:**
- **V1** (`/proteodies/`) : Interface classique 185 protéodies + bouton audio 🔊
- **V2** (`/proteodies2/`) : Interface simplifiée par packs avec samples audio pré-générés

## 🎯 CONTEXTE

Développement du système de **validation audio** pour vérifier le workflow Logic Pro + Vienna Synchron Player, et ajout de nouveaux packs thérapeutiques.

## 🚀 RÉALISATIONS MAJEURES

### 1. **Pack Arthrose (8 protéodies) - Nouveau**

**Catégorie:** 🦴 Arthrose
**Config:**
- Fréquence isochrone: **7 Hz** (anti-inflammatoire + régénération)
- Gamme par défaut: **Mib Lydien** (calmant pour douleur)
- Mode audio: **Isochrone** (délivrance thérapeutique constante)
- Couleur: **#CD853F** (beige/tan pour os/articulations)
- Diapason: **h3O2 (429.62 Hz)** par défaut

**Protéodies:**
1. **COL2A1** - Collagène II (structure principale cartilage articulaire)
2. **ACAN** - Aggrécane (protéoglycane, rétention eau dans cartilage)
3. **SOX9** - Facteur transcription (régénération cartilagineuse)
4. **PRG4** - Lubricine (lubrifiant naturel liquide synovial)
5. **COMP** - Protéine oligomérique matrice cartilagineuse
6. **IL-10** - Interleukine-10 (puissant anti-inflammatoire articulaire)
7. **TGF-β1** - TGF-beta 1 (stimule production matrice cartilagineuse)
8. **FMOD** - Fibromoduline (régule assemblage fibrilles collagène)

**Cibles thérapeutiques:** Hallux valgus (gros orteil), articulations doigts/pouce, arthrose cervicale

### 2. **Pack Peau Sèche - Ajout TIP1;1**

**Protéodie ajoutée:**
- **TIP1;1** - Aquaporine vacuolaire végétale (transfert d'eau phyto)
- Séquence: `CFNPAVTLGAHINPAV` (16 acides aminés)
- Diapason: **h3O2 (429.62 Hz)** déjà configuré par défaut

### 3. **Export MIDI avec choix de durée**

**Fonctionnalité:** Dialog permettant de choisir entre:
- **1 boucle simple** (~10 secondes) → Test rapide workflow Logic Pro
- **Durée personnalisée** (10, 20, 30... 120 minutes) → Export final prêt à l'emploi

**Implémentation:**
- Fonction `exportMIDITemplate()` modifiée (index.html)
- Fonction `generateMIDI()` avec support répétitions
- Calcul automatique répétitions pour atteindre durée cible
- Format nom fichier: `{proteodie}_{duree}min.mid` ou `{proteodie}.mid`

**Dialog UX amélioré:**
```
⏱️ Durée de l'export MIDI

Quelle durée exporter ?

🔁 OK = Durée personnalisée (avec répétitions)
   → Export final prêt à l'emploi (10, 20, 30 min...)

⚡ ANNULER = 1 boucle simple (~10 secondes)
   → Test rapide du workflow Logic Pro
```

## 🔬 OUTILS DE VALIDATION AUDIO

### 1. **analyze_audio.py** - Analyse générale
**Capacités:**
- FFT (Fast Fourier Transform) - Spectre de fréquences
- Détection diapason (440 Hz vs 429.62 Hz h3O2)
- Détection LFO/isochrone (4-14 Hz range)
- Calcul RMS (Root Mean Square) - niveau signal moyen
- Calcul Crest Factor (ratio peak/RMS) - détecte compression
- Génération spectrogrammes (visualisation temps-fréquence)

**Usage:**
```bash
python analyze_audio.py fichier.wav
```

### 2. **analyze_lfo_detailed.py** - Analyse LFO détaillée
**Capacités:**
- Extraction enveloppe amplitude via **Transformée de Hilbert**
- FFT de l'enveloppe pour détecter modulations
- Focus sur plage **Delta (3-5 Hz)** pour DSIP sommeil
- Détection multi-fréquences LFO
- Visualisations avec zoom Delta range

**Usage:**
```bash
python analyze_lfo_detailed.py fichier.wav
```

### 3. **detect_notes_timing.py** - Détection notes et timing
**Capacités:**
- Détection pitch avec **algorithme YIN**
- Groupement détections consécutives en notes
- Calcul durées notes en beats
- Comparaison avec séquence attendue
- Génération timeline visualisation

**Usage:**
```bash
python detect_notes_timing.py fichier.wav "WAGGDASGE" 65
```

### 4. **generate_dsip_midi.py** - Générateur MIDI DSIP
**Capacités:**
- Génère MIDI pour séquence DSIP: `WAGGDASGE`
- Durées spéciales: W et E sur 2 beats, autres sur 1 beat
- BPM: 65, Gamme: Mib Lydien
- Support répétitions pour durée cible
- Format MIDI 0 (single track)

**Usage:**
```bash
python generate_dsip_midi.py [minutes]
```

### 5. **generate_dsip_20min.py** - MIDI 20 minutes DSIP
Génère spécifiquement un fichier 20 minutes pour DSIP avec tous paramètres validés.

## 🎼 WORKFLOW DSIP VALIDÉ

### Configuration Vienna Synchron Player
- **Instrument:** Celestial Strings (couvre tout spectre MIDI)
- **Master Tune:** **-24 cents** (440 Hz → 429.62 Hz h3O2)
- **Vibrato:** **DÉSACTIVÉ** (interférait avec LFO)
- **Velocity curve:** Linéaire

### Configuration Logic Pro
- **Effet Tremolo:** **3.91 Hz** (ondes Delta pour sommeil profond)
- **Tremolo depth:** ~50-70%
- **Compression/Limiter:** **AUCUN** (détruit dynamic range)
- **Export:** WAV 44.1 kHz 16-bit ou supérieur

### Paramètres audio validés
- **Diapason h3O2:** 429.62 Hz (Master Tune -24 cents)
- **LFO cible:** 3.91 Hz ± 0.15 Hz (plage Delta 3.5-4.5 Hz)
- **RMS cible:** -12 à -18 dB
- **Crest Factor cible:** 6-8 (indique bon dynamic range)
- **Pas de compression:** Signal naturel préservé

### Problèmes résolus durant validation

**Problème 1: LFO 7.58 Hz au lieu de 3.91 Hz**
- **Cause:** Vibrato automatique Vienna Synchron (~7.5 Hz) + Tremolo 3.91 Hz = double modulation
- **Solution:** Désactiver vibrato dans Vienna Synchron settings
- **Validation:** LFO final 3.76-4.04 Hz ✅

**Problème 2: Signal compressé/détruit**
- **Symptômes:** RMS -3.51 dB (devrait être ~-16 dB), Crest Factor 1.50 (devrait être 6-8)
- **Cause:** Compressor/Limiter activé dans Logic Pro
- **Solution:** Supprimer tous compresseurs/limiters de track et master
- **Validation:** RMS -15.8 dB, Crest Factor 7.2 ✅

**Problème 3: Diapason instable (440 Hz ↔ 429.62 Hz)**
- **Cause:** Master Tune Vienna Synchron réinitialisé entre sessions
- **Solution:** Vérifier Master Tune = -24 cents avant chaque export
- **Validation:** Diapason stable h3O2 429.62 Hz ✅

## 📊 FICHIERS AUDIO TESTS ANALYSÉS

### Séquence d'itération validation DSIP
1. **sommeil_1m.wav** - Premier test, LFO 7.58 Hz (vibrato+tremolo)
2. **sommeil_1m_2.wav** - Signal détruit par compression
3. **sommeil_1m_3.wav** - Après suppression compression
4. **sommeil_1m_4.wav** - Après désactivation vibrato Vienna
5. **sommeil_20m_extract.wav** - Export final 20 min validé ✅

### Résultats finaux validés
- **LFO détecté:** 3.76-4.04 Hz (cible 3.91 Hz) ✅
- **Diapason:** 429.62 Hz h3O2 ✅
- **RMS:** -15.8 dB ✅
- **Crest Factor:** 7.2 ✅
- **Durée boucle DSIP:** ~10.5 secondes (9 aa)
- **Répétitions 20 min:** ~114 boucles

## 🛠️ CONFIGURATION TECHNIQUE

### Fichiers modifiés
- **`web-ui/public/proteodies/index.html`**
  - Ligne 522: Ajout couleur 🦴 dans CAT_COLORS
  - Ligne 529: Ajout nom FR 'Arthrose' dans CAT_NAMES_FR
  - Ligne 536: Ajout nom EN 'Arthritis' dans CAT_NAMES_EN
  - Ligne 638: Ajout beat freq 7 Hz pour 🦴
  - Ligne 643: Ajout mode isochrone pour 🦴
  - Ligne 647: Ajout gamme Mib pour 🦴
  - Lignes 426-434: Ajout 8 protéodies arthrose
  - Ligne 543,586: Mise à jour count 167 protéodies
  - Fonction `exportMIDITemplate()`: Dialog choix durée
  - Fonction `generateMIDI()`: Support répétitions

### Scripts Python ajoutés
- `analyze_audio.py` (231 lignes)
- `analyze_lfo_detailed.py` (198 lignes)
- `detect_notes_timing.py` (187 lignes)
- `generate_dsip_midi.py` (145 lignes)
- `generate_dsip_20min.py` (98 lignes)

### Dépendances Python requises
```bash
python3 -m venv venv
source venv/bin/activate
pip install numpy scipy matplotlib
```

## 🎵 CONCEPTS CLÉS

### Diapasons
- **Standard (440 Hz):** Diapason concert international
- **Verdi (432 Hz):** Diapason historique/naturel
- **h3O2 (429.62 Hz):** Fréquence résonance eau (Marc Henry)

### Modes audio protéodies
- **Stéréo:** Son classique sans modulation
- **Binaural:** Fréquences différentes G/D (casque requis), crée battements cérébraux
- **Isochrone:** Modulation amplitude à fréquence fixe (pulsations audibles)

### Fréquences thérapeutiques (LFO/Isochrone)
- **Delta (3-5 Hz):** Sommeil profond, régénération
- **Theta (4-8 Hz):** Méditation, créativité
- **Alpha (8-12 Hz):** Relaxation, cohérence
- **Beta (12-30 Hz):** Concentration, vigilance

### Gammes Lydiennes (Jean-Luc Borla)
- **Fa Lydien:** Effet STIMULANT/ÉNERGISANT (activer, stimuler, régénérer)
- **Sib Lydien:** Effet ÉQUILIBRANT (équilibre, harmonise)
- **Mib Lydien:** Effet INHIBANT/CALMANT (calmer, apaiser, relaxer)

## 📝 MAPPING ACIDES AMINÉS → NOTES

Séquence standard utilisée dans protéodies:
```
A→0, C→1, D→2, E→3, F→4, G→5, H→6, I→7, K→8, L→9,
M→10, N→11, P→12, Q→13, R→14, S→15, T→16, V→17, W→18, Y→19
```

Notes MIDI mappées sur gamme sélectionnée (20 notes).

## 🔄 AUTO-SÉLECTION MODES

### Mode audio
L'application détecte automatiquement le mode optimal:
- Catégories thérapeutiques (🧬🧠🦵😴🫃💚🔥🫒⚡🦿🦻💪🩹🩸🧪🌸💉🌺🫘💦🦴) → **Isochrone**
- Catégories plantes (🌿🥒🍅🍇🌵🦟) → **Stéréo**

Utilisateur peut forcer manuellement → choix respecté

### Gamme
Auto-sélection selon catégorie cochée:
- **Mib Lydien (calmant):** Sommeil, Tension, Jambes Sans Repos, Fibromyalgie, Anti-Inflammatoire, Ménière, Sang, Rénal, **Arthrose**
- **Sib Lydien (équilibrant):** Diabète
- **Fa Lydien (stimulant):** Toutes autres catégories

## 🎯 NEXT STEPS POSSIBLES

### Monitoring & Amélioration
- Créer dashboard temps réel validation audio
- Automatiser validation pipeline Logic Pro exports
- Ajouter alertes si LFO/diapason dérivent

### Nouveaux packs protéodies
- Pack Ostéoporose (densité osseuse)
- Pack Tendinites (inflammation tendons)
- Pack Cicatrisation (régénération tissulaire)

### Optimisations workflow
- Plugin VST3 custom pour LFO précis (éviter Tremolo Logic)
- Template Logic Pro pré-configuré pour chaque catégorie
- Export batch automatique toutes protéodies cochées

## 🎵 PROTEODIES V2 - INTERFACE SIMPLIFIÉE

### Architecture V2 (`/proteodies2/`)

**Workflow utilisateur ultra-simple:**
1. Sélectionner pack (ex: Arthrose, Sommeil, Diabète...)
2. Choisir diapason (h3O2 ou Standard)
3. Mode audio (Auto recommandé, ou manuel)
4. Gamme (Auto recommandé, ou Fa/Sib/Mib)
5. Durée via slider (1-60 minutes)
6. ▶ Jouer → Lecture automatique avec samples audio

**Packs disponibles (34 packs, 185 protéodies):**
- 🦴 Arthrose (8 protéodies) - 7 Hz Mib
- 😴 Sommeil (1 protéodie) - 4 Hz Mib
- 💦 Peau Sèche (7 protéodies) - 8 Hz Fa
- 💉 Diabète (9 protéodies) - 8 Hz Sib
- 🧠 Neuro (5 protéodies) - 14 Hz Fa
- 🦵 Genou (5 protéodies) - 10 Hz Fa
- ❤️ Tension (6 protéodies) - 8 Hz Mib
- 🫃 Intestin (5 protéodies) - 6 Hz Fa
- 🫒 Foie (5 protéodies) - 7 Hz Fa
- ⚡ Neuro-Douleur (9 protéodies) - 6 Hz Fa
- 💪 Fibromyalgie (9 protéodies) - 7 Hz Mib
- 🦿 Jambes Sans Repos (6 protéodies) - 8 Hz Mib
- 🦻 Ménière (6 protéodies) - 10 Hz Mib
- 🔥 Métabolisme (6 protéodies) - 12 Hz Fa
- 🩸 Sang (3 protéodies) - 8 Hz Mib
- ... et 19 autres packs

**Fonctionnalités:**
- Auto-configuration paramètres selon pack
- Calcul automatique nombre de boucles
- Barre progression + timer temps réel
- Affichage détails pack (protéodies incluses, fréquence, effet)
- Concaténation protéodies du pack en séquence unique
- Lecture en boucle jusqu'à durée cible

### Script extraction packs (`extract_all_packs.py`)

Extrait automatiquement tous les packs depuis V1:
```python
# Parse PROTEODIES depuis index.html V1
# Groupe par catégorie (cat:'🦴', cat:'😴', etc.)
# Génère code JavaScript V2 avec config
```

**Sortie:**
- Dictionnaire PROTEODIES (id → {name, seq})
- Dictionnaire PACKS (pack_id → {name, emoji, proteodies[], mode, scale, freq, effect})

### Bibliothèque audio (54 MB)

**Structure:**
```
web-ui/public/proteodies/audio/building_blocks/
├── manifest.json (métadonnées)
├── h3o2_stereo/{fa,sib,mib}/A-Y.wav
├── h3o2_isochrone_4hz/{fa,sib,mib}/A-Y.wav
├── h3o2_isochrone_7hz/{fa,sib,mib}/A-Y.wav
├── h3o2_isochrone_10hz/{fa,sib,mib}/A-Y.wav
├── h3o2_isochrone_14hz/{fa,sib,mib}/A-Y.wav
├── standard_stereo/{fa,sib,mib}/A-Y.wav
├── standard_isochrone_4hz/{fa,sib,mib}/A-Y.wav
├── standard_isochrone_7hz/{fa,sib,mib}/A-Y.wav
├── standard_isochrone_10hz/{fa,sib,mib}/A-Y.wav
└── standard_isochrone_14hz/{fa,sib,mib}/A-Y.wav
```

**Total:** 600 samples WAV (2 diapasons × 5 modes × 3 gammes × 20 AA)

## 📦 COMMITS DÉTAILS

### Commit 1: `6853ed6` - Arthrose pack + validation tools
**Fichiers:** 6 modifiés, +1815 lignes
**Date:** 2026-08-08

**Fichiers:**
- analyze_audio.py (analyse générale)
- analyze_lfo_detailed.py (LFO Hilbert)
- detect_notes_timing.py (YIN pitch detection)
- generate_dsip_20min.py (MIDI 20 min)
- generate_dsip_midi.py (MIDI variable)
- web-ui/public/proteodies/index.html (arthrose pack)

### Commit 2: `e39da99` - Proteodies V2 complete system
**Fichiers:** 8 modifiés, +1918 lignes
**Date:** 2026-08-08

**Fichiers:**
- web-ui/public/proteodies2/index.html (interface V2)
- web-ui/public/proteodies/audio-player.js (Web Audio player)
- web-ui/public/test_audio_samples.html (tests)
- generate_proteodies_audio_library.py (génération samples)
- extract_all_packs.py (extraction packs V1→V2)
- AUDIO-SAMPLES-GUIDE.md (documentation)
- web-ui/vite.config.ts (fix routing)
- web-ui/public/proteodies/index.html (bouton audio 🔊)

**Pull Request:**
https://github.com/brusand/gsgui/pull/new/gsgui-v2-prot%C3%A9odies

---
**🧬 Cette mémoire documente le système de validation audio et les nouveaux packs protéodies d'août 2026.**
