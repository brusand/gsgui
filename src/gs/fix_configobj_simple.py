#!/usr/bin/env python3
"""
Simple fix for ConfigObj structure issues in gsgui.ini file.
This version removes all problematic 3-level nesting by converting deep subsections to flat key-value pairs.
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
    skip_lines = 0
    
    i = 0
    while i < len(lines):
        if skip_lines > 0:
            skip_lines -= 1
            i += 1
            continue
            
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
            fixed_lines.append(line + '\n')
            print(f"Kept main section: {line}")
            
        elif sub_section_match:  # Subsection [[subsection]]
            subsection_name = sub_section_match.group(1)
            
            # Handle specific problematic cases
            if subsection_name == 'process':
                # Convert to main section
                fixed_lines.append('[process]\n')
                print(f"Fixed: [[process]] -> [process]")
                
            elif subsection_name in ['photo1', 'photo2', 'winner', 'scores']:
                # Convert to flattened key-value pairs
                print(f"Flattening [[{subsection_name}]]...")
                
                # Read the content of this subsection
                j = i + 1
                while j < len(lines) and not lines[j].strip().startswith('['):
                    content_line = lines[j].strip()
                    if content_line and '=' in content_line:
                        # Convert to flattened format
                        key, value = content_line.split('=', 1)
                        flattened_key = f"{subsection_name}_{key.strip()}"
                        fixed_lines.append(f"{flattened_key} = {value.strip()}\n")
                    elif content_line:
                        # Non key=value line, keep as comment
                        fixed_lines.append(f"# {content_line}\n")
                    else:
                        fixed_lines.append('\n')
                    j += 1
                
                # Skip all the lines we just processed
                skip_lines = j - i - 1
                
            else:
                # Regular subsection - keep as-is
                fixed_lines.append(line + '\n')
                
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
    output_path = file_path.replace('.ini', '_simple_fixed.ini')
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
            print(f"  Turbo history entries: {len(turbo_keys)} (first 3: {turbo_keys[:3]})")
            
        return True
    except Exception as e:
        print(f"✗ ConfigObj parsing failed: {e}")
        # Show the specific line that's causing issues
        if "line" in str(e):
            line_num = re.search(r'line (\d+)', str(e))
            if line_num:
                line_num = int(line_num.group(1))
                print(f"Error at line {line_num}:")
                with open(file_path, 'r') as f:
                    lines = f.readlines()
                    if line_num <= len(lines):
                        print(f"  {line_num}: {lines[line_num-1].rstrip()}")
        return False

if __name__ == "__main__":
    input_file = "/Users/bruno/gsgui/src/gs/gsgui.ini"
    
    print("Fixing gsgui.ini ConfigObj structure (simple approach)...")
    fixed_file = fix_gsgui_ini(input_file)
    
    print("\nTesting ConfigObj parsing...")
    if test_configobj_parsing(fixed_file):
        print("\n✓ Success! The file can now be parsed by ConfigObj.")
        print(f"You can replace the original file with: {fixed_file}")
    else:
        print("\n✗ The fix still has issues. Checking for remaining problems...")