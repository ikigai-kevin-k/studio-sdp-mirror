#!/bin/bash
# -*- coding: utf-8 -*-
#
# Calculate total lines of code in the codebase
# Excludes common non-code files and directories
#

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================"
echo "Codebase Line Count Analysis"
echo "============================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# File types to count
declare -A FILE_TYPES=(
    ["Python"]="*.py"
    ["JavaScript"]="*.js"
    ["TypeScript"]="*.ts"
    ["Shell"]="*.sh"
    ["JSON"]="*.json"
    ["YAML"]="*.yaml *.yml"
    ["Markdown"]="*.md"
    ["Dockerfile"]="Dockerfile*"
    ["Config"]="*.conf *.config *.ini"
    ["SQL"]="*.sql"
    ["HTML"]="*.html"
    ["CSS"]="*.css"
    ["C/C++"]="*.c *.cpp *.h *.hpp"
    ["Go"]="*.go"
    ["Rust"]="*.rs"
    ["Java"]="*.java"
    ["Other"]="*"
)

# Directories to exclude
EXCLUDE_DIRS=(
    ".git"
    "__pycache__"
    "*.pyc"
    "node_modules"
    ".venv"
    "venv"
    "env"
    ".env"
    "dist"
    "build"
    ".pytest_cache"
    ".mypy_cache"
    ".coverage"
    "htmlcov"
    ".tox"
    "*.egg-info"
    ".idea"
    ".vscode"
    ".cursor"
    "*.log"
    "*.csv"
    "*.xlsx"
    "*.xls"
    "*.pdf"
    "*.jpg"
    "*.jpeg"
    "*.png"
    "*.gif"
    "*.ico"
    "*.svg"
    "*.zip"
    "*.tar"
    "*.gz"
    "*.tar.gz"
    "*.whl"
    "*.pyz"
    "*.pyc"
    "*.pyo"
    "*.pyd"
    ".DS_Store"
    "Thumbs.db"
)

# Build find exclude options
FIND_EXCLUDE=""
for dir in "${EXCLUDE_DIRS[@]}"; do
    FIND_EXCLUDE="$FIND_EXCLUDE -not -path '*/$dir/*' -not -name '$dir'"
done

# Total counters
TOTAL_FILES=0
TOTAL_LINES=0
TOTAL_CODE_LINES=0
TOTAL_COMMENT_LINES=0
TOTAL_BLANK_LINES=0

# Function to count lines in a file
count_lines() {
    local file="$1"
    local lines=$(wc -l < "$file" 2>/dev/null || echo "0")
    local code_lines=0
    local comment_lines=0
    local blank_lines=0
    
    # Count by file type
    case "$file" in
        *.py)
            # Python: count code, comments, and blank lines
            code_lines=$(grep -vE '^\s*(#|$)' "$file" 2>/dev/null | grep -vE '^\s*"""' | grep -vE '^\s*''' | wc -l || echo "0")
            comment_lines=$(grep -E '^\s*#' "$file" 2>/dev/null | wc -l || echo "0")
            blank_lines=$(grep -E '^\s*$' "$file" 2>/dev/null | wc -l || echo "0")
            ;;
        *.js|*.ts)
            # JavaScript/TypeScript
            code_lines=$(grep -vE '^\s*(//|/\*|\*|$)' "$file" 2>/dev/null | wc -l || echo "0")
            comment_lines=$(grep -E '^\s*(//|/\*|\*)' "$file" 2>/dev/null | wc -l || echo "0")
            blank_lines=$(grep -E '^\s*$' "$file" 2>/dev/null | wc -l || echo "0")
            ;;
        *.sh)
            # Shell script
            code_lines=$(grep -vE '^\s*(#|$)' "$file" 2>/dev/null | wc -l || echo "0")
            comment_lines=$(grep -E '^\s*#' "$file" 2>/dev/null | wc -l || echo "0")
            blank_lines=$(grep -E '^\s*$' "$file" 2>/dev/null | wc -l || echo "0")
            ;;
        *)
            # Default: all lines are code
            code_lines=$lines
            blank_lines=$(grep -E '^\s*$' "$file" 2>/dev/null | wc -l || echo "0")
            ;;
    esac
    
    echo "$lines|$code_lines|$comment_lines|$blank_lines"
}

# Count by file type
echo -e "${BLUE}Counting lines by file type:${NC}"
echo ""

declare -A TYPE_COUNTS
declare -A TYPE_LINES
declare -A TYPE_FILES

for type in "${!FILE_TYPES[@]}"; do
    patterns="${FILE_TYPES[$type]}"
    type_files=0
    type_lines=0
    
    for pattern in $patterns; do
        # Use find with exclusions
        while IFS= read -r file; do
            if [ -f "$file" ]; then
                result=$(count_lines "$file")
                IFS='|' read -r lines code comment blank <<< "$result"
                
                type_files=$((type_files + 1))
                type_lines=$((type_lines + lines))
                TOTAL_FILES=$((TOTAL_FILES + 1))
                TOTAL_LINES=$((TOTAL_LINES + lines))
                TOTAL_CODE_LINES=$((TOTAL_CODE_LINES + code))
                TOTAL_COMMENT_LINES=$((TOTAL_COMMENT_LINES + comment))
                TOTAL_BLANK_LINES=$((TOTAL_BLANK_LINES + blank))
            fi
        done < <(eval "find . -type f -name '$pattern' $FIND_EXCLUDE 2>/dev/null")
    done
    
    if [ $type_files -gt 0 ]; then
        TYPE_FILES["$type"]=$type_files
        TYPE_LINES["$type"]=$type_lines
        printf "  %-15s: %6d files, %10s lines\n" "$type" "$type_files" "$(printf "%'d" $type_lines)"
    fi
done

echo ""
echo "============================================================"
echo -e "${GREEN}Summary:${NC}"
echo "============================================================"
printf "  Total Files      : %6d\n" "$TOTAL_FILES"
printf "  Total Lines      : %10s\n" "$(printf "%'d" $TOTAL_LINES)"
printf "  Code Lines       : %10s\n" "$(printf "%'d" $TOTAL_CODE_LINES)"
printf "  Comment Lines    : %10s\n" "$(printf "%'d" $TOTAL_COMMENT_LINES)"
printf "  Blank Lines      : %10s\n" "$(printf "%'d" $TOTAL_BLANK_LINES)"
echo ""

# Top 10 largest files
echo -e "${YELLOW}Top 10 Largest Files:${NC}"
find . -type f $FIND_EXCLUDE 2>/dev/null | while read -r file; do
    if [ -f "$file" ]; then
        lines=$(wc -l < "$file" 2>/dev/null || echo "0")
        echo "$lines|$file"
    fi
done | sort -rn | head -10 | while IFS='|' read -r lines file; do
    printf "  %10s lines : %s\n" "$(printf "%'d" $lines)" "$file"
done

echo ""
echo "============================================================"

