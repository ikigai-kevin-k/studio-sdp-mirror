#!/usr/bin/env python3
"""
JSON 格式化工具
用於美化 API response 輸出
"""

import json
import sys
from typing import Any, Dict, List, Union
from datetime import datetime


class JSONFormatter:
    """JSON 格式化器"""
    
    def __init__(self, indent: int = 2, width: int = 80, sort_keys: bool = True):
        """
        初始化格式化器
        
        Args:
            indent: 縮進空格數
            width: 最大行寬
            sort_keys: 是否排序鍵
        """
        self.indent = indent
        self.width = width
        self.sort_keys = sort_keys
    
    def format_json(self, data: Any, title: str = None) -> str:
        """
        格式化 JSON 數據
        
        Args:
            data: 要格式化的數據
            title: 可選的標題
            
        Returns:
            格式化後的字串
        """
        try:
            # 如果是字符串，嘗試解析為 JSON
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except json.JSONDecodeError:
                    return f"原始字符串:\n{data}"
            
            # 格式化 JSON
            formatted = json.dumps(
                data, 
                indent=self.indent, 
                ensure_ascii=False, 
                sort_keys=self.sort_keys
            )
            
            # 添加標題
            if title:
                return f"=== {title} ===\n{formatted}"
            else:
                return formatted
                
        except Exception as e:
            return f"格式化失敗: {e}\n原始數據: {data}"
    
    def print_json(self, data: Any, title: str = None, color: bool = True):
        """
        直接打印格式化的 JSON
        
        Args:
            data: 要格式化的數據
            title: 可選的標題
            color: 是否使用顏色
        """
        formatted = self.format_json(data, title)
        
        if color:
            # 添加顏色 (如果支援)
            try:
                from colorama import init, Fore, Style
                init()
                print(f"{Fore.CYAN}{formatted}{Style.RESET_ALL}")
            except ImportError:
                print(formatted)
        else:
            print(formatted)
    
    def print_table(self, data: Union[Dict, List], title: str = None):
        """
        以表格形式輸出數據
        
        Args:
            data: 要輸出的數據
            title: 可選的標題
        """
        if title:
            print(f"\n{'='*50}")
            print(f"  {title}")
            print(f"{'='*50}")
        
        if isinstance(data, dict):
            self._print_dict_table(data)
        elif isinstance(data, list):
            self._print_list_table(data)
        else:
            print(f"不支援的數據類型: {type(data)}")
    
    def _print_dict_table(self, data: Dict):
        """以表格形式輸出字典"""
        if not data:
            print("(空字典)")
            return
        
        # 計算最大鍵長度
        max_key_len = max(len(str(k)) for k in data.keys())
        
        for key, value in data.items():
            key_str = str(key).ljust(max_key_len)
            
            if isinstance(value, (dict, list)):
                print(f"{key_str}: {type(value).__name__}")
                # 遞歸輸出複雜類型
                self.print_json(value, f"  {key}", color=False)
            else:
                print(f"{key_str}: {value}")
    
    def _print_list_table(self, data: List):
        """以表格形式輸出列表"""
        if not data:
            print("(空列表)")
            return
        
        print(f"列表長度: {len(data)}")
        for i, item in enumerate(data):
            if isinstance(item, (dict, list)):
                print(f"[{i}]: {type(item).__name__}")
                self.print_json(item, f"  項目 {i}", color=False)
            else:
                print(f"[{i}]: {item}")


def print_beautiful_json(data: Any, title: str = None, indent: int = 2):
    """
    快速美化輸出 JSON
    
    Args:
        data: 要格式化的數據
        title: 可選的標題
        indent: 縮進空格數
    """
    formatter = JSONFormatter(indent=indent)
    formatter.print_json(data, title)


def print_json_table(data: Any, title: str = None):
    """
    以表格形式輸出 JSON 數據
    
    Args:
        data: 要輸出的數據
        title: 可選的標題
    """
    formatter = JSONFormatter()
    formatter.print_table(data, title)


def format_api_response(response_data: Any, title: str = "API Response") -> str:
    """
    格式化 API response
    
    Args:
        response_data: API 響應數據
        title: 響應標題
        
    Returns:
        格式化後的字串
    """
    formatter = JSONFormatter(indent=2, sort_keys=True)
    return formatter.format_json(response_data, title)


# 使用範例
if __name__ == "__main__":
    # 測試數據
    sample_data = {
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
                    "createdBy": "SDP"
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
                    "result": {}
                },
                "metadata": {}
            }
        }
    }
    
    print("=== 美化 JSON 輸出 ===")
    print_beautiful_json(sample_data, "API Response")
    
    print("\n=== 表格形式輸出 ===")
    print_json_table(sample_data, "API Response")
