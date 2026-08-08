/**
 * Module de lecture audio protéodies
 * Charge et joue les samples d'acides aminés avec concaténation temps réel
 */

class ProteodiesAudioPlayer {
  constructor() {
    this.audioContext = null;
    this.sampleCache = new Map();
    this.currentPlayback = null;
    this.manifest = null;
    this.isPlaying = false;
    this.stopRequested = false;
  }

  async init() {
    if (!this.audioContext) {
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
    }

    // Charger manifest
    try {
      const response = await fetch('/proteodies/audio/building_blocks/manifest.json');
      this.manifest = await response.json();
      console.log('🎵 Manifest audio chargé:', this.manifest);
      return true;
    } catch (error) {
      console.warn('⚠️  Manifest audio non disponible:', error);
      return false;
    }
  }

  /**
   * Charge un sample audio depuis le cache ou le serveur
   */
  async loadSample(aa, diapason, mode, scale) {
    const key = `${diapason}_${mode}_${scale}_${aa}`;

    if (this.sampleCache.has(key)) {
      return this.sampleCache.get(key);
    }

    try {
      const url = `/proteodies/audio/building_blocks/${diapason}_${mode}/${scale}/${aa}.wav`;
      const response = await fetch(url);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const arrayBuffer = await response.arrayBuffer();
      const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);

      this.sampleCache.set(key, audioBuffer);
      return audioBuffer;
    } catch (error) {
      console.error(`❌ Erreur chargement sample ${key}:`, error);
      return null;
    }
  }

  /**
   * Pré-charge tous les samples d'une séquence
   */
  async preloadSequence(sequence, diapason, mode, scale, onProgress) {
    const uniqueAA = [...new Set(sequence.split(''))];
    const total = uniqueAA.length;
    let loaded = 0;

    const promises = uniqueAA.map(async aa => {
      const buffer = await this.loadSample(aa, diapason, mode, scale);
      loaded++;
      if (onProgress) {
        onProgress(loaded, total);
      }
      return buffer;
    });

    await Promise.all(promises);
    return true;
  }

  /**
   * Joue une protéodie complète avec répétitions
   */
  async playProteody(sequence, options = {}) {
    const {
      diapason = 'h3o2',
      mode = 'isochrone_7hz',
      scale = 'mib',
      duration = 600,  // 10 minutes par défaut
      onProgress = null,
      onComplete = null,
      masterVolume = 0.7,
      reverbMix = 0.3
    } = options;

    // Stop lecture précédente
    this.stop();

    // Reprendre AudioContext si suspendu
    if (this.audioContext.state === 'suspended') {
      await this.audioContext.resume();
    }

    this.isPlaying = true;
    this.stopRequested = false;

    // Pour les très longues séquences (>500 AA), on tronque pour éviter surcharge mémoire
    const MAX_SEQUENCE_LENGTH = 500;
    let workingSequence = sequence;
    if (sequence.length > MAX_SEQUENCE_LENGTH) {
      console.warn(`⚠️ Séquence très longue (${sequence.length} AA), tronquée à ${MAX_SEQUENCE_LENGTH} AA`);
      workingSequence = sequence.substring(0, MAX_SEQUENCE_LENGTH);
    }

    // Pré-charger samples
    console.log(`🎵 Pré-chargement séquence: ${workingSequence.substring(0, 50)}... (${workingSequence.length} AA)`);
    await this.preloadSequence(workingSequence, diapason, mode, scale,
      (loaded, total) => {
        console.log(`📦 Chargement samples: ${loaded}/${total}`);
      }
    );

    // Charger tous les buffers de la séquence
    const buffers = [];
    for (let aa of workingSequence) {
      const buffer = await this.loadSample(aa, diapason, mode, scale);
      if (!buffer) {
        console.error(`❌ Sample manquant: ${aa}`);
        this.isPlaying = false;
        return;
      }
      buffers.push(buffer);
    }

    // Calculer durée d'une boucle
    const loopDuration = buffers.reduce((sum, buf) => sum + buf.duration, 0);
    const numLoops = Math.ceil(duration / loopDuration);

    console.log(`🔁 Durée boucle: ${loopDuration.toFixed(2)}s`);
    console.log(`🔁 Nombre boucles: ${numLoops} pour ${duration}s`);

    // Créer chaîne audio
    const masterGain = this.audioContext.createGain();
    masterGain.gain.value = masterVolume;
    masterGain.connect(this.audioContext.destination);

    // Reverb optionnel
    let reverbNode = null;
    let dryGain = null;
    let wetGain = null;

    if (reverbMix > 0) {
      const convolver = this.audioContext.createConvolver();
      convolver.buffer = this.createReverbImpulse(2.0, 2.0); // 2s reverb

      dryGain = this.audioContext.createGain();
      wetGain = this.audioContext.createGain();

      dryGain.gain.value = 1 - reverbMix;
      wetGain.gain.value = reverbMix;

      reverbNode = convolver;
    }

    // Planifier lecture
    const scheduledSources = [];
    let currentTime = this.audioContext.currentTime + 0.1; // 100ms delay démarrage
    const crossfadeDuration = 0.05; // 50ms crossfade

    for (let loop = 0; loop < numLoops; loop++) {
      if (this.stopRequested) break;

      for (let i = 0; i < buffers.length; i++) {
        if (this.stopRequested) break;

        const buffer = buffers[i];
        const source = this.audioContext.createBufferSource();
        source.buffer = buffer;

        // Connecter à la chaîne audio
        if (reverbNode) {
          source.connect(dryGain);
          dryGain.connect(masterGain);

          source.connect(reverbNode);
          reverbNode.connect(wetGain);
          wetGain.connect(masterGain);
        } else {
          source.connect(masterGain);
        }

        // Crossfade avec sample précédent
        if (i > 0 || loop > 0) {
          const gainNode = this.audioContext.createGain();
          gainNode.gain.setValueAtTime(0, currentTime);
          gainNode.gain.linearRampToValueAtTime(1, currentTime + crossfadeDuration);

          source.disconnect();
          source.connect(gainNode);
          gainNode.connect(reverbNode || masterGain);
        }

        source.start(currentTime);
        source.stop(currentTime + buffer.duration);

        scheduledSources.push(source);
        currentTime += buffer.duration - crossfadeDuration; // Overlap pour crossfade
      }
    }

    // Stocker références
    const playbackStartTime = this.audioContext.currentTime;
    const playbackEndTime = currentTime;
    const totalDuration = playbackEndTime - playbackStartTime;

    this.currentPlayback = {
      sources: scheduledSources,
      startTime: playbackStartTime,
      endTime: playbackEndTime,
      masterGain
    };

    // Progression en temps réel
    if (onProgress) {
      const updateProgress = () => {
        if (!this.isPlaying || this.stopRequested) return;

        const elapsed = this.audioContext.currentTime - playbackStartTime;
        const progress = Math.min(elapsed / totalDuration, 1);
        onProgress(progress);

        if (progress < 1) {
          setTimeout(updateProgress, 100); // Update every 100ms
        }
      };
      setTimeout(updateProgress, 100);
    }

    // Callback fin
    const finalSource = scheduledSources[scheduledSources.length - 1];
    finalSource.onended = () => {
      if (!this.stopRequested) {
        this.isPlaying = false;
        if (onProgress) onProgress(1.0); // Ensure 100%
        if (onComplete) onComplete();
        console.log('✅ Lecture terminée');
      }
    };

    console.log(`▶️  Lecture démarrée: ${sequence.substring(0, 20)}...`);
    console.log(`⏱️  Durée totale: ${totalDuration.toFixed(1)}s`);
  }

  /**
   * Arrête la lecture en cours
   */
  stop() {
    this.stopRequested = true;

    if (this.currentPlayback) {
      // Fade out rapide
      if (this.currentPlayback.masterGain) {
        const now = this.audioContext.currentTime;
        this.currentPlayback.masterGain.gain.setValueAtTime(
          this.currentPlayback.masterGain.gain.value, now
        );
        this.currentPlayback.masterGain.gain.linearRampToValueAtTime(0, now + 0.1);
      }

      // Arrêter toutes les sources
      setTimeout(() => {
        if (this.currentPlayback) {
          this.currentPlayback.sources.forEach(source => {
            try {
              source.stop();
            } catch (e) {
              // Source déjà arrêtée
            }
          });
        }
      }, 150);

      this.currentPlayback = null;
    }

    this.isPlaying = false;
    console.log('⏹️  Lecture arrêtée');
  }

  /**
   * Pause/Resume
   */
  async togglePause() {
    if (this.audioContext.state === 'running') {
      await this.audioContext.suspend();
      console.log('⏸️  Pause');
      return true; // paused
    } else {
      await this.audioContext.resume();
      console.log('▶️  Resume');
      return false; // playing
    }
  }

  /**
   * Crée impulse response pour reverb
   */
  createReverbImpulse(duration, decay) {
    const sampleRate = this.audioContext.sampleRate;
    const length = sampleRate * duration;
    const impulse = this.audioContext.createBuffer(2, length, sampleRate);

    for (let channel = 0; channel < 2; channel++) {
      const channelData = impulse.getChannelData(channel);
      for (let i = 0; i < length; i++) {
        // Bruit blanc avec decay exponentiel
        channelData[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / length, decay);
      }
    }

    return impulse;
  }

  /**
   * Génère un sample de test (synthèse sinusoïdale)
   */
  generateTestSample(freq, duration = 1.0) {
    const sampleRate = this.audioContext.sampleRate;
    const buffer = this.audioContext.createBuffer(1, sampleRate * duration, sampleRate);
    const data = buffer.getChannelData(0);

    for (let i = 0; i < data.length; i++) {
      const t = i / sampleRate;

      // Onde sinusoïdale avec harmoniques
      data[i] = 0.6 * Math.sin(2 * Math.PI * freq * t) +
                0.2 * Math.sin(2 * Math.PI * freq * 2 * t) +
                0.1 * Math.sin(2 * Math.PI * freq * 3 * t);

      // Envelope
      const attack = 0.02;
      const release = 0.1;

      if (t < attack) {
        data[i] *= t / attack;
      } else if (t > duration - release) {
        data[i] *= (duration - t) / release;
      }
    }

    return buffer;
  }

  /**
   * Nettoie les ressources
   */
  destroy() {
    this.stop();
    this.sampleCache.clear();

    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
  }
}

// Export pour utilisation dans index.html
window.ProteodiesAudioPlayer = ProteodiesAudioPlayer;
