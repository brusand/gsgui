#!/usr/bin/env python3
"""
Extraction complète de tous les turbos de tous les profils
Sauvegarde dans turbos.feather avec les colonnes spécifiées par l'utilisateur
"""

import pandas as pd
import numpy as np
from configobj import ConfigObj
from pathlib import Path
from datetime import datetime
import re

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
    try:
        # Chercher le pattern de date à la fin: YYYYMMDD_HHMMSS
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

def extract_all_turbos():
    """Extrait tous les turbos de tous les profils vers turbos.feather"""
    
    print("🚀 === EXTRACTION COMPLÈTE DES TURBOS ===")
    print("📁 Source: Tous les fichiers .ini")
    print("💾 Destination: turbos.feather")
    print("📋 Colonnes: temps_restant, id_photo1, id_photo2, votes_photo1, votes_photo2,")
    print("             rang_photo1, rang_photo2, ratio_photo1, ratio_photo2,")
    print("             id_photo_gagnante, nom_profil, nom_challenge")
    print("=" * 70)
    
    # Fichiers de configuration à traiter
    config_files = [
        'gsgui.ini',
        'src/gs/gsgui.ini', 
        'backend/data/gsgui.ini'
    ]
    
    # Colonnes selon spécification utilisateur
    columns = [
        'temps_restant',       # str - temps restant du challenge
        'id_photo1',           # str - ID de la photo 1
        'id_photo2',           # str - ID de la photo 2  
        'votes_photo1',        # int - nombre de votes photo 1
        'votes_photo2',        # int - nombre de votes photo 2
        'rang_photo1',         # int - rang photo 1
        'rang_photo2',         # int - rang photo 2
        'ratio_photo1',        # float - ratio photo 1
        'ratio_photo2',        # float - ratio photo 2
        'id_photo_gagnante',   # str - ID photo gagnante (vide si pas de résultat)
        'nom_profil',          # str - nom du profil
        'nom_challenge'        # str - nom du challenge
    ]
    
    all_turbos = []
    total_files_processed = 0
    total_profiles_processed = 0
    
    # Traiter chaque fichier de configuration
    for config_path in config_files:
        if not Path(config_path).exists():
            print(f"⚠️ Fichier non trouvé: {config_path}")
            continue
            
        print(f"\n📁 Traitement: {config_path}")
        total_files_processed += 1
        
        try:
            config = ConfigObj(config_path, encoding='utf-8')
        except Exception as e:
            print(f"❌ Erreur lecture {config_path}: {e}")
            continue
        
        # Extraire l'historique turbo
        turbo_history = config.get('turbo_history', {})
        
        if not turbo_history:
            print(f"   ℹ️ Pas d'historique turbo dans {config_path}")
            continue
        
        # Traiter tous les profils
        for profile_name, profile_history in turbo_history.items():
            
            if not isinstance(profile_history, dict):
                continue
                
            print(f"   👤 Profil: {profile_name}")
            total_profiles_processed += 1
            profile_turbos = 0
            
            # Traiter toutes les entrées turbo de ce profil
            for entry_key, entry_data in profile_history.items():
                
                if not isinstance(entry_data, dict):
                    continue
                
                try:
                    # Données de base
                    temps_restant = entry_data.get('time_left', '')
                    nom_challenge = entry_data.get('challenge_title', '')
                    
                    # Données des photos
                    photo1_data = entry_data.get('photo1', {})
                    photo2_data = entry_data.get('photo2', {})
                    
                    id_photo1 = photo1_data.get('id', '')
                    id_photo2 = photo2_data.get('id', '')
                    
                    if not id_photo1 or not id_photo2:
                        continue
                    
                    # Données numériques des photos
                    votes_photo1 = safe_int(photo1_data.get('votes'))
                    votes_photo2 = safe_int(photo2_data.get('votes'))
                    rang_photo1 = safe_int(photo1_data.get('rank'))
                    rang_photo2 = safe_int(photo2_data.get('rank'))
                    ratio_photo1 = safe_float(photo1_data.get('ratio'))
                    ratio_photo2 = safe_float(photo2_data.get('ratio'))
                    
                    # Photo gagnante
                    winner_data = entry_data.get('winner', {})
                    id_photo_gagnante = winner_data.get('id', '')
                    
                    # Si pas de gagnant explicite, laisser vide (colonne vide comme demandé)
                    if not id_photo_gagnante:
                        id_photo_gagnante = ''
                    
                    # Créer l'entrée turbo
                    turbo_entry = {
                        'temps_restant': temps_restant,
                        'id_photo1': id_photo1,
                        'id_photo2': id_photo2,
                        'votes_photo1': votes_photo1,
                        'votes_photo2': votes_photo2,
                        'rang_photo1': rang_photo1,
                        'rang_photo2': rang_photo2,
                        'ratio_photo1': ratio_photo1,
                        'ratio_photo2': ratio_photo2,
                        'id_photo_gagnante': id_photo_gagnante,
                        'nom_profil': profile_name,
                        'nom_challenge': nom_challenge
                    }
                    
                    all_turbos.append(turbo_entry)
                    profile_turbos += 1
                    
                except Exception as e:
                    print(f"      ⚠️ Erreur entrée {entry_key}: {e}")
                    continue
            
            print(f"      ✅ {profile_turbos} turbos extraits")
    
    print(f"\n📊 === RÉSUMÉ EXTRACTION ===")
    print(f"   Fichiers traités: {total_files_processed}")
    print(f"   Profils traités: {total_profiles_processed}")
    print(f"   Total turbos extraits: {len(all_turbos)}")
    
    if len(all_turbos) == 0:
        print("❌ Aucun turbo extrait")
        return
    
    # Créer le DataFrame
    print(f"\n💾 Création du DataFrame...")
    df = pd.DataFrame(all_turbos, columns=columns)
    
    # Définir les types de données appropriés
    df = df.astype({
        'temps_restant': 'string',
        'id_photo1': 'string',
        'id_photo2': 'string',
        'votes_photo1': 'Int64',
        'votes_photo2': 'Int64',
        'rang_photo1': 'Int64', 
        'rang_photo2': 'Int64',
        'ratio_photo1': 'float64',
        'ratio_photo2': 'float64',
        'id_photo_gagnante': 'string',
        'nom_profil': 'string',
        'nom_challenge': 'string'
    })
    
    # Sauvegarder en format Feather
    output_file = 'turbos.feather'
    try:
        df.to_feather(output_file)
        print(f"✅ Sauvegarde réussie: {output_file}")
    except Exception as e:
        print(f"❌ Erreur sauvegarde: {e}")
        return
    
    # Statistiques finales
    print(f"\n📈 === STATISTIQUES FINALES ===")
    print(f"   📄 Fichier: {output_file}")
    print(f"   📊 Taille: {df.shape[0]} lignes × {df.shape[1]} colonnes")
    print(f"   📋 Colonnes: {list(df.columns)}")
    print()
    
    # Statistiques par profil
    profile_stats = df.groupby('nom_profil').size().sort_values(ascending=False)
    print(f"   👥 Turbos par profil:")
    for profile, count in profile_stats.items():
        print(f"      {profile}: {count} turbos")
    print()
    
    # Statistiques par challenge (top 10)
    challenge_stats = df.groupby('nom_challenge').size().sort_values(ascending=False)
    print(f"   🏆 Top 10 challenges:")
    for challenge, count in challenge_stats.head(10).items():
        print(f"      {challenge[:40]}: {count} turbos")
    print()
    
    # Qualité des données
    print(f"   🔍 Qualité des données:")
    print(f"      Turbos avec gagnant: {len(df[df['id_photo_gagnante'] != ''])} ({len(df[df['id_photo_gagnante'] != ''])/len(df)*100:.1f}%)")
    print(f"      Turbos sans gagnant: {len(df[df['id_photo_gagnante'] == ''])} ({len(df[df['id_photo_gagnante'] == ''])/len(df)*100:.1f}%)")
    print(f"      Votes valides photo1: {df['votes_photo1'].notna().sum()} ({df['votes_photo1'].notna().sum()/len(df)*100:.1f}%)")
    print(f"      Ratios valides photo1: {df['ratio_photo1'].notna().sum()} ({df['ratio_photo1'].notna().sum()/len(df)*100:.1f}%)")
    
    # Exemples de requêtes possibles
    print(f"\n🔍 === EXEMPLES D'UTILISATION ===")
    print(f"```python")
    print(f"import pandas as pd")
    print(f"")
    print(f"# Charger les données")
    print(f"df = pd.read_feather('turbos.feather')")
    print(f"")
    print(f"# Requêtes SQL-like")
    print(f"bruno_turbos = df.query('nom_profil == \"bruno\"')")
    print(f"turbos_avec_gagnant = df.query('id_photo_gagnante != \"\"')")
    print(f"ratios_eleves = df.query('ratio_photo1 > 1.5 or ratio_photo2 > 1.5')")
    print(f"")
    print(f"# Analyse par profil")
    print(f"performance_profils = df.groupby('nom_profil')['id_photo_gagnante'].apply(lambda x: (x != '').sum())")
    print(f"")
    print(f"# Préparation sklearn")
    print(f"features = df[['votes_photo1', 'votes_photo2', 'ratio_photo1', 'ratio_photo2']]")
    print(f"```")
    
    print(f"\n🎯 === EXTRACTION TERMINÉE ===")
    print(f"✅ {len(all_turbos)} turbos de {len(profile_stats)} profils extraits")
    print(f"✅ Données sauvegardées dans turbos.feather")
    print(f"✅ Prêt pour analyses et machine learning")
    
    return df

def test_loading():
    """Test de chargement du fichier généré"""
    print(f"\n🧪 === TEST DE CHARGEMENT ===")
    
    try:
        df = pd.read_feather('turbos.feather')
        print(f"✅ Chargement réussi: {df.shape}")
        print(f"📋 Colonnes: {list(df.columns)}")
        
        # Aperçu des données
        print(f"\n👁️ Aperçu des données (5 premières lignes):")
        print(df.head())
        
        # Types de données
        print(f"\n🔧 Types de données:")
        print(df.dtypes)
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur chargement: {e}")
        return False

if __name__ == "__main__":
    # Extraction
    df = extract_all_turbos()
    
    # Test de chargement
    if df is not None:
        test_loading()