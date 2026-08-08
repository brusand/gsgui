#!/usr/bin/env python3
"""
Analyse détaillée multi-fréquences du LFO
Détecte plusieurs modulations simultanées
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
from scipy.io import wavfile
from scipy import signal
import sys

def analyze_lfo_detailed(filepath):
    """Analyse détaillée de l'enveloppe pour détecter LFO multiples"""

    print("=" * 80)
    print(f"ANALYSE LFO DÉTAILLÉE: {filepath}")
    print("=" * 80)

    # Lecture
    sample_rate, audio_data = wavfile.read(filepath)
    duration = len(audio_data) / sample_rate

    # Mono
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

    # 1. Extraction de l'enveloppe d'amplitude
    print("\n" + "─" * 80)
    print("EXTRACTION ENVELOPPE D'AMPLITUDE")
    print("─" * 80)

    # Hilbert transform pour l'enveloppe
    analytic_signal = signal.hilbert(audio_mono)
    amplitude_envelope = np.abs(analytic_signal)

    # Lissage pour enlever les hautes fréquences
    window_size = int(sample_rate * 0.01)  # 10ms
    if window_size % 2 == 0:
        window_size += 1
    amplitude_envelope_smooth = signal.savgol_filter(amplitude_envelope, window_size, 3)

    print(f"Enveloppe extraite : {len(amplitude_envelope)} échantillons")

    # 2. FFT de l'enveloppe (détection LFO)
    print("\n" + "─" * 80)
    print("ANALYSE SPECTRALE DE L'ENVELOPPE (LFO)")
    print("─" * 80)

    # FFT de l'enveloppe
    envelope_fft = np.fft.rfft(amplitude_envelope_smooth)
    envelope_freq = np.fft.rfftfreq(len(amplitude_envelope_smooth), 1/sample_rate)
    envelope_magnitude = np.abs(envelope_fft)

    # Focus sur 0-20 Hz
    lfo_range_idx = (envelope_freq >= 0.5) & (envelope_freq <= 20)
    lfo_freqs = envelope_freq[lfo_range_idx]
    lfo_mags = envelope_magnitude[lfo_range_idx]

    # Trouver les pics
    peaks_idx, properties = signal.find_peaks(lfo_mags, height=np.max(lfo_mags) * 0.05, distance=5)

    print(f"\nPics LFO détectés (0.5-20 Hz):")
    print(f"\n{'#':<4} {'Fréquence':<12} {'Magnitude':<12} {'Interprétation':<30}")
    print("─" * 70)

    # Références
    lfo_references = {
        (3.5, 4.5): "😴 Sommeil DSIP (ondes Delta)",
        (5.5, 6.5): "🫘 Rénal K+/Créatinine",
        (7.5, 8.5): "💦 Peau Sèche",
        (11.5, 12.5): "🌺 Hibiscus Canicule",
    }

    if len(peaks_idx) > 0:
        # Trier par magnitude
        sorted_peaks = sorted(peaks_idx, key=lambda i: lfo_mags[i], reverse=True)

        for rank, idx in enumerate(sorted_peaks[:10], 1):
            freq = lfo_freqs[idx]
            mag = lfo_mags[idx]
            mag_percent = (mag / np.max(lfo_mags)) * 100

            # Trouver la référence
            interpretation = ""
            for (freq_min, freq_max), label in lfo_references.items():
                if freq_min <= freq <= freq_max:
                    interpretation = label
                    break

            print(f"{rank:<4} {freq:>7.2f} Hz   {mag:>10.0f} ({mag_percent:>5.1f}%)  {interpretation}")
    else:
        print("Aucun pic LFO détecté")

    # 3. Vérification spécifique 3-5 Hz (Delta waves)
    print("\n" + "─" * 80)
    print("VÉRIFICATION PLAGE DELTA (3-5 Hz)")
    print("─" * 80)

    delta_range_idx = (envelope_freq >= 3.0) & (envelope_freq <= 5.0)
    delta_freqs = envelope_freq[delta_range_idx]
    delta_mags = envelope_magnitude[delta_range_idx]

    if len(delta_mags) > 0:
        max_delta_idx = np.argmax(delta_mags)
        max_delta_freq = delta_freqs[max_delta_idx]
        max_delta_mag = delta_mags[max_delta_idx]

        # Comparer avec le pic global
        global_max = np.max(lfo_mags)

        print(f"Fréquence Delta maximale: {max_delta_freq:.2f} Hz")
        print(f"Magnitude: {max_delta_mag:.0f}")
        print(f"Ratio vs pic global: {(max_delta_mag/global_max)*100:.1f}%")

        if max_delta_mag / global_max > 0.3:
            print(f"\n✅ LFO Delta présent et significatif (>30% du pic principal)")
        else:
            print(f"\n⚠️  LFO Delta faible ou absent (<30% du pic principal)")
    else:
        print("❌ Aucune modulation détectée dans la plage Delta (3-5 Hz)")

    # 4. Visualisation
    print("\n" + "─" * 80)
    print("GÉNÉRATION GRAPHIQUE")
    print("─" * 80)

    fig, axes = plt.subplots(3, 1, figsize=(14, 10))

    # Plot 1: Signal audio original (extrait)
    extract_duration = min(2.0, duration)  # 2 premières secondes
    extract_samples = int(extract_duration * sample_rate)
    time_extract = np.arange(extract_samples) / sample_rate

    axes[0].plot(time_extract, audio_mono[:extract_samples], color='#1D9E75', linewidth=0.5, alpha=0.7)
    axes[0].plot(time_extract, amplitude_envelope_smooth[:extract_samples],
                 color='#F97316', linewidth=2, label='Enveloppe')
    axes[0].set_xlabel('Temps (s)')
    axes[0].set_ylabel('Amplitude')
    axes[0].set_title('Signal audio + Enveloppe d\'amplitude (2 premières secondes)')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Plot 2: Spectre LFO complet (0-20 Hz)
    axes[1].plot(lfo_freqs, lfo_mags, color='#8B5CF6', linewidth=1.5)
    axes[1].fill_between(lfo_freqs, lfo_mags, alpha=0.3, color='#8B5CF6')

    # Marquer les pics
    if len(peaks_idx) > 0:
        for idx in peaks_idx:
            axes[1].axvline(lfo_freqs[idx], color='red', linestyle='--', alpha=0.5, linewidth=1)
            axes[1].text(lfo_freqs[idx], lfo_mags[idx], f'{lfo_freqs[idx]:.1f}Hz',
                        rotation=90, va='bottom', ha='right', fontsize=9, color='red')

    # Marquer les zones de référence
    axes[1].axvspan(3.5, 4.5, alpha=0.15, color='blue', label='Delta (DSIP)')
    axes[1].axvspan(5.5, 6.5, alpha=0.15, color='brown', label='Rénal')
    axes[1].axvspan(7.5, 8.5, alpha=0.15, color='cyan', label='Peau Sèche')
    axes[1].axvspan(11.5, 12.5, alpha=0.15, color='pink', label='Hibiscus')

    axes[1].set_xlabel('Fréquence (Hz)')
    axes[1].set_ylabel('Magnitude')
    axes[1].set_title('Spectre LFO (modulations d\'amplitude 0.5-20 Hz)')
    axes[1].legend(loc='upper right', fontsize=8)
    axes[1].grid(True, alpha=0.3)
    axes[1].set_xlim(0.5, 20)

    # Plot 3: Zoom sur plage Delta (3-5 Hz)
    axes[2].plot(delta_freqs, delta_mags, color='#10B981', linewidth=2, marker='o', markersize=3)
    axes[2].fill_between(delta_freqs, delta_mags, alpha=0.3, color='#10B981')
    axes[2].axvline(3.91, color='orange', linestyle='--', linewidth=2, label='Cible: 3.91 Hz')
    axes[2].axvline(4.05, color='orange', linestyle=':', linewidth=2, label='Cible: 4.05 Hz')

    if len(delta_mags) > 0 and max_delta_mag > 0:
        axes[2].axvline(max_delta_freq, color='red', linestyle='-', linewidth=1.5,
                       label=f'Détecté: {max_delta_freq:.2f} Hz')

    axes[2].set_xlabel('Fréquence (Hz)')
    axes[2].set_ylabel('Magnitude')
    axes[2].set_title('Zoom sur plage Delta (3-5 Hz) - DSIP Sommeil')
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)
    axes[2].set_xlim(3.0, 5.0)

    plt.tight_layout()

    output_path = filepath.replace('.wav', '_lfo_detailed.png')
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\n✅ Graphique sauvegardé: {output_path}")

    print("\n" + "=" * 80)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    else:
        filepath = 'sommeil_Dsip_LFO_2.wav'

    analyze_lfo_detailed(filepath)
