#!/usr/bin/env python3
"""
Create a minimal working version of gsgui.ini that ConfigObj can parse.
This version focuses on the essential structure while removing problematic nesting.
"""

import re
from pathlib import Path

def create_minimal_working_ini():
    """Create a minimal working gsgui.ini file."""
    
    # Read the original file to extract the essential data
    with open('gsgui.ini.backup', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Extract key information
    player_name = None
    players_data = {}
    current_player = None
    current_section = None
    
    # Parse to extract essential structure
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Find player name from first line
        if i == 0 and '=' in line:
            key, value = line.split('=', 1)
            if key.strip() == 'player':
                player_name = value.strip()
        
        # Track sections
        if re.match(r'^\[([^\[\]]+)\]$', line):
            current_section = re.match(r'^\[([^\[\]]+)\]$', line).group(1)
            current_player = None
        elif re.match(r'^\[\[([^\[\]]+)\]\]$', line):
            subsection = re.match(r'^\[\[([^\[\]]+)\]\]$', line).group(1)
            if current_section == 'players':
                current_player = subsection
                if current_player not in players_data:
                    players_data[current_player] = {}
        elif '=' in line and current_section == 'players' and current_player:
            key, value = line.split('=', 1)
            players_data[current_player][key.strip()] = value.strip()
    
    # Create minimal working file
    minimal_content = []
    
    # Add player name if found
    if player_name:
        minimal_content.append(f"player = {player_name}\n")
    
    # Add players section
    minimal_content.append("\n[players]\n")
    for player, data in players_data.items():
        minimal_content.append(f"[[{player}]]\n")
        for key, value in data.items():
            if key != 'scheduled_strategies':  # Skip problematic nested structures
                minimal_content.append(f"{key} = {value}\n")
    
    # Add process section (converted from problematic [[process]])
    minimal_content.append("\n[process]\n")
    minimal_content.append("# Process configuration section\n")
    
    # Add turbo_history section (simplified)
    minimal_content.append("\n[turbo_history]\n")
    minimal_content.append("# Turbo history data has been simplified to avoid ConfigObj parsing issues\n")
    minimal_content.append("# Original nested structure was too deep for ConfigObj (3+ levels)\n")
    
    # Write the minimal file
    with open('gsgui_minimal_working.ini', 'w', encoding='utf-8') as f:
        f.writelines(minimal_content)
    
    print("Created minimal working gsgui.ini file:")
    print(f"- Player name: {player_name}")
    print(f"- Players found: {list(players_data.keys())}")
    print(f"- File: gsgui_minimal_working.ini")
    
    return 'gsgui_minimal_working.ini'

def test_minimal_file(filename):
    """Test the minimal file with ConfigObj."""
    try:
        from configobj import ConfigObj
        config = ConfigObj(filename, encoding='utf-8')
        print(f"\n✓ SUCCESS! ConfigObj can parse {filename}")
        print(f"Main sections: {list(config.keys())}")
        if 'players' in config:
            print(f"Players: {list(config['players'].keys())}")
        return True
    except Exception as e:
        print(f"\n✗ Failed to parse {filename}: {e}")
        return False

if __name__ == "__main__":
    print("Creating minimal working gsgui.ini...")
    filename = create_minimal_working_ini()
    
    print("\nTesting with ConfigObj...")
    if test_minimal_file(filename):
        print(f"\nYou now have a working ConfigObj-compatible file: {filename}")
        print("This file contains the essential structure without the problematic 3-level nesting.")
        print("You can use this as a base and add back functionality as needed.")
    else:
        print("\nStill having issues with the minimal file.")