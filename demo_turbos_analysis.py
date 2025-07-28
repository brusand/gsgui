#!/usr/bin/env python3
"""
Démonstration d'analyse des données turbos.feather
Exemples de requêtes SQL et préparation sklearn
"""

import pandas as pd
import numpy as np

def demo_turbos_analysis():
    """Démonstration des capacités d'analyse"""
    
    print("🔍 === DÉMONSTRATION ANALYSE TURBOS.FEATHER ===")
    print("📊 Exemples de requêtes SQL et analyses avancées")
    print("=" * 60)
    
    # Charger les données
    print("📂 Chargement des données...")
    df = pd.read_feather('turbos.feather')
    print(f"✅ {len(df)} turbos chargés")
    print()
    
    # === REQUÊTES SQL-LIKE ===
    print("🔍 === REQUÊTES SQL-LIKE ===")
    
    # 1. Turbos par profil
    bruno_turbos = df.query('nom_profil == "bruno"')
    caloune_turbos = df.query('nom_profil == "caloune"')
    print(f"📊 Bruno: {len(bruno_turbos)} turbos")
    print(f"📊 Caloune: {len(caloune_turbos)} turbos")
    
    # 2. Turbos avec résultat
    turbos_avec_gagnant = df.query('id_photo_gagnante != ""')
    print(f"🏆 Turbos avec gagnant: {len(turbos_avec_gagnant)} ({len(turbos_avec_gagnant)/len(df)*100:.1f}%)")
    
    # 3. Ratios élevés
    ratios_eleves = df.query('ratio_photo1 > 1.5 or ratio_photo2 > 1.5')
    print(f"📈 Turbos ratios élevés (>1.5): {len(ratios_eleves)}")
    
    # 4. Double domination (plus de votes ET meilleur ratio)
    double_domination = df.query('votes_photo1 > votes_photo2 and ratio_photo1 > ratio_photo2')
    print(f"🚀 Double domination photo1: {len(double_domination)}")
    
    # 5. Cas équilibrés (ratios proches)
    ratios_proches = df.query('abs(ratio_photo1 - ratio_photo2) < 0.1')
    print(f"⚖️ Ratios équilibrés (<0.1): {len(ratios_proches)}")
    print()
    
    # === ANALYSES PAR PROFIL ===
    print("👥 === ANALYSES PAR PROFIL ===")
    
    # Performance par profil (estimation basée sur données disponibles)
    for profil in df['nom_profil'].unique():
        profil_df = df.query(f'nom_profil == "{profil}"')
        avec_gagnant = profil_df.query('id_photo_gagnante != ""')
        
        print(f"📊 {profil}:")
        print(f"   Total turbos: {len(profil_df)}")
        print(f"   Avec résultat: {len(avec_gagnant)} ({len(avec_gagnant)/len(profil_df)*100:.1f}%)")
        
        if len(avec_gagnant) > 0:
            # Analyser les patterns de victoire
            photo1_gagne = avec_gagnant.query('id_photo_gagnante == id_photo1')
            photo2_gagne = avec_gagnant.query('id_photo_gagnante == id_photo2')
            
            print(f"   Photo1 gagne: {len(photo1_gagne)} ({len(photo1_gagne)/len(avec_gagnant)*100:.1f}%)")
            print(f"   Photo2 gagne: {len(photo2_gagne)} ({len(photo2_gagne)/len(avec_gagnant)*100:.1f}%)")
            
            # Ratios moyens des gagnants
            if len(photo1_gagne) > 0:
                ratio_moyen_p1 = photo1_gagne['ratio_photo1'].mean()
                print(f"   Ratio moyen photo1 gagnante: {ratio_moyen_p1:.2f}")
            
            if len(photo2_gagne) > 0:
                ratio_moyen_p2 = photo2_gagne['ratio_photo2'].mean()
                print(f"   Ratio moyen photo2 gagnante: {ratio_moyen_p2:.2f}")
        print()
    
    # === ANALYSES PAR CHALLENGE ===
    print("🏆 === TOP CHALLENGES ===")
    
    challenge_stats = df.groupby('nom_challenge').agg({
        'id_photo1': 'count',
        'id_photo_gagnante': lambda x: (x != '').sum()
    }).rename(columns={'id_photo1': 'total_turbos', 'id_photo_gagnante': 'avec_gagnant'})
    
    challenge_stats['taux_completion'] = challenge_stats['avec_gagnant'] / challenge_stats['total_turbos'] * 100
    challenge_stats = challenge_stats.sort_values('total_turbos', ascending=False)
    
    print("Top 10 challenges par nombre de turbos:")
    for challenge, row in challenge_stats.head(10).iterrows():
        print(f"   {challenge[:40]:40} | {int(row['total_turbos']):3d} turbos | {row['taux_completion']:5.1f}% complétés")
    print()
    
    # === PRÉPARATION SKLEARN ===
    print("🤖 === PRÉPARATION MACHINE LEARNING ===")
    
    # Filtrer les données complètes
    ml_data = df.query('id_photo_gagnante != ""').copy()
    print(f"📊 Données ML: {len(ml_data)} turbos avec résultats")
    
    # Features de base
    features_base = ml_data[['votes_photo1', 'votes_photo2', 'rang_photo1', 'rang_photo2', 
                            'ratio_photo1', 'ratio_photo2']].copy()
    
    # Features dérivées
    features_base['votes_ratio'] = features_base['votes_photo1'] / features_base['votes_photo2'].replace(0, 1)
    features_base['rang_diff'] = features_base['rang_photo1'] - features_base['rang_photo2']
    features_base['ratio_diff'] = features_base['ratio_photo1'] - features_base['ratio_photo2']
    features_base['votes_diff'] = features_base['votes_photo1'] - features_base['votes_photo2']
    
    # Target: 1 si photo1 gagne, 0 si photo2 gagne
    ml_data['photo1_gagne'] = (ml_data['id_photo_gagnante'] == ml_data['id_photo1']).astype(int)
    
    print(f"📈 Features disponibles: {list(features_base.columns)}")
    print(f"🎯 Target: photo1_gagne (1={ml_data['photo1_gagne'].sum()}, 0={len(ml_data)-ml_data['photo1_gagne'].sum()})")
    
    # Statistiques features
    print(f"\n📊 Statistiques features:")
    print(features_base.describe().round(2))
    
    # Corrélations avec target
    if len(features_base) > 0:
        correlations = features_base.corrwith(ml_data['photo1_gagne']).abs().sort_values(ascending=False)
        print(f"\n🔗 Corrélations avec photo1_gagne:")
        for feature, corr in correlations.items():
            print(f"   {feature:15}: {corr:.3f}")
    
    # === PATTERNS INTÉRESSANTS ===
    print(f"\n🎯 === PATTERNS INTÉRESSANTS ===")
    
    # Pattern 1: Ratio élevé qui perd
    ratio_eleve_perd = ml_data.query('ratio_photo1 > ratio_photo2 and photo1_gagne == 0')
    print(f"❌ Ratio élevé qui perd: {len(ratio_eleve_perd)} cas")
    
    # Pattern 2: Double domination
    double_dom_gagne = ml_data.query('votes_photo1 > votes_photo2 and ratio_photo1 > ratio_photo2 and photo1_gagne == 1')
    print(f"✅ Double domination gagnante: {len(double_dom_gagne)} cas")
    
    # Pattern 3: Inversion de votes
    inversion_votes = ml_data.query('votes_photo1 < votes_photo2 and photo1_gagne == 1')
    print(f"🔄 Moins de votes mais gagne: {len(inversion_votes)} cas")
    
    # === EXPORT POUR ANALYSE EXTERNE ===
    print(f"\n💾 === EXPORT POUR ANALYSE ===")
    
    # Sauvegarder les features ML
    ml_features = features_base.copy()
    ml_features['target'] = ml_data['photo1_gagne']
    ml_features['nom_profil'] = ml_data['nom_profil']
    ml_features['nom_challenge'] = ml_data['nom_challenge']
    
    ml_features.to_feather('turbos_ml.feather')
    print(f"✅ Features ML sauvegardées: turbos_ml.feather")
    
    # CSV pour Excel/autres outils
    ml_features.to_csv('turbos_ml.csv', index=False)
    print(f"✅ CSV sauvegardé: turbos_ml.csv")
    
    print(f"\n🎯 === RÉSUMÉ ===")
    print(f"✅ {len(df)} turbos analysés")
    print(f"✅ {len(ml_data)} turbos prêts pour ML")
    print(f"✅ {len(features_base.columns)} features générées")
    print(f"✅ Fichiers prêts: turbos_ml.feather, turbos_ml.csv")
    
    return {
        'total_turbos': len(df),
        'ml_ready': len(ml_data),
        'features_count': len(features_base.columns),
        'profiles': df['nom_profil'].unique().tolist()
    }

if __name__ == "__main__":
    results = demo_turbos_analysis()
    
    print(f"\n📈 === DONNÉES PRÊTES ===")
    print(f"Fichier principal: turbos.feather ({results['total_turbos']} entrées)")
    print(f"Fichier ML: turbos_ml.feather ({results['ml_ready']} entrées)")
    print(f"Features: {results['features_count']} colonnes")
    print(f"Profils: {', '.join(results['profiles'])}")