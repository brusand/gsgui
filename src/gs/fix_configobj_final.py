#!/usr/bin/env python3
"""
Fix ConfigObj structure issues in gsgui.ini file - Final version.
ConfigObj only supports 2-level nesting: [section] -> [[subsection]]
Three levels like [section] -> [[subsection]] -> [[subsubsection]] are not allowed.
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
                print(f"Fixed: [[process]] -> [process]")
                
            elif subsection_name == 'caloune':
                # Check if we need to create a players section context
                if current_section != 'players':
                    # We need to implicitly be in players section
                    current_section = 'players'
                    
                fixed_lines.append('[[caloune]]\n')
                current_subsection = 'caloune'
                print(f"Fixed: [[caloune]] as player subsection")
                    
            elif subsection_name == 'scheduled_strategies':
                # Handle duplicate scheduled_strategies
                if current_section == 'players' and current_subsection:
                    # This is under a player - keep it
                    fixed_lines.append(line + '\n')
                    print(f"Kept [[scheduled_strategies]] under player {current_subsection}")
                elif current_section == 'players' and not current_subsection:
                    # This is under players but no specific player
                    fixed_lines.append(line + '\n')
                    print(f"Kept [[scheduled_strategies]] under players section")
                else:
                    # Skip duplicate at wrong level
                    print(f"Skipping duplicate [[scheduled_strategies]] at line {i+1}")
                    i += 1
                    continue
                    
            elif subsection_name in ['photo1', 'photo2', 'winner', 'scores']:
                # These cause 3-level nesting issue in ConfigObj
                # Convert them to regular key-value pairs or flatten structure
                if current_section == 'turbo_history':
                    # Skip these subsections and convert their content to key-value pairs
                    print(f"Converting [[{subsection_name}]] to flattened structure")
                    
                    # Read ahead to get the content of this subsection
                    j = i + 1
                    subsection_content = []
                    while j < len(lines) and not lines[j].strip().startswith('['):
                        if lines[j].strip() and '=' in lines[j]:
                            key, value = lines[j].strip().split('=', 1)
                            # Flatten by prefixing with subsection name
                            flattened_line = f"{subsection_name}_{key.strip()} = {value.strip()}\n"
                            subsection_content.append(flattened_line)
                        j += 1
                    
                    # Add the flattened content
                    fixed_lines.extend(subsection_content)
                    
                    # Skip ahead past this subsection
                    i = j - 1  # -1 because we'll increment at the end of the loop
                else:
                    # Keep as-is if not in problematic context
                    fixed_lines.append(line + '\n')
                    
            elif re.match(r'^\d+$', subsection_name):
                # Numeric subsections (challenge IDs) 
                fixed_lines.append(line + '\n')
                print(f"Kept numeric subsection [[{subsection_name}]]")
                    
            else:
                # Regular subsection
                if current_section == 'players':
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
    output_path = file_path.replace('.ini', '_final_fixed.ini')
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
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    input_file = "/Users/bruno/gsgui/src/gs/gsgui.ini"
    
    print("Fixing gsgui.ini ConfigObj structure (final version)...")
    fixed_file = fix_gsgui_ini(input_file)
    
    print("\nTesting ConfigObj parsing...")
    if test_configobj_parsing(fixed_file):
        print("\n✓ Success! The file can now be parsed by ConfigObj.")
        print(f"You can replace the original file with: {fixed_file}")
    else:
        print("\n✗ The fix still has issues. Manual intervention may be needed.")