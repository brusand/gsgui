#!/usr/bin/env python3
"""
Test de connexion au backend
"""

import sys
import asyncio
import aiohttp

async def test_connection():
    """Test simple de connexion"""
    
    print("🔍 Test de connexion au backend...")
    
    try:
        # Test avec aiohttp (comme l'interface)
        async with aiohttp.ClientSession() as session:
            url = "http://localhost:8001/"
            print(f"🔌 Connexion à {url}...")
            
            async with session.get(url) as response:
                print(f"✅ Status: {response.status}")
                data = await response.json()
                print(f"✅ Réponse: {data}")
                
        # Test API challenges
        token = "a1cad95a6d480c14f51dd0eba4914c8337b893c789ec6278bb440c7c9a673b162f042470c62684e6da2bd342ffea7777"
        
        async with aiohttp.ClientSession() as session:
            url = f"http://localhost:8001/api/v1/challenges/?user_token={token}"
            print(f"🔌 Test API challenges: {url}")
            
            async with session.get(url) as response:
                print(f"✅ Status: {response.status}")
                data = await response.json()
                challenges = data.get('challenges', [])
                print(f"✅ Challenges: {len(challenges)}")
                
    except Exception as e:
        print(f"❌ Erreur: {e}")
        print(f"❌ Type: {type(e)}")

if __name__ == "__main__":
    asyncio.run(test_connection())