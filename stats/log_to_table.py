import pandas as pd
import re


def parse_log_file(file_path):
    # 初始化列表來存儲數據
    timestamps = []
    finish_to_start = []
    start_to_launch = []
    launch_to_deal = []
    deal_to_finish = []

    # 讀取日誌文件
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 使用正則表達式分割每個回合的數據
    rounds = re.split(r"-{50}", content)

    for round_data in rounds:
        if not round_data.strip():
            continue

        # 提取時間戳
        timestamp_match = re.search(r"\[(.*?)\]", round_data)
        if timestamp_match:
            timestamps.append(timestamp_match.group(1))

        # 提取各個時間間隔
        for line in round_data.split("\n"):
            if "finish_to_start_time:" in line:
                finish_to_start.append(float(line.split(": ")[1]))
            elif "start_to_launch_time:" in line:
                start_to_launch.append(float(line.split(": ")[1]))
            elif "launch_to_deal_time:" in line:
                launch_to_deal.append(float(line.split(": ")[1]))
            elif "deal_to_finish_time:" in line:
                deal_to_finish.append(float(line.split(": ")[1]))

    # 創建 DataFrame
    df = pd.DataFrame(
        {
            "Timestamp": timestamps,
            "Finish to Start (s)": [round(x, 2) for x in finish_to_start],
            "Start to Launch (s)": [round(x, 2) for x in start_to_launch],
            "Launch to Deal (s)": [round(x, 2) for x in launch_to_deal],
            "Deal to Finish (s)": [round(x, 2) for x in deal_to_finish],
        }
    )

    # 計算總時間
    df["Total Time (s)"] = df.iloc[:, 1:5].sum(axis=1).round(2)

    # 計算統計數據
    stats = pd.DataFrame(
        {
            "Mean": [round(x, 2) for x in df.iloc[:, 1:6].mean()],
            "Median": [round(x, 2) for x in df.iloc[:, 1:6].median()],
            "Min": [round(x, 2) for x in df.iloc[:, 1:6].min()],
            "Max": [round(x, 2) for x in df.iloc[:, 1:6].max()],
            "Std": [round(x, 2) for x in df.iloc[:, 1:6].std()],
        }
    )

    return df, stats


def main():
    # 解析日誌文件
    df, stats = parse_log_file("time_intervals-2api.log")

    # 輸出原始數據表格
    print("\n=== 時間間隔數據表 ===")
    print(df.to_string(index=False))

    # 輸出統計數據
    print("\n=== 統計數據 ===")
    print(stats.to_string())

    # 將結果保存到 CSV 文件
    df.to_csv("time_intervals_data.csv", index=False)
    stats.to_csv("time_intervals_stats.csv")

    print(
        "\n分析結果已保存到 time_intervals_data.csv 和 time_intervals_stats.csv"
    )


if __name__ == "__main__":
    main()
