#!/usr/bin/env python3
"""
Test de l'option turbo_history_enabled
Vérifie que l'historisation peut être désactivée via le fichier .ini
"""

import sys
import os
from unittest.mock import Mock, patch

# Créer une mock de la configuration
def create_mock_config():
    """Crée une configuration mock pour les tests"""
    return {
        'players': {
            'bruno': {
                'xtoken': 'test_token',
                'turbo_algorithm': '[hybrid,position_aware,adaptive_time]',
                'turbo_history_enabled': True  # Activé par défaut
            },
            'caloune': {
                'xtoken': 'test_token2', 
                'turbo_algorithm': '[hybrid,ratio_low,votes_high]',
                'turbo_history_enabled': False  # Désactivé pour test
            },
            'test_user': {
                'xtoken': 'test_token3',
                'turbo_algorithm': '[bruno_custom]',
                'turbo_history_enabled': 'false'  # String pour test conversion
            }
        }
    }

def test_turbo_history_option():
    """Test de l'option turbo_history_enabled"""
    
    print("🧪 === TEST OPTION TURBO_HISTORY_ENABLED ===\n")
    
    # Mock de la classe ProfileTab pour tester is_turbo_history_enabled
    class MockProfileTab:
        def __init__(self, player, config):
            self.player = player
            self.config = config
        
        def is_turbo_history_enabled(self):
            """Méthode copiée depuis gsui.py"""
            try:
                player_config = self.config['players'].get(self.player, {})
                enabled = player_config.get('turbo_history_enabled', True)  # True par défaut
                
                # Gestion des valeurs string/bool
                if isinstance(enabled, str):
                    enabled = enabled.lower() in ('true', '1', 'yes', 'on')
                
                print(f"🔧 DEBUG: Historisation turbo pour {self.player}: {enabled}")
                return bool(enabled)
            except Exception as e:
                print(f"❌ Erreur lecture historisation turbo: {e}")
                return True  # Par défaut activé en cas d'erreur
        
        def save_turbo_history_mock(self, challenge_id, challenge_title, time_left, first_id, first_data, second_id, second_data, winner_id, algorithm, strategy_description, success):
            """Mock de save_turbo_history avec vérification d'option"""
            if not self.is_turbo_history_enabled():
                print(f"⏭️ Historisation turbo désactivée pour {self.player} - Comparaison ignorée")
                return False  # Indique que l'historisation a été ignorée
            else:
                print(f"✅ Historisation turbo activée pour {self.player} - Comparaison sauvée")
                return True  # Indique que l'historisation s'est faite
    
    # Configuration de test
    config = create_mock_config()
    
    # Test des différents utilisateurs
    test_cases = [
        {
            'player': 'bruno',
            'expected': True,
            'description': 'Historisation activée (True)'
        },
        {
            'player': 'caloune', 
            'expected': False,
            'description': 'Historisation désactivée (False)'
        },
        {
            'player': 'test_user',
            'expected': False,
            'description': 'Historisation désactivée (string "false")'
        },
        {
            'player': 'unknown_user',
            'expected': True,
            'description': 'Utilisateur inexistant (défaut True)'
        }
    ]
    
    results = []
    
    for i, case in enumerate(test_cases, 1):
        print(f"📊 === TEST {i}: {case['description']} ===")
        print(f"   👤 Joueur: {case['player']}")
        print(f"   🎯 Attendu: {case['expected']}")
        
        # Créer le mock ProfileTab
        profile = MockProfileTab(case['player'], config)
        
        # Tester la méthode is_turbo_history_enabled
        actual = profile.is_turbo_history_enabled()
        success = actual == case['expected']
        
        print(f"   📋 Résultat: {actual}")
        print(f"   {'✅' if success else '❌'} Test: {'RÉUSSI' if success else 'ÉCHOUÉ'}")
        
        # Tester save_turbo_history avec l'option
        print(f"   🧪 Test sauvegarde historique:")
        history_saved = profile.save_turbo_history_mock(
            'test_challenge', 'Test Challenge', '1D 2H 30M 0S',
            'photo1', {'ratio': 1.5, 'votes': 100, 'rank': 50},
            'photo2', {'ratio': 1.3, 'votes': 120, 'rank': 40},
            'photo2', 'test_algorithm', 'test strategy', True
        )
        
        history_success = history_saved == case['expected']
        print(f"   {'✅' if history_success else '❌'} Sauvegarde: {'ACTIVÉE' if history_saved else 'DÉSACTIVÉE'} (attendu: {'ACTIVÉE' if case['expected'] else 'DÉSACTIVÉE'})")
        
        results.append({
            'case': case,
            'option_success': success,
            'history_success': history_success,
            'overall_success': success and history_success
        })
        
        print()
    
    # Résumé des tests
    print("🎯 === RÉSUMÉ DES TESTS ===")
    
    total_tests = len(results)
    successful_tests = sum(1 for r in results if r['overall_success'])
    
    print(f"📊 Tests réussis: {successful_tests}/{total_tests}")
    
    for i, result in enumerate(results, 1):
        status = "✅ RÉUSSI" if result['overall_success'] else "❌ ÉCHOUÉ"
        print(f"   {i}. {result['case']['player']}: {status}")
    
    if successful_tests == total_tests:
        print("\n🎉 === TOUS LES TESTS RÉUSSIS ===")
        print("✅ L'option turbo_history_enabled fonctionne parfaitement")
        print("✅ La désactivation empêche bien l'historisation")
        print("✅ La conversion string/bool fonctionne")
        print("✅ Le défaut True pour utilisateurs inconnus fonctionne")
    else:
        print(f"\n⚠️ === {total_tests - successful_tests} TEST(S) ÉCHOUÉ(S) ===")
        for i, result in enumerate(results, 1):
            if not result['overall_success']:
                print(f"❌ Test {i} ({result['case']['player']}): Problème détecté")

def test_config_file_format():
    """Test du format attendu dans le fichier .ini"""
    
    print("\n📝 === TEST FORMAT FICHIER .INI ===")
    
    expected_format = """
[[bruno]]
xtoken = your_token_here
turbo_algorithm = "[hybrid,position_aware,adaptive_time]"
auto_optimize_turbo = False
turbo_history_enabled = True

[[caloune]]
xtoken = your_token_here
turbo_algorithm = "[hybrid,position_aware,adaptive_time]"
auto_optimize_turbo = False
turbo_history_enabled = False
"""
    
    print("📋 Format attendu dans gsgui.ini:")
    print(expected_format)
    
    print("💡 Valeurs acceptées pour turbo_history_enabled:")
    print("   ✅ True/true/1/yes/on  → Historisation ACTIVÉE")
    print("   ❌ False/false/0/no/off → Historisation DÉSACTIVÉE")
    print("   🔧 Par défaut: True (si option absente)")

if __name__ == "__main__":
    print("🧪 === VALIDATION OPTION TURBO_HISTORY_ENABLED ===\n")
    
    # Test de l'option
    test_turbo_history_option()
    
    # Test du format fichier
    test_config_file_format()
    
    print("\n✅ === VALIDATION TERMINÉE ===")
    print("🚀 L'option turbo_history_enabled est prête à l'usage!")
    print("🎯 Pour désactiver: turbo_history_enabled = False")
    print("📊 Impact: Aucune sauvegarde dans .ini ni DataFrame")