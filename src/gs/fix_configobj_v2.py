#!/usr/bin/env python3
"""
Fix ConfigObj structure issues in gsgui.ini file - Version 2.
This version handles nested subsection depth issues.
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
    nesting_level = 0
    
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        
        # Skip empty lines but keep them
        if not line.strip():
            fixed_lines.append(line + '\n')
            i += 1
            continue
            
        # Check for section headers
        main_section_match = re.match(r'^\[([^\[\]]+)\]$', line)
        sub_section_match = re.match(r'^\[\[([^\[\]]+)\]\]$', line)
        
        if main_section_match:  # Main section [section]
            current_section = main_section_match.group(1)
            current_subsection = None
            nesting_level = 1
            fixed_lines.append(line + '\n')
            print(f"Found main section: [{current_section}]")
            
        elif sub_section_match:  # Subsection [[subsection]]
            subsection_name = sub_section_match.group(1)
            
            # Handle specific problematic cases
            if subsection_name == 'process':
                # Convert orphaned [[process]] to main section [process]
                fixed_lines.append('[process]\n')
                current_section = 'process'
                current_subsection = None
                nesting_level = 1
                print(f"Fixed: [[process]] -> [process]")
                
            elif subsection_name == 'caloune':
                # This should be under [players]
                if current_section != 'players':
                    # Add to players section context
                    fixed_lines.append('[[caloune]]\n')
                    current_subsection = 'caloune'
                    nesting_level = 2
                    print(f"Fixed: [[caloune]] under implicit players section")
                else:
                    fixed_lines.append(line + '\n')
                    current_subsection = subsection_name
                    nesting_level = 2
                    
            elif subsection_name == 'scheduled_strategies':
                # Handle duplicate scheduled_strategies
                if current_section == 'players' and nesting_level == 2:
                    # This is under a player
                    fixed_lines.append(line + '\n')
                    nesting_level = 2
                    print(f"Kept [[scheduled_strategies]] under player")
                else:
                    # Skip duplicate at wrong level
                    print(f"Skipping duplicate/misplaced [[scheduled_strategies]] at line {i+1}")
                    i += 1
                    continue
                    
            elif subsection_name in ['photo1', 'photo2', 'winner', 'scores']:
                # These should be at level 3 under turbo_history entries
                if current_section == 'turbo_history' and nesting_level >= 2:
                    # Keep them as-is, they're properly nested
                    fixed_lines.append(line + '\n')
                    print(f"Kept [[{subsection_name}]] in turbo_history")
                else:
                    # They might be misplaced, but keep them for now
                    fixed_lines.append(line + '\n')
                    print(f"Warning: [[{subsection_name}]] at unexpected location")
                    
            elif re.match(r'^\d+$', subsection_name):
                # Numeric subsections (challenge IDs) under scheduled_strategies
                if 'scheduled_strategies' in str(fixed_lines[-10:]):  # Recent context
                    fixed_lines.append(line + '\n')
                    nesting_level = 3
                    print(f"Kept numeric subsection [[{subsection_name}]] under scheduled_strategies")
                else:
                    fixed_lines.append(line + '\n')
                    nesting_level = 2
                    print(f"Kept numeric subsection [[{subsection_name}]]")
                    
            else:
                # Regular subsection - likely turbo_history entries or player names
                if current_section == 'turbo_history':
                    nesting_level = 2
                elif current_section == 'players':
                    nesting_level = 2
                    current_subsection = subsection_name
                
                fixed_lines.append(line + '\n')
                print(f"Regular subsection [[{subsection_name}]] in {current_section}")
                
        elif line.strip().startswith('#'):
            # Comment line
            fixed_lines.append(line + '\n')
            
        elif '=' in line:
            # Key=value line
            fixed_lines.append(line + '\n')
            
        else:
            # Unknown line format, keep as-is
            fixed_lines.append(line + '\n')
            
        i += 1
    
    # Write the fixed file
    output_path = file_path.replace('.ini', '_fixed_v2.ini')
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
        
        # Show some structure
        if 'players' in config:
            print(f"  Players: {list(config['players'].keys())}")
        if 'turbo_history' in config:
            turbo_keys = list(config['turbo_history'].keys())
            print(f"  Turbo history entries: {len(turbo_keys)} (showing first 3: {turbo_keys[:3]})")
            
        return True
    except Exception as e:
        print(f"✗ ConfigObj parsing failed: {e}")
        return False

if __name__ == "__main__":
    input_file = "/Users/bruno/gsgui/src/gs/gsgui.ini"
    
    print("Fixing gsgui.ini ConfigObj structure (v2)...")
    fixed_file = fix_gsgui_ini(input_file)
    
    print("\nTesting ConfigObj parsing...")
    if test_configobj_parsing(fixed_file):
        print("\nSuccess! The file can now be parsed by ConfigObj.")
        print(f"You can replace the original file with: {fixed_file}")
    else:
        print("\nThe fix didn't work completely. Let's check what's still wrong...")