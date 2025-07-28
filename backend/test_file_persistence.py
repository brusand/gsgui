#!/usr/bin/env python3
"""
Script de test pour la persistance fichier
Teste la création et récupération d'utilisateurs et challenges via les fichiers .ini
"""

import os
import sys
import asyncio
from pathlib import Path

# Ajouter le chemin de l'app au PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.models.file_based_models import User, Challenge, Strategy, TurboHistory
from app.services.config_manager import config_manager


def test_directory_setup():
    """Test de la création du répertoire data"""
    print("🔍 Testing directory setup...")
    
    # Créer le répertoire data s'il n'existe pas
    data_dir = Path("data")
    if not data_dir.exists():
        data_dir.mkdir()
        print("✅ Created data directory")
    else:
        print("✅ Data directory exists")
    
    return True


def test_user_creation():
    """Test de création d'utilisateur"""
    print("🔍 Testing user creation...")
    
    try:
        # Créer un utilisateur test
        user = User.create(
            user_id="test_user_123",
            username="test_user",
            xtoken="test_token_abcdef123456789",
            turbo_algorithm="bruno_custom",
            auto_optimize_turbo=True
        )
        
        if user:
            print(f"✅ User created: {user.username} (ID: {user.id})")
            return True
        else:
            print("❌ Failed to create user")
            return False
            
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        return False


def test_user_retrieval():
    """Test de récupération d'utilisateur"""
    print("🔍 Testing user retrieval...")
    
    try:
        # Récupérer par ID
        user_by_id = User.get_by_id("test_user_123")
        if user_by_id:
            print(f"✅ Retrieved user by ID: {user_by_id.username}")
        else:
            print("❌ Could not retrieve user by ID")
            return False
        
        # Récupérer par token
        user_by_token = User.get_by_token("test_token_abcdef123456789")
        if user_by_token:
            print(f"✅ Retrieved user by token: {user_by_token.username}")
        else:
            print("❌ Could not retrieve user by token")
            return False
        
        # Vérifier que c'est le même utilisateur
        if user_by_id.id == user_by_token.id:
            print("✅ Both retrieval methods return the same user")
            return True
        else:
            print("❌ Different users returned by ID and token")
            return False
            
    except Exception as e:
        print(f"❌ Error retrieving user: {e}")
        return False


def test_challenge_persistence():
    """Test de persistance des challenges"""
    print("🔍 Testing challenge persistence...")
    
    try:
        user = User.get_by_id("test_user_123")
        if not user:
            print("❌ No test user found")
            return False
        
        # Créer un challenge de test
        from datetime import datetime, timedelta
        
        challenge = Challenge.create_from_api_data(
            user_id=user.id,
            api_challenge_data={
                'id': 'test_challenge_456',
                'title': 'Test Challenge',
                'url': 'https://gurushots.com/test-challenge',
                'end_time': datetime.now() + timedelta(days=1),
                'time_left': {'days': 1, 'hours': 2, 'minutes': 30, 'seconds': 15},
                'votes': 150,
                'rank': 25,
                'level': 'Challenger',
                'exposure': 1000,
                'gps': 0
            }
        )
        
        challenge.selected_strategy = 'end4'
        challenge.status = 'active'
        
        # Sauvegarder
        if challenge.save():
            print("✅ Challenge saved successfully")
        else:
            print("❌ Failed to save challenge")
            return False
        
        # Récupérer les challenges de l'utilisateur
        user_challenges = user.get_challenges()
        if 'test_challenge_456' in user_challenges:
            saved_challenge = user_challenges['test_challenge_456']
            print(f"✅ Challenge retrieved: {saved_challenge.get('challenge_title', 'Unknown')}")
            print(f"   Strategy: {saved_challenge.get('strategy_name', 'None')}")
            print(f"   Status: {saved_challenge.get('status', 'None')}")
            return True
        else:
            print("❌ Challenge not found in user challenges")
            return False
            
    except Exception as e:
        print(f"❌ Error with challenge persistence: {e}")
        return False


def test_strategy_management():
    """Test de gestion des stratégies"""
    print("🔍 Testing strategy management...")
    
    try:
        # Récupérer une stratégie par défaut
        end4_strategy = Strategy.get_by_name('end4')
        if end4_strategy:
            print(f"✅ Retrieved strategy: {end4_strategy.name}")
            print(f"   Description: {end4_strategy.description}")
            print(f"   Steps: {len(end4_strategy.config)}")
        else:
            print("❌ Could not retrieve end4 strategy")
            return False
        
        # Lister toutes les stratégies
        all_strategies = Strategy.list_all()
        print(f"✅ Found {len(all_strategies)} strategies")
        
        for strategy in all_strategies:
            print(f"   - {strategy.name}: {strategy.description}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error with strategy management: {e}")
        return False


def test_turbo_history():
    """Test de l'historique turbo"""
    print("🔍 Testing turbo history...")
    
    try:
        user = User.get_by_id("test_user_123")
        if not user:
            print("❌ No test user found")
            return False
        
        # Créer une entrée turbo de test
        turbo_data = {
            'challenge_id': 'test_challenge_456',
            'challenge_title': 'Test Challenge',
            'time_left': '1D 2H 30M 15S',
            'algorithm': 'bruno_custom',
            'strategy_description': 'Test strategy description',
            'success': True,
            'photo1_id': 'photo1_abc123',
            'photo1_ratio': 1.33,
            'photo1_votes': 200,
            'photo1_rank': 50,
            'photo1_found': True,
            'photo2_id': 'photo2_def456',
            'photo2_ratio': 1.5,
            'photo2_votes': 180,
            'photo2_rank': 60,
            'photo2_found': True,
            'winner_id': 'photo1_abc123',
            'is_photo1_winner': True
        }
        
        turbo_entry = TurboHistory.create(user.id, turbo_data)
        
        if turbo_entry.save():
            print("✅ Turbo history saved successfully")
        else:
            print("❌ Failed to save turbo history")
            return False
        
        # Récupérer l'historique
        history = TurboHistory.get_user_history(user.id, limit=5)
        if history:
            print(f"✅ Retrieved {len(history)} turbo history entries")
            for entry in history:
                print(f"   - Challenge: {entry.challenge_title}, Algorithm: {entry.algorithm}, Success: {entry.success}")
            return True
        else:
            print("❌ No turbo history found")
            return False
            
    except Exception as e:
        print(f"❌ Error with turbo history: {e}")
        return False


def test_file_contents():
    """Test du contenu des fichiers générés"""
    print("🔍 Testing generated file contents...")
    
    try:
        # Vérifier que les fichiers existent
        config_file = Path("data/gsgui.ini")
        strategies_file = Path("data/strategies.ini")
        
        if config_file.exists():
            print("✅ gsgui.ini file exists")
            # Lire quelques lignes pour vérifier
            with open(config_file, 'r') as f:
                first_lines = f.readlines()[:5]
                print("   First lines:")
                for line in first_lines:
                    print(f"     {line.strip()}")
        else:
            print("❌ gsgui.ini file not found")
            return False
        
        if strategies_file.exists():
            print("✅ strategies.ini file exists")
        else:
            print("❌ strategies.ini file not found")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking file contents: {e}")
        return False


def test_config_manager_stats():
    """Test des statistiques du config manager"""
    print("🔍 Testing config manager stats...")
    
    try:
        stats = config_manager.get_stats()
        print("✅ Config manager stats:")
        print(f"   Users: {stats.get('users_count', 0)}")
        print(f"   Strategies: {stats.get('strategies_count', 0)}")
        print(f"   Turbo history: {stats.get('turbo_history_count', 0)}")
        print(f"   Config file: {stats.get('config_file', 'Unknown')}")
        print(f"   Strategies file: {stats.get('strategies_file', 'Unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error getting stats: {e}")
        return False


async def run_all_tests():
    """Lance tous les tests de persistance fichier"""
    print("🚀 GSGUI File Persistence Tests")
    print("=" * 50)
    
    tests = [
        ("Directory Setup", test_directory_setup),
        ("User Creation", test_user_creation),
        ("User Retrieval", test_user_retrieval),
        ("Challenge Persistence", test_challenge_persistence),
        ("Strategy Management", test_strategy_management),
        ("Turbo History", test_turbo_history),
        ("File Contents", test_file_contents),
        ("Config Manager Stats", test_config_manager_stats),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Résumé
    print("\n" + "=" * 50)
    print("📊 FILE PERSISTENCE TEST RESULTS")
    print("=" * 50)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:<25} {status}")
        
        if result:
            passed += 1
        else:
            failed += 1
    
    print("-" * 50)
    print(f"Total: {len(results)} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 All file persistence tests passed!")
        print("💡 The backend is ready for file-based deployment!")
        return 0
    else:
        print(f"\n⚠️ {failed} test(s) failed. Check the implementation.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)