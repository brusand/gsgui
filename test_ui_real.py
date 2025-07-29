#!/usr/bin/env python3
"""
Test de l'interface réelle avec affichage 
"""

import sys
import asyncio
sys.path.append('/Users/bruno/gsgui/src/gs')
from PySide6.QtWidgets import QApplication
from gsui_simple import SimpleGSGUI
import qasync

async def main():
    """Test interface réelle"""
    app = QApplication(sys.argv)
    
    # Event loop
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    # Window
    window = SimpleGSGUI()
    window.show()
    
    print("🎨 Interface affichée - Utilisez le bouton Refresh!")
    print("📋 Pour fermer: Ctrl+C ou fermez la fenêtre")
    
    # Auto-refresh au démarrage
    await asyncio.sleep(1)
    await window.refresh_challenges()
    
    # Run until closed
    try:
        with loop:
            await loop.run_until_complete(asyncio.Event().wait())
    except KeyboardInterrupt:
        print("\n👋 Au revoir")

if __name__ == "__main__":
    asyncio.run(main())