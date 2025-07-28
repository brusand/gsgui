#!/usr/bin/env python3
"""
Interface simple pour interroger turbos.feather
Usage: python query_turbos.py [requête]
"""

import pandas as pd
import sys
import os

# Importer le module d'application d'algorithme
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from apply_algorithm import apply_algorithm_to_query_result

def format_table(df, max_rows=20):
    """Formate un DataFrame pour l'affichage"""
    if len(df) == 0:
        return "Aucun résultat"
    
    # Colonnes d'affichage principales - nouveau format
    display_cols = []
    if 'profile_name' in df.columns:
        display_cols.append('profile_name')
    if 'challenge_title' in df.columns:
        display_cols.append('challenge_title')
    if 'photo1_id' in df.columns:
        display_cols.extend(['photo1_id', 'photo2_id'])
    if 'photo1_votes' in df.columns:
        display_cols.extend(['photo1_votes', 'photo2_votes'])
    if 'photo1_ratio' in df.columns:
        display_cols.extend(['photo1_ratio', 'photo2_ratio'])
    if 'winner_id' in df.columns:
        display_cols.append('winner_id')
    # Ajouter les colonnes d'algorithme si présentes
    if 'algo_choice' in df.columns:
        display_cols.append('algo_choice')
    if 'algo_success' in df.columns:
        display_cols.append('algo_success')
    
    # Ajouter les colonnes d'ensemble si présentes
    algo_cols = [col for col in df.columns if col.endswith('_choice') and col != 'algo_choice']
    display_cols.extend(algo_cols)
    if 'majority_choice' in df.columns:
        display_cols.append('majority_choice')
    if 'majority_success' in df.columns:
        display_cols.append('majority_success')
    
    # Filtrer les colonnes existantes
    display_cols = [col for col in display_cols if col in df.columns]
    display_df = df[display_cols].copy()
    
    # Troncature des noms longs - nouveau format
    if 'challenge_title' in display_df.columns:
        display_df['challenge_title'] = display_df['challenge_title'].str[:25]
    if 'photo1_id' in display_df.columns:
        display_df['photo1_id'] = display_df['photo1_id'].str[:8]
    if 'photo2_id' in display_df.columns:
        display_df['photo2_id'] = display_df['photo2_id'].str[:8]
    if 'winner_id' in display_df.columns:
        display_df['winner_id'] = display_df['winner_id'].str[:8]
    if 'algo_choice' in display_df.columns:
        display_df['algo_choice'] = display_df['algo_choice'].str[:8]
    
    # Tronquer les colonnes d'ensemble
    for col in display_df.columns:
        if col.endswith('_choice') and col != 'algo_choice':
            try:
                display_df[col] = display_df[col].astype(str).str[:8]
            except:
                pass  # Ignorer les erreurs de conversion
    if 'majority_choice' in display_df.columns:
        try:
            display_df['majority_choice'] = display_df['majority_choice'].astype(str).str[:8]
        except:
            pass
    
    # Limiter le nombre de lignes
    if len(display_df) > max_rows:
        result = display_df.head(max_rows).to_string(index=False)
        result += f"\n... et {len(display_df) - max_rows} lignes supplémentaires"
    else:
        result = display_df.to_string(index=False)
    
    return result

def query_turbos(query_str):
    """Exécute une requête sur les données turbos"""
    try:
        # Charger les données
        df = pd.read_feather('turbos.feather')
        
        if not query_str or query_str.strip() == "":
            print(f"📊 Données turbos: {len(df)} entrées")
            print(f"👥 Profils: {', '.join(df['profile_name'].unique())}")
            print(f"📋 Colonnes: {', '.join(df.columns)}")
            return
        
        # Gestion des requêtes spéciales
        view_slice = None
        apply_algorithm = None
        original_query = query_str
        
        # Extraction du paramètre algo=
        if 'algo=' in query_str:
            import re
            # Supporter aussi les ensembles: algo=[bruno_custom,hybrid,votes_ratio]
            algo_match = re.search(r'algo=(\[[^\]]+\]|[a-zA-Z_]+)', query_str)
            if algo_match:
                apply_algorithm = algo_match.group(1)
                query_str = re.sub(r'\s*algo=(\[[^\]]+\]|[a-zA-Z_]+)', '', query_str).strip()
        
        # Extraction du paramètre view=[]
        if 'view=' in query_str:
            import re
            view_match = re.search(r'view=\[(.*?)\]', query_str)
            if view_match:
                view_param = view_match.group(1)
                query_str = re.sub(r'\s*view=\[.*?\]', '', query_str).strip()
                
                # Parser le slice
                try:
                    if ':' in view_param:
                        # Format slice [start:end]
                        parts = view_param.split(':')
                        start = int(parts[0]) if parts[0] else None
                        end = int(parts[1]) if len(parts) > 1 and parts[1] else None
                        view_slice = slice(start, end)
                    else:
                        # Index simple
                        view_slice = int(view_param)
                except:
                    print(f"⚠️ Format view invalide: {view_param}")
        
        # Gestion de la requête spéciale '*'
        if query_str.strip() == "profile_name == '*'":
            query_str = "profile_name.notna()"
        elif query_str.strip() == "nom_profil == '*'":
            query_str = "profile_name.notna()"
        
        # Nettoyer la requête (enlever les espaces en trop)
        query_str = query_str.strip()
        if not query_str:
            query_str = "profile_name.notna()"
        
        # Exécuter la requête
        result = df.query(query_str)
        
        # Appliquer l'algorithme si demandé
        if apply_algorithm:
            try:
                print(f"🤖 Application de l'algorithme: {apply_algorithm}")
                result = apply_algorithm_to_query_result(result, apply_algorithm)
            except Exception as e:
                print(f"❌ Erreur algorithme: {e}")
                return
        
        # Affichage de la requête originale si view ou algo était présent
        display_query = original_query if (view_slice is not None or apply_algorithm) else query_str
        print(f"🔍 Requête: {display_query}")
        print(f"📊 Résultats: {len(result)} lignes")
        
        if len(result) > 0:
            # Appliquer le slice view si spécifié
            if view_slice is not None:
                if isinstance(view_slice, slice):
                    view_result = result.iloc[view_slice]
                    print(f"👁️ Vue: lignes {view_slice.start or 'début'}:{view_slice.stop or 'fin'} ({len(view_result)} lignes affichées)")
                else:
                    view_result = result.iloc[[view_slice]] if view_slice < len(result) else pd.DataFrame()
                    print(f"👁️ Vue: ligne {view_slice} ({len(view_result)} ligne affichée)")
            else:
                view_result = result
            
            # Statistiques rapides (sur toutes les données, pas seulement la vue)
            if 'profile_name' in result.columns and len(result['profile_name'].unique()) > 1:
                profil_counts = result['profile_name'].value_counts()
                print(f"👥 Par profil: {dict(profil_counts)}")
            
            if 'winner_id' in result.columns:
                avec_gagnant = (result['winner_id'].notna() & (result['winner_id'] != '')).sum()
                print(f"🏆 Avec gagnant: {avec_gagnant}/{len(result)} ({avec_gagnant/len(result)*100:.1f}%)")
            
            # Statistiques algorithme si présent
            if 'algo_success' in result.columns:
                algo_total = result['algo_success'].notna().sum()
                algo_successes = result['algo_success'].sum()
                if algo_total > 0:
                    print(f"🤖 Succès algorithme: {algo_successes}/{algo_total} ({algo_successes/algo_total*100:.1f}%)")
            
            # Statistiques ensemble si présent
            if 'majority_success' in result.columns:
                maj_total = result['majority_success'].notna().sum()
                maj_successes = result['majority_success'].sum()
                if maj_total > 0:
                    print(f"🗳️ Succès vote majoritaire: {maj_successes}/{maj_total} ({maj_successes/maj_total*100:.1f}%)")
            
            print("\n📋 Données:")
            if len(view_result) > 0:
                print(format_table(view_result, max_rows=50))  # Plus de lignes si view spécifique
            else:
                print("Aucune donnée dans la vue sélectionnée")
        
    except FileNotFoundError:
        print("❌ Fichier turbos.feather non trouvé!")
        print("Exécutez d'abord: python extract_all_turbos.py")
    except Exception as e:
        print(f"❌ Erreur: {e}")

def main():
    """Fonction principale"""
    if len(sys.argv) > 1:
        # Requête passée en argument
        query = " ".join(sys.argv[1:])
        query_turbos(query)
    else:
        # Mode interactif
        print("🔍 === QUERY TURBOS - Interface simple ===")
        print("Exemples:")
        print('  python query_turbos.py \'profile_name == "bruno"\'')
        print('  python query_turbos.py "photo1_ratio > 1.5"')
        print('  python query_turbos.py "photo1_votes > photo2_votes"')
        print('  python query_turbos.py "nom_profil == \'*\'"          # Toutes les entrées')
        print('  python query_turbos.py "nom_profil == \'*\' view=[-10:]"  # 10 dernières')
        print('  python query_turbos.py "profile_name == \'bruno\' algo=bruno_custom"  # Avec algorithme')
        print('  python query_turbos.py "nom_profil == \'*\' algo=[bruno_custom,hybrid,votes_ratio]"  # Ensemble')
        print()
        
        # Afficher info sur les données
        query_turbos("")
        
        print("\n💡 Exemples de requêtes:")
        examples = [
            'profile_name == "bruno"',
            'nom_profil == "*"',                # Toutes les entrées  
            'nom_profil == "*" view=[-10:]',    # 10 dernières entrées
            'nom_profil == "*" view=[0:5]',     # 5 premières entrées
            'photo1_ratio > 1.5', 
            'photo1_votes > photo2_votes and photo1_ratio > photo2_ratio',
            'abs(photo1_ratio - photo2_ratio) < 0.1',
            'challenge_title.str.contains("Photo") view=[-5:]',
            'profile_name == "bruno" algo=bruno_custom view=[0:10]',  # Avec algorithme
            'nom_profil == "*" algo=bruno_custom view=[-20:]',        # Algorithme sur toutes les données
            'profile_name == "bruno" algo=[bruno_custom,hybrid,votes_ratio] view=[0:5]'  # Ensemble d'algorithmes
        ]
        
        for i, example in enumerate(examples, 1):
            print(f"  {i}. {example}")

if __name__ == "__main__":
    main()