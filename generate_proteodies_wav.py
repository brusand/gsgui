#!/usr/bin/env python3
"""
Génère les fichiers WAV complets pour chaque protéodie
Format: {proteody_id}_{diapason}_{mode}_{scale}.wav
"""

import os
import json
import numpy as np
from scipy.io import wavfile
from pathlib import Path

# Config
SAMPLE_RATE = 44100
BPM = 65
BEAT_DURATION = 60.0 / BPM  # ~0.923s

# Table Sternheimer/Borla (JS v1) : note fixe par acide aminé, colonnes
# stimulante (STIM) et inhibante (INH). U (Sec) et O (Pyl) n'ont pas de note.
AA_TO_NOTE = {
    'G': (57, 77), 'A': (60, 62), 'S': (64, 70), 'P': (65, 69),
    'V': (65, 69), 'T': (65, 69), 'C': (65, 69), 'I': (67, 67),
    'L': (67, 67), 'N': (67, 67), 'D': (67, 67), 'Q': (69, 65),
    'K': (69, 65), 'E': (69, 65), 'M': (69, 65), 'H': (70, 64),
    'F': (71, 63), 'R': (72, 62), 'Y': (72, 62), 'W': (74, 60),
}

def note_for_aa(aa, scale):
    """Note MIDI Borla pour un acide aminé selon la gamme du pack
    (fa=stimulant, mib=inhibant, sib=équilibrant = moyenne des deux)"""
    if aa not in AA_TO_NOTE:
        return None
    stim, inh = AA_TO_NOTE[aa]
    if scale == 'fa':
        return stim
    if scale == 'mib':
        return inh
    return round((stim + inh) / 2)

# Diapasons (cents)
DIAPASONS = {
    'standard': 0,
    'h3o2': -24
}

def midi_to_freq(midi_note, cents=0):
    """Convertit note MIDI en fréquence Hz avec détune en cents"""
    return 440.0 * (2.0 ** ((midi_note - 69 + cents/100.0) / 12.0))

def generate_tone(freq, duration, sample_rate=44100, harmonics=True):
    """Génère une note avec harmoniques et envelope ADSR"""
    t = np.linspace(0, duration, int(sample_rate * duration), False)

    # Fondamentale + harmoniques
    wave = np.sin(2 * np.pi * freq * t)
    if harmonics:
        wave += 0.3 * np.sin(2 * np.pi * freq * 2 * t)  # Octave
        wave += 0.2 * np.sin(2 * np.pi * freq * 3 * t)  # Quinte
        wave += 0.1 * np.sin(2 * np.pi * freq * 5 * t)  # Tierce

    # ADSR envelope
    attack = int(0.05 * sample_rate)
    decay = int(0.1 * sample_rate)
    release = int(0.1 * sample_rate)

    envelope = np.ones_like(wave)

    # Attack
    if len(envelope) > attack:
        envelope[:attack] = np.linspace(0, 1, attack)

    # Decay to sustain
    if len(envelope) > attack + decay:
        envelope[attack:attack+decay] = np.linspace(1, 0.7, decay)

    # Sustain
    if len(envelope) > attack + decay:
        envelope[attack+decay:-release] = 0.7

    # Release
    if len(envelope) > release:
        envelope[-release:] = np.linspace(0.7, 0, release)

    return wave * envelope

def apply_isochronic(audio, freq_hz, sample_rate=44100):
    """Applique modulation isochronique (amplitude)"""
    t = np.linspace(0, len(audio) / sample_rate, len(audio), False)
    lfo = 0.5 + 0.5 * np.sin(2 * np.pi * freq_hz * t)
    return audio * lfo

def sequence_to_audio(sequence, scale='fa', diapason='h3o2', mode='isochrone_10hz'):
    """Convertit une séquence AA en audio"""

    cents = DIAPASONS[diapason]

    # Extraire fréquence LFO du mode
    lfo_freq = None
    if mode.startswith('isochrone_'):
        lfo_freq = float(mode.replace('isochrone_', '').replace('hz', ''))

    audio_parts = []

    for aa in sequence:
        # Mapper AA -> note Borla (STIM/INH) selon la gamme du pack
        final_midi = note_for_aa(aa, scale)
        if final_midi is None:
            continue

        # Convertir en fréquence
        freq = midi_to_freq(final_midi, cents)

        # Générer le son
        tone = generate_tone(freq, BEAT_DURATION, SAMPLE_RATE)

        # Appliquer LFO si mode isochronique
        if lfo_freq:
            tone = apply_isochronic(tone, lfo_freq, SAMPLE_RATE)

        audio_parts.append(tone)

    # Concaténer avec crossfade
    if not audio_parts:
        return np.array([])

    crossfade_samples = int(0.05 * SAMPLE_RATE)  # 50ms
    result = audio_parts[0]

    for i in range(1, len(audio_parts)):
        # Crossfade
        fade_out = np.linspace(1, 0, crossfade_samples)
        fade_in = np.linspace(0, 1, crossfade_samples)

        overlap = len(result) - crossfade_samples
        if overlap < 0:
            result = np.concatenate([result, audio_parts[i]])
        else:
            result[-crossfade_samples:] *= fade_out
            result[-crossfade_samples:] += audio_parts[i][:crossfade_samples] * fade_in
            result = np.concatenate([result, audio_parts[i][crossfade_samples:]])

    # Normaliser
    result = result / np.max(np.abs(result)) * 0.8

    return result

def generate_proteody_wav(proteody, pack_id, output_dir):
    """Génère les fichiers WAV pour une protéodie"""

    proteody_id = proteody['id']
    sequence = proteody['seq']

    print(f"  🧬 {proteody_id} ({len(sequence)} AA)")

    # Charger config pack pour mode/scale par défaut
    pack_file = f'web-ui/public/proteodies_audio/packs/{pack_id}.json'
    with open(pack_file, 'r') as f:
        pack_data = json.load(f)

    default_mode = pack_data['mode']
    default_scale = pack_data['scale']

    # Générer pour diapason h3o2 + mode/scale du pack
    diapason = 'h3o2'
    mode = default_mode
    scale = default_scale

    filename = f"{proteody_id}_{diapason}_{mode}_{scale}.wav"
    filepath = output_dir / filename

    if filepath.exists():
        print(f"    ⏭️  Existe déjà: {filename}")
        return

    # Générer audio
    audio = sequence_to_audio(sequence, scale, diapason, mode)

    if len(audio) == 0:
        print(f"    ❌ Séquence vide")
        return

    # Convertir en int16
    audio_int16 = (audio * 32767).astype(np.int16)

    # Sauvegarder
    wavfile.write(filepath, SAMPLE_RATE, audio_int16)

    duration = len(audio) / SAMPLE_RATE
    size_mb = filepath.stat().st_size / (1024 * 1024)
    print(f"    ✅ {filename} ({duration:.1f}s, {size_mb:.2f} MB)")

def main():
    # Créer répertoire output
    output_dir = Path('web-ui/public/proteodies/audio/proteodies')
    output_dir.mkdir(parents=True, exist_ok=True)

    print("🎵 Génération des fichiers WAV des protéodies\n")

    # Charger l'index des packs
    packs_index_file = 'web-ui/public/proteodies_audio/packs-index.json'
    with open(packs_index_file, 'r') as f:
        packs_index = json.load(f)

    total_proteodies = 0
    total_generated = 0

    # Pour chaque pack
    for pack in packs_index:
        pack_id = pack['id']
        pack_name = pack['name']

        print(f"📦 {pack_name} ({pack['count']} protéodies)")

        # Charger pack complet
        pack_file = f'web-ui/public/proteodies_audio/packs/{pack_id}.json'
        with open(pack_file, 'r') as f:
            pack_data = json.load(f)

        # Générer WAV pour chaque protéodie
        for proteody in pack_data['proteodies']:
            total_proteodies += 1
            generate_proteody_wav(proteody, pack_id, output_dir)
            total_generated += 1

        print()

    print(f"✅ Génération terminée")
    print(f"📊 {total_generated}/{total_proteodies} protéodies")
    print(f"📁 Dossier: {output_dir}")

if __name__ == '__main__':
    main()
