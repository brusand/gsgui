#!/usr/bin/env python3
"""
Analyse de l'échec du turbo votes_ratio_patterns
Comprendre pourquoi seulement 3/6 réussites (50%)
"""

def analyze_turbo_failure():
    """Analyse des échecs du turbo du 26/07/2025 17:02"""
    
    print("🔍 === ANALYSE ÉCHEC TURBO VOTES_RATIO_PATTERNS ===")
    print("📅 Date: 26/07/2025 17:02:50")
    print("🎯 Algorithme: votes_ratio_patterns")
    print("📊 Résultat: 3/6 réussites (50.0%)")
    print("=" * 60)
    
    # Données des paires du turbo
    pairs = [
        # Paire 1: SUCCESS
        {
            'pair': 1,
            'result': 'SUCCESS',
            'chosen': {'id': '5d434ae44e2a51649ed679dc5173cb2b', 'votes': 214, 'rank': 393, 'ratio': 1.5},
            'other': {'id': '49c165209614b86abcaf619dd2a10976', 'votes': 62, 'rank': 546, 'ratio': 1.33},
            'scores': '17% vs 83%',
            'reason': 'ratio: 1.5 vs 1.33'
        },
        # Paire 2: FAILED  
        {
            'pair': 2,
            'result': 'FAILED',
            'chosen': {'id': '3a4850674a4c67e5831a21c0d07582c6', 'votes': 392, 'rank': 221, 'ratio': 1.33},
            'other': {'id': '3a8db85768a7bc65cc2e97083f0ecdbf', 'votes': 342, 'rank': 265, 'ratio': 1.5},
            'winner': {'id': '3a8db85768a7bc65cc2e97083f0ecdbf', 'votes': 342, 'rank': 265, 'ratio': 1.5},
            'scores': '65% vs 35%',
            'reason': 'votes: 392 vs 342'
        },
        # Paire 3: FAILED
        {
            'pair': 3,
            'result': 'FAILED',
            'chosen': {'id': '66f0e103ca95ec5473913aecf03e09b7', 'votes': 347, 'rank': 260, 'ratio': 1.54},
            'other': {'id': '456dd37855c646069dfe058b85d1e908', 'votes': 268, 'rank': 339, 'ratio': 1.43},
            'winner': {'id': '456dd37855c646069dfe058b85d1e908', 'votes': 268, 'rank': 339, 'ratio': 1.43},
            'scores': '39% vs 61%',
            'reason': 'ratio: 1.54 vs 1.43'
        },
        # Paire 4: SUCCESS
        {
            'pair': 4,
            'result': 'SUCCESS',
            'chosen': {'id': '6ad34eb809aa19e1111a20f084af7afb', 'votes': 348, 'rank': 259, 'ratio': 1.5},
            'other': {'id': '16798a2077002f5d7a204614408ff572', 'votes': 318, 'rank': 289, 'ratio': 1.5},
            'scores': '65% vs 35%',
            'reason': 'ratios égaux, votes: 348 vs 318'
        },
        # Paire 5: FAILED
        {
            'pair': 5,
            'result': 'FAILED',
            'chosen': {'id': '5a2eaa3661d87c2f88ae5d2f83373c9a', 'votes': 305, 'rank': 302, 'ratio': 1.5},
            'other': {'id': '186364984d45611dee35ce50c076f01c', 'votes': 253, 'rank': 354, 'ratio': 1.5},
            'winner': {'id': '186364984d45611dee35ce50c076f01c', 'votes': 253, 'rank': 354, 'ratio': 1.5},
            'scores': '60% vs 40%',
            'reason': 'ratios égaux, votes: 305 vs 253'
        },
        # Paire 6: SUCCESS  
        {
            'pair': 6,
            'result': 'SUCCESS',
            'chosen': {'id': '43beaed676f6000b492fab85b08e196b', 'votes': 358, 'rank': 250, 'ratio': 2.02},
            'other': {'id': '46d41833bf113d5e8187422358b807f5', 'votes': 247, 'rank': 360, 'ratio': 1.33},
            'scores': '37% vs 63%',
            'reason': 'ratio: 2.02 vs 1.33'
        },
        # Paire 7: FAILED
        {
            'pair': 7,
            'result': 'FAILED',
            'chosen': {'id': '6299e743d4d73ed4d2f53271f093a495', 'votes': 306, 'rank': 301, 'ratio': 1.78},
            'other': {'id': '2f4b2d0b2e9b1d670372e94c5b002e2e', 'votes': 245, 'rank': 362, 'ratio': 1.33},
            'winner': {'id': '2f4b2d0b2e9b1d670372e94c5b002e2e', 'votes': 245, 'rank': 362, 'ratio': 1.33},
            'scores': '65% vs 35%',
            'reason': 'ratio: 1.78 vs 1.33'
        }
    ]
    
    print("📋 === ANALYSE DÉTAILLÉE DES PAIRES ===")
    
    successes = []
    failures = []
    
    for pair in pairs:
        print(f"\n🔸 Paire {pair['pair']}: {pair['result']}")
        print(f"   Choisi: votes={pair['chosen']['votes']}, rank={pair['chosen']['rank']}, ratio={pair['chosen']['ratio']}")
        print(f"   Autre:  votes={pair['other']['votes']}, rank={pair['other']['rank']}, ratio={pair['other']['ratio']}")
        print(f"   Scores: {pair['scores']}")
        print(f"   Raison: {pair['reason']}")
        
        if pair['result'] == 'SUCCESS':
            successes.append(pair)
        else:
            failures.append(pair)
            winner = pair.get('winner', {})
            print(f"   ❌ Vrai gagnant: votes={winner['votes']}, rank={winner['rank']}, ratio={winner['ratio']}")
    
    print(f"\n📊 === PATTERNS DES SUCCÈS ===")
    print(f"Nombre de succès: {len(successes)}")
    for success in successes:
        chosen = success['chosen']
        other = success['other']
        print(f"   Paire {success['pair']}: {chosen['ratio']} vs {other['ratio']} (votes: {chosen['votes']} vs {other['votes']})")
    
    print(f"\n❌ === PATTERNS DES ÉCHECS ===")
    print(f"Nombre d'échecs: {len(failures)}")
    
    for failure in failures:
        chosen = failure['chosen']
        other = failure['other']
        winner = failure.get('winner', other)
        
        print(f"\n   Paire {failure['pair']}:")
        print(f"      Choisi: ratio={chosen['ratio']}, votes={chosen['votes']}, rank={chosen['rank']}")
        print(f"      Gagnant: ratio={winner['ratio']}, votes={winner['votes']}, rank={winner['rank']}")
        
        # Analyser pourquoi l'algorithme s'est trompé
        ratio_diff = chosen['ratio'] - winner['ratio']
        votes_diff = chosen['votes'] - winner['votes']
        rank_diff = chosen['rank'] - winner['rank']  # Rang plus petit = meilleur
        
        print(f"      Écarts: ratio={ratio_diff:+.2f}, votes={votes_diff:+.0f}, rank={rank_diff:+.0f}")
        
        # Identifier le problème principal
        problems = []
        if ratio_diff > 0 and failure['result'] == 'FAILED':
            problems.append(f"Ratio plus élevé mais a perdu ({chosen['ratio']} vs {winner['ratio']})")
        if votes_diff > 0 and failure['result'] == 'FAILED':
            problems.append(f"Plus de votes mais a perdu ({chosen['votes']} vs {winner['votes']})")
        if rank_diff < 0 and failure['result'] == 'FAILED':
            problems.append(f"Meilleur rang mais a perdu (#{chosen['rank']} vs #{winner['rank']})")
            
        print(f"      Problèmes: {'; '.join(problems) if problems else 'Situation normale'}")
    
    print(f"\n🔬 === ANALYSE ALGORITHME VOTES_RATIO_PATTERNS ===")
    
    # Analyser les cas où l'algorithme échoue
    print("Cas problématiques identifiés:")
    
    # Échec type 1: Paire 2 - votes >> ratio
    print("\n1. 📈 VOTES vs RATIO (Paire 2):")
    print("   - Choisi: 392 votes, ratio 1.33")
    print("   - Gagnant: 342 votes, ratio 1.5")
    print("   - Problème: L'algo privilégie les votes quand ratios proches")
    print("   - Solution: Donner plus de poids au ratio même avec diff modérée")
    
    # Échec type 2: Paire 3 - ratio plus élevé perd
    print("\n2. 🎯 RATIO ÉLEVÉ PERD (Paire 3):")
    print("   - Choisi: ratio 1.54, 347 votes")
    print("   - Gagnant: ratio 1.43, 268 votes")
    print("   - Problème: Différence ratio faible (0.11) mais important")
    print("   - Solution: Analyser les seuils critiques de ratios")
    
    # Échec type 3: Paire 5 - ratios égaux, votes privilégiés
    print("\n3. ⚖️ RATIOS ÉGAUX (Paire 5):")
    print("   - Choisi: ratio 1.5, 305 votes")
    print("   - Gagnant: ratio 1.5, 253 votes")
    print("   - Problème: Quand ratios égaux, votes ne suffisent pas")
    print("   - Solution: Intégrer le rang comme critère décisif")
    
    # Échec type 4: Paire 7 - ratio élevé perd contre ratio bas
    print("\n4. 🔄 INVERSION RATIO (Paire 7):")
    print("   - Choisi: ratio 1.78, 306 votes")
    print("   - Gagnant: ratio 1.33, 245 votes")
    print("   - Problème: Ratio significativement plus élevé mais perd")
    print("   - Solution: Pattern contre-intuitif à analyser")
    
    print(f"\n💡 === RECOMMANDATIONS ===")
    
    print("1. 🔧 AMÉLIORER L'ALGORITHME:")
    print("   - Intégrer le rang comme critère décisif en cas d'égalité")
    print("   - Revoir les seuils de différence de ratio")
    print("   - Analyser les patterns contre-intuitifs (ratio élevé qui perd)")
    
    print("\n2. 📊 ANALYSER LES DONNÉES:")
    print("   - Ce turbo semble avoir des patterns différents de l'historique")
    print("   - Performance 50% vs 69.8% attendu = problème de généralisation")
    print("   - Possibilité que ce challenge ait des règles différentes")
    
    print("\n3. 🎯 STRATÉGIE:")
    print("   - Revenir temporairement à Bruno Custom (66% vs 50%)")
    print("   - Enrichir l'historique avec plus de cas récents")
    print("   - Développer une version hybride votes_ratio_patterns_v2")
    
    return {
        'total_pairs': len(pairs),
        'successes': len(successes),
        'failures': len(failures),
        'accuracy': len(successes) / len(pairs) * 100
    }

if __name__ == "__main__":
    results = analyze_turbo_failure()
    print(f"\n📈 === RÉSUMÉ ===")
    print(f"Performance: {results['successes']}/{results['total_pairs']} = {results['accuracy']:.1f}%")
    print(f"Attendu: 69.8% (sur historique)")
    print(f"Écart: {results['accuracy'] - 69.8:+.1f}%")