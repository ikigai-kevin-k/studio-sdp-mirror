import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.dates import DateFormatter
import matplotlib.dates as mdates
from scipy import stats

# Set font for displaying Chinese characters if needed
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei']
plt.rcParams['axes.unicode_minus'] = False

# Read CSV file, assuming the first row is the header
try:
    # Try to read the CSV file, specify column names
    df = pd.read_csv('time_intervals_data.csv', 
                     names=['timestamp', 'col1', 'col2', 'col3', 'col4', 'col5'],
                     header=None)
    
    # Check if the first row is a header
    if 'Timestamp' in str(df.iloc[0, 0]) or 'timestamp' in str(df.iloc[0, 0]):
        df = df.iloc[1:].reset_index(drop=True)  # If yes, remove the first row
    
    # Convert timestamp column to datetime objects, explicitly specify format
    df['timestamp'] = pd.to_datetime(df['timestamp'], format='%Y-%m-%d %H:%M:%S.%f')
    
    # Convert other columns to numeric type
    for col in df.columns[1:]:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Check and handle missing values
    print(f"Number of missing values in the data:\n{df.isna().sum()}")
    df = df.dropna()  # Remove rows with missing values
    
    # Rename columns for better understanding
    df = df.rename(columns={
        'col1': 'finish_to_start',
        'col2': 'start_to_launch',
        'col3': 'launch_to_deal',
        'col4': 'deal_to_finish',
        'col5': 'total_time'
    })
    
    print(f"Dataset size: {df.shape}")
    print(f"Dataset time range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    
    # Basic statistical information
    print("\nBasic statistical information:")
    print(df.describe())
    
    # Set chart style
    sns.set(style="whitegrid")
    plt.figure(figsize=(15, 10))
    
    # 1. Plot time series - all columns
    fig, axes = plt.subplots(5, 1, figsize=(15, 20), sharex=True)
    
    # Set date formatter
    date_form = DateFormatter("%H:%M")
    
    columns_to_plot = df.columns[1:]
    for i, col in enumerate(columns_to_plot):
        axes[i].plot(df['timestamp'], df[col], label=col, linewidth=1.5)
        axes[i].set_title(f'{col} Over Time', fontsize=14)
        axes[i].set_ylabel('Time (seconds)', fontsize=12)
        axes[i].legend(loc='upper right')
        axes[i].xaxis.set_major_formatter(date_form)
        axes[i].xaxis.set_major_locator(mdates.HourLocator(interval=1))
        axes[i].grid(True, linestyle='--', alpha=0.7)
    
    plt.xlabel('Time', fontsize=12)
    plt.tight_layout()
    plt.savefig('time_series_all_columns.png')
    
    # 2. Plot total time series with outliers marked
    plt.figure(figsize=(15, 8))
    
    # Calculate Z-scores to detect outliers
    z_scores = np.abs(stats.zscore(df['total_time']))
    outliers = z_scores > 3  # Z-score > 3 is considered an outlier
    
    plt.plot(df['timestamp'], df['total_time'], label='Total Time', linewidth=1.5, color='blue')
    plt.scatter(df.loc[outliers, 'timestamp'], df.loc[outliers, 'total_time'], 
                color='red', label='Outliers', s=50, zorder=5)
    
    plt.title('Total Processing Time Over Time (with Outliers)', fontsize=16)
    plt.xlabel('Time', fontsize=14)
    plt.ylabel('Time (seconds)', fontsize=14)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    plt.gca().xaxis.set_major_formatter(date_form)
    plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=1))
    plt.tight_layout()
    plt.savefig('total_time_with_outliers.png')
    
    # 3. Plot boxplot to compare distributions of each column
    plt.figure(figsize=(12, 8))
    sns.boxplot(data=df[columns_to_plot])
    plt.title('Distribution Comparison of Processing Stages', fontsize=16)
    plt.ylabel('Time (seconds)', fontsize=14)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig('boxplot_comparison.png')
    
    # 4. Plot correlation heatmap
    plt.figure(figsize=(10, 8))
    correlation_matrix = df[columns_to_plot].corr()
    sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', fmt='.2f', linewidths=0.5)
    plt.title('Correlation Analysis of Processing Stages', fontsize=16)
    plt.tight_layout()
    plt.savefig('correlation_heatmap.png')
    
    # 5. Plot moving average (for total time)
    plt.figure(figsize=(15, 8))
    
    # Calculate moving average (window size = 10)
    window_size = 10
    df['total_time_moving_avg'] = df['total_time'].rolling(window=window_size).mean()
    
    plt.plot(df['timestamp'], df['total_time'], label='Original Total Time', alpha=0.5, linewidth=1, color='blue')
    plt.plot(df['timestamp'], df['total_time_moving_avg'], label=f'{window_size}-point Moving Average', 
             linewidth=2, color='red')
    
    plt.title('Total Processing Time Trend Analysis (Moving Average)', fontsize=16)
    plt.xlabel('Time', fontsize=14)
    plt.ylabel('Time (seconds)', fontsize=14)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    plt.gca().xaxis.set_major_formatter(date_form)
    plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=1))
    plt.tight_layout()
    plt.savefig('moving_average.png')
    
    # 6. Plot scatter plot of start_to_launch vs launch_to_deal
    plt.figure(figsize=(10, 8))
    plt.scatter(df['start_to_launch'], df['launch_to_deal'], alpha=0.6)
    plt.title('Start to Launch Time vs Launch to Deal Time', fontsize=16)
    plt.xlabel('Start to Launch Time (seconds)', fontsize=14)
    plt.ylabel('Launch to Deal Time (seconds)', fontsize=14)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig('start_to_launch_vs_launch_to_deal.png')
    
    # 7. Plot hourly average processing time
    df['hour'] = df['timestamp'].dt.hour
    hourly_avg = df.groupby('hour')[columns_to_plot].mean()
    
    plt.figure(figsize=(15, 8))
    for col in columns_to_plot:
        plt.plot(hourly_avg.index, hourly_avg[col], marker='o', label=col)
    
    plt.title('Hourly Average Processing Time', fontsize=16)
    plt.xlabel('Hour', fontsize=14)
    plt.ylabel('Average Time (seconds)', fontsize=14)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    plt.xticks(range(min(df['hour']), max(df['hour'])+1))
    plt.tight_layout()
    plt.savefig('hourly_average.png')
    
    print("Visualization analysis completed, charts have been saved.")
    
except Exception as e:
    print(f"Error occurred while processing data: {e}")