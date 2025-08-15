#!/usr/bin/env python3
"""Test script pour la nouvelle architecture hiérarchique"""

import sys
import os
sys.path.append('/Users/bruno/gsgui/backend')

from gs_backend import save_strategy_with_actions
from datetime import datetime, timedelta

# Test: Créer une stratégie unlocked_boost avec structure hiérarchique
challenge_id = "106546"
strategy_name = "unlocked_boost"
profile_id = "bruno"
challenge_title = "Frame within Frame"

# Actions de test
actions = [
    {
        'action': 'unlocked_boost',
        'params': '0',
        'job_id': 'extended_unlocked_boost_106546_20250815_164000_action_0_unlocked_boost',
        'scheduled_at': (datetime.now() + timedelta(minutes=10)).isoformat(),
        'status': 'scheduled',
        'result_message': '',
        'executed_at': ''
    },
    {
        'action': 'vote',
        'params': '100',
        'job_id': 'vote_106546_20250815_164000_action_1_vote',
        'scheduled_at': (datetime.now() + timedelta(minutes=15)).isoformat(),
        'status': 'scheduled',
        'result_message': '',
        'executed_at': ''
    }
]

print("🧪 Test: Sauvegarde stratégie hiérarchique")
success = save_strategy_with_actions(challenge_id, strategy_name, actions, profile_id, challenge_title)

if success:
    print("✅ Stratégie hiérarchique sauvegardée avec succès!")
else:
    print("❌ Échec de sauvegarde de la stratégie hiérarchique")