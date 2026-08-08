#!/usr/bin/env python3
"""
Génère les fichiers JSON pour le chargement à la demande des packs
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

# Parser les protéodies
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

# Config par défaut catégories
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

# 1. Générer index des packs (léger, pour le sélecteur)
packs_index = []
for cat, prots in sorted(packs.items()):
    if cat not in CAT_CONFIG:
        continue

    cfg = CAT_CONFIG[cat]
    pack_id = cfg['name'].lower().replace(' ', '_').replace('-', '_').replace('+', 'plus').replace('/', '_')
    # Normaliser les caractères accentués pour compatibilité URL
    pack_id = pack_id.replace('é', 'e').replace('è', 'e').replace('ê', 'e')
    pack_id = pack_id.replace('à', 'a').replace('â', 'a')
    pack_id = pack_id.replace('î', 'i').replace('ï', 'i')
    pack_id = pack_id.replace('ô', 'o')
    pack_id = pack_id.replace('û', 'u').replace('ù', 'u')

    packs_index.append({
        'id': pack_id,
        'name': cfg['name'],
        'emoji': cat,
        'count': len(prots),
        'mode': cfg['mode'],
        'scale': cfg['scale'],
        'freq': f"{cfg['freq']} Hz",
        'effect': cfg['effect']
    })

# Sauvegarder index
with open('web-ui/public/proteodies2/packs-index.json', 'w', encoding='utf-8') as f:
    json.dump(packs_index, f, indent=2, ensure_ascii=False)

print(f"✅ Index packs sauvegardé: {len(packs_index)} packs")

# 2. Générer fichier JSON pour chaque pack (détails + séquences)
import os
os.makedirs('web-ui/public/proteodies2/packs', exist_ok=True)

for cat, prots in packs.items():
    if cat not in CAT_CONFIG:
        continue

    cfg = CAT_CONFIG[cat]
    pack_id = cfg['name'].lower().replace(' ', '_').replace('-', '_').replace('+', 'plus').replace('/', '_')
    # Normaliser les caractères accentués pour compatibilité URL
    pack_id = pack_id.replace('é', 'e').replace('è', 'e').replace('ê', 'e')
    pack_id = pack_id.replace('à', 'a').replace('â', 'a')
    pack_id = pack_id.replace('î', 'i').replace('ï', 'i')
    pack_id = pack_id.replace('ô', 'o')
    pack_id = pack_id.replace('û', 'u').replace('ù', 'u')

    # Créer description
    if len(prots) == 1:
        desc = prots[0]['desc']
    else:
        desc = f"Pack complet {cfg['name']} : {', '.join([p['name'].split(' — ')[-1] if ' — ' in p['name'] else p['name'] for p in prots[:3]])}"
        if len(prots) > 3:
            desc += f" + {len(prots)-3} autres"

    pack_data = {
        'id': pack_id,
        'name': cfg['name'],
        'emoji': cat,
        'mode': cfg['mode'],
        'scale': cfg['scale'],
        'freq': f"{cfg['freq']} Hz",
        'effect': cfg['effect'],
        'desc': desc,
        'proteodies': [{
            'id': p['id'],
            'name': p['name'],
            'seq': p['seq'],
            'desc': p['desc']
        } for p in prots]
    }

    # Sauvegarder
    with open(f'web-ui/public/proteodies2/packs/{pack_id}.json', 'w', encoding='utf-8') as f:
        json.dump(pack_data, f, indent=2, ensure_ascii=False)

print(f"✅ {len(packs)} fichiers packs générés dans web-ui/public/proteodies2/packs/")
print(f"📊 Total: {sum(len(p) for p in packs.values())} protéodies")
