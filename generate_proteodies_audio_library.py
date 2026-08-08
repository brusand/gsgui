#!/usr/bin/env python3
"""
Génération automatique bibliothèque audio protéodies
Utilise DawDreamer pour charger Vienna Synchron VST3 et render chaque acide aminé
"""

import os
import json
from pathlib import Path

# NOTE: DawDreamer nécessite installation séparée
# pip install dawdreamer
try:
    from dawdreamer import RenderEngine
    DAWDREAMER_AVAILABLE = True
except ImportError:
    print("⚠️  DawDreamer non installé. Mode simulation activé.")
    print("    Installation: pip install dawdreamer")
    DAWDREAMER_AVAILABLE = False

import numpy as np
from scipy.io import wavfile

# Configuration
SAMPLE_RATE = 44100
BPM = 65
BEAT_DURATION = 60.0 / BPM  # ~0.923 secondes

# Gammes
SCALES = {
    'fa': [41,43,45,47,48,50,52,53,55,57,59,60,62,64,65,67,69,71,72,74],  # Fa Lydien
    'sib': [46,48,50,52,53,55,57,58,60,62,64,65,67,69,70,72,74,76,77,79], # Sib Lydien
    'mib': [51,53,55,57,58,60,62,63,65,67,69,70,72,74,75,77,79,81,82,84], # Mib Lydien
}

# Mapping acides aminés
AMINO_ACIDS = "ACDEFGHIKLMNPQRSTVWY"
AA_MAP = {aa: i for i, aa in enumerate(AMINO_ACIDS)}

# Diapasons (Master Tune offset en cents)
DIAPASONS = {
    'standard': 0,      # 440 Hz
    'h3o2': -24,        # 429.62 Hz
}

# Modes audio et fréquences LFO
AUDIO_MODES = {
    'stereo': None,           # Pas de LFO
    'isochrone_4hz': 4.0,     # Delta (sommeil)
    'isochrone_7hz': 7.0,     # Theta (arthrose, anti-inflammatoire)
    'isochrone_10hz': 10.0,   # Alpha (standard)
    'isochrone_14hz': 14.0,   # Beta (neuro)
}

def midi_to_freq(note, master_tune_cents=0):
    """Convertit note MIDI en fréquence avec offset master tune"""
    return 440.0 * (2 ** ((note - 69 + master_tune_cents/100) / 12))

def generate_sine_wave(freq, duration, sample_rate=44100):
    """Génère onde sinusoïdale avec envelope ADSR et padding crossfade"""
    # Ajouter padding pour crossfade (50ms de chaque côté)
    crossfade_samples = int(0.05 * sample_rate)
    total_duration = duration + (2 * crossfade_samples / sample_rate)

    t = np.linspace(0, total_duration, int(sample_rate * total_duration), False)
    wave = np.sin(2 * np.pi * freq * t)

    # Harmoniques pour timbre plus riche (proche bol tibétain)
    wave += 0.3 * np.sin(2 * np.pi * freq * 2 * t)  # Octave
    wave += 0.2 * np.sin(2 * np.pi * freq * 3 * t)  # Quinte
    wave += 0.1 * np.sin(2 * np.pi * freq * 5 * t)  # Tierce majeure (2 octaves)
    wave = wave / np.max(np.abs(wave))  # Normaliser

    # Envelope ADSR
    attack = int(0.02 * sample_rate)   # 20ms
    decay = int(0.05 * sample_rate)    # 50ms
    sustain_level = 0.85
    release = int(0.1 * sample_rate)   # 100ms

    envelope = np.ones_like(wave)

    # Attack
    envelope[:attack] = np.linspace(0, 1, attack)

    # Decay
    envelope[attack:attack+decay] = np.linspace(1, sustain_level, decay)

    # Sustain (reste du signal jusqu'au release)
    sustain_start = attack + decay
    sustain_end = len(envelope) - release
    envelope[sustain_start:sustain_end] = sustain_level

    # Release
    envelope[-release:] = np.linspace(sustain_level, 0, release)

    # Crossfade zones (fade in/out aux extrémités)
    fade_curve = np.linspace(0, 1, crossfade_samples)
    envelope[:crossfade_samples] *= fade_curve
    envelope[-crossfade_samples:] *= fade_curve[::-1]

    return wave * envelope * 0.6  # -4.4 dB headroom pour LFO

def apply_tremolo(audio, lfo_freq, sample_rate=44100, depth=0.7):
    """Applique effet tremolo (isochrone) avec profondeur ajustable"""
    t = np.linspace(0, len(audio)/sample_rate, len(audio), False)
    # LFO avec profondeur ajustable (depth=0.7 → 30% min, 100% max)
    lfo = (1 - depth) + depth * np.sin(2 * np.pi * lfo_freq * t)
    lfo = np.clip(lfo, 0, 1)  # Sécurité
    return audio * lfo

def generate_with_dawdreamer(vst_path, output_dir):
    """Génération avec Vienna Synchron via DawDreamer"""
    if not DAWDREAMER_AVAILABLE:
        print("❌ DawDreamer requis pour génération VST")
        return False

    print("🎹 Initialisation DawDreamer...")
    engine = RenderEngine(SAMPLE_RATE, 512)

    # Charger Vienna Synchron
    print(f"📦 Chargement VST: {vst_path}")
    synth = engine.make_plugin_processor("vienna", vst_path)

    if not synth:
        print("❌ Impossible de charger Vienna Synchron")
        return False

    # TODO: Identifier param IDs Vienna Synchron
    # synth.get_parameter_count()
    # synth.get_parameter_name(i)

    for diapason_name, tune_cents in DIAPASONS.items():
        print(f"\n🎼 Diapason: {diapason_name} ({tune_cents} cents)")

        # Set master tune
        # synth.set_parameter(PARAM_MASTER_TUNE, tune_cents / 100.0)

        for mode_name, lfo_freq in AUDIO_MODES.items():
            print(f"  🎵 Mode: {mode_name}")

            mode_dir = output_dir / f"{diapason_name}_{mode_name}"
            mode_dir.mkdir(parents=True, exist_ok=True)

            for scale_name, scale_notes in SCALES.items():
                print(f"    🎶 Gamme: {scale_name}")

                scale_dir = mode_dir / scale_name
                scale_dir.mkdir(exist_ok=True)

                for i, aa in enumerate(AMINO_ACIDS):
                    midi_note = scale_notes[i]

                    # Render note
                    engine.load_graph([(synth, [])])
                    synth.clear_midi()
                    synth.add_midi_note(midi_note, 80, 0.0, BEAT_DURATION)

                    audio = engine.render(BEAT_DURATION + 0.5)  # +padding

                    # Appliquer LFO si isochrone
                    if lfo_freq:
                        audio = apply_tremolo(audio[0], lfo_freq, SAMPLE_RATE)
                    else:
                        audio = audio[0]  # Mono ou stereo[0]

                    # Sauvegarder
                    filepath = scale_dir / f"{aa}.wav"
                    wavfile.write(filepath, SAMPLE_RATE,
                                (audio * 32767).astype(np.int16))

                    print(f"      ✅ {aa} → {filepath.name}")

    return True

def generate_with_synthesis(output_dir):
    """Génération avec synthèse sinusoïdale (fallback sans VST)"""
    print("🎹 Génération synthèse sinusoïdale (sans VST)...")

    for diapason_name, tune_cents in DIAPASONS.items():
        print(f"\n🎼 Diapason: {diapason_name}")

        for mode_name, lfo_freq in AUDIO_MODES.items():
            print(f"  🎵 Mode: {mode_name}")

            mode_dir = output_dir / f"{diapason_name}_{mode_name}"
            mode_dir.mkdir(parents=True, exist_ok=True)

            for scale_name, scale_notes in SCALES.items():
                print(f"    🎶 Gamme: {scale_name}")

                scale_dir = mode_dir / scale_name
                scale_dir.mkdir(exist_ok=True)

                for i, aa in enumerate(AMINO_ACIDS):
                    midi_note = scale_notes[i]
                    freq = midi_to_freq(midi_note, tune_cents)

                    # Générer son
                    audio = generate_sine_wave(freq, BEAT_DURATION, SAMPLE_RATE)

                    # Appliquer LFO si isochrone
                    if lfo_freq:
                        audio = apply_tremolo(audio, lfo_freq, SAMPLE_RATE)

                    # Sauvegarder
                    filepath = scale_dir / f"{aa}.wav"
                    wavfile.write(filepath, SAMPLE_RATE,
                                (audio * 32767).astype(np.int16))

                    print(f"      ✅ {aa} → {filepath.name}")

    return True

def generate_manifest(output_dir):
    """Génère manifest.json pour l'application web"""
    manifest = {
        "version": "1.0.0",
        "sample_rate": SAMPLE_RATE,
        "bpm": BPM,
        "beat_duration": BEAT_DURATION,
        "diapasons": DIAPASONS,
        "modes": {k: v for k, v in AUDIO_MODES.items()},
        "scales": SCALES,
        "amino_acids": AMINO_ACIDS,
        "total_samples": len(DIAPASONS) * len(AUDIO_MODES) * len(SCALES) * len(AMINO_ACIDS)
    }

    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)

    print(f"\n📄 Manifest généré: {manifest_path}")
    return manifest

def main():
    print("🧬 Génération bibliothèque audio protéodies")
    print("=" * 60)

    # Configuration chemins
    output_dir = Path("web-ui/public/proteodies/audio/building_blocks")
    output_dir.mkdir(parents=True, exist_ok=True)

    vst_path = "/Library/Audio/Plug-Ins/VST3/Vienna Synchron Player.vst3"

    # Choix méthode génération
    if DAWDREAMER_AVAILABLE and Path(vst_path).exists():
        print("✅ Vienna Synchron détecté")
        success = generate_with_dawdreamer(vst_path, output_dir)
    else:
        if not Path(vst_path).exists():
            print(f"⚠️  Vienna Synchron non trouvé: {vst_path}")
        print("🔄 Fallback: synthèse sinusoïdale")
        success = generate_with_synthesis(output_dir)

    if success:
        # Générer manifest
        manifest = generate_manifest(output_dir)

        print("\n" + "=" * 60)
        print("✅ GÉNÉRATION TERMINÉE")
        print(f"📊 Total samples: {manifest['total_samples']}")
        print(f"💾 Dossier: {output_dir}")
        print(f"📦 Taille estimée: ~{manifest['total_samples'] * 0.05:.1f} MB")
        print("\n💡 Prochaine étape: Intégrer lecture Web Audio API dans index.html")
    else:
        print("\n❌ Échec génération")

if __name__ == "__main__":
    main()
