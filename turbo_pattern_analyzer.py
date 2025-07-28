#!/usr/bin/env python3
"""
Analyseur de patterns turbo GSGUI
Utilise l'IA pour découvrir des patterns récurrents et optimiser les algorithmes
"""

import pandas as pd
import numpy as np
from configobj import ConfigObj
from collections import defaultdict
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import warnings
warnings.filterwarnings('ignore')

class TurboPatternAnalyzer:
    def __init__(self, config_path='gsgui.ini'):
        self.config = ConfigObj(config_path, encoding='utf-8')
        self.data = []
        self.df = None
        
    def load_turbo_history(self, player='bruno'):
        """Charge l'historique turbo et le convertit en DataFrame"""
        print(f"🔍 Chargement de l'historique turbo pour {player}...")
        
        history = self.config.get('turbo_history', {}).get(player, {})
        
        for key, comp_data in history.items():
            photo1 = comp_data.get('photo1', {})
            photo2 = comp_data.get('photo2', {})
            winner_info = comp_data.get('winner', {})
            
            # Ignorer les comparaisons invalides
            if not (photo1.get('found') and photo2.get('found')):
                continue
                
            # Conversion sécurisée
            def safe_float(val, default=0.0):
                try:
                    return float(val) if val else default
                except:
                    return default
            
            # Déterminer le gagnant basé sur l'ID winner uniquement
            winner_id = winner_info.get('id', '')
            photo1_id = photo1.get('id', '')
            photo2_id = photo2.get('id', '')
            
            # Logique fiable: comparer winner_id avec photo1_id et photo2_id
            if winner_id == photo1_id:
                winner_is_photo1 = True
            elif winner_id == photo2_id:
                winner_is_photo1 = False
            else:
                # Cas d'erreur - ignorer cette entrée
                continue
            
            # Extraire les données
            data_point = {
                'photo1_id': photo1_id,
                'photo1_ratio': safe_float(photo1.get('ratio', 0)),
                'photo1_votes': safe_float(photo1.get('votes', 0)),
                'photo1_rank': safe_float(photo1.get('rank', 999)),
                
                'photo2_id': photo2_id,
                'photo2_ratio': safe_float(photo2.get('ratio', 0)),
                'photo2_votes': safe_float(photo2.get('votes', 0)),
                'photo2_rank': safe_float(photo2.get('rank', 999)),
                
                'winner_id': winner_id,
                'winner_is_photo1': winner_is_photo1,
                'algorithm': comp_data.get('algorithm', 'unknown'),
                'success': comp_data.get('success', False)
            }
            
            self.data.append(data_point)
        
        self.df = pd.DataFrame(self.data)
        print(f"✅ Chargé {len(self.df)} comparaisons valides")
        return self.df
    
    def categorize_comparisons(self):
        """Catégorise les comparaisons par patterns de ratios"""
        print("\\n📊 === CATÉGORISATION DES PATTERNS ===")
        
        def categorize_ratio_pair(r1, r2, tolerance=0.1):
            # Arrondir à 0.1 près
            r1_cat = round(r1 / tolerance) * tolerance
            r2_cat = round(r2 / tolerance) * tolerance
            
            # Catégories spéciales
            if r1_cat == r2_cat:
                return f"ÉGALITÉ_{r1_cat:.1f}"
            elif r1_cat < 1.0 or r2_cat < 1.0:
                return f"SOUS_1.0_{min(r1_cat, r2_cat):.1f}_vs_{max(r1_cat, r2_cat):.1f}"
            elif r1_cat > 2.0 or r2_cat > 2.0:
                return f"PLUS_2.0_{min(r1_cat, r2_cat):.1f}_vs_{max(r1_cat, r2_cat):.1f}"
            elif abs(r1_cat - 1.5) < 0.1 or abs(r2_cat - 1.5) < 0.1:
                return f"ZONE_1.5_{min(r1_cat, r2_cat):.1f}_vs_{max(r1_cat, r2_cat):.1f}"
            else:
                return f"NORMAL_{min(r1_cat, r2_cat):.1f}_vs_{max(r1_cat, r2_cat):.1f}"
        
        # Appliquer la catégorisation
        self.df['ratio_category'] = self.df.apply(
            lambda row: categorize_ratio_pair(row['photo1_ratio'], row['photo2_ratio']), 
            axis=1
        )
        
        # Analyser les patterns par catégorie
        pattern_analysis = {}
        
        for category in self.df['ratio_category'].unique():
            cat_data = self.df[self.df['ratio_category'] == category]
            
            if len(cat_data) < 3:  # Ignorer les catégories avec trop peu de données
                continue
            
            # Analyser les caractéristiques des gagnants
            winners_when_photo1 = cat_data[cat_data['winner_is_photo1'] == True]
            winners_when_photo2 = cat_data[cat_data['winner_is_photo1'] == False]
            
            analysis = {
                'total_comparisons': len(cat_data),
                'photo1_wins': len(winners_when_photo1),
                'photo2_wins': len(winners_when_photo2),
                'photo1_win_rate': len(winners_when_photo1) / len(cat_data) * 100,
                'avg_winner_votes': 0,
                'avg_winner_rank': 0,
                'avg_winner_ratio': 0,
                'pattern_insights': []
            }
            
            # Caractéristiques moyennes des gagnants
            all_winners = []
            for _, row in cat_data.iterrows():
                if row['winner_is_photo1']:
                    all_winners.append({
                        'votes': row['photo1_votes'],
                        'rank': row['photo1_rank'],
                        'ratio': row['photo1_ratio']
                    })
                else:
                    all_winners.append({
                        'votes': row['photo2_votes'],
                        'rank': row['photo2_rank'],
                        'ratio': row['photo2_ratio']
                    })
            
            if all_winners:
                analysis['avg_winner_votes'] = np.mean([w['votes'] for w in all_winners])
                analysis['avg_winner_rank'] = np.mean([w['rank'] for w in all_winners])
                analysis['avg_winner_ratio'] = np.mean([w['ratio'] for w in all_winners])
            
            # Détection de patterns
            if analysis['photo1_win_rate'] > 70:
                analysis['pattern_insights'].append("Photo1 gagne très souvent")
            elif analysis['photo1_win_rate'] < 30:
                analysis['pattern_insights'].append("Photo2 gagne très souvent")
            
            pattern_analysis[category] = analysis
        
        self.pattern_analysis = pattern_analysis
        
        # Afficher les résultats
        print(f"🎯 Trouvé {len(pattern_analysis)} catégories avec assez de données:")
        print()
        
        for category, analysis in sorted(pattern_analysis.items(), 
                                       key=lambda x: x[1]['total_comparisons'], 
                                       reverse=True)[:15]:  # Top 15
            print(f"📊 {category}")
            print(f"   Total: {analysis['total_comparisons']} comparaisons")
            print(f"   Photo1 gagne: {analysis['photo1_win_rate']:.1f}% ({analysis['photo1_wins']}/{analysis['total_comparisons']})")
            print(f"   Gagnant moyen: votes={analysis['avg_winner_votes']:.0f}, rang={analysis['avg_winner_rank']:.0f}, ratio={analysis['avg_winner_ratio']:.2f}")
            if analysis['pattern_insights']:
                print(f"   🔍 Pattern: {', '.join(analysis['pattern_insights'])}")
            print()
        
        return pattern_analysis
    
    def create_features(self):
        """Crée des features pour l'apprentissage automatique"""
        print("🧠 === CRÉATION DES FEATURES POUR IA ===")
        
        # Features de base
        features = pd.DataFrame()
        
        # Différences absolues et ratios
        features['ratio_diff'] = self.df['photo1_ratio'] - self.df['photo2_ratio']
        features['votes_diff'] = self.df['photo1_votes'] - self.df['photo2_votes']
        features['rank_diff'] = self.df['photo1_rank'] - self.df['photo2_rank']
        
        # Ratios relatifs
        features['votes_ratio'] = self.df['photo1_votes'] / (self.df['photo2_votes'] + 1)
        features['rank_ratio'] = self.df['photo2_rank'] / (self.df['photo1_rank'] + 1)  # Inversé car rang faible = mieux
        
        # Features catégorielles
        features['photo1_ratio_cat'] = pd.cut(self.df['photo1_ratio'], 
                                            bins=[0, 0.8, 1.0, 1.2, 1.4, 1.6, 2.0, float('inf')],
                                            labels=['très_faible', 'faible', 'bon', 'moyen', 'élevé', 'très_élevé', 'extrême'])
        
        features['photo2_ratio_cat'] = pd.cut(self.df['photo2_ratio'], 
                                            bins=[0, 0.8, 1.0, 1.2, 1.4, 1.6, 2.0, float('inf')],
                                            labels=['très_faible', 'faible', 'bon', 'moyen', 'élevé', 'très_élevé', 'extrême'])
        
        # Features de domination
        features['photo1_dominates_votes'] = (self.df['photo1_votes'] > self.df['photo2_votes'] * 1.5).astype(int)
        features['photo1_dominates_rank'] = (self.df['photo1_rank'] < self.df['photo2_rank'] * 0.7).astype(int)
        features['photo1_dominates_ratio'] = (self.df['photo1_ratio'] < self.df['photo2_ratio'] * 0.9).astype(int)
        
        # Features de zone dangereuse
        features['photo1_danger_zone'] = (abs(self.df['photo1_ratio'] - 1.5) < 0.1).astype(int)
        features['photo2_danger_zone'] = (abs(self.df['photo2_ratio'] - 1.5) < 0.1).astype(int)
        
        # Features de sweet spot
        features['photo1_sweet_spot'] = ((self.df['photo1_ratio'] >= 1.15) & (self.df['photo1_ratio'] <= 1.30)).astype(int)
        features['photo2_sweet_spot'] = ((self.df['photo2_ratio'] >= 1.15) & (self.df['photo2_ratio'] <= 1.30)).astype(int)
        
        # One-hot encoding pour variables catégorielles
        features = pd.get_dummies(features, columns=['photo1_ratio_cat', 'photo2_ratio_cat'])
        
        self.features = features
        self.target = self.df['winner_is_photo1'].astype(int)
        
        print(f"✅ Créé {len(features.columns)} features pour {len(features)} échantillons")
        return features, self.target
    
    def train_ai_model(self):
        """Entraîne un modèle IA pour prédire le gagnant"""
        print("\\n🤖 === ENTRAÎNEMENT MODÈLE IA ===")
        
        X, y = self.create_features()
        
        # Split train/test
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)
        
        # Modèle Random Forest
        model = RandomForestClassifier(n_estimators=100, random_state=42, max_depth=10)
        model.fit(X_train, y_train)
        
        # Prédictions
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        print(f"🎯 Précision du modèle IA: {accuracy:.1%}")
        print()
        print("📊 Rapport détaillé:")
        print(classification_report(y_test, y_pred, target_names=['Photo2 gagne', 'Photo1 gagne']))
        
        # Importance des features
        feature_importance = pd.DataFrame({
            'feature': X.columns,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        print("\\n🔍 Features les plus importantes:")
        for i, row in feature_importance.head(10).iterrows():
            print(f"   {row['feature']}: {row['importance']:.3f}")
        
        self.model = model
        self.feature_importance = feature_importance
        
        return model, accuracy
    
    def generate_optimized_algorithm(self):
        """Génère un algorithme optimisé basé sur l'analyse IA"""
        print("\\n🚀 === GÉNÉRATION ALGORITHME OPTIMISÉ ===")
        
        # Analyser l'importance des features
        top_features = self.feature_importance.head(15)
        
        algorithm_rules = []
        
        # Règles basées sur les top features
        for _, row in top_features.iterrows():
            feature = row['feature']
            importance = row['importance']
            
            if importance < 0.05:  # Seuil minimum
                continue
                
            if 'ratio_diff' in feature:
                algorithm_rules.append(f"# Règle {len(algorithm_rules)+1}: Différence de ratio importante (importance: {importance:.3f})")
                algorithm_rules.append("if abs(first_ratio - second_ratio) > 0.3:")
                algorithm_rules.append("    return first_id if first_ratio < second_ratio else second_id")
                
            elif 'votes_diff' in feature:
                algorithm_rules.append(f"# Règle {len(algorithm_rules)+1}: Différence de votes importante (importance: {importance:.3f})")
                algorithm_rules.append("if abs(first_votes - second_votes) > 500:")
                algorithm_rules.append("    return first_id if first_votes > second_votes else second_id")
                
            elif 'sweet_spot' in feature:
                algorithm_rules.append(f"# Règle {len(algorithm_rules)+1}: Sweet spot 1.15-1.30 (importance: {importance:.3f})")
                algorithm_rules.append("first_sweet = 1.15 <= first_ratio <= 1.30")
                algorithm_rules.append("second_sweet = 1.15 <= second_ratio <= 1.30")
                algorithm_rules.append("if first_sweet and not second_sweet:")
                algorithm_rules.append("    return first_id")
                algorithm_rules.append("elif second_sweet and not first_sweet:")
                algorithm_rules.append("    return second_id")
        
        # Générer le code de l'algorithme
        algorithm_code = f'''
def ai_optimized_algorithm(first_id, first_data, second_id, second_data):
    """
    Algorithme optimisé par IA - Précision estimée: {self.model.score(self.features, self.target):.1%}
    Basé sur l'analyse de {len(self.df)} comparaisons historiques
    """
    first_ratio = first_data.get('ratio', 0)
    second_ratio = second_data.get('ratio', 0)
    first_votes = first_data.get('votes', 0)
    second_votes = second_data.get('votes', 0)
    first_rank = first_data.get('rank', 999)
    second_rank = second_data.get('rank', 999)
    
    # Conversion sécurisée
    def safe_float(val, default=0.0):
        try:
            return float(val) if val else default
        except:
            return default
    
    first_ratio = safe_float(first_ratio)
    second_ratio = safe_float(second_ratio)
    first_votes = safe_float(first_votes)
    second_votes = safe_float(second_votes)
    first_rank = safe_float(first_rank)
    second_rank = safe_float(second_rank)
    
    {chr(10).join(algorithm_rules)}
    
    # Fallback: utiliser le modèle IA directement
    # (Cette partie nécessiterait l'intégration du modèle entraîné)
    
    # Fallback final: ratio le plus faible
    return first_id if first_ratio <= second_ratio else second_id
'''
        
        print("🎯 Algorithme optimisé généré!")
        print("💾 Sauvegarde dans 'ai_optimized_algorithm.py'...")
        
        with open('ai_optimized_algorithm.py', 'w', encoding='utf-8') as f:
            f.write(algorithm_code)
        
        print("✅ Algorithme sauvegardé!")
        return algorithm_code
    
    def run_full_analysis(self, player='bruno'):
        """Lance l'analyse complète"""
        print("🚀 === ANALYSE COMPLÈTE DES PATTERNS TURBO ===")
        print(f"📅 Analysing player: {player}")
        print("=" * 60)
        
        # 1. Charger les données
        self.load_turbo_history(player)
        
        if len(self.df) < 20:
            print("❌ Pas assez de données pour une analyse fiable")
            return
        
        # 2. Catégoriser les patterns
        self.categorize_comparisons()
        
        # 3. Entraîner le modèle IA
        model, accuracy = self.train_ai_model()
        
        # 4. Générer l'algorithme optimisé
        self.generate_optimized_algorithm()
        
        print("\\n🎉 === RÉSUMÉ DE L'ANALYSE ===")
        print(f"📊 Données analysées: {len(self.df)} comparaisons")
        print(f"🎯 Précision IA: {accuracy:.1%}")
        print(f"🏆 Objectif: Dépasser les 66% actuels")
        print(f"💡 Potentiel d'amélioration: {max(0, accuracy - 0.66):.1%}")
        print()
        print("📁 Fichiers générés:")
        print("   - ai_optimized_algorithm.py (algorithme optimisé)")
        print()
        print("🔍 Prochaines étapes:")
        print("   1. Intégrer l'algorithme dans gsui.py")
        print("   2. Tester sur l'historique")
        print("   3. Comparer avec bruno_custom (66%)")

if __name__ == "__main__":
    analyzer = TurboPatternAnalyzer()
    analyzer.run_full_analysis()