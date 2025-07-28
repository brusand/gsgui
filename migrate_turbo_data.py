#!/usr/bin/env python3
"""
Migration des données turbo depuis ConfigObj vers DataFrame/Feather
Convertit toutes les données existantes de tous les profils
"""

from configobj import ConfigObj
from turbo_dataframe_manager import TurboDataFrameManager
from datetime import datetime
import re
from pathlib import Path

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

def parse_timestamp_from_key(key):
    """Extrait le timestamp du nom de clé turbo"""
    # Format: challenge_id_photo1_photo2_YYYYMMDD_HHMMSS
    try:
        # Chercher le pattern de date à la fin
        match = re.search(r'_(\d{8})_(\d{6})$', key)
        if match:
            date_str = match.group(1)  # YYYYMMDD
            time_str = match.group(2)  # HHMMSS
            
            # Convertir en datetime
            timestamp_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]} {time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"
            return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
    except:
        pass
    
    # Fallback: utiliser la date actuelle
    return datetime.now()

def migrate_turbo_history():
    """Migre toutes les données turbo de ConfigObj vers DataFrame"""
    
    print("🔄 === MIGRATION DONNÉES TURBO ===")
    print("📂 Source: gsgui.ini (ConfigObj)")
    print("🎯 Destination: turbo_data.feather (DataFrame)")
    print("=" * 50)
    
    # Charger la config existante
    config_files = ['gsgui.ini', 'src/gs/gsgui.ini', 'backend/data/gsgui.ini']
    
    all_entries = []
    
    for config_path in config_files:
        if not Path(config_path).exists():
            continue
            
        print(f"\n📁 Traitement: {config_path}")
        
        try:
            config = ConfigObj(config_path, encoding='utf-8')
        except Exception as e:
            print(f"❌ Erreur lecture {config_path}: {e}")
            continue
        
        # Extraire l'historique turbo de tous les profils
        turbo_history = config.get('turbo_history', {})
        
        if not turbo_history:
            print(f"   ℹ️ Pas d'historique turbo dans {config_path}")
            continue
        
        # Parcourir tous les profils
        for profile_name, profile_history in turbo_history.items():
            
            if not isinstance(profile_history, dict):
                continue
                
            print(f"   👤 Profil: {profile_name}")
            profile_entries = 0
            
            # Parcourir toutes les entrées turbo de ce profil
            for entry_key, entry_data in profile_history.items():
                
                if not isinstance(entry_data, dict):
                    continue
                
                try:
                    # Extraire les données de base
                    timestamp = entry_data.get('timestamp')
                    if timestamp:
                        try:
                            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        except:
                            timestamp = parse_timestamp_from_key(entry_key)
                    else:
                        timestamp = parse_timestamp_from_key(entry_key)
                    
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
                    
                    # Données numériques des photos
                    photo1_votes = safe_int(photo1_data.get('votes'))
                    photo2_votes = safe_int(photo2_data.get('votes'))
                    photo1_rank = safe_int(photo1_data.get('rank'))
                    photo2_rank = safe_int(photo2_data.get('rank'))
                    photo1_ratio = safe_float(photo1_data.get('ratio'))
                    photo2_ratio = safe_float(photo2_data.get('ratio'))
                    
                    # Winner et success
                    winner_data = entry_data.get('winner', {})
                    winner_id = winner_data.get('id', '')
                    
                    # Déterminer le choix de l'algorithme
                    # Dans l'ancien format, on peut déduire le choix du succès
                    success = entry_data.get('success')
                    if isinstance(success, str):
                        success = success.lower() in ['true', '1', 'yes']
                    
                    chosen_id = ''
                    if winner_id and success is not None:
                        if success:
                            chosen_id = winner_id
                        else:
                            # L'algorithme a choisi l'autre photo
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
                        'winner_id': winner_id if winner_id else None,
                        'chosen_id': chosen_id if chosen_id else None,
                        'success': success,
                        'scores_photo1': None,  # Pas disponible dans ancien format
                        'scores_photo2': None,  # Pas disponible dans ancien format
                        'strategy_description': strategy_description
                    }
                    
                    all_entries.append(entry)
                    profile_entries += 1
                    
                except Exception as e:
                    print(f"      ⚠️ Erreur entrée {entry_key}: {e}")
                    continue
            
            print(f"      ✅ {profile_entries} entrées extraites")
    
    print(f"\n📊 Total entrées collectées: {len(all_entries)}")
    
    if len(all_entries) == 0:
        print("❌ Aucune donnée à migrer")
        return
    
    # Créer le gestionnaire DataFrame et ajouter toutes les entrées
    print("\n💾 Création du DataFrame...")
    manager = TurboDataFrameManager("turbo_data.feather")
    
    # Ajouter toutes les entrées au DataFrame
    import pandas as pd
    
    df_new = pd.DataFrame(all_entries)
    
    # Définir les types de données
    df_new = df_new.astype({
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
    
    # Remplacer le DataFrame du manager
    manager.df = df_new
    manager._save_dataframe()
    
    print(f"✅ Migration terminée: {len(df_new)} entrées")
    
    # Statistiques finales
    stats = manager.get_stats()
    print(f"\n📈 === RÉSUMÉ MIGRATION ===")
    print(f"   Entrées totales: {stats['total_entries']}")
    print(f"   Profils: {', '.join(stats['profiles'])}")
    print(f"   Algorithmes: {', '.join(stats['algorithms'])}")
    print(f"   Période: {stats['date_range']['min']} → {stats['date_range']['max']}")
    
    # Test requête
    print(f"\n🔍 === EXEMPLES REQUÊTES ===")
    
    # Succès par algorithme
    success_by_algo = manager.query("success == True").groupby('algorithm').size()
    print(f"   Succès par algorithme:")
    for algo, count in success_by_algo.items():
        total_algo = len(manager.query(f"algorithm == '{algo}' and success.notna()"))
        pct = count / total_algo * 100 if total_algo > 0 else 0
        print(f"      {algo}: {count}/{total_algo} ({pct:.1f}%)")
    
    # Données par profil
    by_profile = manager.df.groupby('profile_name').size()
    print(f"   Entrées par profil:")
    for profile, count in by_profile.items():
        print(f"      {profile}: {count} entrées")
    
    print(f"\n🎯 === PRÊT POUR ANALYSE ===")
    print(f"   Fichier: turbo_data.feather")
    print(f"   Utilisation: TurboDataFrameManager('turbo_data.feather')")
    print(f"   Requêtes SQL: manager.query('algorithm == \"bruno_custom\"')")
    print(f"   Export sklearn: manager.export_for_sklearn()")

if __name__ == "__main__":
    migrate_turbo_history()