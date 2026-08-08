#!/usr/bin/env python3
"""
Détection précise des notes et leur timing dans un fichier audio
Utilise l'analyse pitch par fenêtres temporelles
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
from scipy.io import wavfile
from scipy import signal
import sys

# Configuration DSIP
DSIP_SEQ = 'WAGGDASGE'
DSIP_MIDI = [82, 51, 60, 60, 55, 51, 77, 60, 57]
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

def freq_to_midi(freq):
    """Convertit fréquence Hz en note MIDI"""
    if freq <= 0:
        return 0
    return round(69 + 12 * np.log2(freq / 440))

def midi_to_note_name(midi):
    """Convertit MIDI en nom de note"""
    note_idx = int(midi) % 12
    octave = (int(midi) // 12) - 1
    return f"{NOTE_NAMES[note_idx]}{octave}"

def detect_pitch_yin(audio_chunk, sample_rate):
    """
    Détection de pitch avec algorithme YIN simplifié
    Retourne la fréquence fondamentale
    """
    # Autocorrélation
    autocorr = np.correlate(audio_chunk, audio_chunk, mode='full')
    autocorr = autocorr[len(autocorr)//2:]

    # Normalisation
    if autocorr[0] == 0:
        return 0
    autocorr = autocorr / autocorr[0]

    # Trouver le premier minimum local
    diff = np.diff(autocorr)

    # Chercher dans la plage 50-2000 Hz
    min_period = int(sample_rate / 2000)
    max_period = int(sample_rate / 50)

    if max_period >= len(autocorr):
        max_period = len(autocorr) - 1

    # Trouver le premier pic après le minimum
    start = min_period
    peaks = []
    for i in range(start, min(max_period, len(autocorr)-1)):
        if autocorr[i] > 0.7:  # Seuil de corrélation
            peaks.append((i, autocorr[i]))

    if not peaks:
        return 0

    # Prendre le pic avec la meilleure corrélation
    best_peak = max(peaks, key=lambda x: x[1])
    period = best_peak[0]

    freq = sample_rate / period
    return freq

def analyze_notes_timing(filepath, a4_tuning=429.62):
    """Analyse le timing précis de chaque note"""

    print("=" * 80)
    print(f"DÉTECTION NOTES ET TIMING: {filepath}")
    print("=" * 80)

    # Lecture fichier
    sample_rate, audio_data = wavfile.read(filepath)
    duration = len(audio_data) / sample_rate

    # Conversion mono
    if len(audio_data.shape) > 1:
        audio_mono = np.mean(audio_data, axis=1)
    else:
        audio_mono = audio_data

    # Normalisation
    audio_mono = audio_mono.astype(float)
    if audio_mono.max() > 0:
        audio_mono = audio_mono / np.abs(audio_mono).max()

    print(f"\nDurée: {duration:.2f}s")
    print(f"Sample rate: {sample_rate} Hz")
    print(f"Diapason: {a4_tuning} Hz")

    # Analyse par fenêtres de temps
    window_size = int(sample_rate * 0.1)  # 100ms windows
    hop_size = int(sample_rate * 0.05)    # 50ms hop (overlap)

    num_windows = (len(audio_mono) - window_size) // hop_size

    print(f"\nAnalyse par fenêtres de {window_size/sample_rate*1000:.0f}ms")
    print(f"Nombre de fenêtres: {num_windows}")

    # Détection pitch pour chaque fenêtre
    times = []
    freqs = []
    midis = []
    amplitudes = []

    for i in range(num_windows):
        start = i * hop_size
        end = start + window_size
        chunk = audio_mono[start:end]

        # Amplitude RMS de la fenêtre
        rms = np.sqrt(np.mean(chunk**2))

        # Détection pitch si amplitude suffisante
        if rms > 0.01:  # Seuil de bruit
            freq = detect_pitch_yin(chunk, sample_rate)

            if freq > 50 and freq < 2000:  # Plage valide
                time = start / sample_rate
                midi = freq_to_midi(freq * (440 / a4_tuning))  # Ajustement diapason

                times.append(time)
                freqs.append(freq)
                midis.append(midi)
                amplitudes.append(rms)

    # Regrouper les détections en notes continues
    print("\n" + "─" * 80)
    print("NOTES DÉTECTÉES")
    print("─" * 80)
    print(f"\n{'#':<4} {'Temps':<12} {'Durée':<10} {'MIDI':<6} {'Note':<8} {'Freq':<10} {'AA':<4}")
    print("─" * 80)

    if not times:
        print("❌ Aucune note détectée")
        return

    # Grouper les fenêtres consécutives avec le même MIDI
    notes_detected = []
    current_midi = midis[0]
    start_time = times[0]
    end_time = times[0]
    freq_sum = freqs[0]
    freq_count = 1

    for i in range(1, len(times)):
        time_gap = times[i] - times[i-1]
        midi_diff = abs(midis[i] - current_midi)

        # Si même note (tolérance 1 semitone) et pas de gap temporel
        if midi_diff <= 1 and time_gap < 0.15:
            end_time = times[i]
            freq_sum += freqs[i]
            freq_count += 1
        else:
            # Nouvelle note
            avg_freq = freq_sum / freq_count
            duration = end_time - start_time + 0.05  # +hop_size

            notes_detected.append({
                'start': start_time,
                'end': end_time,
                'duration': duration,
                'midi': current_midi,
                'freq': avg_freq
            })

            # Recommencer
            current_midi = midis[i]
            start_time = times[i]
            end_time = times[i]
            freq_sum = freqs[i]
            freq_count = 1

    # Dernière note
    avg_freq = freq_sum / freq_count
    duration = end_time - start_time + 0.05
    notes_detected.append({
        'start': start_time,
        'end': end_time,
        'duration': duration,
        'midi': current_midi,
        'freq': avg_freq
    })

    # Afficher les notes détectées
    bpm = 65
    beat_duration = 60 / bpm  # 0.923s par noire

    for i, note in enumerate(notes_detected):
        note_name = midi_to_note_name(note['midi'])
        beats = note['duration'] / beat_duration

        # Trouver l'acide aminé correspondant
        aa = '?'
        if note['midi'] in DSIP_MIDI:
            idx = DSIP_MIDI.index(note['midi'])
            aa = DSIP_SEQ[idx]

        print(f"{i+1:<4} {note['start']:>6.2f}s - {note['end']:>5.2f}s   {note['duration']:>5.2f}s ({beats:>4.1f}♩)  "
              f"{note['midi']:<6} {note_name:<8} {note['freq']:>7.1f} Hz {aa:<4}")

    # Statistiques
    print("\n" + "─" * 80)
    print("STATISTIQUES")
    print("─" * 80)

    total_notes = len(notes_detected)
    total_duration = sum(n['duration'] for n in notes_detected)
    avg_duration = total_duration / total_notes if total_notes > 0 else 0

    print(f"\nNotes détectées:        {total_notes}")
    print(f"Durée totale audio:     {duration:.2f}s")
    print(f"Durée totale notes:     {total_duration:.2f}s")
    print(f"Durée moyenne/note:     {avg_duration:.2f}s ({avg_duration/beat_duration:.1f} temps)")

    print(f"\nSéquence DSIP attendue: {DSIP_SEQ} (9 notes)")
    print(f"Notes MIDI attendues:   {DSIP_MIDI}")

    # Comparaison avec DSIP
    print("\n" + "─" * 80)
    print("COMPARAISON AVEC SÉQUENCE DSIP")
    print("─" * 80)

    detected_midis = [n['midi'] for n in notes_detected]

    print(f"\nNotes détectées: {detected_midis}")
    print(f"Notes attendues: {DSIP_MIDI}")

    matches = 0
    for i, expected_midi in enumerate(DSIP_MIDI):
        if i < len(detected_midis):
            detected = detected_midis[i]
            if abs(detected - expected_midi) <= 1:
                matches += 1
                print(f"  ✅ Note {i+1}: {detected} ≈ {expected_midi} ({DSIP_SEQ[i]})")
            else:
                print(f"  ❌ Note {i+1}: {detected} ≠ {expected_midi} ({DSIP_SEQ[i]})")
        else:
            print(f"  ❌ Note {i+1}: MANQUANTE (attendu: {expected_midi} = {DSIP_SEQ[i]})")

    if total_notes > len(DSIP_MIDI):
        print(f"\n⚠️  {total_notes - len(DSIP_MIDI)} note(s) en trop détectée(s)")

    print(f"\n{'✅' if matches == len(DSIP_MIDI) else '⚠️ '} Correspondance: {matches}/{len(DSIP_MIDI)} notes")

    # Visualisation
    print("\n" + "─" * 80)
    print("GÉNÉRATION GRAPHIQUE")
    print("─" * 80)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8))

    # Plot 1: Notes dans le temps
    for i, note in enumerate(notes_detected):
        ax1.barh(note['midi'], note['duration'], left=note['start'],
                height=2, alpha=0.7, color='#1D9E75', edgecolor='white', linewidth=0.5)
        ax1.text(note['start'] + note['duration']/2, note['midi'],
                f"{i+1}", ha='center', va='center', fontsize=9, fontweight='bold')

    # Marquer les notes attendues DSIP
    for midi in set(DSIP_MIDI):
        ax1.axhline(midi, color='orange', linestyle='--', alpha=0.3, linewidth=1)

    ax1.set_xlabel('Temps (s)')
    ax1.set_ylabel('Note MIDI')
    ax1.set_title('Timeline des notes détectées')
    ax1.grid(True, alpha=0.3, axis='x')
    ax1.set_xlim(0, duration)

    # Plot 2: Durée des notes
    note_indices = range(1, len(notes_detected) + 1)
    durations = [n['duration'] for n in notes_detected]
    beats = [d / beat_duration for d in durations]

    bars = ax2.bar(note_indices, beats, color='#F97316', alpha=0.7, edgecolor='white', linewidth=1)

    # Ligne de référence à 1 temps et 2 temps
    ax2.axhline(1, color='green', linestyle='--', alpha=0.5, linewidth=1.5, label='1 temps (noire)')
    ax2.axhline(2, color='red', linestyle='--', alpha=0.5, linewidth=1.5, label='2 temps (blanche)')

    ax2.set_xlabel('Numéro de note')
    ax2.set_ylabel('Durée (en temps)')
    ax2.set_title('Durée de chaque note (en temps/noires)')
    ax2.legend()
    ax2.grid(True, alpha=0.3, axis='y')

    # Annoter les notes
    for i, (bar, note) in enumerate(zip(bars, notes_detected)):
        note_name = midi_to_note_name(note['midi'])
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                f"{note_name}\n{beats[i]:.1f}♩", ha='center', va='bottom', fontsize=8)

    plt.tight_layout()

    output_path = filepath.replace('.wav', '_notes_timing.png')
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\n✅ Graphique sauvegardé: {output_path}")

    print("\n" + "=" * 80)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    else:
        filepath = 'sommeil_Dsip.wav'

    analyze_notes_timing(filepath, a4_tuning=429.62)
