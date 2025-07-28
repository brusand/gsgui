#!/usr/bin/env python3
"""
Interface en ligne de commande pour interroger turbos.feather
Version simple sans interface graphique
"""

import pandas as pd
import sys

def load_data():
    """Charge les données turbos"""
    try:
        df = pd.read_feather('turbos.feather')
        print(f"✅ Données chargées: {len(df)} turbos")
        print(f"📋 Colonnes: {', '.join(df.columns)}")
        print(f"👥 Profils: {', '.join(df['profile_name'].unique())}")
        return df
    except FileNotFoundError:
        print("❌ Fichier turbos.feather non trouvé!")
        print("Exécutez d'abord: python extract_all_turbos.py")
        return None
    except Exception as e:
        print(f"❌ Erreur chargement: {e}")
        return None

def display_results(df, query=""):
    """Affiche les résultats avec statistiques"""
    print(f"\n📊 === RÉSULTATS ===")
    if query:
        print(f"🔍 Requête: {query}")
    print(f"📈 Lignes: {len(df)}")
    
    if len(df) == 0:
        print("⚠️ Aucun résultat")
        return
    
    # Statistiques rapides
    if 'profile_name' in df.columns:
        profils = df['profile_name'].value_counts()
        print(f"👥 Par profil: {dict(profils)}")
    
    if 'winner_id' in df.columns:
        avec_gagnant = (df['winner_id'] != '').sum()
        print(f"🏆 Avec gagnant: {avec_gagnant}/{len(df)} ({avec_gagnant/len(df)*100:.1f}%)")
    
    # Affichage du tableau (limité)
    display_limit = 20
    if len(df) > display_limit:
        print(f"\n📋 Aperçu ({display_limit} premières lignes):")
        display_df = df.head(display_limit)
    else:
        print(f"\n📋 Toutes les données:")
        display_df = df
    
    # Colonnes principales pour l'affichage
    main_cols = ['profile_name', 'challenge_title', 'photo1_id', 'photo2_id', 'photo1_votes', 'photo2_votes', 
                'photo1_ratio', 'photo2_ratio', 'winner_id']
    available_cols = [col for col in main_cols if col in display_df.columns]
    
    # Troncature des noms longs
    display_df = display_df.copy()
    if 'challenge_title' in display_df.columns:
        display_df['challenge_title'] = display_df['challenge_title'].str[:20]
    if 'photo1_id' in display_df.columns:
        display_df['photo1_id'] = display_df['photo1_id'].str[:8]
    if 'photo2_id' in display_df.columns:
        display_df['photo2_id'] = display_df['photo2_id'].str[:8]
    if 'winner_id' in display_df.columns:
        display_df['winner_id'] = display_df['winner_id'].str[:8]
    
    print(display_df[available_cols].to_string(index=False))
    
    if len(df) > display_limit:
        print(f"\n... et {len(df) - display_limit} lignes supplémentaires")

def show_examples():
    """Affiche des exemples de requêtes"""
    examples = [
        'profile_name == "bruno"',
        'profile_name == "caloune"',
        'profile_name == "*"                              # Toutes les entrées',
        'profile_name == "*" view=[-10:]                  # 10 dernières entrées',
        'profile_name == "*" view=[0:5]                   # 5 premières entrées',
        'winner_id != ""',
        'photo1_ratio > 1.5',
        'photo1_votes > photo2_votes',
        'photo1_votes > 500 and photo1_ratio > 1.5',
        'abs(photo1_ratio - photo2_ratio) < 0.1',
        'challenge_title.str.contains("Photo")',
        'photo1_ratio > photo2_ratio and photo1_votes < photo2_votes',
        'profile_name == "bruno" and photo1_ratio > 1.8 view=[-3:]'
    ]
    
    print("\n💡 === EXEMPLES DE REQUÊTES ===")
    for i, example in enumerate(examples, 1):
        print(f"{i:2d}. {example}")
    print()

def main():
    """Fonction principale interactive"""
    print("🔍 === TURBOS CLI - Interrogation de turbos.feather ===")
    print("Tapez 'help' pour l'aide, 'exit' pour quitter")
    print("=" * 60)
    
    # Charger les données
    df = load_data()
    if df is None:
        return
    
    current_df = df.copy()
    
    while True:
        try:
            # Saisie de la requête
            query = input(f"\n🔍 Requête SQL-like (ou 'help'): ").strip()
            
            if query.lower() in ['exit', 'quit', 'q']:
                print("👋 Au revoir!")
                break
            
            elif query.lower() in ['help', 'h', '?']:
                show_examples()
                continue
            
            elif query.lower() in ['reset', 'r']:
                current_df = df.copy()
                print("🔄 Vue réinitialisée")
                display_results(current_df)
                continue
            
            elif query.lower() in ['export', 'e']:
                filename = f"turbos_export_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
                current_df.to_csv(filename, index=False)
                print(f"💾 Export: {filename} ({len(current_df)} lignes)")
                continue
            
            elif query.lower() in ['stats', 's']:
                print(f"\n📊 === STATISTIQUES ===")
                print(f"Total turbos: {len(df)}")
                print(f"Turbos affichés: {len(current_df)}")
                print(f"Colonnes: {len(df.columns)}")
                print("\nDistribution par profil:")
                print(df['profile_name'].value_counts())
                print("\nTop 10 challenges:")
                print(df['challenge_title'].value_counts().head(10))
                continue
            
            elif not query:
                # Requête vide = afficher tout
                current_df = df.copy()
                display_results(current_df)
                continue
            
            # Exécuter la requête
            try:
                result_df = df.query(query)
                current_df = result_df
                display_results(result_df, query)
                
            except Exception as e:
                print(f"❌ Erreur requête: {e}")
                print("💡 Vérifiez la syntaxe pandas (ex: profile_name == \"bruno\")")
        
        except KeyboardInterrupt:
            print("\n👋 Au revoir!")
            break
        except EOFError:
            print("\n👋 Au revoir!")
            break

if __name__ == "__main__":
    main()