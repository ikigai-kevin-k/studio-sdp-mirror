#!/usr/bin/env python3
"""
Basic Python code obfuscation script
Removes comments and compresses whitespace while preserving docstrings
"""

import re
import sys
import os


def obfuscate_python_file(file_path):
    """Obfuscate a single Python file"""
    try:
        # Read the file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Remove single-line comments (but preserve docstrings)
        lines = content.split('\n')
        processed_lines = []
        in_docstring = False
        docstring_char = None

        for line in lines:
            stripped = line.strip()
            
            # Check for docstring start/end
            if not in_docstring:
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    in_docstring = True
                    docstring_char = stripped[:3]
                    processed_lines.append(line)
                    continue
            else:
                if stripped.endswith(docstring_char):
                    in_docstring = False
                    docstring_char = None
                    processed_lines.append(line)
                    continue
            
            # If not in docstring, remove comments
            if not in_docstring:
                # Remove comments but preserve strings
                in_string = False
                string_char = None
                new_line = ''
                i = 0
                
                while i < len(line):
                    char = line[i]
                    
                    if not in_string and char in ['"', "'"]:
                        in_string = True
                        string_char = char
                        new_line += char
                    elif in_string and char == string_char:
                        # Check if it's escaped
                        if i > 0 and line[i-1] != '\\':
                            in_string = False
                            string_char = None
                        new_line += char
                    elif not in_string and char == '#':
                        # Found comment, stop processing this line
                        break
                    else:
                        new_line += char
                    
                    i += 1
                
                # Compress whitespace
                new_line = re.sub(r'[ \t]+', ' ', new_line)
                processed_lines.append(new_line)
            else:
                processed_lines.append(line)

        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(processed_lines))
            
        print(f"✅ Obfuscated: {file_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error obfuscating {file_path}: {e}")
        return False


def main():
    """Main function"""
    if len(sys.argv) != 2:
        print("Usage: python obfuscate.py <file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} does not exist")
        sys.exit(1)
    
    success = obfuscate_python_file(file_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
