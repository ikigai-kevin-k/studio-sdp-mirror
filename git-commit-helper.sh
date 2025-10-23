#!/bin/bash

# Git Commit Helper Script for SDP Roulette
# 這個腳本幫助您選擇性地跳過 CI/CD 流程

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to show usage
show_usage() {
    echo "Git Commit Helper for SDP Roulette"
    echo ""
    echo "用法: $0 [選項] <commit message>"
    echo ""
    echo "選項:"
    echo "  -s, --skip-ci     跳過 CI/CD 流程 (使用 [skip-ci] 標記)"
    echo "  -n, --no-build    跳過建置流程 (使用 [no-build] 標記)"
    echo "  -h, --help        顯示此說明"
    echo ""
    echo "範例:"
    echo "  $0 \"Update documentation\""
    echo "  $0 -s \"Fix typo in comments\""
    echo "  $0 --no-build \"Minor code cleanup\""
    echo ""
    echo "注意: 這些選項只對 dev/ella/deploy 分支有效"
}

# Function to check if we're on the correct branch
check_branch() {
    local current_branch=$(git branch --show-current)
    if [[ "$current_branch" != "dev/ella/deploy" ]]; then
        print_color $YELLOW "警告: 您目前不在 dev/ella/deploy 分支上"
        print_color $YELLOW "當前分支: $current_branch"
        print_color $YELLOW "CI/CD 控制標記只對 dev/ella/deploy 分支有效"
        echo ""
    fi
}

# Function to perform git commit
do_commit() {
    local message="$1"
    local skip_ci="$2"
    local no_build="$3"
    
    local final_message="$message"
    
    if [[ "$skip_ci" == "true" ]]; then
        final_message="$message [skip-ci]"
        print_color $BLUE "將使用標記: [skip-ci]"
    elif [[ "$no_build" == "true" ]]; then
        final_message="$message [no-build]"
        print_color $BLUE "將使用標記: [no-build]"
    else
        print_color $GREEN "將正常觸發 CI/CD 流程"
    fi
    
    echo ""
    print_color $YELLOW "Commit message: $final_message"
    echo ""
    
    read -p "確認執行 git commit? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if git commit -m "$final_message"; then
            print_color $GREEN "✓ Commit 成功完成!"
            
            if [[ "$skip_ci" == "true" || "$no_build" == "true" ]]; then
                print_color $BLUE "✓ CI/CD 流程將被跳過"
            else
                print_color $GREEN "✓ CI/CD 流程將正常執行"
            fi
        else
            print_color $RED "✗ Commit 失敗"
            exit 1
        fi
    else
        print_color $YELLOW "Commit 已取消"
        exit 0
    fi
}

# Main script logic
main() {
    local skip_ci=false
    local no_build=false
    local commit_message=""
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -s|--skip-ci)
                skip_ci=true
                shift
                ;;
            -n|--no-build)
                no_build=true
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            -*)
                print_color $RED "錯誤: 未知選項 $1"
                show_usage
                exit 1
                ;;
            *)
                if [[ -z "$commit_message" ]]; then
                    commit_message="$1"
                else
                    commit_message="$commit_message $1"
                fi
                shift
                ;;
        esac
    done
    
    # Check if commit message is provided
    if [[ -z "$commit_message" ]]; then
        print_color $RED "錯誤: 請提供 commit message"
        show_usage
        exit 1
    fi
    
    # Check if both options are specified
    if [[ "$skip_ci" == "true" && "$no_build" == "true" ]]; then
        print_color $RED "錯誤: 不能同時使用 --skip-ci 和 --no-build"
        exit 1
    fi
    
    # Check if we're in a git repository
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        print_color $RED "錯誤: 當前目錄不是 git 倉庫"
        exit 1
    fi
    
    # Check if there are staged changes
    if ! git diff --cached --quiet; then
        print_color $YELLOW "警告: 沒有 staged 的變更"
        print_color $YELLOW "請先使用 'git add' 來 stage 您的變更"
        exit 1
    fi
    
    # Check branch
    check_branch
    
    # Perform commit
    do_commit "$commit_message" "$skip_ci" "$no_build"
}

# Run main function with all arguments
main "$@"
