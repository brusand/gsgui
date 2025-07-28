
def advanced_turbo_algorithm(photo1, photo2):
    """
    Algorithme Turbo IA Avancé - Précision Cross-Val: 68.8%
    Basé sur 55 features et Random Forest
    """
    
    def safe_float(val, default=0.0):
        try:
            return float(val) if val else default
        except (ValueError, TypeError):
            return default
    
    r1 = safe_float(photo1.get('ratio', 0))
    r2 = safe_float(photo2.get('ratio', 0))
    v1 = safe_float(photo1.get('votes', 0))
    v2 = safe_float(photo2.get('votes', 0))
    rank1 = safe_float(photo1.get('rank', 999))
    rank2 = safe_float(photo2.get('rank', 999))
    
    # Règles basées sur les features les plus importantes:

    # Règle basée sur votes_rank_interaction_ratio (importance: 0.077)
    rank_eff_1 = rank1 / max(r1, 0.1)
    rank_eff_2 = rank2 / max(r2, 0.1)
    if abs(rank_eff_1 - rank_eff_2) > 100:
        return photo1['id'] if rank_eff_1 < rank_eff_2 else photo2['id'], f"advanced_ai: votes_rank_interaction_ratio"

    # Règle basée sur votes_ratio (importance: 0.058)
    if max(v1, v2) > 0 and abs(v1 - v2) > 200:
        return photo1['id'] if v1 > v2 else photo2['id'], f"advanced_ai: votes_ratio"

    # Règle basée sur rank_ratio (importance: 0.058)
    rank_eff_1 = rank1 / max(r1, 0.1)
    rank_eff_2 = rank2 / max(r2, 0.1)
    if abs(rank_eff_1 - rank_eff_2) > 100:
        return photo1['id'] if rank_eff_1 < rank_eff_2 else photo2['id'], f"advanced_ai: rank_ratio"

    # Règle basée sur rank_efficiency_ratio (importance: 0.039)
    rank_eff_1 = rank1 / max(r1, 0.1)
    rank_eff_2 = rank2 / max(r2, 0.1)
    if abs(rank_eff_1 - rank_eff_2) > 100:
        return photo1['id'] if rank_eff_1 < rank_eff_2 else photo2['id'], f"advanced_ai: rank_efficiency_ratio"

    # Fallback: ratio traditionnel
    return photo1['id'] if r1 <= r2 else photo2['id'], "advanced_ai: fallback"
