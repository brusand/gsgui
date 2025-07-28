#!/usr/bin/env python3
"""
Analyse du bug des IDs gagnants incohérents
Hypothèse: image_id retourné au lieu de first_id/second_id en cas d'erreur
"""

from configobj import ConfigObj

def analyze_winner_bug():
    """Analyse le bug des gagnants incohérents"""
    
    print("🔍 === ANALYSE BUG WINNER_ID ===")
    print("Hypothèse: image_id retourné au lieu de first_id/second_id")
    print("=" * 60)
    
    # Charger les données .ini originales
    try:
        config = ConfigObj('gsgui.ini', encoding='utf-8')
    except:
        print("❌ Impossible de charger gsgui.ini")
        return
    
    turbo_history = config.get('turbo_history', {})
    
    problematic_cases = []
    total_cases = 0
    
    # Analyser toutes les entrées
    for profile_name, profile_history in turbo_history.items():
        if not isinstance(profile_history, dict):
            continue
            
        for entry_key, entry_data in profile_history.items():
            if not isinstance(entry_data, dict):
                continue
                
            total_cases += 1
            
            # Extraire les données
            photo1_data = entry_data.get('photo1', {})
            photo2_data = entry_data.get('photo2', {})
            winner_data = entry_data.get('winner', {})
            
            photo1_id = photo1_data.get('id', '')
            photo2_id = photo2_data.get('id', '')
            winner_id = winner_data.get('id', '')
            algorithm = entry_data.get('algorithm', 'unknown')
            success = entry_data.get('success', None)
            
            if not photo1_id or not photo2_id or not winner_id:
                continue
            
            # Vérifier la cohérence
            is_consistent = winner_id == photo1_id or winner_id == photo2_id
            
            if not is_consistent:
                # Cas problématique trouvé
                problematic_cases.append({
                    'entry_key': entry_key,
                    'profile': profile_name,
                    'challenge_title': entry_data.get('challenge_title', 'Unknown'),
                    'photo1_id': photo1_id,
                    'photo2_id': photo2_id,
                    'winner_id': winner_id,
                    'algorithm': algorithm,
                    'success': success,
                    'timestamp': entry_data.get('timestamp', 'Unknown')
                })
    
    print(f"📊 Analyse terminée:")
    print(f"   Total cas: {total_cases}")
    print(f"   Cas problématiques: {len(problematic_cases)}")
    print(f"   Taux d'erreur: {len(problematic_cases)/total_cases*100:.1f}%")
    
    if len(problematic_cases) == 0:
        print("✅ Aucun cas problématique trouvé dans gsgui.ini")
        return
    
    # Analyser les patterns
    print(f"\n🔍 === ANALYSE PATTERNS ===")
    
    # Par algorithme
    algo_count = {}
    for case in problematic_cases:
        algo = case['algorithm']
        algo_count[algo] = algo_count.get(algo, 0) + 1
    
    print(f"🤖 Par algorithme:")
    for algo, count in sorted(algo_count.items(), key=lambda x: x[1], reverse=True):
        print(f"   {algo}: {count} cas")
    
    # Par succès/échec
    success_count = {'True': 0, 'False': 0, 'None': 0}
    for case in problematic_cases:
        success_key = str(case['success'])
        success_count[success_key] = success_count.get(success_key, 0) + 1
    
    print(f"\n✅❌ Par résultat:")
    for result, count in success_count.items():
        print(f"   {result}: {count} cas")
    
    # IDs gagnants récurrents
    winner_count = {}
    for case in problematic_cases:
        winner_id = case['winner_id'][:8]  # Tronquer pour grouper
        winner_count[winner_id] = winner_count.get(winner_id, 0) + 1
    
    print(f"\n🏆 IDs gagnants récurrents:")
    sorted_winners = sorted(winner_count.items(), key=lambda x: x[1], reverse=True)
    for winner_id, count in sorted_winners[:5]:
        print(f"   {winner_id}: {count} occurrences")
    
    # Exemples détaillés
    print(f"\n📋 === EXEMPLES DÉTAILLÉS ===")
    for i, case in enumerate(problematic_cases[:5]):
        print(f"\n{i+1}. {case['profile']} | {case['challenge_title']}")
        print(f"   Entry: {case['entry_key']}")
        print(f"   Photo1: {case['photo1_id'][:8]}")
        print(f"   Photo2: {case['photo2_id'][:8]}")
        print(f"   Winner: {case['winner_id'][:8]} ❌")
        print(f"   Algorithm: {case['algorithm']}")
        print(f"   Success: {case['success']}")
        print(f"   Timestamp: {case['timestamp']}")
    
    # Test hypothèse: winner_id est-il un image_id qui a été choisi ?
    print(f"\n🧪 === TEST HYPOTHÈSE ===")
    print(f"Hypothèse: winner_id = image_id choisi par l'algorithme")
    
    # Comparer les cas SUCCESS vs FAILED
    success_cases = [c for c in problematic_cases if c['success'] == True]
    failed_cases = [c for c in problematic_cases if c['success'] == False]
    none_cases = [c for c in problematic_cases if c['success'] is None]
    
    print(f"📊 Répartition des cas problématiques:")
    print(f"   SUCCESS: {len(success_cases)} (étrange!)")
    print(f"   FAILED: {len(failed_cases)} (normal si hypothèse correcte)")
    print(f"   None/Unknown: {len(none_cases)}")
    
    # Si l'hypothèse est correcte, les cas FAILED devraient être majoritaires
    if len(failed_cases) > len(success_cases):
        print(f"✅ Hypothèse plausible: plus de cas FAILED que SUCCESS")
    else:
        print(f"❓ Hypothèse douteuse: plus de cas SUCCESS que FAILED")
    
    return problematic_cases

if __name__ == "__main__":
    problematic_cases = analyze_winner_bug()
    
    if problematic_cases:
        print(f"\n💡 === RECOMMANDATIONS ===")
        print(f"1. 🔧 CORRIGER LE CODE:")
        print(f"   - Lignes 1274, 1279, 1284 dans submit_single_turbo_selection")
        print(f"   - Retourner None au lieu de image_id en cas d'erreur")
        print(f"   - Ou déterminer le vrai gagnant autrement")
        print(f"\n2. 🧹 NETTOYER LES DONNÉES:")
        print(f"   - {len(problematic_cases)} entrées à corriger")
        print(f"   - Utiliser turbos_clean.feather pour les analyses")
        print(f"\n3. 🔄 PRÉVENIR LES FUTURES ERREURS:")
        print(f"   - Validation des winner_id avant sauvegarde")
        print(f"   - Logs plus détaillés des erreurs de soumission")