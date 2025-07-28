#!/usr/bin/env python3
"""
Intégration du modèle Random Forest dans l'algorithme turbo
Utilise le modèle entraîné pour les prédictions réelles
"""

import pandas as pd
import numpy as np
from configobj import ConfigObj
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import pickle

class TurboRandomForest:
    def __init__(self, config_path='gsgui.ini'):
        self.config = ConfigObj(config_path, encoding='utf-8')
        self.model = None
        self.feature_names = []
        
    def safe_float(self, val, default=0.0):
        try:
            return float(val) if val else default
        except (ValueError, TypeError):
            return default
    
    def create_features(self, photo1, photo2):
        """Crée les features pour une prédiction"""
        # Données de base
        r1 = self.safe_float(photo1.get('ratio', 0))
        r2 = self.safe_float(photo2.get('ratio', 0))
        v1 = self.safe_float(photo1.get('votes', 0))
        v2 = self.safe_float(photo2.get('votes', 0))
        rank1 = self.safe_float(photo1.get('rank', 999))
        rank2 = self.safe_float(photo2.get('rank', 999))
        
        # Éviter divisions par zéro
        r1_safe = max(r1, 0.001)
        r2_safe = max(r2, 0.001)
        v1_safe = max(v1, 1)
        v2_safe = max(v2, 1)
        rank1_safe = max(rank1, 1)
        rank2_safe = max(rank2, 1)
        
        features = {}
        
        # Features de base
        features['ratio_1'] = r1
        features['ratio_2'] = r2
        features['votes_1'] = v1
        features['votes_2'] = v2
        features['rank_1'] = rank1
        features['rank_2'] = rank2
        
        # Différences
        features['ratio_diff'] = r1 - r2
        features['votes_diff'] = v1 - v2
        features['rank_diff'] = rank1 - rank2
        features['ratio_diff_abs'] = abs(r1 - r2)
        features['votes_diff_abs'] = abs(v1 - v2)
        features['rank_diff_abs'] = abs(rank1 - rank2)
        
        # Ratios des métriques
        features['ratio_ratio'] = r1_safe / r2_safe
        features['votes_ratio'] = v1_safe / v2_safe
        features['rank_ratio'] = rank2_safe / rank1_safe  # Inversé car plus petit = mieux
        
        # Features composées importantes (basées sur l'analyse)
        features['views_est_1'] = v1_safe / r1_safe
        features['views_est_2'] = v2_safe / r2_safe
        features['views_est_ratio'] = features['views_est_1'] / features['views_est_2']
        
        features['perf_score_1'] = v1 * r1
        features['perf_score_2'] = v2 * r2
        features['perf_score_diff'] = features['perf_score_1'] - features['perf_score_2']
        
        features['rank_penalty_1'] = rank1 * r1
        features['rank_penalty_2'] = rank2 * r2
        features['rank_penalty_diff'] = features['rank_penalty_1'] - features['rank_penalty_2']
        
        features['rank_efficiency_1'] = rank1_safe / r1_safe
        features['rank_efficiency_2'] = rank2_safe / r2_safe
        features['rank_efficiency_ratio'] = features['rank_efficiency_2'] / features['rank_efficiency_1']
        
        # Features catégoriques
        def categorize_ratio(r):
            if r < 0.8: return 0
            elif r < 1.0: return 1
            elif r < 1.2: return 2
            elif r < 1.4: return 3
            elif r < 1.6: return 4
            elif r < 2.0: return 5
            else: return 6
        
        features['ratio_cat_1'] = categorize_ratio(r1)
        features['ratio_cat_2'] = categorize_ratio(r2)
        features['ratio_cat_diff'] = features['ratio_cat_1'] - features['ratio_cat_2']
        
        # Similitudes
        features['ratio_similar'] = 1 if abs(r1 - r2) < 0.05 else 0
        features['votes_similar'] = 1 if abs(v1 - v2) < 50 else 0
        features['rank_similar'] = 1 if abs(rank1 - rank2) < 100 else 0
        
        # Statistiques
        features['ratio_mean'] = (r1 + r2) / 2
        features['votes_mean'] = (v1 + v2) / 2
        features['rank_mean'] = (rank1 + rank2) / 2
        features['ratio_min'] = min(r1, r2)
        features['ratio_max'] = max(r1, r2)
        features['votes_max'] = max(v1, v2)
        features['rank_min'] = min(rank1, rank2)
        features['ratio_std'] = abs(r1 - r2) / 2
        features['votes_std'] = abs(v1 - v2) / 2
        features['rank_std'] = abs(rank1 - rank2) / 2
        
        # Features interaction les plus importantes
        features['votes_rank_interaction_1'] = v1_safe / rank1_safe
        features['votes_rank_interaction_2'] = v2_safe / rank2_safe
        features['votes_rank_interaction_ratio'] = features['votes_rank_interaction_1'] / features['votes_rank_interaction_2']
        
        # Score GuruShots hypothétique
        features['guru_score_1'] = (v1_safe / rank1_safe) / r1_safe
        features['guru_score_2'] = (v2_safe / rank2_safe) / r2_safe
        features['guru_score_diff'] = features['guru_score_1'] - features['guru_score_2']
        
        # Avantages spécifiques
        features['photo1_ratio_advantage'] = 1 if r1 < r2 * 0.9 else 0
        features['photo2_ratio_advantage'] = 1 if r2 < r1 * 0.9 else 0
        features['photo1_votes_compensation'] = 1 if (v1 > v2 * 2 and r1 > r2) else 0
        features['photo2_votes_compensation'] = 1 if (v2 > v1 * 2 and r2 > r1) else 0
        features['photo1_rank_advantage'] = 1 if rank1 < rank2 * 0.7 else 0
        features['photo2_rank_advantage'] = 1 if rank2 < rank1 * 0.7 else 0
        
        return features
    
    def train_model(self):
        """Entraîne le modèle Random Forest"""
        print("🤖 Entraînement du modèle Random Forest...")
        
        history = self.config.get('turbo_history', {}).get('bruno', {})
        
        data = []
        for key, comp_data in history.items():
            photo1 = comp_data.get('photo1', {})
            photo2 = comp_data.get('photo2', {})
            winner_info = comp_data.get('winner', {})
            
            if not (photo1.get('found') and photo2.get('found')):
                continue
            
            winner_id = winner_info.get('id', '')
            if winner_id not in [photo1.get('id', ''), photo2.get('id', '')]:
                continue
            
            features = self.create_features(photo1, photo2)
            features['target'] = 1 if winner_id == photo1.get('id', '') else 0
            data.append(features)
        
        df = pd.DataFrame(data)
        print(f"✅ {len(df)} échantillons d'entraînement")
        
        X = df.drop('target', axis=1)
        y = df['target']
        
        self.feature_names = X.columns.tolist()
        
        # Modèle Random Forest optimisé
        self.model = RandomForestClassifier(
            n_estimators=200,
            max_depth=15,
            min_samples_split=10,
            min_samples_leaf=5,
            max_features='sqrt',
            random_state=42,
            class_weight='balanced'
        )
        
        self.model.fit(X, y)
        
        # Sauvegarder le modèle
        with open('turbo_rf_model.pkl', 'wb') as f:
            pickle.dump({
                'model': self.model,
                'feature_names': self.feature_names
            }, f)
        
        print("✅ Modèle entraîné et sauvegardé: turbo_rf_model.pkl")
    
    def load_model(self):
        """Charge le modèle sauvegardé"""
        try:
            with open('turbo_rf_model.pkl', 'rb') as f:
                data = pickle.load(f)
                self.model = data['model']
                self.feature_names = data['feature_names']
            print("✅ Modèle chargé")
            return True
        except FileNotFoundError:
            print("❌ Modèle non trouvé, entraînement nécessaire")
            return False
    
    def predict_winner(self, photo1, photo2):
        """Prédit le gagnant avec le modèle Random Forest"""
        if self.model is None:
            return None, 0.5, "Modèle non entraîné"
        
        features = self.create_features(photo1, photo2)
        
        # Créer DataFrame avec toutes les features attendues
        X = pd.DataFrame([features], columns=self.feature_names)
        
        # Prédiction
        prediction = self.model.predict(X)[0]
        probabilities = self.model.predict_proba(X)[0]
        
        winner_id = photo1['id'] if prediction == 1 else photo2['id']
        confidence = max(probabilities)
        reason = f"RF_confidence:{confidence:.3f}"
        
        return winner_id, confidence, reason

def rf_turbo_algorithm(photo1, photo2):
    """Algorithme turbo utilisant Random Forest"""
    # Initialiser et charger le modèle
    rf = TurboRandomForest()
    
    if not rf.load_model():
        # Si pas de modèle, utiliser fallback simple
        r1 = rf.safe_float(photo1.get('ratio', 0))
        r2 = rf.safe_float(photo2.get('ratio', 0))
        winner_id = photo1['id'] if r1 <= r2 else photo2['id']
        return winner_id, "fallback_no_model"
    
    winner_id, confidence, reason = rf.predict_winner(photo1, photo2)
    return winner_id, reason

def test_rf_integration():
    """Test de l'intégration Random Forest"""
    print("🚀 === TEST INTÉGRATION RANDOM FOREST ===")
    
    # Entraîner le modèle
    rf = TurboRandomForest()
    rf.train_model()
    
    # Tester l'algorithme
    config = ConfigObj('gsgui.ini', encoding='utf-8')
    history = config.get('turbo_history', {}).get('bruno', {})
    
    test_cases = []
    for key, comp_data in history.items():
        photo1 = comp_data.get('photo1', {})
        photo2 = comp_data.get('photo2', {})
        winner_info = comp_data.get('winner', {})
        
        if not (photo1.get('found') and photo2.get('found')):
            continue
        
        winner_id = winner_info.get('id', '')
        if winner_id not in [photo1.get('id', ''), photo2.get('id', '')]:
            continue
            
        test_cases.append({
            'photo1': photo1,
            'photo2': photo2,
            'winner_id': winner_id
        })
    
    # Test
    correct = 0
    confidence_sum = 0
    
    for test_case in test_cases:
        predicted_winner, reason = rf_turbo_algorithm(test_case['photo1'], test_case['photo2'])
        
        if predicted_winner == test_case['winner_id']:
            correct += 1
        
        # Extraire confiance si disponible
        if 'confidence:' in reason:
            try:
                conf = float(reason.split('confidence:')[1])
                confidence_sum += conf
            except:
                confidence_sum += 0.5
        else:
            confidence_sum += 0.5
    
    accuracy = correct / len(test_cases) * 100
    avg_confidence = confidence_sum / len(test_cases)
    
    print(f"\n📊 === RÉSULTATS RANDOM FOREST ===")
    print(f"Précision: {accuracy:.1f}% ({correct}/{len(test_cases)})")
    print(f"Confiance moyenne: {avg_confidence:.3f}")
    print(f"Objectif Bruno Custom: 66.0%")
    
    if accuracy > 66.0:
        print(f"🎉 SUCCÈS! +{accuracy-66.0:.1f}% au-dessus de l'objectif!")
    else:
        print(f"📈 Performance: {accuracy-66.0:+.1f}% vs objectif")

if __name__ == "__main__":
    test_rf_integration()