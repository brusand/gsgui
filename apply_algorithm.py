#!/usr/bin/env python3
"""
Module pour appliquer l'algorithme bruno_custom sur une sélection de données
et ajouter les colonnes algo_choice et algo_success
"""

import pandas as pd
import sys
import os

# Importer les algorithmes
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from bruno_custom_refined import bruno_custom_refined
from ensemble_algorithms import ensemble_vote, hybrid_algorithm, votes_ratio_algorithm, ratio_low_algorithm, votes_high_algorithm, random_algorithm
from position_aware_algorithm import position_aware_algorithm
from adaptive_time_algorithm import adaptive_time_algorithm

def apply_bruno_custom_algorithm(df):
    """
    Applique l'algorithme bruno_custom sur un DataFrame et ajoute les colonnes:
    - algo_choice: ID de la photo sélectionnée par l'algorithme
    - algo_success: True si l'algorithme a choisi le gagnant, False sinon
    """
    
    if len(df) == 0:
        return df
    
    # Créer les nouvelles colonnes
    algo_choices = []
    algo_successes = []
    
    for _, row in df.iterrows():
        # Préparer les données pour l'algorithme
        first_data = {
            'ratio': row['photo1_ratio'],
            'votes': row['photo1_votes'], 
            'rank': row['photo1_rank']
        }
        
        second_data = {
            'ratio': row['photo2_ratio'],
            'votes': row['photo2_votes'],
            'rank': row['photo2_rank']
        }
        
        # Appliquer l'algorithme
        try:
            winner_id, winner_ratio, loser_ratio, winner_votes, reason = bruno_custom_refined(
                row['photo1_id'], first_data, 
                row['photo2_id'], second_data
            )
            
            algo_choices.append(winner_id)
            
            # Déterminer le succès: l'algorithme a-t-il choisi le même que le vrai gagnant?
            actual_winner = row['winner_id']
            if pd.isna(actual_winner) or actual_winner == '':
                # Pas de gagnant réel connu
                algo_successes.append(None)
            else:
                # Comparer avec le gagnant réel
                algo_successes.append(winner_id == actual_winner)
                
        except Exception as e:
            print(f"Erreur algorithme pour ligne {row.name}: {e}")
            algo_choices.append(None)
            algo_successes.append(None)
    
    # Ajouter les colonnes au DataFrame
    df_result = df.copy()
    df_result['algo_choice'] = algo_choices
    df_result['algo_success'] = algo_successes
    
    return df_result

def apply_position_aware_algorithm(df):
    """
    Applique l'algorithme position_aware sur un DataFrame et ajoute les colonnes:
    - algo_choice: ID de la photo sélectionnée par l'algorithme
    - algo_success: True si l'algorithme a choisi le gagnant, False sinon
    """
    
    if len(df) == 0:
        return df
    
    # Créer les nouvelles colonnes
    algo_choices = []
    algo_successes = []
    
    for _, row in df.iterrows():
        # Préparer les données pour l'algorithme
        first_data = {
            'ratio': row['photo1_ratio'],
            'votes': row['photo1_votes'], 
            'rank': row['photo1_rank']
        }
        
        second_data = {
            'ratio': row['photo2_ratio'],
            'votes': row['photo2_votes'],
            'rank': row['photo2_rank']
        }
        
        # Appliquer l'algorithme
        try:
            winner_id, winner_ratio, loser_ratio, winner_votes, reason = position_aware_algorithm(
                row['photo1_id'], first_data, 
                row['photo2_id'], second_data
            )
            
            algo_choices.append(winner_id)
            
            # Déterminer le succès: l'algorithme a-t-il choisi le même que le vrai gagnant?
            actual_winner = row['winner_id']
            if pd.isna(actual_winner) or actual_winner == '':
                # Pas de gagnant réel connu
                algo_successes.append(None)
            else:
                # Comparer avec le gagnant réel
                algo_successes.append(winner_id == actual_winner)
                
        except Exception as e:
            print(f"Erreur algorithme pour ligne {row.name}: {e}")
            algo_choices.append(None)
            algo_successes.append(None)
    
    # Ajouter les colonnes au DataFrame
    df_result = df.copy()
    df_result['algo_choice'] = algo_choices
    df_result['algo_success'] = algo_successes
    
    return df_result

def apply_ensemble_algorithms(df, algorithms=['bruno_custom', 'hybrid', 'votes_ratio']):
    """
    Applique un ensemble d'algorithmes avec vote majoritaire
    Ajoute une colonne pour chaque algorithme + majority_choice et majority_success
    """
    
    if len(df) == 0:
        return df
    
    # Créer les colonnes pour chaque algorithme
    algo_columns = {}
    for algo in algorithms:
        algo_columns[f'{algo}_choice'] = []
    
    majority_choices = []
    majority_successes = []
    
    for _, row in df.iterrows():
        # Préparer les données pour les algorithmes
        first_data = {
            'ratio': row['photo1_ratio'],
            'votes': row['photo1_votes'], 
            'rank': row['photo1_rank']
        }
        
        second_data = {
            'ratio': row['photo2_ratio'],
            'votes': row['photo2_votes'],
            'rank': row['photo2_rank']
        }
        
        try:
            # Appliquer l'ensemble d'algorithmes
            majority_choice, individual_choices, vote_details, majority_reason = ensemble_vote(
                row['photo1_id'], first_data, 
                row['photo2_id'], second_data,
                algorithms
            )
            
            # Stocker les choix individuels
            for algo in algorithms:
                algo_columns[f'{algo}_choice'].append(individual_choices.get(algo, None))
            
            majority_choices.append(majority_choice)
            
            # Déterminer le succès: le vote majoritaire a-t-il choisi le bon gagnant?
            actual_winner = row['winner_id']
            if pd.isna(actual_winner) or actual_winner == '':
                majority_successes.append(None)
            else:
                majority_successes.append(majority_choice == actual_winner)
                
        except Exception as e:
            print(f"Erreur ensemble pour ligne {row.name}: {e}")
            for algo in algorithms:
                algo_columns[f'{algo}_choice'].append(None)
            majority_choices.append(None)
            majority_successes.append(None)
    
    # Ajouter toutes les colonnes au DataFrame
    df_result = df.copy()
    for col_name, col_data in algo_columns.items():
        df_result[col_name] = col_data
    df_result['majority_choice'] = majority_choices
    df_result['majority_success'] = majority_successes
    
    return df_result

def apply_algorithm_to_query_result(df, algorithm='bruno_custom'):
    """
    Interface principale pour appliquer un algorithme à un résultat de requête
    Supporte: algorithmes individuels ou ensemble d'algorithmes
    """
    
    # Vérifier que les colonnes nécessaires sont présentes
    required_cols = ['photo1_id', 'photo2_id', 'photo1_ratio', 'photo2_ratio', 
                     'photo1_votes', 'photo2_votes', 'photo1_rank', 'photo2_rank']
    
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Colonnes manquantes: {missing_cols}")
    
    # Traiter les ensembles d'algorithmes
    if algorithm.startswith('[') and algorithm.endswith(']'):
        # Parse ensemble: [bruno_custom,hybrid,votes_ratio]
        algo_list = algorithm[1:-1].split(',')
        algo_list = [algo.strip() for algo in algo_list]
        
        print(f"🤖 Application de l'ensemble {algorithm} sur {len(df)} entrées...")
        df_result = apply_ensemble_algorithms(df, algo_list)
        
        # Statistiques pour l'ensemble
        total_with_winner = (df_result['winner_id'].notna() & (df_result['winner_id'] != '')).sum()
        majority_successes = df_result['majority_success'].sum() if 'majority_success' in df_result.columns else 0
        
        print(f"✅ Ensemble appliqué:")
        print(f"   - Algorithmes: {', '.join(algo_list)}")
        print(f"   - Entrées traitées: {len(df_result)}")
        print(f"   - Avec gagnant réel: {total_with_winner}")
        if total_with_winner > 0 and majority_successes > 0:
            success_rate = majority_successes / total_with_winner * 100
            print(f"   - Succès vote majoritaire: {majority_successes}/{total_with_winner} ({success_rate:.1f}%)")
        
        # Statistiques par algorithme individuel
        for algo in algo_list:
            col_name = f'{algo}_choice'
            if col_name in df_result.columns:
                algo_successes = sum(
                    1 for i, row in df_result.iterrows() 
                    if (pd.notna(row['winner_id']) and row['winner_id'] != '' and 
                        pd.notna(row[col_name]) and row[col_name] == row['winner_id'])
                )
                if total_with_winner > 0:
                    algo_rate = algo_successes / total_with_winner * 100
                    print(f"   - Succès {algo}: {algo_successes}/{total_with_winner} ({algo_rate:.1f}%)")
        
        return df_result
    
    # Algorithmes individuels
    elif algorithm == 'bruno_custom':
        print(f"🤖 Application de l'algorithme {algorithm} sur {len(df)} entrées...")
        df_result = apply_bruno_custom_algorithm(df)
        
    elif algorithm == 'position_aware':
        print(f"🤖 Application de l'algorithme {algorithm} sur {len(df)} entrées...")
        df_result = apply_position_aware_algorithm(df)
        
    elif algorithm == 'adaptive_time':
        print(f"🤖 Application de l'algorithme {algorithm} sur {len(df)} entrées...")
        df_result = apply_adaptive_time_algorithm(df)
        
    else:
        raise ValueError(f"Algorithme non supporté: {algorithm}")
    
    # Statistiques pour algorithme individuel
    total_with_winner = (df_result['winner_id'].notna() & (df_result['winner_id'] != '')).sum()
    algo_successes = df_result['algo_success'].sum() if 'algo_success' in df_result.columns else 0
    
    print(f"✅ Algorithme appliqué:")
    print(f"   - Entrées traitées: {len(df_result)}")
    print(f"   - Avec gagnant réel: {total_with_winner}")
    if total_with_winner > 0 and algo_successes > 0:
        success_rate = algo_successes / total_with_winner * 100
        print(f"   - Succès de l'algorithme: {algo_successes}/{total_with_winner} ({success_rate:.1f}%)")
    
    return df_result

def apply_adaptive_time_algorithm(df):
    """
    Applique l'algorithme adaptive_time sur un DataFrame et ajoute les colonnes:
    - algo_choice: ID de la photo sélectionnée par l'algorithme
    - algo_success: True si l'algorithme a choisi le gagnant, False sinon
    """
    
    if len(df) == 0:
        return df
    
    # Créer les nouvelles colonnes
    algo_choices = []
    algo_successes = []
    
    for _, row in df.iterrows():
        # Préparer les données pour l'algorithme
        first_data = {
            'ratio': row['photo1_ratio'],
            'votes': row['photo1_votes'], 
            'rank': row['photo1_rank']
        }
        
        second_data = {
            'ratio': row['photo2_ratio'],
            'votes': row['photo2_votes'],
            'rank': row['photo2_rank']
        }
        
        # Appliquer l'algorithme avec un temps par défaut
        try:
            winner_id, winner_ratio, loser_ratio, winner_votes, reason = adaptive_time_algorithm(
                row['photo1_id'], first_data, 
                row['photo2_id'], second_data,
                time_left="0D 12H 0M 0S"  # Temps par défaut moyen terme
            )
            
            algo_choices.append(winner_id)
            
            # Déterminer le succès: l'algorithme a-t-il choisi le même que le vrai gagnant?
            actual_winner = row['winner_id']
            if pd.isna(actual_winner) or actual_winner == '':
                # Pas de gagnant réel connu
                algo_successes.append(None)
            else:
                # Comparer avec le gagnant réel
                algo_successes.append(winner_id == actual_winner)
                
        except Exception as e:
            print(f"Erreur algorithme pour ligne {row.name}: {e}")
            algo_choices.append(None)
            algo_successes.append(None)
    
    # Ajouter les colonnes au DataFrame
    df_result = df.copy()
    df_result['algo_choice'] = algo_choices
    df_result['algo_success'] = algo_successes
    
    return df_result

if __name__ == "__main__":
    # Test rapide
    print("🧪 Test apply_algorithm.py")
    
    # Charger quelques données pour test
    try:
        df = pd.read_feather('turbos.feather')
        df_sample = df.head(5)
        
        print(f"📊 Test sur {len(df_sample)} entrées:")
        df_result = apply_algorithm_to_query_result(df_sample)
        
        print("\n📋 Résultat:")
        display_cols = ['photo1_id', 'photo2_id', 'winner_id', 'algo_choice', 'algo_success']
        print(df_result[display_cols].to_string(index=False))
        
    except Exception as e:
        print(f"❌ Erreur test: {e}")