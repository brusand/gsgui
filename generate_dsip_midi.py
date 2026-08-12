#!/usr/bin/env python3
"""
Génère le fichier MIDI DSIP complet (9 notes)
Basé sur le code de l'application proteodies
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

def var_length(value):
    """Encode un entier en variable-length quantity (MIDI standard)"""
    result = bytearray([value & 0x7F])
    value >>= 7
    while value > 0:
        result.insert(0, (value & 0x7F) | 0x80)
        value >>= 7
    return bytes(result)

def generate_midi(seq, bpm):
    """Génère un fichier MIDI Format 0"""

    ppqn = 480  # Pulses per quarter note
    ticks_per_note = ppqn  # Une noire par note

    # Header chunk
    header = b'MThd'
    header += struct.pack('>I', 6)  # Header length
    header += struct.pack('>H', 0)  # Format 0 (single track)
    header += struct.pack('>H', 1)  # Number of tracks
    header += struct.pack('>H', ppqn)  # Ticks per quarter note

    # Track chunk
    track_events = bytearray()

    # Tempo meta event (500000 us per beat = 120 BPM par défaut, on ajuste après)
    tempo_us = int(60_000_000 / bpm)
    track_events += var_length(0)  # Delta time 0
    track_events += b'\xFF\x51\x03'  # Tempo meta event
    track_events += struct.pack('>I', tempo_us)[1:]  # 3 bytes (skip first byte)

    # Track name
    track_name = f'DSIP - {seq}'.encode('ascii')
    track_events += var_length(0)  # Delta time 0
    track_events += b'\xFF\x03'  # Track name meta event
    track_events += bytes([len(track_name)]) + track_name

    # Generate notes
    velocity = 80
    channel = 0

    for i, aa in enumerate(seq):
        midi_note = midi_for_aa(aa)

        # Note On
        delta = var_length(0 if i == 0 else ticks_per_note)
        track_events += delta
        track_events += bytes([0x90 | channel, midi_note, velocity])

        # Note Off (after ticks_per_note)
        track_events += var_length(ticks_per_note)
        track_events += bytes([0x80 | channel, midi_note, 0])

    # End of track
    track_events += var_length(0)
    track_events += b'\xFF\x2F\x00'

    # Track chunk header
    track = b'MTrk'
    track += struct.pack('>I', len(track_events))
    track += track_events

    return header + track

def analyze_midi(data):
    """Analyse le fichier MIDI généré"""
    print("=" * 80)
    print("ANALYSE DU FICHIER MIDI DSIP")
    print("=" * 80)

    # Parse header
    if data[:4] != b'MThd':
        print("❌ Header MIDI invalide")
        return

    header_len = struct.unpack('>I', data[4:8])[0]
    format_type = struct.unpack('>H', data[8:10])[0]
    num_tracks = struct.unpack('>H', data[10:12])[0]
    ppqn = struct.unpack('>H', data[12:14])[0]

    print(f"\n📄 HEADER MIDI")
    print(f"Format:        {format_type} (single track)")
    print(f"Tracks:        {num_tracks}")
    print(f"PPQN:          {ppqn} (pulses per quarter note)")

    # Parse track
    track_offset = 14
    if data[track_offset:track_offset+4] != b'MTrk':
        print("❌ Track chunk invalide")
        return

    track_len = struct.unpack('>I', data[track_offset+4:track_offset+8])[0]
    print(f"Track length:  {track_len} bytes")

    # Count note events
    note_count = 0
    notes = []
    pos = track_offset + 8

    while pos < len(data):
        # Parse delta time (variable length)
        delta = 0
        while True:
            if pos >= len(data):
                break
            byte = data[pos]
            pos += 1
            delta = (delta << 7) | (byte & 0x7F)
            if not (byte & 0x80):
                break

        if pos >= len(data):
            break

        # Parse event
        status = data[pos]
        pos += 1

        if status == 0xFF:  # Meta event
            if pos >= len(data):
                break
            meta_type = data[pos]
            pos += 1
            if pos >= len(data):
                break
            meta_len = data[pos]
            pos += 1
            pos += meta_len

            if meta_type == 0x2F:  # End of track
                break
        elif (status & 0xF0) == 0x90:  # Note On
            if pos + 1 >= len(data):
                break
            midi_note = data[pos]
            velocity = data[pos+1]
            pos += 2
            if velocity > 0:
                note_count += 1
                notes.append(midi_note)
        elif (status & 0xF0) == 0x80:  # Note Off
            pos += 2
        else:
            # Skip unknown events
            if pos + 1 < len(data):
                pos += 2

    print(f"\n🎵 NOTES DÉTECTÉES: {note_count}")

    NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

    print(f"\n{'#':<3} {'MIDI':<6} {'Note':<8} {'AA':<4}")
    print("─" * 30)
    for i, midi in enumerate(notes):
        note_name = NOTE_NAMES[midi % 12]
        octave = (midi // 12) - 1
        aa = DSIP_SEQ[i] if i < len(DSIP_SEQ) else '?'
        print(f"{i+1:<3} {midi:<6} {note_name}{octave:<7} {aa:<4}")

    print("\n" + "=" * 80)

if __name__ == '__main__':
    print("=" * 80)
    print("GÉNÉRATION FICHIER MIDI DSIP")
    print("=" * 80)

    print(f"\nSéquence:  {DSIP_SEQ}")
    print(f"Tempo:     {BPM} BPM")
    print(f"Gamme:     {SCALE.upper()} Lydien (calmant)")
    print(f"Notes:     {len(DSIP_SEQ)}")

    # Generate MIDI
    midi_data = generate_midi(DSIP_SEQ, BPM)

    # Save to file
    output_file = 'dsip.mid'
    with open(output_file, 'wb') as f:
        f.write(midi_data)

    print(f"\n✅ Fichier MIDI généré: {output_file} ({len(midi_data)} bytes)")

    # Analyze
    analyze_midi(midi_data)
