# 🎵 Guide - Samples Audio Protéodies

## 📊 Vue d'ensemble

Le système de samples audio permet d'écouter les protéodies directement dans le navigateur sans dépendance externe (Logic Pro, Vienna Synchron, etc.).

**Avantages:**
- ✅ Lecture immédiate navigateur (Web Audio API)
- ✅ Qualité audio pré-rendue garantie
- ✅ Pas de dépendance DAW pour utilisateur final
- ✅ Calcul automatique répétitions pour durée cible
- ✅ Crossfade entre notes pour transitions fluides

## 🏗️ Architecture

### Structure fichiers

```
web-ui/public/proteodies/audio/
├── building_blocks/              # Building blocks (acides aminés individuels)
│   ├── manifest.json             # Métadonnées bibliothèque
│   ├── h3o2_stereo/
│   │   ├── fa/                   # Gamme Fa Lydien
│   │   │   ├── A.wav
│   │   │   ├── C.wav
│   │   │   └── ... (20 fichiers)
│   │   ├── sib/                  # Gamme Sib Lydien
│   │   └── mib/                  # Gamme Mib Lydien
│   ├── h3o2_isochrone_4hz/       # Delta (sommeil)
│   ├── h3o2_isochrone_7hz/       # Theta (arthrose, anti-inflammatoire)
│   ├── h3o2_isochrone_10hz/      # Alpha (standard)
│   ├── h3o2_isochrone_14hz/      # Beta (neuro)
│   ├── standard_stereo/          # Idem avec diapason 440 Hz
│   ├── standard_isochrone_4hz/
│   ├── standard_isochrone_7hz/
│   ├── standard_isochrone_10hz/
│   └── standard_isochrone_14hz/
└── audio-player.js               # Module Web Audio API
```

### Statistiques

- **Total samples:** 600 fichiers WAV
- **Taille totale:** ~54 MB
- **Diapasons:** h3O2 (429.62 Hz), Standard (440 Hz)
- **Modes:** Stereo, Isochrone 4/7/10/14 Hz
- **Gammes:** Fa/Sib/Mib Lydien
- **Acides aminés:** 20 (ACDEFGHIKLMNPQRSTVWY)

## 🎹 Génération samples

### Méthode 1: Synthèse sinusoïdale (fallback)

Script Python utilise synthèse multi-harmoniques pour générer samples:

```bash
cd /Volumes/SSD/devs/gsgui
source venv/bin/activate
python generate_proteodies_audio_library.py
```

**Caractéristiques synthèse:**
- Onde fondamentale + 3 harmoniques (octave, quinte, tierce)
- Envelope ADSR (Attack/Decay/Sustain/Release)
- Crossfade zones 50ms début/fin
- Tremolo pour modes isochrones (depth 70%)
- Timbre inspiré bol tibétain

**Durée génération:** ~30 secondes pour 600 samples

### Méthode 2: Vienna Synchron + DawDreamer (production)

Pour qualité production, utiliser Vienna Synchron VST3:

```bash
pip install dawdreamer
```

Modifier `generate_proteodies_audio_library.py`:
- Décommenter section DawDreamer
- Configurer chemin VST: `/Library/Audio/Plug-Ins/VST3/Vienna Synchron Player.vst3`
- Identifier parameter IDs pour Master Tune

**Note:** DawDreamer nécessite JUCE et peut nécessiter build depuis source sur macOS.

## 🎵 Utilisation dans interface

### Bouton play audio (🔊)

Chaque protéodie affiche un bouton audio si samples disponibles:

```
[✓] Arthrose — Collagène II Cartilage  🔊 ⓘ
```

**Comportement:**
- Clic → Lecture 1 boucle (~10 secondes)
- Respecte paramètres interface (diapason, gamme, reverb)
- Mode audio mappé automatiquement vers samples disponibles
- Crossfade automatique entre notes

### Mapping modes audio → samples

| Mode interface | Fréquence LFO | Sample utilisé      |
|----------------|---------------|---------------------|
| Stéréo         | -             | `*_stereo`          |
| Isochrone      | 4 Hz          | `*_isochrone_4hz`   |
| Isochrone      | 7 Hz          | `*_isochrone_7hz`   |
| Isochrone      | 10 Hz         | `*_isochrone_10hz`  |
| Isochrone      | 14 Hz         | `*_isochrone_14hz`  |
| Binaural       | N/A           | Fallback isochrone  |

**Note:** Binaural utilise samples isochrones car battements binauraux nécessitent stéréo différentiel (non pré-rendable en mono).

## 🔧 Module audio-player.js

### API ProteodiesAudioPlayer

```javascript
const player = new ProteodiesAudioPlayer();

// Initialiser
await player.init();

// Jouer protéodie
await player.playProteody("WAGGDASGE", {
  diapason: 'h3o2',       // 'h3o2' ou 'standard'
  mode: 'isochrone_7hz',  // stereo, isochrone_4/7/10/14hz
  scale: 'mib',           // fa, sib, mib
  duration: 600,          // secondes (10 min)
  masterVolume: 0.7,      // 0-1
  reverbMix: 0.3,         // 0-1
  onProgress: (p) => {},  // callback progression
  onComplete: () => {}    // callback fin
});

// Arrêter
player.stop();

// Pause/Resume
await player.togglePause();
```

### Fonctionnalités avancées

**Cache samples:**
- Map LRU en mémoire
- Évite rechargement réseau
- Pré-chargement séquence avant lecture

**Crossfade:**
- 50ms overlap entre notes
- Gain envelopé linéairement
- Transitions fluides

**Reverb:**
- Convolution avec impulse response générée
- Decay exponentiel 2s
- Mix dry/wet ajustable

## 📈 Performance

### Chargement initial
- Manifest.json: ~1 KB
- Premier sample: ~90 KB (décodage ~20ms)
- Cache navigateur: samples réutilisés

### Lecture
- Latency: ~100ms (buffer Web Audio)
- CPU: <5% (Web Audio optimisé hardware)
- Mémoire: ~10 MB par protéodie chargée

### Bande passante
- 1 protéodie (20 AA): ~1.8 MB samples
- Cache agressif: téléchargement unique

## 🚀 Prochaines étapes

### Améliorations possibles

1. **Streaming chunks**
   - Diviser fichiers longs en chunks
   - Progressive loading pendant lecture
   - Réduire temps chargement initial

2. **Compression audio**
   - Encoder en OGG/Opus (50% smaller)
   - Fallback WAV pour compatibilité
   - Trade-off taille vs qualité

3. **Pre-render protéodies populaires**
   - Top 10 protéodies complètes (20 min)
   - Download on-demand
   - Éviter concaténation temps réel

4. **Worker Thread**
   - Décodage audio dans Worker
   - UI non bloquante
   - Meilleure performance mobile

5. **VST automation workflow**
   - Script Reaper + ReaScript
   - Batch export automatique
   - Integration CI/CD

## 🐛 Dépannage

### Samples non chargés
- Vérifier console navigateur: `🎵 Manifest audio chargé`
- Vérifier fichiers: `ls web-ui/public/proteodies/audio/building_blocks/`
- Regénérer: `python generate_proteodies_audio_library.py`

### Clicks/pops
- Augmenter crossfade: `crossfadeDuration = 0.1` (100ms)
- Vérifier envelope ADSR dans generate script
- Samples peuvent nécessiter fade in/out plus long

### Diapason incorrect
- Vérifier Master Tune cents dans génération
- h3O2 = -24 cents (429.62 Hz)
- Standard = 0 cents (440 Hz)

### LFO pas assez fort
- Augmenter tremolo depth: `apply_tremolo(..., depth=0.8)`
- Vérifier fréquence LFO dans samples
- Analyser avec `analyze_lfo_detailed.py`

## 📚 Références

**Web Audio API:**
- https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API

**DawDreamer:**
- https://github.com/DBraun/DawDreamer

**Vienna Synchron Player:**
- https://www.vsl.co.at/

**Protéodies theory:**
- Marc Henry: Fréquence h3O2 (429.62 Hz)
- Jean-Luc Borla: Gammes Lydiennes thérapeutiques

---
**Créé:** 2026-08-08
**Version:** 1.0.0
