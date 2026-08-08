#!/usr/bin/env python3
"""
Génère UN fichier MIDI par pack
Contient toutes les protéodies du pack en séquence, bouclées selon la durée demandée
"""

import json
import sys
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

def pack_to_midi(proteodies, scale='fa', output_file='pack.mid', duration_minutes=10):
    """
    Convertit un pack complet en fichier MIDI
    Joue toutes les protéodies en séquence, puis boucle pour atteindre la durée
    """
    scale_notes = SCALES[scale]

    # Concaténer toutes les séquences du pack
    full_sequence = ''.join([p['seq'] for p in proteodies])

    # Calculer durée d'une boucle
    loop_beats = len(full_sequence)
    loop_duration = loop_beats * BEAT_DURATION

    # Calculer nombre de boucles nécessaires
    target_duration = duration_minutes * 60
    num_loops = int(target_duration / loop_duration) + 1

    print(f"  📊 Séquence totale: {len(full_sequence)} AA")
    print(f"  ⏱️  Durée boucle: {loop_duration:.1f}s")
    print(f"  🔁 Nombre de boucles: {num_loops}")

    # Créer fichier MIDI
    midi = MIDIFile(1)  # 1 piste
    track = 0
    channel = 0
    time = 0
    tempo = BPM
    volume = 100

    midi.addTempo(track, time, tempo)

    # Générer les notes (toutes les protéodies, N boucles)
    for loop in range(num_loops):
        for aa in full_sequence:
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

    final_duration = time * BEAT_DURATION
    return final_duration

def main():
    # Créer répertoire output
    output_dir = Path('midi_packs_export')
    output_dir.mkdir(exist_ok=True)

    # Durée en argument ou 10 min par défaut
    if len(sys.argv) > 1:
        try:
            duration_minutes = int(sys.argv[1])
        except ValueError:
            print("❌ Durée invalide")
            print("Usage: python generate_pack_midi.py [durée_minutes]")
            return
    else:
        duration_minutes = 10
        print("💡 Durée par défaut: 10 minutes (utilisez un argument pour changer)")
        print()

    print(f"🎼 Génération des fichiers MIDI par pack ({duration_minutes} min)\n")

    # Charger l'index des packs
    packs_index_file = 'web-ui/public/proteodies2/packs-index.json'
    with open(packs_index_file, 'r') as f:
        packs_index = json.load(f)

    total_packs = 0
    total_duration = 0

    # Pour chaque pack
    for pack in packs_index:
        pack_id = pack['id']
        pack_name = pack['name']
        scale = pack['scale']
        mode = pack['mode']
        freq = pack['freq']

        print(f"📦 {pack_name}")
        print(f"  🎵 Gamme: {scale.upper()}, Mode: {mode}, Fréquence: {freq}")

        # Charger pack complet
        pack_file = f'web-ui/public/proteodies2/packs/{pack_id}.json'
        with open(pack_file, 'r') as f:
            pack_data = json.load(f)

        # Nom fichier: {pack_id}_{scale}_{duration}min.mid
        filename = f"{pack_id}_{scale}_{duration_minutes}min.mid"
        filepath = output_dir / filename

        # Générer MIDI
        duration = pack_to_midi(pack_data['proteodies'], scale, filepath, duration_minutes)

        total_packs += 1
        total_duration += duration

        print(f"  ✅ {filename} ({duration/60:.1f} min)")
        print()

    print(f"✅ Génération terminée")
    print(f"📊 {total_packs} fichiers MIDI (packs complets)")
    print(f"⏱️  Durée totale: {total_duration/60:.1f} min")
    print(f"📁 Dossier: {output_dir}")
    print()
    print("📝 Prochaines étapes:")
    print("   1. Ouvrir Logic Pro avec template Vienna Synchron")
    print("   2. Importer le fichier MIDI du pack souhaité")
    print("   3. Configurer Master Tune = -24 cents (h3O2)")
    print("   4. Configurer Tremolo selon le mode (voir nom fichier)")
    print("   5. Exporter: Fichier > Exporter > Audio")

if __name__ == '__main__':
    main()
