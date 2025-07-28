#!/usr/bin/env python3
"""
Analyse détaillée des échecs d'Advanced RF (52.1%) vs Bruno Custom (59.8%)
Comprendre pourquoi le Random Forest sous-performe en production
"""

import pandas as pd
import numpy as np
from configobj import ConfigObj
import pickle

def safe_float(val, default=0.0):
    try:
        return float(val) if val else default
    except (ValueError, TypeError):
        return default

def load_rf_model():
    """Charge le modèle Random Forest"""
    try:
        with open('turbo_rf_model.pkl', 'rb') as f:
            model_data = pickle.load(f)
            return model_data['model'], model_data['feature_names']
    except:
        return None, None

def create_rf_features(photo1_data, photo2_data):
    """Crée les features pour le modèle Random Forest (même logique que gsui.py)"""
    # Données de base
    r1 = safe_float(photo1_data.get('ratio', 0))
    r2 = safe_float(photo2_data.get('ratio', 0))
    v1 = safe_float(photo1_data.get('votes', 0))
    v2 = safe_float(photo2_data.get('votes', 0))
    rank1 = safe_float(photo1_data.get('rank', 999))
    rank2 = safe_float(photo2_data.get('rank', 999))
    
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
    features['rank_ratio'] = rank2_safe / rank1_safe
    
    # Features composées importantes
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

def advanced_rf_predict(photo1, photo2, model, feature_names):
    """Prédit avec Advanced RF"""
    try:
        features = create_rf_features(photo1, photo2)
        X = pd.DataFrame([features], columns=feature_names)
        prediction = model.predict(X)[0]
        probabilities = model.predict_proba(X)[0]
        confidence = max(probabilities)
        
        if prediction == 1:  # Photo1 gagne
            return photo1['id'], confidence, f"advanced_rf: Photo1 (conf:{confidence:.3f})"
        else:  # Photo2 gagne
            return photo2['id'], confidence, f"advanced_rf: Photo2 (conf:{confidence:.3f})"
    except Exception as e:
        # Fallback en cas d'erreur
        return photo1['id'], 0.5, f"advanced_rf: error {e}"

def bruno_custom_predict(photo1, photo2):
    """Prédit avec Bruno Custom (logique exacte de gsui.py)"""
    first_ratio = safe_float(photo1.get('ratio', 0))
    second_ratio = safe_float(photo2.get('ratio', 0))
    first_votes = safe_float(photo1.get('votes', 0))
    second_votes = safe_float(photo2.get('votes', 0))
    first_rank = safe_float(photo1.get('rank', 999))
    second_rank = safe_float(photo2.get('rank', 999))
    
    first_id = photo1['id']
    second_id = photo2['id']
    
    # RÈGLE 1: Éviter ratio < 1.0
    if first_ratio < 1.0 and second_ratio >= 1.0:
        return second_id, f"bruno_custom: éviter <1.0 ({first_ratio} vs {second_ratio})"
    elif second_ratio < 1.0 and first_ratio >= 1.0:
        return first_id, f"bruno_custom: éviter <1.0 ({second_ratio} vs {first_ratio})"
    elif first_ratio < 1.0 and second_ratio < 1.0:
        # Les deux sous 1.0: choisir le moins pire
        if first_ratio >= second_ratio:
            return first_id, f"bruno_custom: moins pire <1.0 ({first_ratio} vs {second_ratio})"
        else:
            return second_id, f"bruno_custom: moins pire <1.0 ({second_ratio} vs {first_ratio})"
    
    # RÈGLE 2: Si pas de ratio < 1.0, utiliser ratio supérieur
    if abs(first_ratio - second_ratio) > 0.1:
        if first_ratio > second_ratio:
            return first_id, f"bruno_custom: ratio supérieur ({first_ratio} > {second_ratio})"
        else:
            return second_id, f"bruno_custom: ratio supérieur ({second_ratio} > {first_ratio})"

    # RÈGLE 3: Si ratios similaires, utiliser le meilleur rank
    if first_rank < second_rank:  # Plus petit rank = meilleur
        return first_id, f"bruno_custom: meilleur rank ({first_rank} vs {second_rank})"
    elif second_rank < first_rank:
        return second_id, f"bruno_custom: meilleur rank ({second_rank} vs {first_rank})"

    # RÈGLE 4: Fallback sur les votes si ranks égaux
    if first_votes > second_votes:
        return first_id, f"bruno_custom: plus de votes ({first_votes} vs {second_votes})"
    else:
        return second_id, f"bruno_custom: plus de votes ({second_votes} vs {first_votes})"

def analyze_rf_failures():
    """Analyse détaillée des échecs d'Advanced RF"""
    print("🔍 === ANALYSE ÉCHECS ADVANCED RF vs BRUNO CUSTOM ===")
    print("📊 Objectif: Comprendre pourquoi RF (52.1%) < Bruno (59.8%)")
    print("=" * 65)
    
    # Charger les données
    config = ConfigObj('gsgui.ini', encoding='utf-8')
    history = config.get('turbo_history', {}).get('bruno', {})
    
    if not history:
        print("❌ Pas d'historique turbo trouvé")
        return
    
    # Charger le modèle RF
    rf_model, feature_names = load_rf_model()
    if rf_model is None:
        print("❌ Impossible de charger le modèle Random Forest")
        return
    
    print(f"✅ Modèle RF chargé avec {len(feature_names)} features")
    
    # Préparer les données de test
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
            'winner_id': winner_id,
            'key': key
        })
    
    print(f"📊 Analyse sur {len(test_cases)} comparaisons")
    
    # Analyser chaque cas
    rf_correct = 0
    bruno_correct = 0
    both_correct = 0
    both_wrong = 0
    rf_only_correct = 0
    bruno_only_correct = 0
    
    failure_cases = {
        'rf_wrong_bruno_right': [],
        'rf_right_bruno_wrong': [],
        'both_wrong': []
    }
    
    print("\n🔄 Analyse en cours...")
    
    for i, case in enumerate(test_cases):
        # Prédictions
        rf_pred, rf_conf, rf_reason = advanced_rf_predict(case['photo1'], case['photo2'], rf_model, feature_names)
        bruno_pred, bruno_reason = bruno_custom_predict(case['photo1'], case['photo2'])
        
        # Vérifier si correct
        rf_is_correct = rf_pred == case['winner_id']
        bruno_is_correct = bruno_pred == case['winner_id']
        
        # Statistiques
        if rf_is_correct:
            rf_correct += 1
        if bruno_is_correct:
            bruno_correct += 1
        
        if rf_is_correct and bruno_is_correct:
            both_correct += 1
        elif not rf_is_correct and not bruno_is_correct:
            both_wrong += 1
            failure_cases['both_wrong'].append({
                'case': case,
                'rf_pred': rf_pred,
                'bruno_pred': bruno_pred,
                'rf_reason': rf_reason,
                'bruno_reason': bruno_reason,
                'rf_conf': rf_conf
            })
        elif rf_is_correct and not bruno_is_correct:
            rf_only_correct += 1
            failure_cases['rf_right_bruno_wrong'].append({
                'case': case,
                'rf_pred': rf_pred,
                'bruno_pred': bruno_pred,
                'rf_reason': rf_reason,
                'bruno_reason': bruno_reason,
                'rf_conf': rf_conf
            })
        elif not rf_is_correct and bruno_is_correct:
            bruno_only_correct += 1
            failure_cases['rf_wrong_bruno_right'].append({
                'case': case,
                'rf_pred': rf_pred,
                'bruno_pred': bruno_pred,
                'rf_reason': rf_reason,
                'bruno_reason': bruno_reason,
                'rf_conf': rf_conf
            })
    
    total = len(test_cases)
    rf_accuracy = rf_correct / total * 100
    bruno_accuracy = bruno_correct / total * 100
    
    # Résultats globaux
    print(f"\n📈 === RÉSULTATS GLOBAUX ===")
    print(f"Advanced RF: {rf_accuracy:.1f}% ({rf_correct}/{total})")
    print(f"Bruno Custom: {bruno_accuracy:.1f}% ({bruno_correct}/{total})")
    print(f"Différence: {bruno_accuracy - rf_accuracy:+.1f}%")
    
    print(f"\n🔢 === RÉPARTITION DÉTAILLÉE ===")
    print(f"✅ Les deux corrects: {both_correct} ({both_correct/total*100:.1f}%)")
    print(f"❌ Les deux incorrects: {both_wrong} ({both_wrong/total*100:.1f}%)")
    print(f"🤖 RF seul correct: {rf_only_correct} ({rf_only_correct/total*100:.1f}%)")
    print(f"👑 Bruno seul correct: {bruno_only_correct} ({bruno_only_correct/total*100:.1f}%)")
    
    # Analyse des échecs critiques (RF faux, Bruno correct)
    critical_failures = failure_cases['rf_wrong_bruno_right']
    print(f"\n🚨 === ÉCHECS CRITIQUES RF (Bruno gagne seul) ===")
    print(f"Nombre: {len(critical_failures)}")
    
    if critical_failures:
        print("\n📋 Top 10 échecs critiques:")
        
        # Analyser les patterns d'échec
        low_confidence_failures = []
        high_confidence_failures = []
        
        for failure in critical_failures[:10]:
            case = failure['case']
            p1 = case['photo1']
            p2 = case['photo2']
            winner = "Photo1" if case['winner_id'] == p1['id'] else "Photo2"
            rf_choice = "Photo1" if failure['rf_pred'] == p1['id'] else "Photo2"
            bruno_choice = "Photo1" if failure['bruno_pred'] == p1['id'] else "Photo2"
            
            print(f"\n   {len([f for f in critical_failures if f == failure])+1}. Photo1(r:{safe_float(p1.get('ratio')):.2f}, v:{safe_float(p1.get('votes')):.0f}, rk:{safe_float(p1.get('rank')):.0f}) vs Photo2(r:{safe_float(p2.get('ratio')):.2f}, v:{safe_float(p2.get('votes')):.0f}, rk:{safe_float(p2.get('rank')):.0f})")
            print(f"      Gagnant réel: {winner}")
            print(f"      RF prédit: {rf_choice} (conf:{failure['rf_conf']:.3f}) - {failure['rf_reason']}")
            print(f"      Bruno prédit: {bruno_choice} - {failure['bruno_reason']}")
            
            if failure['rf_conf'] < 0.6:
                low_confidence_failures.append(failure)
            else:
                high_confidence_failures.append(failure)
        
        print(f"\n📊 Analyse confiance RF:")
        print(f"   Échecs faible confiance (<0.6): {len(low_confidence_failures)}")
        print(f"   Échecs forte confiance (≥0.6): {len(high_confidence_failures)}")
        
        if len(low_confidence_failures) > len(high_confidence_failures):
            print("   💡 Hypothèse: RF pas assez confiant dans ses prédictions")
        else:
            print("   ⚠️ Problème: RF confiant mais se trompe systématiquement")
    
    # Succès uniques de RF
    rf_successes = failure_cases['rf_right_bruno_wrong']
    print(f"\n🎯 === SUCCÈS UNIQUES RF (RF gagne seul) ===")
    print(f"Nombre: {len(rf_successes)}")
    
    if rf_successes:
        print("\nTop 5 cas où RF bat Bruno:")
        for i, success in enumerate(rf_successes[:5]):
            case = success['case']
            p1 = case['photo1']
            p2 = case['photo2']
            winner = "Photo1" if case['winner_id'] == p1['id'] else "Photo2"
            
            print(f"   {i+1}. {winner} gagne - RF conf:{success['rf_conf']:.3f}")
            print(f"      RF: {success['rf_reason']}")
            print(f"      Bruno: {success['bruno_reason']}")
    
    # Recommandations
    print(f"\n🎯 === RECOMMANDATIONS ===")
    
    if bruno_accuracy > rf_accuracy + 5:
        print("✅ GARDER BRUNO CUSTOM comme défaut")
        print("   - Performance supérieure confirmée")
        print("   - Logique simple et robuste")
        print("   - Pas de dépendances externes")
    
    if len(low_confidence_failures) > len(critical_failures) // 2:
        print("🔧 AMÉLIORER RF:")
        print("   - Ajuster seuil de confiance minimum")
        print("   - Fallback vers Bruno si confiance < 0.7")
    
    if len(critical_failures) > 20:
        print("⚠️ PROBLÈME RF MAJEUR:")
        print("   - Trop d'échecs critiques")
        print("   - Revoir les features engineering")
        print("   - Possibles overfitting sur données d'entraînement")

if __name__ == "__main__":
    analyze_rf_failures()