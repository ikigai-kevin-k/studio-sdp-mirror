#!/usr/bin/env python3
"""
Script to rename log files from SBO001_{mmdd}_complete.log to sbo_{yyyy-mm-dd}.log
Uses file modification time to determine the year.
"""

import os
import re
from pathlib import Path
from datetime import datetime


def parse_mmdd_from_filename(filename):
    """
    Extract mmdd from filename like SBO001_1006_complete.log
    Returns (month, day) tuple or None if pattern doesn't match
    """
    # Pattern: SBO001_{mmdd}_complete.log
    pattern = r'SBO001_(\d{4})_complete\.log'
    match = re.match(pattern, filename)
    if match:
        mmdd = match.group(1)
        month = int(mmdd[:2])
        day = int(mmdd[2:])
        return month, day
    return None


def get_year_from_file_mtime(file_path):
    """
    Get year from file modification time
    """
    mtime = os.path.getmtime(file_path)
    return datetime.fromtimestamp(mtime).year


def rename_log_file(old_path, dry_run=True):
    """
    Rename a log file from SBO001_{mmdd}_complete.log to sbo_{yyyy-mm-dd}.log
    
    Args:
        old_path: Path object for the old file
        dry_run: If True, only print what would be done without actually renaming
    
    Returns:
        True if successful, False otherwise
    """
    filename = old_path.name
    month_day = parse_mmdd_from_filename(filename)
    
    if month_day is None:
        print(f'  ⚠️  Skipping {filename}: pattern does not match')
        return False
    
    month, day = month_day
    
    # Validate month and day
    if month < 1 or month > 12:
        print(f'  ⚠️  Skipping {filename}: invalid month {month}')
        return False
    
    if day < 1 or day > 31:
        print(f'  ⚠️  Skipping {filename}: invalid day {day}')
        return False
    
    # Get year from file modification time
    try:
        year = get_year_from_file_mtime(old_path)
    except Exception as e:
        print(f'  ⚠️  Skipping {filename}: cannot get file mtime: {e}')
        return False
    
    # Generate new filename: sbo_{yyyy-mm-dd}.log
    new_filename = f'sbo_{year}-{month:02d}-{day:02d}.log'
    new_path = old_path.parent / new_filename
    
    # Check if target file already exists
    if new_path.exists():
        print(f'  ⚠️  Skipping {filename}: target {new_filename} already exists')
        return False
    
    if dry_run:
        print(f'  📝 Would rename: {filename} -> {new_filename}')
    else:
        try:
            old_path.rename(new_path)
            print(f'  ✅ Renamed: {filename} -> {new_filename}')
            return True
        except Exception as e:
            print(f'  ❌ Error renaming {filename}: {e}')
            return False
    
    return True


def main():
    """
    Main function to rename all matching log files
    """
    logs_dir = Path('logs')
    
    if not logs_dir.exists():
        print(f'Error: Directory {logs_dir} does not exist')
        return
    
    # Find all SBO001_{mmdd}_complete.log files
    pattern = 'SBO001_*_complete.log'
    log_files = sorted(logs_dir.glob(pattern))
    
    if not log_files:
        print('No SBO001_*_complete.log files found')
        return
    
    print(f'Found {len(log_files)} log files to rename\n')
    print('=' * 60)
    print('DRY RUN MODE - No files will be renamed')
    print('=' * 60)
    print()
    
    # First pass: dry run
    success_count = 0
    for log_file in log_files:
        if rename_log_file(log_file, dry_run=True):
            success_count += 1
    
    print()
    print('=' * 60)
    print(f'Summary: {success_count}/{len(log_files)} files can be renamed')
    print('=' * 60)
    print()
    
    # Ask for confirmation
    if success_count > 0:
        response = input('Do you want to proceed with renaming? (yes/no): ')
        if response.lower() in ['yes', 'y']:
            print()
            print('=' * 60)
            print('RENAMING FILES...')
            print('=' * 60)
            print()
            
            success_count = 0
            for log_file in log_files:
                if rename_log_file(log_file, dry_run=False):
                    success_count += 1
            
            print()
            print('=' * 60)
            print(f'✅ Renamed {success_count} files successfully!')
            print('=' * 60)
        else:
            print('Cancelled. No files were renamed.')
    else:
        print('No files to rename.')


if __name__ == '__main__':
    main()

