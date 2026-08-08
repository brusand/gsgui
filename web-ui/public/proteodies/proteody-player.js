/**
 * ProteodyPlayer - Joue les fichiers WAV complets des protéodies
 * Au lieu de générer à la volée avec des samples, charge les WAV pré-générés
 */
class ProteodyPlayer {
  constructor() {
    this.audioContext = null;
    this.isPlaying = false;
    this.stopRequested = false;
    this.currentPlayback = null;
    this.wavCache = new Map(); // Cache des fichiers WAV chargés
  }

  async init() {
    this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
    console.log('🎵 ProteodyPlayer initialisé');
  }

  /**
   * Charge un fichier WAV de protéodie
   */
  async loadProteodyWav(proteodyId, diapason, mode, scale) {
    const filename = `${proteodyId}_${diapason}_${mode}_${scale}.wav`;
    const url = `/proteodies/audio/proteodies/${filename}`;

    // Vérifier cache
    if (this.wavCache.has(url)) {
      return this.wavCache.get(url);
    }

    try {
      const response = await fetch(url);
      if (!response.ok) {
        console.error(`❌ WAV non trouvé: ${url}`);
        return null;
      }

      const arrayBuffer = await response.arrayBuffer();
      const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);

      this.wavCache.set(url, audioBuffer);
      console.log(`✅ WAV chargé: ${filename} (${audioBuffer.duration.toFixed(1)}s)`);

      return audioBuffer;
    } catch (error) {
      console.error(`❌ Erreur chargement ${url}:`, error);
      return null;
    }
  }

  /**
   * Joue un pack complet (liste de protéodies)
   * Chaque protéodie joue une fois, puis on boucle tout le pack
   */
  async playPack(proteodies, options = {}) {
    const {
      diapason = 'h3o2',
      mode = 'isochrone_10hz',
      scale = 'fa',
      duration = 600,
      onProgress = null,
      onComplete = null,
      masterVolume = 0.7
    } = options;

    // Stop lecture précédente
    this.stop();

    // Reprendre AudioContext si suspendu
    if (this.audioContext.state === 'suspended') {
      await this.audioContext.resume();
    }

    this.isPlaying = true;
    this.stopRequested = false;

    // Charger tous les WAV du pack
    console.log(`📦 Chargement ${proteodies.length} protéodies...`);
    const buffers = [];

    for (const proteody of proteodies) {
      const buffer = await this.loadProteodyWav(
        proteody.id,
        diapason,
        mode,
        scale
      );

      if (!buffer) {
        console.error(`❌ Protéodie manquante: ${proteody.id}`);
        this.isPlaying = false;
        return;
      }

      buffers.push(buffer);
    }

    // Calculer durée d'une boucle complète du pack
    const packDuration = buffers.reduce((sum, buf) => sum + buf.duration, 0);
    const numLoops = Math.ceil(duration / packDuration);

    console.log(`🔁 Durée pack: ${packDuration.toFixed(2)}s`);
    console.log(`🔁 Nombre boucles: ${numLoops} pour ${duration}s`);

    // Créer chaîne audio
    const masterGain = this.audioContext.createGain();
    masterGain.gain.value = masterVolume;
    masterGain.connect(this.audioContext.destination);

    // Planifier lecture
    const scheduledSources = [];
    let currentTime = this.audioContext.currentTime + 0.1; // 100ms delay
    const playbackStartTime = currentTime;

    for (let loop = 0; loop < numLoops; loop++) {
      if (this.stopRequested) break;

      for (const buffer of buffers) {
        if (this.stopRequested) break;

        const source = this.audioContext.createBufferSource();
        source.buffer = buffer;
        source.connect(masterGain);

        source.start(currentTime);
        source.stop(currentTime + buffer.duration);

        scheduledSources.push(source);
        currentTime += buffer.duration;
      }
    }

    const playbackEndTime = currentTime;
    const totalDuration = playbackEndTime - playbackStartTime;

    // Stocker références
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
        if (onProgress) onProgress(1.0);
        if (onComplete) onComplete();
        console.log('✅ Lecture terminée');
      }
    };

    console.log(`▶️  Lecture démarrée: ${proteodies.length} protéodies × ${numLoops} boucles`);
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
}
