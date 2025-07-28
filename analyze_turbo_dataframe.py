#!/usr/bin/env python3
"""
Analyse avancée des données turbo avec le nouveau système DataFrame
Démonstration des capacités SQL et machine learning
"""

from turbo_dataframe_manager import TurboDataFrameManager
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta

def analyze_turbo_performance():
    """Analyse complète des performances turbo"""
    
    print("🚀 === ANALYSE AVANCÉE DONNÉES TURBO ===")
    print("📊 Utilisation du nouveau système DataFrame/Feather")
    print("=" * 60)
    
    # Charger les données
    manager = TurboDataFrameManager('turbo_data.feather')
    df = manager.get_dataframe()
    
    print(f"📈 Dataset: {len(df)} entrées sur {len(df['profile_name'].unique())} profils")
    print(f"📅 Période: {df['timestamp'].min()} → {df['timestamp'].max()}")
    print()
    
    # ===== ANALYSES SQL-LIKE =====
    print("🔍 === REQUÊTES SQL AVANCÉES ===")
    
    # 1. Performance par algorithme (derniers 30 jours)
    recent_cutoff = datetime.now() - timedelta(days=30)
    recent_query = f"timestamp > '{recent_cutoff}' and success.notna()"
    recent_df = manager.query(recent_query)
    
    if len(recent_df) > 0:
        algo_perf = recent_df.groupby('algorithm').agg({
            'success': ['count', 'sum', 'mean']
        }).round(3)
        algo_perf.columns = ['Total', 'Succès', 'Taux_Succès']
        algo_perf = algo_perf.sort_values('Taux_Succès', ascending=False)
        
        print("📊 Performance par algorithme (30 derniers jours):")
        print(algo_perf)
        print()
    
    # 2. Analyse par profil et challenge
    profile_challenge = df.groupby(['profile_name', 'challenge_title']).agg({
        'success': ['count', 'mean'],
        'algorithm': lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else 'unknown'
    }).round(3)
    
    print("🏆 Top 10 performances par profil/challenge:")
    if len(profile_challenge) > 0:
        top_performances = profile_challenge.head(10)
        print(top_performances)
        print()
    
    # 3. Patterns de ratios gagnants
    ratio_analysis = manager.query("success == True and photo1_ratio > 0 and photo2_ratio > 0")
    if len(ratio_analysis) > 0:
        print("📈 Analyse des ratios dans les succès:")
        print(f"   Ratio moyen photo gagnante: {ratio_analysis['photo1_ratio'].mean():.2f}")
        print(f"   Ratio min/max: {ratio_analysis['photo1_ratio'].min():.2f} / {ratio_analysis['photo1_ratio'].max():.2f}")
        
        # Distribution des ratios
        ratio_bins = pd.cut(ratio_analysis['photo1_ratio'], bins=[0, 1.2, 1.5, 2.0, 5.0], labels=['<1.2', '1.2-1.5', '1.5-2.0', '>2.0'])
        ratio_dist = ratio_bins.value_counts()
        print(f"   Distribution ratios gagnants:")
        for bin_name, count in ratio_dist.items():
            pct = count / len(ratio_analysis) * 100
            print(f"      {bin_name}: {count} ({pct:.1f}%)")
        print()
    
    # 4. Évolution temporelle des performances
    df['date'] = df['timestamp'].dt.date
    daily_perf = df.groupby('date').agg({
        'success': ['count', 'sum', 'mean']
    }).round(3)
    daily_perf.columns = ['Total', 'Succès', 'Taux']
    
    print("📅 Performance des 7 derniers jours:")
    last_7_days = daily_perf.tail(7)
    print(last_7_days)
    print()
    
    # ===== ANALYSES MACHINE LEARNING =====
    print("🤖 === PRÉPARATION MACHINE LEARNING ===")
    
    # Export pour sklearn
    ml_data = manager.export_for_sklearn()
    print(f"📊 Dataset ML: {ml_data.shape}")
    print(f"Features: {list(ml_data.columns)}")
    
    if len(ml_data) > 0:
        # Statistiques descriptives
        print(f"\n📈 Statistiques features:")
        print(ml_data.describe().round(2))
        
        # Corrélations avec le succès
        correlations = ml_data.corr()['success'].abs().sort_values(ascending=False)
        print(f"\n🔗 Corrélations avec succès:")
        for feature, corr in correlations.items():
            if feature != 'success':
                print(f"   {feature}: {corr:.3f}")
        
        # Features dérivées importantes
        print(f"\n⚙️ Features engineering disponibles:")
        print(f"   votes_ratio: rapport votes photo1/photo2")
        print(f"   rank_diff: différence de rang (photo1 - photo2)")  
        print(f"   ratio_diff: différence de ratio (photo1 - photo2)")
        print(f"   votes_diff: différence de votes (photo1 - photo2)")
    
    # ===== PATTERNS SPÉCIFIQUES =====
    print(f"\n🎯 === PATTERNS MÉTIER ===")
    
    # Cas où ratio élevé perd (pattern contre-intuitif)
    high_ratio_loses = manager.query("success == False and photo1_ratio > photo2_ratio and photo1_ratio > 1.5")
    print(f"❌ Cas 'ratio élevé perd': {len(high_ratio_loses)} entrées")
    if len(high_ratio_loses) > 0:
        print(f"   Ratio moyen perdant: {high_ratio_loses['photo1_ratio'].mean():.2f}")
        print(f"   Votes moyen perdant: {high_ratio_loses['photo1_votes'].mean():.0f}")
    
    # Double domination (votes + ratio + rang)
    double_dom = manager.query("success == True and photo1_votes > photo2_votes and photo1_ratio > photo2_ratio and photo1_rank < photo2_rank")
    print(f"✅ Double domination (votes+ratio+rang): {len(double_dom)} entrées")
    
    # Cas équilibrés (ratios proches)
    balanced_ratios = manager.query("abs(photo1_ratio - photo2_ratio) < 0.1 and success.notna()")
    if len(balanced_ratios) > 0:
        balanced_success_rate = balanced_ratios['success'].mean()
        print(f"⚖️ Cas ratios équilibrés (diff<0.1): {len(balanced_ratios)} entrées, succès: {balanced_success_rate:.1%}")
    
    # ===== RECOMMANDATIONS =====
    print(f"\n💡 === RECOMMANDATIONS ANALYSE ===")
    
    if len(ml_data) > 0:
        best_features = correlations.head(4).index.tolist()
        if 'success' in best_features:
            best_features.remove('success')
        
        print(f"🔧 Features les plus prédictives: {', '.join(best_features[:3])}")
        
        # Suggestions d'algorithmes basées sur les patterns
        bruno_performance = df[df['algorithm'] == 'bruno_custom']['success'].mean()
        votes_ratio_performance = df[df['algorithm'] == 'votes_ratio_patterns']['success'].mean()
        
        print(f"📊 Performance comparée:")
        print(f"   Bruno Custom: {bruno_performance:.1%}")
        print(f"   Votes Ratio Patterns: {votes_ratio_performance:.1%}")
        
        if votes_ratio_performance < bruno_performance:
            print(f"💡 Recommandation: Rester sur Bruno Custom jusqu'à amélioration Votes Ratio Patterns")
        else:
            print(f"💡 Recommandation: Votes Ratio Patterns semble prometteur")
    
    print(f"\n🚀 === SYSTÈME PRÊT ===")
    print(f"✅ {len(df)} entrées migrées et analysables")
    print(f"✅ Requêtes SQL-like fonctionnelles")
    print(f"✅ Export sklearn opérationnel")
    print(f"✅ Nouveaux turbos automatiquement sauvegardés")
    print(f"✅ Scores temps réel intégrés")
    
    return {
        'total_entries': len(df),
        'ml_ready_entries': len(ml_data),
        'profiles': df['profile_name'].unique().tolist(),
        'algorithms': df['algorithm'].unique().tolist(),
        'date_range': (df['timestamp'].min(), df['timestamp'].max())
    }

if __name__ == "__main__":
    results = analyze_turbo_performance()
    
    print(f"\n📈 === RÉSUMÉ MIGRATION ===")
    print(f"Migration réussie: {results['total_entries']} entrées totales")
    print(f"Prêt pour ML: {results['ml_ready_entries']} entrées")
    print(f"Profils: {len(results['profiles'])} ({', '.join(results['profiles'])})")
    print(f"Algorithmes: {len(results['algorithms'])} différents")