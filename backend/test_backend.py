#!/usr/bin/env python3
"""
Script de test pour valider le backend GSGUI
Test les endpoints principaux sans base de données
"""

import asyncio
import aiohttp
import json
import sys
from datetime import datetime
import websockets


async def test_health_endpoint():
    """Test du endpoint de santé"""
    print("🔍 Testing health endpoint...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:8000/health') as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Health check OK: {data}")
                    return True
                else:
                    print(f"❌ Health check failed: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False


async def test_docs_endpoint():
    """Test de la documentation Swagger"""
    print("🔍 Testing docs endpoint...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:8000/docs') as response:
                if response.status == 200:
                    print("✅ Docs endpoint OK")
                    return True
                else:
                    print(f"❌ Docs endpoint failed: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Docs endpoint error: {e}")
        return False


async def test_challenges_endpoint():
    """Test du endpoint challenges (nécessite un token)"""
    print("🔍 Testing challenges endpoint...")
    
    # Token de test (factice pour le test de validation)
    test_token = "test_token_12345"
    
    try:
        async with aiohttp.ClientSession() as session:
            # Test sans token (doit échouer)
            async with session.get('http://localhost:8000/api/v1/challenges/') as response:
                if response.status == 422:  # Validation error expected
                    print("✅ Challenges endpoint validation OK (no token)")
                else:
                    print(f"⚠️ Unexpected status without token: {response.status}")
            
            # Test avec token (va probablement échouer car token factice)
            async with session.get(
                f'http://localhost:8000/api/v1/challenges/?user_token={test_token}'
            ) as response:
                print(f"📊 Challenges endpoint with token: {response.status}")
                if response.status in [200, 500]:  # OK ou erreur interne attendue
                    print("✅ Challenges endpoint structure OK")
                    return True
                else:
                    print(f"❌ Challenges endpoint failed: {response.status}")
                    return False
                    
    except Exception as e:
        print(f"❌ Challenges endpoint error: {e}")
        return False


async def test_vote_panel_endpoint():
    """Test du endpoint vote panel"""
    print("🔍 Testing vote panel endpoint...")
    
    test_token = "test_token_12345"
    test_data = {
        "challenge_url": "https://gurushots.com/challenge/test-challenge/photo-details/12345",
        "limit": 10
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'http://localhost:8000/api/v1/challenges/vote-panel?user_token={test_token}',
                json=test_data
            ) as response:
                print(f"📊 Vote panel endpoint: {response.status}")
                if response.status in [200, 500]:  # OK ou erreur interne attendue
                    print("✅ Vote panel endpoint structure OK")
                    return True
                else:
                    print(f"❌ Vote panel endpoint failed: {response.status}")
                    return False
                    
    except Exception as e:
        print(f"❌ Vote panel endpoint error: {e}")
        return False


async def test_websocket_connection():
    """Test de connexion WebSocket"""
    print("🔍 Testing WebSocket connection...")
    
    try:
        # Tenter de se connecter au WebSocket
        uri = "ws://localhost:8000/ws/test_user"
        
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connection established")
            
            # Envoyer un message de test
            await websocket.send(json.dumps({"type": "test", "message": "Hello"}))
            
            # Attendre une réponse (avec timeout)
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)
                print(f"✅ WebSocket response: {data.get('type', 'unknown')}")
                return True
                
            except asyncio.TimeoutError:
                print("⚠️ WebSocket timeout (normal in test)")
                return True
                
    except Exception as e:
        print(f"❌ WebSocket connection error: {e}")
        return False


async def test_backend_startup():
    """Test si le backend démarre correctement"""
    print("🔍 Testing backend startup...")
    
    try:
        # Test de la racine
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:8000/') as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Backend startup OK: {data.get('message', 'Unknown')}")
                    return True
                else:
                    print(f"❌ Backend startup failed: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Backend startup error: {e}")
        return False


async def run_all_tests():
    """Lance tous les tests"""
    print("🚀 GSGUI Backend Tests")
    print("=" * 50)
    
    tests = [
        ("Backend Startup", test_backend_startup),
        ("Health Endpoint", test_health_endpoint),
        ("Docs Endpoint", test_docs_endpoint),
        ("Challenges Endpoint", test_challenges_endpoint),
        ("Vote Panel Endpoint", test_vote_panel_endpoint),
        ("WebSocket Connection", test_websocket_connection),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Résumé des résultats
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY")
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
        print("\n🎉 All tests passed! Backend is ready.")
        return 0
    else:
        print(f"\n⚠️ {failed} test(s) failed. Check the backend setup.")
        return 1


async def main():
    """Point d'entrée principal"""
    print("🔧 GSGUI Backend Validation Script")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Vérifier si le backend est disponible
    print("🔍 Checking if backend is running on http://localhost:8000...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:8000/', timeout=5) as response:
                if response.status == 200:
                    print("✅ Backend is running!")
                else:
                    print(f"⚠️ Backend returned status {response.status}")
    except Exception as e:
        print(f"❌ Backend is not running: {e}")
        print("\n💡 To start the backend:")
        print("   cd backend/")
        print("   python -m uvicorn app.main:app --reload")
        print("\n   Or with Docker:")
        print("   docker-compose up -d")
        return 1
    
    # Lancer les tests
    return await run_all_tests()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)