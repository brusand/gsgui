#!/usr/bin/env python3
"""
Vérification de la cohérence des données dans turbos.feather
Détecte les cas où l'ID gagnant ne correspond à aucune des deux photos
"""

import pandas as pd

def check_data_consistency():
    """Vérifie la cohérence des données turbo"""
    
    print("🔍 === VÉRIFICATION COHÉRENCE DONNÉES TURBO ===")
    print("Détection des ID gagnants incohérents")
    print("=" * 60)
    
    # Charger les données
    try:
        df = pd.read_feather('turbos.feather')
        print(f"✅ {len(df)} entrées chargées")
    except FileNotFoundError:
        print("❌ Fichier turbos.feather non trouvé!")
        return
    
    # Filtrer les entrées avec gagnant
    df_with_winner = df[df['id_photo_gagnante'] != ''].copy()
    print(f"📊 {len(df_with_winner)} entrées avec gagnant à vérifier")
    print()
    
    # Détecter les incohérences
    inconsistent_entries = []
    
    for idx, row in df_with_winner.iterrows():
        photo1_id = row['id_photo1']
        photo2_id = row['id_photo2'] 
        winner_id = row['id_photo_gagnante']
        
        # Vérifier si le gagnant correspond à l'une des deux photos
        if winner_id != photo1_id and winner_id != photo2_id:
            inconsistent_entries.append({
                'index': idx,
                'profil': row['nom_profil'],
                'challenge': row['nom_challenge'], 
                'photo1_id': photo1_id,
                'photo2_id': photo2_id,
                'winner_id': winner_id,
                'votes1': row['votes_photo1'],
                'votes2': row['votes_photo2'],
                'ratio1': row['ratio_photo1'],
                'ratio2': row['ratio_photo2']
            })
    
    print(f"📈 === RÉSULTATS VÉRIFICATION ===")
    print(f"✅ Entrées cohérentes: {len(df_with_winner) - len(inconsistent_entries)}")
    print(f"❌ Entrées incohérentes: {len(inconsistent_entries)}")
    print(f"📊 Taux de cohérence: {(len(df_with_winner) - len(inconsistent_entries)) / len(df_with_winner) * 100:.1f}%")
    print()
    
    if len(inconsistent_entries) > 0:
        print(f"🔍 === ANALYSE DES INCOHÉRENCES ===")
        
        # Statistiques par profil
        profil_errors = {}
        for entry in inconsistent_entries:
            profil = entry['profil']
            profil_errors[profil] = profil_errors.get(profil, 0) + 1
        
        print(f"❌ Erreurs par profil:")
        for profil, count in profil_errors.items():
            total_profil = len(df_with_winner[df_with_winner['nom_profil'] == profil])
            pct = count / total_profil * 100
            print(f"   {profil}: {count}/{total_profil} ({pct:.1f}%)")
        
        # Statistiques par challenge
        challenge_errors = {}
        for entry in inconsistent_entries:
            challenge = entry['challenge']
            challenge_errors[challenge] = challenge_errors.get(challenge, 0) + 1
        
        print(f"\n❌ Top 10 challenges avec erreurs:")
        sorted_challenges = sorted(challenge_errors.items(), key=lambda x: x[1], reverse=True)
        for challenge, count in sorted_challenges[:10]:
            print(f"   {challenge[:40]:40}: {count} erreurs")
        
        # Exemples d'incohérences
        print(f"\n🔍 === EXEMPLES D'INCOHÉRENCES ===")
        for i, entry in enumerate(inconsistent_entries[:10]):
            print(f"\n{i+1:2d}. {entry['profil']} | {entry['challenge'][:30]}")
            print(f"    Photo1: {entry['photo1_id'][:8]} (v:{entry['votes1']}, r:{entry['ratio1']:.2f})")
            print(f"    Photo2: {entry['photo2_id'][:8]} (v:{entry['votes2']}, r:{entry['ratio2']:.2f})")
            print(f"    Gagnant: {entry['winner_id'][:8]} ❌ (ne correspond à aucune photo)")
        
        if len(inconsistent_entries) > 10:
            print(f"\n... et {len(inconsistent_entries) - 10} autres incohérences")
        
        # Analyse des patterns d'erreurs
        print(f"\n🔬 === ANALYSE PATTERNS D'ERREURS ===")
        
        # IDs gagnants les plus fréquents dans les erreurs
        winner_id_counts = {}
        for entry in inconsistent_entries:
            winner_id = entry['winner_id'][:8]  # Tronquer pour grouper
            winner_id_counts[winner_id] = winner_id_counts.get(winner_id, 0) + 1
        
        print(f"🏆 IDs gagnants erronés les plus fréquents:")
        sorted_winners = sorted(winner_id_counts.items(), key=lambda x: x[1], reverse=True)
        for winner_id, count in sorted_winners[:5]:
            print(f"   {winner_id}: {count} occurrences")
        
        # Vérifier si certains IDs gagnants sont des IDs de photos dans d'autres lignes
        print(f"\n🔗 === VÉRIFICATION CROISÉE ===")
        all_photo_ids = set(df['id_photo1'].tolist() + df['id_photo2'].tolist())
        
        cross_ref_count = 0
        for entry in inconsistent_entries[:5]:  # Vérifier les 5 premiers
            winner_id = entry['winner_id']
            if winner_id in all_photo_ids:
                cross_ref_count += 1
                print(f"   ✅ {winner_id[:8]} existe comme photo dans d'autres lignes")
            else:
                print(f"   ❌ {winner_id[:8]} n'existe nulle part comme photo")
        
        print(f"\n📊 Sur {min(5, len(inconsistent_entries))} vérifiés:")
        print(f"   {cross_ref_count} IDs gagnants existent comme photos ailleurs")
        print(f"   {min(5, len(inconsistent_entries)) - cross_ref_count} IDs gagnants sont complètement orphelins")
    
    # Recommandations
    print(f"\n💡 === RECOMMANDATIONS ===")
    
    if len(inconsistent_entries) > 0:
        print(f"1. 🧹 NETTOYAGE DONNÉES:")
        print(f"   - {len(inconsistent_entries)} entrées à corriger ou supprimer")
        print(f"   - Représentent {len(inconsistent_entries) / len(df_with_winner) * 100:.1f}% des données")
        
        print(f"\n2. 🔍 ORIGINE PROBABLE:")
        print(f"   - Erreur dans la migration des données")
        print(f"   - Mélange d'IDs entre différents turbos")
        print(f"   - Problème de correspondance lors de l'extraction")
        
        print(f"\n3. 🔧 SOLUTIONS:")
        print(f"   - Exclure ces entrées des analyses ML")
        print(f"   - Vérifier les logs de migration")
        print(f"   - Re-extraire depuis les sources originales")
        
        # Créer un fichier avec les entrées problématiques
        inconsistent_df = pd.DataFrame(inconsistent_entries)
        inconsistent_df.to_csv('turbos_inconsistent.csv', index=False)
        print(f"\n💾 EXPORT: turbos_inconsistent.csv créé avec {len(inconsistent_entries)} entrées problématiques")
        
        # Créer un fichier nettoyé
        clean_df = df_with_winner.drop(index=[entry['index'] for entry in inconsistent_entries])
        clean_df.to_feather('turbos_clean.feather')
        print(f"💾 EXPORT: turbos_clean.feather créé avec {len(clean_df)} entrées cohérentes")
        
    else:
        print(f"✅ Toutes les données sont cohérentes !")
    
    return {
        'total_entries': len(df),
        'entries_with_winner': len(df_with_winner),
        'inconsistent_entries': len(inconsistent_entries),
        'consistency_rate': (len(df_with_winner) - len(inconsistent_entries)) / len(df_with_winner) * 100 if len(df_with_winner) > 0 else 0
    }

if __name__ == "__main__":
    results = check_data_consistency()
    
    print(f"\n📈 === RÉSUMÉ ===")
    print(f"Total entrées: {results['total_entries']}")
    print(f"Avec gagnant: {results['entries_with_winner']}")
    print(f"Incohérentes: {results['inconsistent_entries']}")
    print(f"Taux cohérence: {results['consistency_rate']:.1f}%")