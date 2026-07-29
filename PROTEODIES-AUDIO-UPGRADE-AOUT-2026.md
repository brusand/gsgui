# Protéodies Audio Upgrade - Plan Août 2026

## 📋 Contexte actuel (Juillet 2026)

### ✅ Ce qui est déjà implémenté

**Protocol H complet (20 minutes)** :
- Signal départ (1 note G)
- 5 min silence (325 G notes, playback silencieux)
- 10 min TPH1 Sérotonine (36 loops de WFLSQQHER)
- 5 min silence (325 G notes, playback silencieux)
- Signal fin (2 notes GG)
- Randomisation : audio mode (stereo/isochrone), ordre (séquentiel/random), diapason (H2O 429.62Hz / Standard 440Hz)
- Logging automatique dans localStorage avec timestamp
- Fonction `exportProtocolHLogs()` dans console

**3 gammes Lydiennes (JL Borla)** :
1. **Fa Lydien (stimulant)** : fa sol la si do ré mi
   - MIDI: [53,55,57,59,60,62,64,65,67,69,71,72,74,76,77,79,81,83,84,86]
   - Auto-assigné à : 🧠 Neuro, 🧪 Protocol H, 🦵 Genou, 🔥 Métabolisme, 🍴 Boulimie, 💚 Régénération, 🫒 Foie, ⚡ Neuro-Douleur, etc.

2. **Sib Lydien (équilibrant)** : si♭ do ré mi fa sol la
   - MIDI: [46,48,50,52,53,55,57,58,60,62,64,65,67,69,70,72,74,76,77,79]
   - Disponible manuellement, idéal pour : 😊 Humeur, 🌌 Conscience, 🫃 Intestin, 👁️ Yeux, 💧 Eau

3. **Mib Lydien (inhibant/calmant)** : mi♭ fa sol la si♭ do ré
   - MIDI: [51,53,55,57,58,60,62,63,65,67,69,70,72,74,75,77,79,81,82,84]
   - Auto-assigné à : 😴 Sommeil, ❤️ Tension, 🦿 Jambes Sans Repos, 💪 Fibromyalgie, 🩹 Anti-inflammatoire, 🦟 Anti-démangeaisons, 🩸 Sang, 🦻 Ménière

**Auto-sélection intelligente** :
- Mode audio (stereo/isochrone) selon catégorie
- Gamme (fa/sib/mib) selon effet thérapeutique recherché
- Override manuel possible (flags `audioModeManuallyChanged`, `scaleManuallyChanged`)

**142 protéodies organisées** par catégories avec descriptions

**Fréquences isochrones** adaptées par catégorie :
- 😴 Sommeil : 4 Hz (Delta → sommeil profond)
- 🩸 Sang/Tension : 8 Hz (Alpha → relaxation)
- 🦿 Jambes Sans Repos : 8 Hz (Alpha → calme)
- 🧠 Neuro : 14 Hz (Beta → cognition)
- 🔥 Métabolisme : 12 Hz (Beta → activation)
- 🦵 Genou : 10 Hz (Alpha → réparation)
- 🌌 Conscience : 6 Hz (Theta → méditation)

**Web Audio API** prête pour intégration samples :
- AudioContext, oscillateurs synthétiques actuels
- Support reverb, gain, panning
- Isochrone via gain modulation
- Architecture modulaire

---

## 🎯 OBJECTIF AOÛT 2026 : Audio Upgrade

### Problème actuel
Sons **synthétiques basiques** (oscillateurs Web Audio) = qualité "jouet"

### Solution envisagée
**Samples audio professionnels** + **Enregistrements guitare personnels**

---

## 🎸 PROJET MAJEUR : Jouer les protéodies à la guitare

### L'idée révolutionnaire
**Jouer soi-même ses protéodies sur guitare** = approche Tomatis personnalisée + protéodies

**Avantages** :
- Vibrations physiques de la guitare touchent le corps directement
- Intention personnelle infusée dans chaque note
- Son unique, vivant (pas enregistré/répétitif)
- Thérapie ACTIVE vs passive (devient l'instrument)
- Triple puissance : protéodie + intention + vibrations

### Guitares disponibles

#### 🔥 **GUITARE MANOUCHE** (Selmer style)
**Caractère** : Percussif, attaque claire, médiums brillants

**Idéale pour protéodies STIMULANTES** :
- 🧠 Neuro (dopamine, sérotonine) → attaque précise = impact neuronal
- 🔥 Métabolisme → son énergique
- ⚡ Neuro-douleur → GABA, endorphines
- 🧪 **Protocol H** → sérotonine (son vivant, énergisant)
- **Gammes** : Fa Lydien (stimulant), Sib Lydien (équilibrant)
- **Tempo** : 80-100 BPM

**Style recommandé** :
- Arpèges Django/Stochelo style
- Picking alterné strict
- Pompe manouche soft
- Ornements : pull-off, hammer-on (pas de bends)
- Son pur (pas d'effets)

**Setup son** :
- Cordes Argentine tension moyenne
- Médiator écaille épaisseur moyenne
- Reverb courte (salle acoustique)
- Micro statique 30cm rosace (AKG C214, AT2020)

**Positions gamme Fa Lydien** :
```
Position 2-5 (sweet spot manouche):
e|--8(Do)--10(Ré)--12(Mi)--13(Fa)--
B|--6(Fa)--8(Sol)--10(La)--12(Do)--
G|--5(Do)--7(Ré)--9(Mi)--10(Fa)----
D|--7(La)--9(Si)--10(Do)--12(Ré)---
A|--8(Mi)--10(Fa)--12(Sol)---------

Position haute (brillance):
e|--13(Fa)--15(Sol)--17(La)--
B|--13(Do)--15(Ré)--17(Mi)---
G|--12(Fa)--14(Sol)--16(La)--
```

---

#### 🎷 **ÉLECTRIQUE JAZZ** (Archtop)
**Caractère** : Rond, feutré, sustain long, méditatif

**Idéale pour protéodies CALMANTES** :
- 😴 Sommeil (DSIP) → son chaud, enveloppant
- ❤️ Tension → relaxant, apaisant
- 🦿 Jambes Sans Repos → son continu, hypnotique
- 💪 Fibromyalgie → douceur, réconfort
- 🦻 Ménière → calme, stable
- 🌌 Conscience → méditatif
- **Gammes** : Mib Lydien (inhibant/calmant)
- **Tempo** : 50-75 BPM

**Style recommandé** :
- Fingerstyle, thumb picking (Wes Montgomery)
- Legato, notes tenues
- Chord melody possible
- Son feutré, round

**Setup son** :
- Micro manche (plus chaud)
- Tone roulé à 50-60%
- Reverb longue (cathédrale, hall)
- Delay léger (300-500ms, 1-2 répétitions)
- Chorus subtil optionnel
- Compression moyenne (ratio 3:1)

**Positions gamme Mib Lydien** :
```
Position basse (warmth):
e|--6(Mib)--8(Fa)--10(Sol)--11(La)--
B|--4(Sib)--6(Do)--8(Ré)--9(Mib)----
G|--3(Sib)--5(Do)--7(Ré)--8(Mib)----
D|--5(Sol)--7(La)--8(Sib)--10(Do)---
A|--6(Ré)--8(Mib)--10(Fa)-----------
E|--6(Sib)--8(Do)--10(Ré)------------

Position thumb (à la Wes):
e|--11(La)--13(Sib)--15(Do)--
B|--11(Mib)--13(Fa)--15(Sol)-
G|--10(Mib)--12(Fa)--14(Sol)-
D|--12(Do)--13(Ré)--15(Mib)--
```

---

### Exemple concret : Protocol H avec guitare manouche

**Séquence TPH1** : `WFLSQQHER` (36 loops, 10 minutes)
- Trp Phe Leu Ser Gln Gln His Glu Arg

**Style Django ralenti** :
- Picking alterné strict
- Arpèges rapides (sweep léger)
- Attaque forte → médium → forte (dynamique)
- Tempo : 80 BPM, swing léger
- Feeling : comme "Minor Swing" méditatif mais vivant

**Effet recherché** :
- Son percussif, énergisant
- Stimule production sérotonine
- Isochrone 10 Hz superposé (ondes Alpha-Beta)
- Fa Lydien (effet stimulant)

---

## 🛠️ FONCTIONNALITÉS À IMPLÉMENTER (Août)

### 1️⃣ Export Tablature/Partition (PRIORITÉ 1)

**Bouton "Export Guitar Tab"** qui génère fichier texte :

```
DSIP (Sommeil) - Mib Lydien - 65 BPM
Durée totale: 1min 12s

Séquence: W A G G D A S G E

W = Trp (Tryptophane) - 3 temps - Note: Mi (E)
  → Corde 1 (e) - Case 12

A = Ala (Alanine) - 1 temps - Note: Fa (F)
  → Corde 1 (e) - Case 13

G = Gly (Glycine) - 1 temps - Note: Sol (G)
  → Corde 3 (G) - Case 5

[etc...]

Tablature ASCII:
e|--12--13--------------------------
B|----------13--15------------------
G|---------------7--9--10-----------
D|---------------------------12--14-
A|----------------------------------
E|----------------------------------
   W   A   G   G   D   A   S   G   E
```

**Code à implémenter** :
```javascript
function exportGuitarTab(proteody) {
  const scale = getScale();
  const bpm = document.getElementById('bpm').value;
  const gamme = document.getElementById('gamme').value;

  let tab = `${proteody.name}\n`;
  tab += `Gamme: ${gamme} - Tempo: ${bpm} BPM\n`;
  tab += `Durée totale: ${calculateDuration(proteody)}\n\n`;
  tab += `Séquence: ${proteody.seq}\n\n`;

  // Détail chaque acide aminé
  proteody.seq.split('').forEach(aa => {
    const note = midiFor(aa);
    const noteName = getNoteName(note);
    const fret = mapNoteToFretboard(note, scale);
    const ticks = ticksFor(aa);

    tab += `${aa} = ${NAMES[aa]} - ${ticks} temps - Note: ${noteName}\n`;
    tab += `  → Corde ${fret.string} (${fret.stringName}) - Case ${fret.fret}\n\n`;
  });

  // Générer ASCII tab
  tab += generateASCIITab(proteody);

  // Download
  const blob = new Blob([tab], {type: 'text/plain'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${proteody.id}_guitar_tab.txt`;
  a.click();
}

function mapNoteToFretboard(midiNote, scale) {
  // Mapping intelligent vers positions confortables
  // Retourne: {string: 1-6, stringName: 'e/B/G/D/A/E', fret: 0-17}
}
```

---

### 2️⃣ Export MIDI (PRIORITÉ 1)

**Bouton "Export MIDI"** pour ouvrir dans DAW (Logic, Ableton, GarageBand)

**Avantages** :
- Jouer avec métronome
- Modifier tempo facilement
- Enregistrer guitare par-dessus
- Ajouter effets (reverb, delay)

**Library à utiliser** : `@tonejs/midi` ou `midi-writer-js`

**Code à implémenter** :
```javascript
function exportMIDI(proteody) {
  const midi = new Midi();
  const track = midi.addTrack();

  const bpm = parseInt(document.getElementById('bpm').value);
  const beat = 60 / bpm;

  let time = 0;
  proteody.seq.split('').forEach(aa => {
    const note = midiFor(aa);
    const duration = ticksFor(aa) * beat;

    track.addNote({
      midi: note,
      time: time,
      duration: duration,
      velocity: velFor(aa) * 127 // 0-127
    });

    time += duration;
  });

  // Download .mid file
  const blob = new Blob([midi.toArray()], {type: 'audio/midi'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${proteody.id}.mid`;
  a.click();
}
```

---

### 3️⃣ Mode "Play Along" visuel (PRIORITÉ 2)

Affichage en temps réel pendant lecture :
- Note actuelle en GROS
- Position sur le manche (corde + case)
- Timing/métronome visuel
- Barre de progression

**Design UI** :
```html
<div id="guitar-play-along" style="display: none;">
  <div class="current-note">SOL (G)</div>
  <div class="current-fret">Corde 3 - Case 5</div>
  <div class="fretboard-visual">
    <!-- Visualisation manche simplifié -->
  </div>
  <div class="progress-bar">
    <div class="progress-fill" style="width: 45%"></div>
  </div>
  <div class="metronome">♩ ♩ ♩ ♪</div>
</div>
```

**Integration dans `playOne()`** :
```javascript
async function playOne(prot) {
  // ... code existant

  for(let i=0; i<seq.length; i++) {
    const aa = seq[i];
    const note = midiFor(aa);
    const noteName = getNoteName(note);
    const fret = mapNoteToFretboard(note);

    // Afficher pour guitariste
    if (document.getElementById('play-along-mode').checked) {
      document.getElementById('current-note').textContent = noteName;
      document.getElementById('current-fret').textContent =
        `Corde ${fret.string} - Case ${fret.fret}`;
      highlightFretboardPosition(fret);
    }

    // ... rest of playback
  }
}
```

---

### 4️⃣ Intégration samples audio (PRIORITÉ 3)

#### Architecture samples :

```
/web-ui/public/samples/
  /guitare-manouche/
    C3.mp3
    E3.mp3
    G3.mp3
    C4.mp3
    E4.mp3
    G4.mp3
    C5.mp3
  /guitare-jazz/
    C3.mp3
    E3.mp3
    ...
  /voix-choeur/
    C3.mp3
    ...
  /bol-tibetain/
    C3.mp3
    ...
  /piano-steinway/
    C3.mp3
    ...
```

**Stratégie multisampling** :
- Samples tous les 3-4 demi-tons (C, Eb, F#, A)
- Pitch shifting pour notes intermédiaires (playbackRate)
- Total : ~7 samples par octave × 3 octaves = 21 samples/instrument
- Taille estimée : 50-200 KB/sample → 1-4 MB/instrument

#### Code SampleManager :

```javascript
class SampleManager {
  constructor() {
    this.buffers = {};
    this.loading = false;
  }

  async loadInstrument(instrument) {
    if (this.buffers[instrument]) return;

    this.loading = true;
    const samples = SAMPLE_LIBRARY[instrument];

    for (const [note, url] of Object.entries(samples)) {
      const response = await fetch(url);
      const arrayBuffer = await response.arrayBuffer();
      const audioBuffer = await audioCtx.decodeAudioData(arrayBuffer);
      this.buffers[`${instrument}_${note}`] = audioBuffer;
    }

    this.loading = false;
  }

  getBuffer(instrument, midiNote) {
    // Trouver le sample le plus proche
    const closestSample = findClosestSample(midiNote);
    const buffer = this.buffers[`${instrument}_${closestSample}`];
    const pitchShift = calculatePitchShift(midiNote, closestSample);

    return { buffer, pitchShift };
  }
}

const sampleManager = new SampleManager();
```

#### Modification playNote() :

```javascript
function playNote(freq, dur, vel, cat) {
  const instrument = currentInstr; // 'bol', 'voix', 'guitare-manouche', etc.

  // Mode synthé (fallback)
  if (!sampleManager.buffers[instrument] || instrument === 'synth') {
    // Code actuel avec oscillateurs
    return;
  }

  // Mode samples
  const midiNote = freqToMidi(freq);
  const { buffer, pitchShift } = sampleManager.getBuffer(instrument, midiNote);

  const source = audioCtx.createBufferSource();
  source.buffer = buffer;
  source.playbackRate.value = pitchShift;

  const gainNode = audioCtx.createGain();
  gainNode.gain.setValueAtTime(vel, audioCtx.currentTime);
  gainNode.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + dur);

  source.connect(gainNode);
  gainNode.connect(reverbNode);

  // Isochrone mode
  if (audioMode === 'isochronic') {
    const beatFreq = BEAT_FREQS[cat] || 10;
    modulateGainIsochrone(gainNode, dur, beatFreq);
  }

  source.start();
  source.stop(audioCtx.currentTime + dur);
}
```

---

### 5️⃣ Upload samples personnalisés (PRIORITÉ 4)

**Interface upload** :
```html
<div class="custom-samples">
  <h3>Enregistrements personnalisés</h3>
  <button onclick="uploadCustomSample('guitare-manouche')">
    Upload Guitare Manouche
  </button>
  <button onclick="uploadCustomSample('guitare-jazz')">
    Upload Guitare Jazz
  </button>

  <input type="file" id="sample-upload" accept="audio/*" multiple style="display:none">
</div>
```

**Code upload** :
```javascript
function uploadCustomSample(instrument) {
  const input = document.getElementById('sample-upload');
  input.onchange = async (e) => {
    const files = e.target.files;

    for (const file of files) {
      // Détecter la note depuis le nom de fichier (ex: C3.mp3, E4.wav)
      const noteName = extractNoteFromFilename(file.name);

      const arrayBuffer = await file.arrayBuffer();
      const audioBuffer = await audioCtx.decodeAudioData(arrayBuffer);

      // Stocker dans sampleManager
      sampleManager.buffers[`${instrument}_${noteName}`] = audioBuffer;

      // Sauvegarder dans IndexedDB pour persistance
      await saveToIndexedDB(instrument, noteName, arrayBuffer);
    }

    alert(`${files.length} samples uploaded for ${instrument}!`);
  };

  input.click();
}
```

---

## 🎤 SAMPLES PROFESSIONNELS À ACQUÉRIR

### Priorités utilisateur (ordre) :
1. **Voix** : Chœur hommes OU femmes (ou les deux)
2. **Bol tibétain** : Sons authentiques
3. **Piano Steinway** : Grand piano qualité

### Options samples VOIX :

**Premium** :
- **Strezov Sampling - Storm Choir 2** (~300€) - référence absolue
- **Soundiron - Venus Symphonic Women's Choir** (~250€)
- **Sonokinetic - Capriccio** (chœur complet) (~200€)

**Gratuit** :
- **Versilian Studios Chamber Choir (VSCO)** - très correct
- **Freesound.org** - qualité variable, chercher "choir", "vocal"

### Options BOL TIBÉTAIN :

**Premium** :
- **Soniccouture - Gongs & Singing Bowls** (~100€) - excellent
- **Native Instruments - Tibet** (dans Komplete) - authentique
- **Impact Soundworks - Boru** (~150€, inclut bols)

**Gratuit** :
- **Freesound.org** - chercher "tibetan bowl", "singing bowl"
- Qualité très variable, bien écouter avant

### Options PIANO STEINWAY :

**Premium** :
- **Native Instruments - The Grandeur** (Steinway D) - dans Komplete Ultimate (~600€)
- **Spitfire Audio - Felt Piano** (~30€) - plus intimiste, doux
- **Pianoteq - Steinway D** (~150€) - physique modeling (pas samples)

**Gratuit** :
- **Salamander Grand Piano** - très correct, bien pour commencer
- **Ivy Audio - Piano in 162** - free, qualité décente

### Budget estimé :

**Option tout gratuit** : 0€
- VSCO Choir
- Freesound bols tibétains
- Salamander Piano

**Option mix** : 100-200€
- VSCO Choir (gratuit)
- Soniccouture Bols (~100€)
- Salamander Piano (gratuit)

**Option full pro** : 600-900€
- Storm Choir 2 ou Venus Choir (250-300€)
- Soniccouture Bols (100€)
- Native Instruments Komplete (600€ - inclut piano + Tibet + pleins d'autres)

**Recommandation** : Commencer avec **samples gratuits** pour tester architecture, puis investir si concluant.

---

## 📅 WORKFLOW AOÛT 2026

### Semaine 1 : Exports & Pratique guitare

**Jour 1-2 : Code exports**
- [ ] Implémenter `exportGuitarTab()`
- [ ] Implémenter `exportMIDI()`
- [ ] Tester avec 5-10 protéodies clés
- [ ] Commit sur develop

**Jour 3-7 : Pratique guitare**
- [ ] Sélectionner 10-15 protéodies prioritaires :
  - Sommeil (DSIP)
  - Protocol H (TPH1)
  - Neuro (TH, DBH)
  - Douleur (BPC-157)
  - Tension (Apelin, eNOS)
  - etc.
- [ ] Export tabs pour chaque protéodie
- [ ] Pratiquer séquences :
  - 5-7 sur guitare manouche (stimulantes)
  - 5-7 sur guitare jazz (calmantes)

### Semaine 2 : Enregistrements guitare

**Préparation** :
- [ ] Setup home studio (interface audio, micros, DAW)
- [ ] Test son manouche (micro statique, position)
- [ ] Test son jazz électrique (direct/ampli, effets)
- [ ] Réglages compression, EQ, reverb

**Enregistrement** :
- [ ] Manouche : protéodies stimulantes (Fa Lydien)
  - Notes longues pour samples
  - OU séquences complètes
- [ ] Jazz électrique : protéodies calmantes (Mib Lydien)
  - Thumb picking, son rond
  - Notes tenues

**Post-production** :
- [ ] Normaliser audio
- [ ] Découper samples par note (si approche multisampling)
- [ ] Exporter WAV 24bit → MP3 320kbps
- [ ] Organiser dans `/web-ui/public/samples/`

### Semaine 3 : Intégration code

**SampleManager** :
- [ ] Créer classe `SampleManager`
- [ ] Loader avec progression (spinner UI)
- [ ] Cache IndexedDB pour persistance
- [ ] Pitch shifting (playbackRate calculation)

**Modification playback** :
- [ ] Modifier `playNote()` pour utiliser AudioBuffer
- [ ] Fallback synthé si samples non chargés
- [ ] Support isochrone avec samples
- [ ] Test toutes protéodies

**UI** :
- [ ] Ajouter sélection instrument avec tes samples
- [ ] Mode "HQ" (samples) vs "Lite" (synthé)
- [ ] Upload samples personnalisés
- [ ] Play Along mode visuel

### Semaine 4 : Samples pro & Tests

**Acquisition samples** (selon budget/décision) :
- [ ] Télécharger/acheter samples voix
- [ ] Télécharger/acheter samples bol tibétain
- [ ] Télécharger/acheter samples piano
- [ ] Organiser dans arborescence `/samples/`

**Intégration** :
- [ ] Charger samples pro dans SampleManager
- [ ] Tester qualité sonore
- [ ] Comparer : guitare perso vs samples pro vs synthé
- [ ] Optimiser taille/compression

**Tests utilisateur** :
- [ ] Protocol H complet avec guitare manouche
- [ ] Session sommeil (DSIP) avec guitare jazz
- [ ] Comparer efficacité thérapeutique subjective

**Commit final** :
- [ ] Push tout sur develop
- [ ] Documentation update
- [ ] Changelog

---

## ❓ QUESTIONS EN SUSPENS (à répondre)

### Setup technique :
1. **Interface audio** : Tu as quoi comme interface ? (Focusrite, Universal Audio, autre ?)
2. **Micros** : Tu as des micros statiques pour guitare manouche ? (AKG, Audio-Technica, Rode ?)
3. **DAW** : Tu utilises quoi ? (Logic Pro, Ableton, GarageBand, Reaper, autre ?)
4. **Expérience recording** : À l'aise avec prise de son ou besoin de tips détaillés ?

### Style musical :
5. **Style manouche** : Plutôt Django Reinhardt (swing vintage) ou Stochelo Rosenberg (moderne précis) ?
6. **Pédalier jazz** : Tu as reverb/delay en hardware ou tu préfères software (plugins) ?

### Budget & priorités :
7. **Budget samples** : Prêt à investir ~300-500€ dans Kontakt/packs pro ou priorité gratuit pour tester ?
8. **Priorité instruments samples pro** : Ordre final ?
   - Voix chœur (hommes/femmes/mixte ?)
   - Bol tibétain
   - Piano Steinway
9. **Taille téléchargement acceptable** : 10 MB ? 50 MB ? 100 MB pour l'app complète ?

### Timeline :
10. **Dates précises août** : Disponible quelle période ? (début/mi/fin août ?)
11. **Discussion JL Borla** : Prévue quand ? Avant août ou pendant ?

### Vision produit :
12. **Public cible final** : Usage perso uniquement ou partage à communauté/amis ?
13. **Spatialisation audio** : Vraiment pas prioritaire ou juste "après" ?
14. **Mode offline** : Important que samples soient en cache (PWA) ou connexion OK ?

---

## 🎯 VISION ULTIME : Session Protocol H avec guitare

**20 minutes d'auto-thérapie personnalisée** :

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROTOCOL H - Session avec GUITARE MANOUCHE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Settings randomisés :
✓ Audio mode: Isochrone 10 Hz (ondes Alpha-Beta)
✓ Ordre: Séquentiel
✓ Diapason: H2O (429.62 Hz - eau structurée)
✓ Gamme: Fa Lydien (stimulant)
✓ Instrument: TES enregistrements guitare manouche

Timeline:
00:00 - Signal départ (1 note)
        → Guitare jazz électrique (doux, ancrage)

00:05 - Silence 5 min
        → Méditation, respiration

05:05 - TPH1 Sérotonine (10 min)
        → GUITARE MANOUCHE énergique !!
        → TES arpèges Django-style
        → Isochrone 10 Hz superposé
        → Intention: produire sérotonine
        → 36 loops de WFLSQQHER

15:05 - Silence 5 min
        → Intégration, méditation

20:05 - Signal fin (2 notes)
        → Guitare jazz électrique (ancrage)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Résultat attendu:
• TES vibrations guitaristiques uniques
• Protocole scientifique Sternheimer validé
• Gamme sacrée Lydien (Borla)
• Fréquence eau H2O (Marc Henry)
• Isochrone 10 Hz (ondes Alpha-Beta)
• Intention personnelle consciente

= Thérapie sonore totalement UNIQUE et PERSONNALISÉE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 📚 RÉFÉRENCES

**JL Borla** :
- Vidéo gammes Lydien : https://www.youtube.com/watch?v=W07K80mXzcU
- Fa Lydien = stimulant
- Sib Lydien = équilibrant (stimulant + inhibant)
- Mib Lydien = inhibant

**Protéodies Sternheimer** :
- Mapping acides aminés → notes musicales
- Séquences protéiques = mélodies thérapeutiques
- Base scientifique : biologie moléculaire + musicothérapie

**Marc Henry** :
- Diapason H2O : 429.62 Hz (résonance eau structurée)
- Eau = 4ème état de la matière (EZ Water, Gerald Pollack)

**Tomatis** :
- Effet Tomatis : fréquences filtrées pour rééducation auditive
- Approche : écoute active + vibrations corporelles
- Inspiration pour approche guitare live

**Web Audio API** :
- Documentation MDN : https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API
- Specs W3C
- Support navigateurs : Chrome, Safari, Firefox, Edge

---

## 🔥 CONCLUSION

Ce projet fusionne :
- **Science** : Protéodies Sternheimer (biologie moléculaire)
- **Tradition** : Gammes Lydien sacrées (JL Borla)
- **Physique** : Fréquence H2O 429.62 Hz (Marc Henry)
- **Neurologie** : Isochrone 4-14 Hz (ondes cérébrales)
- **Art** : TES enregistrements guitare (manouche + jazz)
- **Intention** : Thérapie personnalisée consciente

= **Outil thérapeutique sonore totalement UNIQUE** 🎸✨

Rendez-vous début août pour créer tout ça ! 🚀

---

**Fichier créé le** : 29 juillet 2026
**Dernière mise à jour** : 29 juillet 2026
**Status** : En attente réponses questions + implémentation août
**Repository** : `/Volumes/SSD/devs/gsgui`
**Branch** : `develop`
