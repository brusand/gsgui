#!/usr/bin/env python3
"""
Fix ConfigObj structure issues in gsgui.ini file.
"""

import re
import sys
from pathlib import Path

def fix_gsgui_ini(file_path):
    """Fix structural issues in gsgui.ini file."""
    
    # Read the file
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f"Original file has {len(lines)} lines")
    
    fixed_lines = []
    current_section = None
    current_subsection = None
    in_players_section = False
    
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        
        # Track what section we're in
        if re.match(r'^\[([^\[\]]+)\]$', line):  # Main section [section]
            section_match = re.match(r'^\[([^\[\]]+)\]$', line)
            current_section = section_match.group(1)
            current_subsection = None
            in_players_section = current_section == 'players'
            fixed_lines.append(line + '\n')
            print(f"Found main section: [{current_section}]")
            
        elif re.match(r'^\[\[([^\[\]]+)\]\]$', line):  # Subsection [[subsection]]
            subsection_match = re.match(r'^\[\[([^\[\]]+)\]\]$', line)
            subsection_name = subsection_match.group(1)
            
            # Handle specific problematic cases
            if subsection_name == 'process':
                # Convert orphaned [[process]] to main section [process]
                fixed_lines.append('[process]\n')
                current_section = 'process'
                current_subsection = None
                in_players_section = False
                print(f"Fixed: [[process]] -> [process]")
                
            elif subsection_name == 'caloune':
                # This should be under [players]
                if current_section != 'players':
                    # We're not in players section, so this is orphaned
                    # Add it to players section
                    fixed_lines.append('[[caloune]]\n')
                    current_subsection = 'caloune'
                    in_players_section = True
                    print(f"Fixed: orphaned [[caloune]] kept as player subsection")
                else:
                    fixed_lines.append(line + '\n')
                    current_subsection = subsection_name
                    
            elif subsection_name == 'scheduled_strategies':
                # Handle duplicate scheduled_strategies
                if current_section == 'players' and current_subsection:
                    # This is the second scheduled_strategies under a player
                    fixed_lines.append(line + '\n')
                    print(f"Kept [[scheduled_strategies]] under player {current_subsection}")
                elif current_section == 'players' and not current_subsection:
                    # This is the first scheduled_strategies under bruno
                    # Find the previous player subsection
                    fixed_lines.append(line + '\n')
                    print(f"Kept [[scheduled_strategies]] under players section")
                else:
                    # This might be orphaned, skip it or handle appropriately
                    print(f"Skipping duplicate [[scheduled_strategies]] at line {i+1}")
                    i += 1
                    continue
                    
            else:
                # Regular subsection
                fixed_lines.append(line + '\n')
                current_subsection = subsection_name
                
        else:
            # Regular line (key=value or empty)
            fixed_lines.append(line + '\n')
            
        i += 1
    
    # Write the fixed file
    output_path = file_path.replace('.ini', '_fixed.ini')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)
    
    print(f"Fixed file written to: {output_path}")
    print(f"Fixed file has {len(fixed_lines)} lines")
    
    return output_path

def test_configobj_parsing(file_path):
    """Test if the fixed file can be parsed by ConfigObj."""
    try:
        from configobj import ConfigObj
        config = ConfigObj(file_path, encoding='utf-8')
        print(f"✓ ConfigObj parsing successful!")
        print(f"  Main sections: {list(config.keys())}")
        return True
    except Exception as e:
        print(f"✗ ConfigObj parsing failed: {e}")
        return False

if __name__ == "__main__":
    input_file = "/Users/bruno/gsgui/src/gs/gsgui.ini"
    
    print("Fixing gsgui.ini ConfigObj structure...")
    fixed_file = fix_gsgui_ini(input_file)
    
    print("\nTesting ConfigObj parsing...")
    if test_configobj_parsing(fixed_file):
        print("\nSuccess! The file can now be parsed by ConfigObj.")
        print(f"You can replace the original file with: {fixed_file}")
    else:
        print("\nThe fix didn't work completely. Manual intervention may be needed.")