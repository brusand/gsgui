#!/usr/bin/env python3
"""
Génère le fichier MIDI DSIP complet pour 20 minutes
Avec les durées correctes: W et E sur 2 temps, les autres sur 1 temps
"""

import struct

# Table Sternheimer/Borla (JS v1) : note fixe par acide aminé, colonnes
# stimulante (STIM) et inhibante (INH). U (Sec) et O (Pyl) n'ont pas de note.
AA_TO_NOTE = {
    'G': (57, 77), 'A': (60, 62), 'S': (64, 70), 'P': (65, 69),
    'V': (65, 69), 'T': (65, 69), 'C': (65, 69), 'I': (67, 67),
    'L': (67, 67), 'N': (67, 67), 'D': (67, 67), 'Q': (69, 65),
    'K': (69, 65), 'E': (69, 65), 'M': (69, 65), 'H': (70, 64),
    'F': (71, 63), 'R': (72, 62), 'Y': (72, 62), 'W': (74, 60),
}

DSIP_SEQ = 'WAGGDASGE'
BPM = 65
SCALE = 'mib'  # calmant -> colonne INH

def midi_for_aa(aa):
    """Calcule la note MIDI Borla pour un acide aminé (colonne INH, gamme mib=calmant)"""
    if aa not in AA_TO_NOTE:
        return 51  # Note par défaut
    stim, inh = AA_TO_NOTE[aa]
    return inh if SCALE == 'mib' else stim

DSIP_MIDI_NOTES = [midi_for_aa(aa) for aa in DSIP_SEQ]  # Notes MIDI Borla (STIM/INH)

# Durées spécifiques (en temps/noires)
# D'après l'analyse audio: W (première) et E (dernière) sont sur 2 temps
NOTE_DURATIONS = [
    2,  # W (Tryptophane) - 2 temps
    1,  # A
    1,  # G
    1,  # G
    1,  # D
    1,  # A
    1,  # S
    1,  # G
    2,  # E (Glutamate) - 2 temps
]

def var_length(value):
    """Encode un entier en variable-length quantity (MIDI standard)"""
    result = bytearray([value & 0x7F])
    value >>= 7
    while value > 0:
        result.insert(0, (value & 0x7F) | 0x80)
        value >>= 7
    return bytes(result)

def generate_dsip_midi_20min(seq, midi_notes, note_durations, bpm, target_duration_min=20):
    """Génère un fichier MIDI DSIP pour la durée cible"""

    ppqn = 480  # Pulses per quarter note
    ticks_per_quarter = ppqn

    # Calculer le nombre de répétitions nécessaires
    beat_duration_seconds = 60 / bpm
    total_beats_per_loop = sum(note_durations)
    loop_duration_seconds = total_beats_per_loop * beat_duration_seconds
    target_duration_seconds = target_duration_min * 60
    num_repetitions = int(target_duration_seconds / loop_duration_seconds) + 1

    print("=" * 80)
    print("GÉNÉRATION MIDI DSIP 20 MINUTES")
    print("=" * 80)
    print(f"\nSéquence:             {seq}")
    print(f"Notes MIDI:           {midi_notes}")
    print(f"Durées (en temps):    {note_durations}")
    print(f"Tempo:                {bpm} BPM")
    print(f"Temps total/boucle:   {total_beats_per_loop} temps")
    print(f"Durée/boucle:         {loop_duration_seconds:.2f}s")
    print(f"Durée cible:          {target_duration_min} minutes ({target_duration_seconds}s)")
    print(f"Répétitions:          {num_repetitions}")
    print(f"Durée finale:         {num_repetitions * loop_duration_seconds / 60:.2f} min")

    # Header chunk
    header = b'MThd'
    header += struct.pack('>I', 6)  # Header length
    header += struct.pack('>H', 0)  # Format 0 (single track)
    header += struct.pack('>H', 1)  # Number of tracks
    header += struct.pack('>H', ppqn)

    # Track chunk
    track_events = bytearray()

    # Tempo meta event
    tempo_us = int(60_000_000 / bpm)
    track_events += var_length(0)  # Delta time 0
    track_events += b'\xFF\x51\x03'  # Tempo meta event
    track_events += struct.pack('>I', tempo_us)[1:]  # 3 bytes

    # Track name
    track_name = f'DSIP 20min - {seq} x{num_repetitions}'.encode('ascii')
    track_events += var_length(0)
    track_events += b'\xFF\x03'
    track_events += bytes([len(track_name)]) + track_name

    # Time signature (optional but useful)
    track_events += var_length(0)
    track_events += b'\xFF\x58\x04'  # Time signature
    track_events += bytes([4, 2, 24, 8])  # 4/4 time

    # Generate notes with repetitions
    velocity = 80
    channel = 0
    total_notes = 0

    for rep in range(num_repetitions):
        for i, (aa, midi_note, duration_beats) in enumerate(zip(seq, midi_notes, note_durations)):
            duration_ticks = int(duration_beats * ticks_per_quarter)

            # Note On
            delta = var_length(0 if (rep == 0 and i == 0) else 0)
            track_events += delta
            track_events += bytes([0x90 | channel, midi_note, velocity])

            # Note Off (after duration)
            track_events += var_length(duration_ticks)
            track_events += bytes([0x80 | channel, midi_note, 0])

            total_notes += 1

            # Progress indicator
            if total_notes % 100 == 0:
                print(f"  Génération: {total_notes} notes... ({total_notes/(num_repetitions*len(seq))*100:.1f}%)")

    # End of track
    track_events += var_length(0)
    track_events += b'\xFF\x2F\x00'

    # Track chunk header
    track = b'MTrk'
    track += struct.pack('>I', len(track_events))
    track += track_events

    print(f"\n✅ Total notes générées: {total_notes}")
    print(f"   Taille track: {len(track_events)} bytes")

    return header + track

if __name__ == '__main__':
    # Vérification des notes MIDI
    print("\nVérification séquence DSIP:")
    print(f"{'AA':<4} {'MIDI':<6} {'Durée':<8}")
    print("─" * 25)
    for aa, midi, dur in zip(DSIP_SEQ, DSIP_MIDI_NOTES, NOTE_DURATIONS):
        calculated_midi = midi_for_aa(aa)
        match = "✅" if calculated_midi == midi else f"⚠️ (calculé: {calculated_midi})"
        print(f"{aa:<4} {midi:<6} {dur} temps  {match}")

    # Générer le fichier MIDI
    print("\n" + "─" * 80)
    midi_data = generate_dsip_midi_20min(
        DSIP_SEQ,
        DSIP_MIDI_NOTES,
        NOTE_DURATIONS,
        BPM,
        target_duration_min=20
    )

    # Sauvegarder
    output_file = 'dsip_20min.mid'
    with open(output_file, 'wb') as f:
        f.write(midi_data)

    print(f"\n" + "=" * 80)
    print(f"✅ FICHIER MIDI GÉNÉRÉ: {output_file}")
    print(f"   Taille: {len(midi_data):,} bytes ({len(midi_data)/1024:.1f} KB)")
    print("=" * 80)

    print("\n📋 INSTRUCTIONS LOGIC PRO:")
    print("─" * 80)
    print("1. Importer dsip_20min.mid dans Logic Pro")
    print("2. Assigner Vienna Synchron Celestial Strings à la piste")
    print("3. Réglages Vienna:")
    print("   • Master Tune: -24 cents (diapason h3O2 429.62 Hz)")
    print("4. Ajouter effet Tremolo:")
    print("   • Rate: 3.91 Hz (ou 4.05 Hz)")
    print("   • Depth: 40%")
    print("   • Waveform: Square (si disponible)")
    print("5. Bounce en WAV/FLAC 44.1kHz Stéréo")
    print("   • Include Audio Tail: ON")
    print("=" * 80)
