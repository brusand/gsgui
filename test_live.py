#!/usr/bin/env python3
"""
Test en temps réel - Voir ce qui se passe exactement
"""

import sys
import asyncio
import time
sys.path.append('/Users/bruno/gsgui/src/gs')
from PySide6.QtWidgets import QApplication
from gsui_simple import SimpleGSGUI
import qasync

class LiveTester:
    def __init__(self):
        self.window = None
        
    async def test_step_by_step(self):
        """Test étape par étape avec logs"""
        
        print("=" * 60)
        print("🧪 TEST EN TEMPS RÉEL - Interface GSGUI")
        print("=" * 60)
        
        # 1. Créer l'application
        print("1️⃣ Création application Qt...")
        app = QApplication(sys.argv)
        loop = qasync.QEventLoop(app)
        asyncio.set_event_loop(loop)
        print("   ✅ Application Qt créée")
        
        # 2. Créer la fenêtre
        print("\n2️⃣ Création fenêtre SimpleGSGUI...")
        self.window = SimpleGSGUI()
        print(f"   ✅ Fenêtre créée")
        print(f"   👤 Profil: {self.window.player}")
        print(f"   🔑 Token: {'Oui' if self.window.user_token else 'Non'}")
        
        # 3. Afficher la fenêtre
        print("\n3️⃣ Affichage fenêtre...")
        self.window.show()
        print("   ✅ Fenêtre affichée")
        
        # 4. Attendre un peu
        print("\n4️⃣ Attente initialisation (3 secondes)...")
        await asyncio.sleep(3)
        
        # 5. Vérifier l'état
        print("\n5️⃣ État actuel:")
        print(f"   📋 Challenges dans dict: {len(self.window.challenges)}")
        print(f"   📋 Items dans liste: {self.window.challenge_list.count()}")
        
        # 6. Test refresh manuel
        print("\n6️⃣ Test refresh manuel...")
        try:
            await self.window.refresh_challenges()
            print("   ✅ Refresh terminé")
        except Exception as e:
            print(f"   ❌ Erreur refresh: {e}")
        
        # 7. État final
        print("\n7️⃣ État final:")
        print(f"   📋 Challenges dans dict: {len(self.window.challenges)}")
        print(f"   📋 Items dans liste: {self.window.challenge_list.count()}")
        
        if self.window.challenge_list.count() > 0:
            print("   📋 Contenu de la liste:")
            for i in range(self.window.challenge_list.count()):
                item = self.window.challenge_list.item(i)
                print(f"      {i+1}. {item.text()}")
        else:
            print("   ❌ PROBLÈME: Aucun item dans la liste!")
        
        # 8. Vérification visuelle
        print("\n8️⃣ Interface visible à l'écran")
        print("   👀 Regardez l'écran - voyez-vous la fenêtre GSGUI ?")
        print("   👀 Y a-t-il des challenges affichés dans la liste ?")
        
        # Garder l'interface ouverte 10 secondes
        print("\n⏰ Interface reste ouverte 10 secondes pour inspection...")
        for i in range(10, 0, -1):
            print(f"   ⏰ Fermeture dans {i}s...", end='\r')
            await asyncio.sleep(1)
        
        print("\n\n" + "=" * 60)
        print("🎯 Test terminé")
        
        app.quit()

async def main():
    tester = LiveTester()
    await tester.test_step_by_step()

if __name__ == "__main__":
    # S'assurer que le backend est démarré
    import subprocess
    import requests
    
    try:
        response = requests.get("http://localhost:8001/", timeout=2)
        print("✅ Backend accessible")
    except:
        print("🚀 Démarrage backend...")
        subprocess.Popen([sys.executable, "backend_simple.py"], 
                        cwd="/Users/bruno/gsgui",
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL)
        time.sleep(3)
    
    asyncio.run(main())