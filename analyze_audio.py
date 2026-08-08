#!/usr/bin/env python3
"""
Analyse complète d'un fichier audio WAV/FLAC
- Métadonnées et propriétés
- Analyse spectrale
- Détection de pitch/notes
- Vérification diapason (440 Hz vs 429.62 Hz)
- Détection effets isochroniques (pulsations LFO)
- Spectrogramme visuel
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Backend non-interactif pour générer des images
from scipy import signal
from scipy.io import wavfile
import sys

def analyze_audio(filepath):
    """Analyse complète d'un fichier audio"""

    print("=" * 80)
    print(f"ANALYSE AUDIO: {filepath}")
    print("=" * 80)

    # 1. LECTURE DU FICHIER
    try:
        sample_rate, audio_data = wavfile.read(filepath)
        print(f"\n✅ Fichier chargé avec succès")
    except Exception as e:
        print(f"\n❌ Erreur de lecture: {e}")
        return

    # 2. MÉTADONNÉES
    print("\n" + "─" * 80)
    print("📊 MÉTADONNÉES")
    print("─" * 80)

    duration = len(audio_data) / sample_rate
    is_stereo = len(audio_data.shape) > 1 and audio_data.shape[1] == 2
    channels = 2 if is_stereo else 1

    print(f"Sample Rate:     {sample_rate} Hz")
    print(f"Durée:           {duration:.2f} secondes ({duration/60:.2f} minutes)")
    print(f"Canaux:          {channels} ({'Stéréo' if is_stereo else 'Mono'})")
    print(f"Échantillons:    {len(audio_data):,}")
    print(f"Résolution:      {audio_data.dtype}")

    # Conversion en mono si stéréo (moyenne des canaux)
    if is_stereo:
        audio_mono = np.mean(audio_data, axis=1)
        audio_left = audio_data[:, 0]
        audio_right = audio_data[:, 1]
    else:
        audio_mono = audio_data
        audio_left = audio_data
        audio_right = audio_data

    # Normalisation
    audio_mono = audio_mono.astype(float)
    if audio_mono.max() > 0:
        audio_mono = audio_mono / np.abs(audio_mono).max()

    # 3. ANALYSE DYNAMIQUE
    print("\n" + "─" * 80)
    print("📈 DYNAMIQUE")
    print("─" * 80)

    rms = np.sqrt(np.mean(audio_mono**2))
    peak = np.max(np.abs(audio_mono))

    print(f"RMS (niveau moyen): {rms:.4f} ({20*np.log10(rms+1e-10):.2f} dB)")
    print(f"Peak (niveau max):  {peak:.4f} ({20*np.log10(peak+1e-10):.2f} dB)")
    print(f"Crest Factor:       {peak/rms:.2f}")

    # 4. ANALYSE SPECTRALE (FFT)
    print("\n" + "─" * 80)
    print("🎵 ANALYSE SPECTRALE (FFT)")
    print("─" * 80)

    # FFT sur tout le signal (ou un extrait si trop long)
    analysis_samples = min(len(audio_mono), sample_rate * 10)  # Max 10 secondes
    fft_data = np.fft.fft(audio_mono[:analysis_samples])
    fft_freq = np.fft.fftfreq(analysis_samples, 1/sample_rate)

    # Gardons seulement les fréquences positives
    positive_freq_idx = fft_freq > 0
    fft_freq_pos = fft_freq[positive_freq_idx]
    fft_magnitude = np.abs(fft_data[positive_freq_idx])

    # Trouver les pics de fréquence
    freq_threshold = np.max(fft_magnitude) * 0.1  # 10% du pic max
    peaks_idx = signal.find_peaks(fft_magnitude, height=freq_threshold, distance=10)[0]

    # Trier par magnitude
    peaks_idx_sorted = peaks_idx[np.argsort(fft_magnitude[peaks_idx])[::-1]]

    print(f"\nTop 10 fréquences détectées:")
    for i, idx in enumerate(peaks_idx_sorted[:10]):
        freq = fft_freq_pos[idx]
        mag = fft_magnitude[idx]
        mag_db = 20 * np.log10(mag / fft_magnitude.max())

        # Essayer de détecter la note MIDI correspondante
        if freq > 20:  # Éviter les très basses fréquences
            midi_note = 69 + 12 * np.log2(freq / 440)
            note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
            note_idx = int(round(midi_note)) % 12
            octave = int(round(midi_note)) // 12 - 1
            note_name = f"{note_names[note_idx]}{octave}"

            print(f"  {i+1:2d}. {freq:8.2f} Hz  ({mag_db:6.2f} dB)  ≈ {note_name} (MIDI {int(round(midi_note))})")
        else:
            print(f"  {i+1:2d}. {freq:8.2f} Hz  ({mag_db:6.2f} dB)")

    # 5. VÉRIFICATION DIAPASON
    print("\n" + "─" * 80)
    print("🎼 VÉRIFICATION DIAPASON")
    print("─" * 80)

    # Chercher un La autour de 440 Hz ou 429.62 Hz
    a4_440_range = (435, 445)
    a4_h3o2_range = (425, 434)

    a4_440_idx = np.where((fft_freq_pos >= a4_440_range[0]) & (fft_freq_pos <= a4_440_range[1]))[0]
    a4_h3o2_idx = np.where((fft_freq_pos >= a4_h3o2_range[0]) & (fft_freq_pos <= a4_h3o2_range[1]))[0]

    if len(a4_440_idx) > 0:
        max_440_idx = a4_440_idx[np.argmax(fft_magnitude[a4_440_idx])]
        a4_440_detected = fft_freq_pos[max_440_idx]
        a4_440_mag = fft_magnitude[max_440_idx]
        print(f"La4 Standard (440 Hz):  {a4_440_detected:.2f} Hz (magnitude: {a4_440_mag:.0f})")
    else:
        a4_440_detected = None
        print(f"La4 Standard (440 Hz):  Non détecté")

    if len(a4_h3o2_idx) > 0:
        max_h3o2_idx = a4_h3o2_idx[np.argmax(fft_magnitude[a4_h3o2_idx])]
        a4_h3o2_detected = fft_freq_pos[max_h3o2_idx]
        a4_h3o2_mag = fft_magnitude[max_h3o2_idx]
        print(f"La4 h3O2 (429.62 Hz):   {a4_h3o2_detected:.2f} Hz (magnitude: {a4_h3o2_mag:.0f})")
    else:
        a4_h3o2_detected = None
        print(f"La4 h3O2 (429.62 Hz):   Non détecté")

    # Déterminer quel diapason est le plus probable
    if a4_440_detected and a4_h3o2_detected:
        if a4_440_mag > a4_h3o2_mag:
            print(f"\n→ Diapason probable: Standard 440 Hz")
        else:
            print(f"\n→ Diapason probable: h3O2 429.62 Hz")
    elif a4_440_detected:
        print(f"\n→ Diapason probable: Standard 440 Hz")
    elif a4_h3o2_detected:
        print(f"\n→ Diapason probable: h3O2 429.62 Hz")
    else:
        print(f"\n→ Aucun La4 détecté (pas de référence diapason claire)")

    # 6. DÉTECTION EFFETS ISOCHRONIQUES (pulsations 4-14 Hz)
    print("\n" + "─" * 80)
    print("🌊 DÉTECTION EFFETS ISOCHRONIQUES (LFO 4-14 Hz)")
    print("─" * 80)

    # Analyse de l'enveloppe d'amplitude
    # Calcul de l'enveloppe via Hilbert Transform
    analytic_signal = signal.hilbert(audio_mono[:analysis_samples])
    amplitude_envelope = np.abs(analytic_signal)

    # FFT de l'enveloppe pour détecter les modulations
    envelope_fft = np.fft.fft(amplitude_envelope)
    envelope_freq = np.fft.fftfreq(len(amplitude_envelope), 1/sample_rate)

    # Chercher dans la plage 4-14 Hz
    lfo_range = (4, 14)
    lfo_idx = np.where((envelope_freq >= lfo_range[0]) & (envelope_freq <= lfo_range[1]))[0]

    if len(lfo_idx) > 0:
        lfo_magnitude = np.abs(envelope_fft[lfo_idx])
        max_lfo_idx = lfo_idx[np.argmax(lfo_magnitude)]
        lfo_freq_detected = envelope_freq[max_lfo_idx]
        lfo_mag = lfo_magnitude[np.argmax(lfo_magnitude)]

        print(f"Fréquence LFO détectée: {lfo_freq_detected:.2f} Hz (magnitude: {lfo_mag:.0f})")

        # Correspondance avec les packs proteodies
        pack_freqs = {
            '🌺 Hibiscus Canicule': 12,
            '🫘 Rénal K+/Créatinine': 6,
            '💦 Peau Sèche': 8,
        }

        min_diff = float('inf')
        matching_pack = None
        for pack_name, pack_freq in pack_freqs.items():
            diff = abs(lfo_freq_detected - pack_freq)
            if diff < min_diff:
                min_diff = diff
                matching_pack = pack_name

        if min_diff < 1.0:  # Tolérance de 1 Hz
            print(f"→ Correspond au pack: {matching_pack} ({pack_freqs[matching_pack]} Hz)")
        else:
            print(f"→ Ne correspond pas exactement aux packs connus")
    else:
        print(f"Aucune modulation LFO détectée dans la plage 4-14 Hz")

    # 7. SPECTROGRAMME
    print("\n" + "─" * 80)
    print("📊 GÉNÉRATION DU SPECTROGRAMME")
    print("─" * 80)

    # Créer le spectrogramme
    fig, axes = plt.subplots(3, 1, figsize=(14, 10))

    # Plot 1: Forme d'onde
    time_axis = np.arange(len(audio_mono)) / sample_rate
    axes[0].plot(time_axis, audio_mono, color='#1D9E75', linewidth=0.5)
    axes[0].set_xlabel('Temps (s)')
    axes[0].set_ylabel('Amplitude')
    axes[0].set_title('Forme d\'onde')
    axes[0].grid(True, alpha=0.3)
    axes[0].set_xlim(0, duration)

    # Plot 2: Spectrogramme
    frequencies, times, Sxx = signal.spectrogram(audio_mono, sample_rate, nperseg=2048)
    im = axes[1].pcolormesh(times, frequencies, 10 * np.log10(Sxx + 1e-10),
                             shading='gouraud', cmap='viridis')
    axes[1].set_ylabel('Fréquence (Hz)')
    axes[1].set_xlabel('Temps (s)')
    axes[1].set_title('Spectrogramme')
    axes[1].set_ylim(0, 2000)  # Limiter à 2000 Hz pour mieux voir les notes
    plt.colorbar(im, ax=axes[1], label='Puissance (dB)')

    # Plot 3: Spectre de puissance moyen
    axes[2].plot(fft_freq_pos, 20 * np.log10(fft_magnitude / fft_magnitude.max()),
                 color='#F97316', linewidth=1)
    axes[2].set_xlabel('Fréquence (Hz)')
    axes[2].set_ylabel('Magnitude (dB)')
    axes[2].set_title('Spectre de puissance')
    axes[2].grid(True, alpha=0.3)
    axes[2].set_xlim(0, 2000)
    axes[2].set_ylim(-60, 0)

    # Marquer les pics principaux
    for idx in peaks_idx_sorted[:5]:
        freq = fft_freq_pos[idx]
        if freq < 2000:
            axes[2].axvline(freq, color='red', linestyle='--', alpha=0.5, linewidth=0.8)

    plt.tight_layout()

    output_path = filepath.replace('.wav', '_analysis.png').replace('.flac', '_analysis.png')
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\n✅ Spectrogramme sauvegardé: {output_path}")

    print("\n" + "=" * 80)
    print("ANALYSE TERMINÉE")
    print("=" * 80)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    else:
        filepath = '/Volumes/SSD/devs/gsgui/dsip_bip.wav'

    analyze_audio(filepath)
