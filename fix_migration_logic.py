#!/usr/bin/env python3
"""
Correction du script de migration pour éviter les incohérences
Validation des winner_id avant déduction du chosen_id
"""

from configobj import ConfigObj
from turbo_dataframe_manager import TurboDataFrameManager
from datetime import datetime
import re
import pandas as pd

def safe_float(val, default=0.0):
    """Conversion sécurisée vers float"""
    try:
        return float(val) if val else default
    except (ValueError, TypeError):
        return default

def safe_int(val, default=0):
    """Conversion sécurisée vers int"""
    try:
        return int(float(val)) if val else default
    except (ValueError, TypeError):
        return default

def migrate_turbo_data_fixed():
    """Migration corrigée avec validation des winner_id"""
    
    print("🔧 === MIGRATION CORRIGÉE DES DONNÉES TURBO ===")
    print("✅ Validation des winner_id avant déduction chosen_id")
    print("=" * 60)
    
    config_files = ['gsgui.ini', 'src/gs/gsgui.ini', 'backend/data/gsgui.ini']
    
    all_entries = []
    inconsistent_count = 0
    total_entries = 0
    
    for config_path in config_files:
        if not Path(config_path).exists():
            continue
            
        print(f"\n📁 Traitement: {config_path}")
        
        try:
            config = ConfigObj(config_path, encoding='utf-8')
        except Exception as e:
            print(f"❌ Erreur lecture {config_path}: {e}")
            continue
        
        turbo_history = config.get('turbo_history', {})
        if not turbo_history:
            continue
        
        for profile_name, profile_history in turbo_history.items():
            if not isinstance(profile_history, dict):
                continue
                
            print(f"   👤 Profil: {profile_name}")
            profile_entries = 0
            profile_inconsistent = 0
            
            for entry_key, entry_data in profile_history.items():
                if not isinstance(entry_data, dict):
                    continue
                
                total_entries += 1
                
                try:
                    # Extraire données de base
                    timestamp = entry_data.get('timestamp')
                    if timestamp:
                        try:
                            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        except:
                            timestamp = datetime.now()
                    else:
                        timestamp = datetime.now()
                    
                    challenge_id = entry_data.get('challenge_id', '')
                    challenge_title = entry_data.get('challenge_title', '')
                    time_left = entry_data.get('time_left', '')
                    algorithm = entry_data.get('algorithm', 'unknown')
                    strategy_description = entry_data.get('strategy_description', '')
                    
                    # Données des photos
                    photo1_data = entry_data.get('photo1', {})
                    photo2_data = entry_data.get('photo2', {})
                    
                    photo1_id = photo1_data.get('id', '')
                    photo2_id = photo2_data.get('id', '')
                    
                    if not photo1_id or not photo2_id:
                        continue
                    
                    # Données numériques
                    photo1_votes = safe_int(photo1_data.get('votes'))
                    photo2_votes = safe_int(photo2_data.get('votes'))
                    photo1_rank = safe_int(photo1_data.get('rank'))
                    photo2_rank = safe_int(photo2_data.get('rank'))
                    photo1_ratio = safe_float(photo1_data.get('ratio'))
                    photo2_ratio = safe_float(photo2_data.get('ratio'))
                    
                    # Winner et success
                    winner_data = entry_data.get('winner', {})
                    winner_id = winner_data.get('id', '')
                    success = entry_data.get('success')
                    if isinstance(success, str):
                        success = success.lower() in ['true', '1', 'yes']
                    
                    # ===== LOGIQUE CORRIGÉE =====
                    chosen_id = ''
                    
                    # 1. D'abord valider que winner_id est cohérent
                    is_winner_valid = winner_id in [photo1_id, photo2_id] if winner_id else False
                    
                    if not is_winner_valid and winner_id:
                        # Winner_id incohérent - marquer comme problématique
                        print(f"      ⚠️ Winner incohérent: {entry_key[:60]}...")
                        print(f"         Photo1: {photo1_id[:8]}, Photo2: {photo2_id[:8]}")
                        print(f"         Winner: {winner_id[:8]} (ne correspond à aucune photo)")
                        inconsistent_count += 1
                        profile_inconsistent += 1
                        
                        # Ignorer cette entrée ou la marquer différemment
                        continue  # Skip les entrées incohérentes
                    
                    # 2. Déduire chosen_id seulement si winner_id est valide
                    if is_winner_valid and success is not None:
                        if success:
                            # Success: l'algorithme a choisi le gagnant
                            chosen_id = winner_id
                        else:
                            # Failed: l'algorithme a choisi l'autre photo
                            chosen_id = photo2_id if winner_id == photo1_id else photo1_id
                    
                    # Créer l'entrée
                    entry = {
                        'timestamp': timestamp,
                        'profile_name': profile_name,
                        'challenge_id': challenge_id,
                        'challenge_title': challenge_title,
                        'time_left': time_left,
                        'algorithm': algorithm,
                        'photo1_id': photo1_id,
                        'photo2_id': photo2_id,
                        'photo1_votes': photo1_votes,
                        'photo2_votes': photo2_votes,
                        'photo1_rank': photo1_rank,
                        'photo2_rank': photo2_rank,
                        'photo1_ratio': photo1_ratio,
                        'photo2_ratio': photo2_ratio,
                        'winner_id': winner_id if is_winner_valid else None,
                        'chosen_id': chosen_id if chosen_id else None,
                        'success': success,
                        'scores_photo1': None,
                        'scores_photo2': None,
                        'strategy_description': strategy_description
                    }
                    
                    all_entries.append(entry)
                    profile_entries += 1
                    
                except Exception as e:
                    print(f"      ❌ Erreur entrée {entry_key}: {e}")
                    continue
            
            if profile_inconsistent > 0:
                print(f"      ⚠️ {profile_inconsistent} entrées incohérentes ignorées")
            print(f"      ✅ {profile_entries} entrées valides extraites")
    
    print(f"\n📊 === RÉSUMÉ MIGRATION CORRIGÉE ===")
    print(f"   Entrées traitées: {total_entries}")
    print(f"   Entrées incohérentes: {inconsistent_count}")
    print(f"   Entrées valides: {len(all_entries)}")
    print(f"   Taux de cohérence: {(len(all_entries)/(total_entries-inconsistent_count)*100) if total_entries > inconsistent_count else 100:.1f}%")
    
    if len(all_entries) == 0:
        print("❌ Aucune donnée valide à migrer")
        return
    
    # Créer le DataFrame
    print(f"\n💾 Création du DataFrame corrigé...")
    df = pd.DataFrame(all_entries)
    
    # Définir les types de données
    df = df.astype({
        'timestamp': 'datetime64[ns]',
        'profile_name': 'string',
        'challenge_id': 'string', 
        'challenge_title': 'string',
        'time_left': 'string',
        'algorithm': 'string',
        'photo1_id': 'string',
        'photo2_id': 'string',
        'photo1_votes': 'Int64',
        'photo2_votes': 'Int64', 
        'photo1_rank': 'Int64',
        'photo2_rank': 'Int64',
        'photo1_ratio': 'float64',
        'photo2_ratio': 'float64',
        'winner_id': 'string',
        'chosen_id': 'string',
        'success': 'boolean',
        'scores_photo1': 'float64',
        'scores_photo2': 'float64',
        'strategy_description': 'string'
    })
    
    # Sauvegarder
    df.to_feather('turbos_fixed.feather')
    print(f"✅ Données corrigées sauvegardées: turbos_fixed.feather")
    
    # Test de cohérence final
    print(f"\n🔍 === VÉRIFICATION FINALE ===")
    with_winner = df[df['winner_id'].notna() & (df['winner_id'] != '')]
    
    inconsistent_final = 0
    for _, row in with_winner.iterrows():
        if row['winner_id'] not in [row['photo1_id'], row['photo2_id']]:
            inconsistent_final += 1
    
    print(f"✅ Entrées avec gagnant: {len(with_winner)}")
    print(f"✅ Entrées cohérentes: {len(with_winner) - inconsistent_final}")
    print(f"❌ Entrées incohérentes: {inconsistent_final}")
    print(f"🎯 Taux final de cohérence: {(len(with_winner) - inconsistent_final)/len(with_winner)*100:.1f}%")
    
    return df

if __name__ == "__main__":
    from pathlib import Path
    df_fixed = migrate_turbo_data_fixed()
    
    if df_fixed is not None:
        print(f"\n🎉 === MIGRATION CORRIGÉE TERMINÉE ===")
        print(f"✅ Fichier: turbos_fixed.feather ({len(df_fixed)} entrées)")
        print(f"✅ Cohérence: 100% garantie")
        print(f"✅ Prêt pour remplacement de turbos.feather")