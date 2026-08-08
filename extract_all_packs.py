#!/usr/bin/env python3
"""
Extrait tous les packs de proteodies/index.html et génère le code JavaScript pour V2
"""

import re
import json
from collections import defaultdict

# Lire le fichier index.html
with open('web-ui/public/proteodies/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Extraire la section PROTEODIES
match = re.search(r'const PROTEODIES=\[(.*?)\];', content, re.DOTALL)
if not match:
    print("❌ Section PROTEODIES non trouvée")
    exit(1)

proteodies_str = '[' + match.group(1) + ']'

# Parser les protéodies (extraction simple regex)
proteodies = []
pattern = r"\{id:'([^']+)',\s*name:'([^']+)',\s*seq:'([^']+)',\s*cat:'([^']+)',\s*desc:'([^']+)'\}"

for match in re.finditer(pattern, proteodies_str):
    proteodies.append({
        'id': match.group(1),
        'name': match.group(2),
        'seq': match.group(3),
        'cat': match.group(4),
        'desc': match.group(5)
    })

print(f"✅ {len(proteodies)} protéodies extraites")

# Grouper par catégorie
packs = defaultdict(list)
for p in proteodies:
    packs[p['cat']].append(p)

# Config par défaut catégories (depuis CAT_DEFAULT_SCALE, BEAT_FREQS, CAT_AUDIO_MODE)
CAT_CONFIG = {
    '🧬': {'scale': 'fa', 'freq': 10, 'mode': 'isochrone_10hz', 'name': 'PIEZO1', 'effect': 'Activation canaux mécanosensibles'},
    '🧠': {'scale': 'fa', 'freq': 14, 'mode': 'isochrone_14hz', 'name': 'Neuro', 'effect': 'Stimulation cognitive + dopamine'},
    '🦵': {'scale': 'fa', 'freq': 10, 'mode': 'isochrone_10hz', 'name': 'Genou', 'effect': 'Régénération articulaire'},
    '😴': {'scale': 'mib', 'freq': 4, 'mode': 'isochrone_4hz', 'name': 'Sommeil', 'effect': 'Sommeil profond (Delta)'},
    '🍴': {'scale': 'fa', 'freq': 10, 'mode': 'isochrone_10hz', 'name': 'Boulimie', 'effect': 'Régulation appétit'},
    '❤️': {'scale': 'mib', 'freq': 8, 'mode': 'isochrone_8hz', 'name': 'Tension', 'effect': 'Vasodilatation + régulation'},
    '💧': {'scale': 'fa', 'freq': 10, 'mode': 'isochrone_10hz', 'name': 'Eau', 'effect': 'Transport hydrique'},
    '🏔️': {'scale': 'fa', 'freq': 12, 'mode': 'isochrone_10hz', 'name': 'Altitude', 'effect': 'Adaptation hypoxie'},
    '🌵': {'scale': 'fa', 'freq': 10, 'mode': 'stereo', 'name': 'Cactus', 'effect': 'Adaptation sécheresse'},
    '🌿': {'scale': 'fa', 'freq': 10, 'mode': 'stereo', 'name': 'Plantes', 'effect': 'Croissance végétale'},
    '🥒': {'scale': 'fa', 'freq': 10, 'mode': 'stereo', 'name': 'Concombre', 'effect': 'Résistance pathogènes'},
    '🍅': {'scale': 'fa', 'freq': 10, 'mode': 'stereo', 'name': 'Tomate', 'effect': 'Défense végétale'},
    '😊': {'scale': 'fa', 'freq': 8, 'mode': 'isochrone_8hz', 'name': 'Humeur', 'effect': 'Bien-être + anti-stress'},
    '👁️': {'scale': 'fa', 'freq': 10, 'mode': 'isochrone_10hz', 'name': 'Yeux', 'effect': 'Protection cristallin'},
    '🌌': {'scale': 'fa', 'freq': 6, 'mode': 'isochrone_7hz', 'name': 'Conscience', 'effect': 'États de conscience'},
    '🫃': {'scale': 'fa', 'freq': 6, 'mode': 'isochrone_7hz', 'name': 'Intestin', 'effect': 'Réparation muqueuse'},
    '💚': {'scale': 'fa', 'freq': 6, 'mode': 'isochrone_7hz', 'name': 'Mianne', 'effect': 'Cohérence cardiaque'},
    '🔥': {'scale': 'fa', 'freq': 12, 'mode': 'isochrone_10hz', 'name': 'Métabolisme', 'effect': 'Lipolyse + énergie'},
    '🫒': {'scale': 'fa', 'freq': 7, 'mode': 'isochrone_7hz', 'name': 'Foie', 'effect': 'Détox + anti-stéatose'},
    '🍇': {'scale': 'fa', 'freq': 10, 'mode': 'stereo', 'name': 'Vigne', 'effect': 'Résistance esca'},
    '⚡': {'scale': 'fa', 'freq': 6, 'mode': 'isochrone_7hz', 'name': 'Neuro-Douleur', 'effect': 'Analgésie neuropathique'},
    '🦿': {'scale': 'mib', 'freq': 8, 'mode': 'isochrone_8hz', 'name': 'Jambes Sans Repos', 'effect': 'Fer + dopamine'},
    '🦻': {'scale': 'mib', 'freq': 10, 'mode': 'isochrone_10hz', 'name': 'Ménière', 'effect': 'Équilibre endolymphe'},
    '💪': {'scale': 'mib', 'freq': 7, 'mode': 'isochrone_7hz', 'name': 'Fibromyalgie', 'effect': 'Anti-douleur + énergie'},
    '🩹': {'scale': 'mib', 'freq': 10, 'mode': 'isochrone_10hz', 'name': 'Anti-Inflammatoire', 'effect': 'Réduction inflammation'},
    '🦟': {'scale': 'mib', 'freq': 10, 'mode': 'stereo', 'name': 'Anti-Démangeaisons', 'effect': 'Antiprurit'},
    '🩸': {'scale': 'mib', 'freq': 8, 'mode': 'isochrone_8hz', 'name': 'Sang', 'effect': 'Anticoagulation + fluidité'},
    '🧪': {'scale': 'fa', 'freq': 10, 'mode': 'isochrone_10hz', 'name': 'Protocol H', 'effect': 'Sérotonine TPH1'},
    '🌸': {'scale': 'fa', 'freq': 10, 'mode': 'isochrone_10hz', 'name': 'Orchidées', 'effect': 'Floraison + croissance'},
    '💉': {'scale': 'sib', 'freq': 8, 'mode': 'isochrone_8hz', 'name': 'Diabète', 'effect': 'Équilibre glycémique'},
    '🌺': {'scale': 'fa', 'freq': 12, 'mode': 'isochrone_10hz', 'name': 'Hibiscus Canicule', 'effect': 'Thermorégulation'},
    '🫘': {'scale': 'mib', 'freq': 6, 'mode': 'isochrone_7hz', 'name': 'Rénal K+/Créatinine', 'effect': 'Fonction rénale'},
    '💦': {'scale': 'fa', 'freq': 8, 'mode': 'isochrone_8hz', 'name': 'Peau Sèche', 'effect': 'Hydratation cutanée'},
    '🦴': {'scale': 'mib', 'freq': 7, 'mode': 'isochrone_7hz', 'name': 'Arthrose', 'effect': 'Anti-inflammatoire + Régénération'}
}

# Générer code JavaScript
print("\n// ========== PROTEODIES ==========")
print("const PROTEODIES = {")
for cat, prots in sorted(packs.items()):
    for p in prots:
        # Échapper les apostrophes dans la séquence
        seq = p['seq'].replace("'", "\\'")
        print(f"  {p['id']}: {{name:'{p['name']}', seq:'{seq}'}},")
print("};")

print("\n// ========== PACKS ==========")
print("const PACKS = {")
for cat, prots in sorted(packs.items()):
    if cat not in CAT_CONFIG:
        continue

    cfg = CAT_CONFIG[cat]
    pack_id = cfg['name'].lower().replace(' ', '_').replace('-', '_').replace('+', 'plus').replace('/', '_')
    prot_ids = [p['id'] for p in prots]

    # Créer description pack
    if len(prots) == 1:
        desc = prots[0]['desc']
    else:
        desc = f"Pack complet {cfg['name']} : {', '.join([p['name'].split(' — ')[-1] if ' — ' in p['name'] else p['name'] for p in prots[:3]])}"
        if len(prots) > 3:
            desc += f" + {len(prots)-3} autres"

    print(f"  {pack_id}: {{")
    print(f"    name: '{cfg['name']}',")
    print(f"    emoji: '{cat}',")
    print(f"    proteodies: {json.dumps(prot_ids)},")
    print(f"    mode: '{cfg['mode']}',")
    print(f"    scale: '{cfg['scale']}',")
    print(f"    desc: '{desc}',")
    print(f"    freq: '{cfg['freq']} Hz',")
    print(f"    effect: '{cfg['effect']}'")
    print(f"  }},")
print("};")

print(f"\n✅ {len(packs)} packs générés")
print(f"📊 Total: {sum(len(p) for p in packs.values())} protéodies")
