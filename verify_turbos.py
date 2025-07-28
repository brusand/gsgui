#!/usr/bin/env python3

import pandas as pd

def verify_turbos_consistency():
    """Vérifie la cohérence du fichier turbos.feather"""
    
    df = pd.read_feather('turbos.feather')
    print(f'✅ turbos.feather: {len(df)} entrées')
    
    with_winner = df[df['winner_id'].notna() & (df['winner_id'] != '')]
    inconsistent = 0
    
    for _, row in with_winner.iterrows():
        if row['winner_id'] not in [row['photo1_id'], row['photo2_id']]:
            inconsistent += 1
    
    consistency_rate = (len(with_winner) - inconsistent) / len(with_winner) * 100 if len(with_winner) > 0 else 100
    print(f'✅ Cohérence: {len(with_winner) - inconsistent}/{len(with_winner)} = {consistency_rate:.1f}%')
    
    return consistency_rate == 100.0

if __name__ == "__main__":
    verify_turbos_consistency()