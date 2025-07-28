#!/usr/bin/env python3
"""
Gestionnaire de stockage des turbos au format DataFrame/Feather
Remplace le système de stockage ConfigObj par un format plus analytique
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Any
import logging

class TurboDataFrameManager:
    """Gestionnaire de stockage des données turbo en DataFrame/Feather"""
    
    def __init__(self, storage_path: str = "turbo_data.feather"):
        """
        Initialise le gestionnaire
        
        Args:
            storage_path: Chemin vers le fichier Feather
        """
        self.storage_path = Path(storage_path)
        
        # Schema des colonnes
        self.columns = [
            'timestamp',           # datetime - timestamp du turbo
            'profile_name',        # str - nom du profil (bruno, etc.)
            'challenge_id',        # str - ID du challenge
            'challenge_title',     # str - titre du challenge
            'time_left',          # str - temps restant (format "1D 2H 30M 15S")
            'algorithm',          # str - algorithme utilisé
            'photo1_id',          # str - ID de la photo 1
            'photo2_id',          # str - ID de la photo 2
            'photo1_votes',       # int - nombre de votes photo 1
            'photo2_votes',       # int - nombre de votes photo 2
            'photo1_rank',        # int - rang photo 1
            'photo2_rank',        # int - rang photo 2
            'photo1_ratio',       # float - ratio photo 1
            'photo2_ratio',       # float - ratio photo 2
            'winner_id',          # str - ID photo gagnante (vide si pas de résultat)
            'chosen_id',          # str - ID photo choisie par l'algorithme
            'success',            # bool - True si choix correct
            'scores_photo1',      # float - score % photo 1 (ex: 17.0 pour 17%)
            'scores_photo2',      # float - score % photo 2 (ex: 83.0 pour 83%)
            'strategy_description' # str - description stratégie
        ]
        
        # Initialiser le DataFrame
        self.df = self._load_or_create_dataframe()
    
    def _load_or_create_dataframe(self) -> pd.DataFrame:
        """Charge le DataFrame existant ou en crée un nouveau"""
        
        if self.storage_path.exists():
            try:
                print(f"📂 Chargement des données existantes: {self.storage_path}")
                df = pd.read_feather(self.storage_path)
                print(f"✅ {len(df)} entrées chargées")
                return df
            except Exception as e:
                print(f"⚠️ Erreur lors du chargement: {e}")
                print("🔄 Création d'un nouveau DataFrame")
        
        # Créer un DataFrame vide avec le bon schema
        df = pd.DataFrame(columns=self.columns)
        
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
        
        print(f"✨ Nouveau DataFrame créé avec {len(self.columns)} colonnes")
        return df
    
    def add_turbo_entry(self, 
                       profile_name: str,
                       challenge_id: str, 
                       challenge_title: str,
                       time_left: str,
                       algorithm: str,
                       photo1_id: str,
                       photo2_id: str,
                       photo1_data: Dict,
                       photo2_data: Dict,
                       chosen_id: str,
                       winner_id: Optional[str] = None,
                       scores_str: Optional[str] = None,
                       strategy_description: str = "") -> None:
        """
        Ajoute une entrée turbo au DataFrame
        
        Args:
            profile_name: Nom du profil
            challenge_id: ID du challenge
            challenge_title: Titre du challenge
            time_left: Temps restant
            algorithm: Algorithme utilisé
            photo1_id: ID photo 1
            photo2_id: ID photo 2
            photo1_data: Données photo 1 (votes, rank, ratio)
            photo2_data: Données photo 2 (votes, rank, ratio)
            chosen_id: ID photo choisie
            winner_id: ID photo gagnante (None si pas encore connu)
            scores_str: Scores au format "17% vs 83%"
            strategy_description: Description stratégie
        """
        
        # Parser les scores
        scores_photo1, scores_photo2 = self._parse_scores(scores_str)
        
        # Déterminer le succès
        success = None
        if winner_id and chosen_id:
            success = (winner_id == chosen_id)
        
        # Créer la nouvelle entrée
        new_entry = {
            'timestamp': datetime.now(),
            'profile_name': profile_name,
            'challenge_id': challenge_id,
            'challenge_title': challenge_title,
            'time_left': time_left,
            'algorithm': algorithm,
            'photo1_id': photo1_id,
            'photo2_id': photo2_id,
            'photo1_votes': self._safe_int(photo1_data.get('votes')),
            'photo2_votes': self._safe_int(photo2_data.get('votes')),
            'photo1_rank': self._safe_int(photo1_data.get('rank')),
            'photo2_rank': self._safe_int(photo2_data.get('rank')),
            'photo1_ratio': self._safe_float(photo1_data.get('ratio')),
            'photo2_ratio': self._safe_float(photo2_data.get('ratio')),
            'winner_id': winner_id,
            'chosen_id': chosen_id,
            'success': success,
            'scores_photo1': scores_photo1,
            'scores_photo2': scores_photo2,
            'strategy_description': strategy_description
        }
        
        # Ajouter au DataFrame
        new_row = pd.DataFrame([new_entry])
        self.df = pd.concat([self.df, new_row], ignore_index=True)
        
        # Sauvegarder
        self._save_dataframe()
        
        print(f"💾 Turbo ajouté: {profile_name} - {challenge_title[:30]}... ({algorithm})")
    
    def _parse_scores(self, scores_str: Optional[str]) -> tuple[Optional[float], Optional[float]]:
        """Parse les scores au format '17% vs 83%'"""
        if not scores_str:
            return None, None
            
        try:
            parts = scores_str.replace('%', '').split(' vs ')
            if len(parts) == 2:
                return float(parts[0]), float(parts[1])
        except:
            pass
        
        return None, None
    
    def _safe_int(self, value: Any) -> Optional[int]:
        """Conversion sécurisée vers int"""
        if value is None or value == '':
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None
    
    def _safe_float(self, value: Any) -> Optional[float]:
        """Conversion sécurisée vers float"""
        if value is None or value == '':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _save_dataframe(self) -> None:
        """Sauvegarde le DataFrame au format Feather"""
        try:
            self.df.to_feather(self.storage_path)
            print(f"💾 DataFrame sauvegardé: {len(self.df)} entrées")
        except Exception as e:
            print(f"❌ Erreur sauvegarde: {e}")
    
    def update_winner(self, profile_name: str, photo1_id: str, photo2_id: str, 
                     winner_id: str, timestamp_window_minutes: int = 5) -> bool:
        """
        Met à jour le gagnant d'un turbo récent
        
        Args:
            profile_name: Nom du profil
            photo1_id: ID photo 1
            photo2_id: ID photo 2  
            winner_id: ID du gagnant
            timestamp_window_minutes: Fenêtre de temps pour trouver l'entrée
            
        Returns:
            True si mise à jour réussie
        """
        
        # Trouver l'entrée correspondante récente
        now = datetime.now()
        window = pd.Timedelta(minutes=timestamp_window_minutes)
        
        mask = (
            (self.df['profile_name'] == profile_name) &
            ((self.df['photo1_id'] == photo1_id) & (self.df['photo2_id'] == photo2_id) |
             (self.df['photo1_id'] == photo2_id) & (self.df['photo2_id'] == photo1_id)) &
            (self.df['timestamp'] > (now - window)) &
            (self.df['winner_id'].isna())
        )
        
        matching_entries = self.df[mask]
        
        if len(matching_entries) == 0:
            print(f"⚠️ Aucune entrée trouvée pour mise à jour gagnant")
            return False
        
        if len(matching_entries) > 1:
            print(f"⚠️ Plusieurs entrées trouvées, mise à jour de la plus récente")
            # Prendre la plus récente
            idx = matching_entries['timestamp'].idxmax()
        else:
            idx = matching_entries.index[0]
        
        # Mettre à jour
        self.df.at[idx, 'winner_id'] = winner_id
        self.df.at[idx, 'success'] = (self.df.at[idx, 'chosen_id'] == winner_id)
        
        # Sauvegarder
        self._save_dataframe()
        
        print(f"✅ Gagnant mis à jour: {winner_id} (succès: {self.df.at[idx, 'success']})")
        return True
    
    def get_dataframe(self) -> pd.DataFrame:
        """Retourne le DataFrame pour analyse"""
        return self.df.copy()
    
    def query(self, query_str: str) -> pd.DataFrame:
        """Execute une requête SQL-like sur le DataFrame"""
        try:
            return self.df.query(query_str)
        except Exception as e:
            print(f"❌ Erreur requête: {e}")
            return pd.DataFrame()
    
    def get_stats(self) -> Dict:
        """Retourne des statistiques sur les données"""
        
        total_entries = len(self.df)
        
        if total_entries == 0:
            return {'total_entries': 0}
        
        # Statistiques par profil
        profile_stats = self.df.groupby('profile_name').agg({
            'success': ['count', 'sum', 'mean'],
            'algorithm': 'nunique'
        }).round(3)
        
        # Statistiques par algorithme
        algo_stats = self.df.groupby('algorithm').agg({
            'success': ['count', 'sum', 'mean']
        }).round(3)
        
        # Données récentes
        recent_data = self.df[self.df['timestamp'] > (datetime.now() - pd.Timedelta(days=7))]
        
        return {
            'total_entries': total_entries,
            'profiles': list(self.df['profile_name'].unique()),
            'algorithms': list(self.df['algorithm'].unique()),
            'date_range': {
                'min': self.df['timestamp'].min(),
                'max': self.df['timestamp'].max()
            },
            'recent_entries_7d': len(recent_data),
            'profile_stats': profile_stats,
            'algorithm_stats': algo_stats
        }
    
    def export_for_sklearn(self, filter_complete_only: bool = True) -> pd.DataFrame:
        """
        Exporte les données dans un format prêt pour sklearn
        
        Args:
            filter_complete_only: Si True, ne retourne que les entrées avec résultat
            
        Returns:
            DataFrame avec features numériques pour ML
        """
        
        df = self.df.copy()
        
        if filter_complete_only:
            df = df[df['success'].notna()]
        
        if len(df) == 0:
            print("⚠️ Aucune donnée complète pour sklearn")
            return pd.DataFrame()
        
        # Features pour ML
        ml_features = df[[
            'photo1_votes', 'photo2_votes',
            'photo1_rank', 'photo2_rank', 
            'photo1_ratio', 'photo2_ratio',
            'success'
        ]].copy()
        
        # Ajouter des features dérivées
        ml_features['votes_ratio'] = ml_features['photo1_votes'] / ml_features['photo2_votes']
        ml_features['rank_diff'] = ml_features['photo1_rank'] - ml_features['photo2_rank']  
        ml_features['ratio_diff'] = ml_features['photo1_ratio'] - ml_features['photo2_ratio']
        ml_features['votes_diff'] = ml_features['photo1_votes'] - ml_features['photo2_votes']
        
        # Remplacer les valeurs infinies et manquantes
        ml_features = ml_features.replace([np.inf, -np.inf], np.nan)
        ml_features = ml_features.dropna()
        
        print(f"📊 Données sklearn: {len(ml_features)} entrées avec {len(ml_features.columns)} features")
        
        return ml_features

# Test et exemples d'utilisation
if __name__ == "__main__":
    
    # Test du gestionnaire
    manager = TurboDataFrameManager("test_turbo_data.feather")
    
    # Exemple d'ajout de données
    manager.add_turbo_entry(
        profile_name="bruno",
        challenge_id="105484", 
        challenge_title="Photographer of the Week",
        time_left="1D 2H 30M 15S",
        algorithm="votes_ratio_patterns",
        photo1_id="photo1_abc123",
        photo2_id="photo2_def456", 
        photo1_data={'votes': 214, 'rank': 393, 'ratio': 1.5},
        photo2_data={'votes': 62, 'rank': 546, 'ratio': 1.33},
        chosen_id="photo1_abc123",
        winner_id="photo1_abc123",
        scores_str="17% vs 83%",
        strategy_description="Test turbo"
    )
    
    # Afficher les stats
    stats = manager.get_stats()
    print(f"\n📊 Statistiques:")
    for key, value in stats.items():
        if key not in ['profile_stats', 'algorithm_stats']:
            print(f"   {key}: {value}")
    
    # Test requête
    recent = manager.query("algorithm == 'votes_ratio_patterns'")
    print(f"\n🔍 Requête test: {len(recent)} entrées votes_ratio_patterns")
    
    # Test export sklearn
    ml_data = manager.export_for_sklearn()
    print(f"\n🤖 Export sklearn: {ml_data.shape}")