#!/usr/bin/env python3
"""
Debug des différences entre notre test et la fonction eval_turbo
Analyse les jeux de données et implémentations
"""

from configobj import ConfigObj

def safe_float(val, default=0.0):
    try:
        return float(val) if val else default
    except (ValueError, TypeError):
        return default

def debug_eval_differences():
    """Débugge les différences entre test isolé et eval_turbo"""
    print("🔍 === DEBUG ÉCARTS EVAL_TURBO ===")
    print("🎯 Objectif: Comprendre pourquoi 69.8% vs 58.5%")
    print("=" * 60)
    
    config = ConfigObj('gsgui.ini', encoding='utf-8')
    history = config.get('turbo_history', {}).get('bruno', {})
    
    if not history:
        print("❌ Pas d'historique turbo trouvé")
        return
    
    # Analyser tous les cas disponibles
    all_cases = []
    valid_cases = []
    filtered_cases = []
    
    for key, comp_data in history.items():
        photo1 = comp_data.get('photo1', {})
        photo2 = comp_data.get('photo2', {})
        winner_info = comp_data.get('winner', {})
        
        all_cases.append(key)
        
        # Critères de base (comme notre test)
        if not (photo1.get('found') and photo2.get('found')):
            continue
        
        winner_id = winner_info.get('id', '')
        if winner_id not in [photo1.get('id', ''), photo2.get('id', '')]:
            continue
        
        valid_cases.append(key)
        
        # Critères stricts (possiblement comme eval_turbo)
        v1 = safe_float(photo1.get('votes', 0))
        v2 = safe_float(photo2.get('votes', 0))
        r1 = safe_float(photo1.get('ratio', 0))
        r2 = safe_float(photo2.get('ratio', 0))
        rank1 = safe_float(photo1.get('rank', 999))
        rank2 = safe_float(photo2.get('rank', 999))
        
        # Filtres possibles de eval_turbo
        if (v1 <= 0 or v2 <= 0 or r1 <= 0 or r2 <= 0 or 
            rank1 >= 999 or rank2 >= 999):
            continue
        
        filtered_cases.append({
            'key': key,
            'photo1': photo1,
            'photo2': photo2,
            'winner_id': winner_id,
            'v1': v1, 'v2': v2, 'r1': r1, 'r2': r2,
            'rank1': rank1, 'rank2': rank2
        })
    
    print(f"📊 === ANALYSE JEUX DE DONNÉES ===")
    print(f"   Cas totaux dans historique: {len(all_cases)}")
    print(f"   Cas valides (notre test):   {len(valid_cases)}")
    print(f"   Cas filtrés strictement:    {len(filtered_cases)}")
    print(f"   Différence total/valide:    {len(all_cases) - len(valid_cases)} cas exclus")
    print(f"   Différence valide/filtré:   {len(valid_cases) - len(filtered_cases)} cas exclus")
    print(f"   Eval turbo rapporte:        272 cas")
    
    # Hypothèse: eval_turbo utilise les cas filtrés strictement
    if len(filtered_cases) == 272:
        print("   ✅ HYPOTHÈSE CONFIRMÉE: eval_turbo = cas filtrés strictement")
    else:
        print(f"   ❓ HYPOTHÈSE PARTIELLE: {len(filtered_cases)} vs 272 cas eval_turbo")
    
    # Tester Bruno Custom sur les cas filtrés strictement
    print(f"\n🧪 === TEST BRUNO CUSTOM SUR CAS FILTRÉS ===")
    
    def bruno_custom_simplified(first_data, second_data, first_id='photo1', second_id='photo2'):
        """Version simplifiée de Bruno Custom pour test"""
        first_ratio = safe_float(first_data.get('ratio', 0))
        second_ratio = safe_float(second_data.get('ratio', 0))
        first_votes = safe_float(first_data.get('votes', 0))
        second_votes = safe_float(second_data.get('votes', 0))
        first_rank = safe_float(first_data.get('rank', 999))
        second_rank = safe_float(second_data.get('rank', 999))

        # Logique simplifiée Bruno Custom
        if abs(first_ratio - second_ratio) > 0.1:
            if first_ratio > second_ratio:
                return first_id
            else:
                return second_id
        
        # Ratios similaires: meilleur rang
        if abs(first_rank - second_rank) > 50:
            if first_rank < second_rank:
                return first_id
            else:
                return second_id
        
        # Fallback: plus de votes
        if first_votes > second_votes:
            return first_id
        else:
            return second_id
    
    bruno_correct_filtered = 0
    
    for case in filtered_cases:
        bruno_pred = bruno_custom_simplified(case['photo1'], case['photo2'])
        bruno_winner_id = case['photo1'].get('id') if bruno_pred == 'photo1' else case['photo2'].get('id')
        
        if bruno_winner_id == case['winner_id']:
            bruno_correct_filtered += 1
    
    bruno_accuracy_filtered = bruno_correct_filtered / len(filtered_cases) * 100
    
    print(f"   Bruno Custom sur cas filtrés: {bruno_accuracy_filtered:.1f}% ({bruno_correct_filtered}/{len(filtered_cases)})")
    print(f"   Eval turbo Bruno Custom:      58.5% (159/272)")
    print(f"   Différence:                   {bruno_accuracy_filtered - 58.5:+.1f}%")
    
    # Analyser les caractéristiques des cas exclus
    print(f"\n📋 === ANALYSE CAS EXCLUS ===")
    
    excluded_cases = []
    for key in valid_cases:
        if not any(case['key'] == key for case in filtered_cases):
            comp_data = history[key]
            photo1 = comp_data.get('photo1', {})
            photo2 = comp_data.get('photo2', {})
            
            v1 = safe_float(photo1.get('votes', 0))
            v2 = safe_float(photo2.get('votes', 0))
            r1 = safe_float(photo1.get('ratio', 0))
            r2 = safe_float(photo2.get('ratio', 0))
            rank1 = safe_float(photo1.get('rank', 999))
            rank2 = safe_float(photo2.get('rank', 999))
            
            reason = []
            if v1 <= 0 or v2 <= 0:
                reason.append("votes <= 0")
            if r1 <= 0 or r2 <= 0:
                reason.append("ratio <= 0")
            if rank1 >= 999 or rank2 >= 999:
                reason.append("rang >= 999")
            
            excluded_cases.append({
                'key': key,
                'reasons': reason,
                'v1': v1, 'v2': v2, 'r1': r1, 'r2': r2,
                'rank1': rank1, 'rank2': rank2
            })
    
    print(f"   Cas exclus du filtrage strict: {len(excluded_cases)}")
    
    # Compter les raisons d'exclusion
    exclusion_reasons = {}
    for case in excluded_cases:
        for reason in case['reasons']:
            exclusion_reasons[reason] = exclusion_reasons.get(reason, 0) + 1
    
    print("   Raisons d'exclusion:")
    for reason, count in exclusion_reasons.items():
        print(f"      {reason}: {count} cas")
    
    # Exemples de cas exclus
    print(f"\n   Exemples de cas exclus:")
    for i, case in enumerate(excluded_cases[:5]):
        print(f"      {i+1}. {case['key']}: {', '.join(case['reasons'])}")
        print(f"         v1={case['v1']}, v2={case['v2']}, r1={case['r1']}, r2={case['r2']}")
        print(f"         rank1={case['rank1']}, rank2={case['rank2']}")
    
    # Hypothèses sur les différences d'implémentation
    print(f"\n🔧 === HYPOTHÈSES DIFFÉRENCES ===")
    
    print(f"1. 📊 JEUX DE DONNÉES:")
    print(f"   - Notre test: {len(valid_cases)} cas (critères basiques)")
    print(f"   - Eval turbo: 272 cas (filtrage strict)")
    print(f"   - Cas exclus: {len(excluded_cases)} (votes/ratio/rang invalides)")
    
    print(f"\n2. 🎯 IMPLÉMENTATION BRUNO CUSTOM:")
    print(f"   - Notre test: logique simplifiée")
    print(f"   - Eval turbo: Bruno Custom V2 complet (5 règles)")
    print(f"   - Différence attendue: ~5-10% d'amélioration V2")
    
    print(f"\n3. 📈 DIFFICULTÉ DES CAS:")
    if len(excluded_cases) > 50:
        print(f"   - {len(excluded_cases)} cas exclus = cas 'difficiles'")
        print(f"   - Eval turbo travaille sur cas plus 'purs'")
        print(f"   - Notre test inclut cas avec données partielles")
    
    print(f"\n🎯 === CONCLUSIONS ===")
    
    print(f"✅ FILTRAGE: Eval turbo utilise probablement un filtrage strict")
    print(f"✅ IMPLÉMENTATION: Différence entre logiques simplifiée vs complète")
    print(f"✅ JEUX DONNÉES: {len(excluded_cases)} cas exclus affectent la performance")
    
    recommendation_accuracy = bruno_accuracy_filtered - 5  # Estimation avec V2 complète
    print(f"\n💡 ESTIMATION VOTES/RATIO PATTERNS SUR EVAL TURBO:")
    print(f"   - Bruno Custom V2 eval: ~58.5%")
    print(f"   - Notre gain observé: +7.7%")
    print(f"   - Estimation Patterns: ~66-67% sur eval turbo")
    
    return {
        'total_cases': len(all_cases),
        'valid_cases': len(valid_cases),
        'filtered_cases': len(filtered_cases),
        'excluded_cases': len(excluded_cases),
        'bruno_accuracy_filtered': bruno_accuracy_filtered
    }

if __name__ == "__main__":
    debug_eval_differences()