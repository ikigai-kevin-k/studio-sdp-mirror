#!/usr/bin/env python3
"""
測試美化後的 API 輸出
"""

import json


def simulate_api_response():
    """模擬你的 API 響應"""
    return {
        "error": None,
        "data": {
            "table": {
                "gameCode": "BCR-001",
                "gameType": "auto-sic-bo",
                "visibility": "hidden",
                "betPeriod": 5,
                "name": "",
                "pause": {
                    "reason": "dev",
                    "createdAt": "2025-08-22T06:21:20.972Z",
                    "createdBy": "SDP",
                },
                "streams": {},
                "autopilot": {},
                "sdpConfig": {},
                "tableRound": {
                    "roundId": "BCR-001-20250822-061148",
                    "gameCode": "BCR-001",
                    "gameType": "auto-sic-bo",
                    "betStopTime": "2025-08-22T06:11:53.103Z",
                    "status": "bet-txn-stopped",
                    "createdAt": "2025-08-22T06:11:48.104Z",
                    "result": {},
                },
                "metadata": {},
            }
        },
    }


def test_original_vs_beautified():
    """測試原始輸出 vs 美化輸出"""
    print("🚀 API Response 美化測試")
    print("=" * 60)

    # 模擬 API 響應
    response_data = simulate_api_response()

    print("❌ 原始輸出 (醜陋):")
    print("-" * 30)
    print(response_data)

    print("\n✅ 美化輸出 (易讀):")
    print("-" * 30)
    print("=== BCR API Response ===")
    print(json.dumps(response_data, indent=2, ensure_ascii=False))

    print("\n🎯 關鍵信息提取:")
    print("-" * 30)
    if "data" in response_data and "table" in response_data["data"]:
        table = response_data["data"]["table"]
        round_info = table.get("tableRound", {})

        print(f"Game Code: {table.get('gameCode')}")
        print(f"Game Type: {table.get('gameType')}")
        print(f"Bet Period: {table.get('betPeriod')} seconds")
        print(f"Round ID: {round_info.get('roundId')}")
        print(f"Status: {round_info.get('status')}")
        print(f"Pause Reason: {table.get('pause', {}).get('reason')}")


if __name__ == "__main__":
    test_original_vs_beautified()
