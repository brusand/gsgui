#!/usr/bin/env python3
"""
Test de quelques requêtes sur turbos.feather
"""

import pandas as pd

def test_queries():
    """Test des requêtes sur les données turbos"""
    
    print("🔍 === TEST REQUÊTES TURBOS.FEATHER ===")
    
    # Charger les données
    df = pd.read_feather('turbos.feather')
    print(f"✅ {len(df)} turbos chargés")
    print()
    
    # Test de différentes requêtes
    queries = [
        ('nom_profil == "bruno"', "Turbos de Bruno"),
        ('ratio_photo1 > 1.5', "Ratios photo1 élevés"),
        ('votes_photo1 > votes_photo2 and ratio_photo1 > ratio_photo2', "Double domination photo1"),
        ('abs(ratio_photo1 - ratio_photo2) < 0.1', "Ratios équilibrés"),
        ('id_photo_gagnante != ""', "Turbos avec gagnant"),
        ('nom_challenge.str.contains("Photo")', "Challenges avec 'Photo'"),
    ]
    
    for query, description in queries:
        try:
            result = df.query(query)
            print(f"🔍 {description}")
            print(f"   Requête: {query}")
            print(f"   Résultats: {len(result)} lignes")
            
            if len(result) > 0:
                # Aperçu des 3 premières lignes
                preview = result[['nom_profil', 'nom_challenge', 'votes_photo1', 'votes_photo2', 'ratio_photo1', 'ratio_photo2']].head(3)
                print("   Aperçu:")
                for _, row in preview.iterrows():
                    print(f"      {row['nom_profil']} | {row['nom_challenge'][:20]:20} | v1:{row['votes_photo1']:3} v2:{row['votes_photo2']:3} | r1:{row['ratio_photo1']:.2f} r2:{row['ratio_photo2']:.2f}")
            print()
            
        except Exception as e:
            print(f"❌ Erreur requête '{query}': {e}")
    
    # Statistiques globales
    print("📊 === STATISTIQUES GLOBALES ===")
    print(f"Total turbos: {len(df)}")
    print(f"Profils: {', '.join(df['nom_profil'].unique())}")
    print(f"Turbos avec gagnant: {(df['id_photo_gagnante'] != '').sum()}")
    print()
    
    print("👥 Par profil:")
    for profil in df['nom_profil'].unique():
        profil_df = df[df['nom_profil'] == profil]
        avec_gagnant = (profil_df['id_photo_gagnante'] != '').sum()
        print(f"   {profil}: {len(profil_df)} turbos, {avec_gagnant} avec gagnant ({avec_gagnant/len(profil_df)*100:.1f}%)")
    
    print("\n🏆 Top 5 challenges:")
    top_challenges = df['nom_challenge'].value_counts().head(5)
    for challenge, count in top_challenges.items():
        print(f"   {challenge[:30]:30}: {count} turbos")

if __name__ == "__main__":
    test_queries()