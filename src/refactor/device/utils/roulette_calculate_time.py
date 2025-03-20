import csv
from datetime import datetime
import os
import glob

def calculate_time_from_log(file_path):
    # First, remove any existing analysis files
    existing_files = glob.glob('time_analysis_*.csv')
    for file in existing_files:
        try:
            os.remove(file)
            print(f"已刪除舊的分析檔案：{file}")
        except Exception as e:
            print(f"刪除檔案 {file} 時發生錯誤：{e}")
    
    # Initialize list to store all trial results
    all_trials = []
    
    # Initialize counters for current trial
    current_counters = {
        '2': 0,
        '3': 0,
        '4': 0,
        '5': 0
    }
    
    # Read the file and count lines
    with open(file_path, 'r') as file:
        for line in file:
            # If empty line, save current trial and reset counters
            if line.strip() == "":
                if any(current_counters.values()):  # Only save if there's data
                    all_trials.append(current_counters.copy())
                    current_counters = {
                        '2': 0,
                        '3': 0,
                        '4': 0,
                        '5': 0
                    }
                continue
                
            # Check if line contains '*X;' pattern
            if '*X;' in line:
                # Split the line and get the number after '*X;'
                parts = line.split(';')
                if len(parts) >= 2:
                    number = parts[1]
                    if number in current_counters:
                        current_counters[number] += 1
    
    # Add the last trial if it has data
    if any(current_counters.values()):
        all_trials.append(current_counters)
    
    # Generate timestamp for CSV filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f'time_analysis_{timestamp}.csv'
    
    # Write results to CSV with restructured format
    with open(csv_filename, 'w', newline='') as csvfile:
        # Define new column headers
        fieldnames = ['Trial', '*X;2', '*X;3', '*X;4', '*X;5']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        # Write each trial as a single row
        for trial_num, trial_data in enumerate(all_trials, 1):
            row_data = {'Trial': trial_num}
            for number, count in trial_data.items():
                seconds = count / 2
                row_data[f'*X;{number}'] = seconds
            writer.writerow(row_data)
    
    # Print results to console
    print("分析結果：")
    for trial_num, trial_data in enumerate(all_trials, 1):
        print(f"\n試驗 {trial_num}:")
        for number, count in trial_data.items():
            seconds = count / 2
            print(f"*X;{number} 出現 {count} 行，相當於 {seconds} 秒")
    
    print(f"\n結果已儲存至：{csv_filename}")

# 使用範例
file_path = 'calculate_time.log'
calculate_time_from_log(file_path)