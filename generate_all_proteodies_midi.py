#!/usr/bin/env python3
"""
Génère tous les fichiers MIDI pour toutes les protéodies
À importer ensuite dans Logic Pro pour export WAV avec Vienna Synchron
"""

import json
from midiutil import MIDIFile
from pathlib import Path

# Mapping acides aminés -> MIDI notes
AA_TO_MIDI = {
    'A': 57, 'C': 60, 'D': 62, 'E': 64, 'F': 65, 'G': 67,
    'H': 69, 'I': 71, 'K': 72, 'L': 74, 'M': 76, 'N': 77,
    'P': 79, 'Q': 81, 'R': 83, 'S': 84, 'T': 86, 'V': 88,
    'W': 89, 'Y': 91
}

# Gammes Lydiennes (MIDI notes de base)
SCALES = {
    'fa': [41, 43, 45, 47, 48, 50, 52],   # F Lydian
    'sib': [46, 48, 50, 52, 53, 55, 57],  # Bb Lydian
    'mib': [51, 53, 55, 57, 58, 60, 62]   # Eb Lydian
}

BPM = 65
BEAT_DURATION = 60.0 / BPM  # ~0.923s par beat

def sequence_to_midi(sequence, scale='fa', output_file='proteody.mid', num_loops=1):
    """
    Convertit une séquence d'acides aminés en fichier MIDI
    """
    scale_notes = SCALES[scale]

    # Créer fichier MIDI
    midi = MIDIFile(1)  # 1 piste
    track = 0
    channel = 0
    time = 0
    tempo = BPM
    volume = 100

    midi.addTempo(track, time, tempo)

    # Générer les notes
    for loop in range(num_loops):
        for aa in sequence:
            if aa not in AA_TO_MIDI:
                continue

            # Mapper AA -> note de la gamme
            aa_midi = AA_TO_MIDI[aa]
            scale_index = aa_midi % len(scale_notes)
            final_midi = scale_notes[scale_index]

            # Transposer à l'octave appropriée
            octave = (aa_midi - 57) // 7
            final_midi += octave * 12

            # Ajouter la note
            midi.addNote(track, channel, final_midi, time, 1, volume)
            time += 1

    # Écrire fichier
    with open(output_file, 'wb') as f:
        midi.writeFile(f)

    duration_secs = time * BEAT_DURATION
    return duration_secs

def main():
    # Créer répertoire output
    output_dir = Path('midi_export')
    output_dir.mkdir(exist_ok=True)

    print("🎼 Génération des fichiers MIDI pour toutes les protéodies\n")

    # Charger l'index des packs
    packs_index_file = 'web-ui/public/proteodies2/packs-index.json'
    with open(packs_index_file, 'r') as f:
        packs_index = json.load(f)

    total_midi = 0
    total_duration = 0

    # Pour chaque pack
    for pack in packs_index:
        pack_id = pack['id']
        pack_name = pack['name']
        scale = pack['scale']

        print(f"📦 {pack_name} (gamme: {scale.upper()})")

        # Charger pack complet
        pack_file = f'web-ui/public/proteodies2/packs/{pack_id}.json'
        with open(pack_file, 'r') as f:
            pack_data = json.load(f)

        # Générer MIDI pour chaque protéodie (1 boucle)
        for proteody in pack_data['proteodies']:
            proteody_id = proteody['id']
            sequence = proteody['seq']

            # Nom fichier: {proteody_id}_{scale}.mid
            filename = f"{proteody_id}_{scale}.mid"
            filepath = output_dir / filename

            # Générer MIDI
            duration = sequence_to_midi(sequence, scale, filepath, num_loops=1)

            total_midi += 1
            total_duration += duration

            print(f"  ✅ {filename} ({len(sequence)} AA, {duration:.1f}s)")

        print()

    print(f"✅ Génération terminée")
    print(f"📊 {total_midi} fichiers MIDI")
    print(f"⏱️  Durée totale: {total_duration/60:.1f} min")
    print(f"📁 Dossier: {output_dir}")
    print()
    print("📝 Prochaines étapes:")
    print("   1. Ouvrir Logic Pro avec template Vienna Synchron + Tremolo")
    print("   2. Importer les fichiers MIDI dans le dossier midi_export/")
    print("   3. Configurer Master Tune = -24 cents (h3O2)")
    print("   4. Configurer Tremolo selon le mode du pack (voir packs-index.json)")
    print("   5. Exporter par batch: Fichier > Exporter > Toutes les pistes comme fichiers audio")

if __name__ == '__main__':
    main()
