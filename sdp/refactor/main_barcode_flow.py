import asyncio
import logging
import json
import time
from typing import Optional
import requests
import argparse
import os
import logging.handlers

from controller import GameConfig, GameType
from deviceController import BarcodeController
from los_api.api import start_post, deal_post, finish_post, get_roundID, resume_post

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BarcodeTest:
    def __init__(self, device_path: str):
        self.logger = logging.getLogger("BarcodeTest")
        self.device_path = device_path
        
        # LOS API configuration
        self.game_code = 'SDP-001'
        self.token = 'E5LN4END9Q'
        self.get_url = f'https://crystal-los.iki-cit.cc/v1/service/table/{self.game_code}'
        self.post_url = f'https://crystal-los.iki-cit.cc/v1/service/sdp/table/{self.game_code}'
        
        # Initialize controllers
        self.config = GameConfig(
            game_type=GameType.SICBO,
            room_id=self.game_code,
            broker_host="",  # Not needed for this test
            broker_port=0    # Not needed for this test
        )
        self.barcode_controller = BarcodeController(self.config)

    async def process_barcode(self, barcode: str):
        """處理掃描到的條碼"""
        self.logger.info(f"Processing barcode: {barcode}")
        if len(barcode) == 3 and barcode != "NOREAD":  # 有效的條碼結果
            self.last_barcode = barcode
            self.barcode_received = True

    async def run_test(self):
        """執行測試流程"""
        self.logger.info("Starting barcode test flow...")
        
        # 初始化條碼掃描器
        await self.barcode_controller.initialize(
            device_path=self.device_path,
            callback=self.process_barcode
        )

        while True:
            try:
                # 檢查上一局的狀態
                self.logger.info("Checking previous round status...")
                try:
                    round_id, status, bet_period = get_roundID(self.get_url, self.token)
                    self.logger.info(f"round_id: {round_id}, status: {status}, bet_period: {bet_period}")
                    
                    # 如果上一局停在 bet-stopped，需要先完成該局
                    if status == "bet-stopped":
                        self.logger.info("Detected incomplete previous round, cleaning up...")
                        resume_post(self.post_url, self.token)
                        deal_post(self.post_url, self.token, round_id, [-1])
                        finish_post(self.post_url, self.token)
                        self.logger.info("Previous round cleanup completed")
                        await asyncio.sleep(2)
                except Exception as e:
                    self.logger.error(f"Error checking previous round: {e}")
                    await asyncio.sleep(5)
                    continue

                # 開始新的回合
                self.logger.info("Starting new round...")
                round_id, bet_period = start_post(self.post_url, self.token)
                self.logger.info(f"New round started: {round_id}")

                if round_id == -1:
                    self.logger.error("Failed to start new round")
                    await asyncio.sleep(5)
                    continue

                # 等待下注時間
                self.logger.info(f"Waiting for betting period ({bet_period} seconds)...")
                await asyncio.sleep(bet_period)

                # 等待掃描結果
                self.logger.info("Waiting for barcode scan...")
                self.barcode_received = False
                self.last_barcode = None
                
                # 等待最多10秒獲取掃描結果
                timeout = 10
                start_time = time.time()
                while not self.barcode_received and (time.time() - start_time) < timeout:
                    await asyncio.sleep(0.1)

                if self.barcode_received and self.last_barcode:
                    self.logger.info(f"Received valid barcode: {self.last_barcode}")
                    
                    # 將條碼結果轉換為數字列表（例如：'KH1' -> [11, 8, 1]）
                    # 這裡需要根據您的實際需求調整轉換邏輯
                    result = [ord(c) % 6 + 1 for c in self.last_barcode]
                    
                    # 發送結果到 LOS API
                    self.logger.info(f"Sending deal result to LOS API: {result}")
                    deal_post(self.post_url, self.token, round_id, result)
                    
                    # 等待結果顯示
                    await asyncio.sleep(4)
                    
                    # 結束回合
                    self.logger.info("Finishing round...")
                    finish_post(self.post_url, self.token)
                    
                else:
                    self.logger.error("Timeout waiting for barcode scan")
                    # 發送預設結果
                    deal_post(self.post_url, self.token, round_id, [-1, -1, -1])
                    finish_post(self.post_url, self.token)

                # 等待下一輪開始
                await asyncio.sleep(2)

            except Exception as e:
                self.logger.error(f"Error in test flow: {e}")
                await asyncio.sleep(5)

    async def cleanup(self):
        """清理資源"""
        await self.barcode_controller.cleanup()

async def main():
    parser = argparse.ArgumentParser(description='Barcode Scanner Test')
    parser.add_argument('device_path', help='Path to the HID device (e.g., /dev/hidraw0)')
    args = parser.parse_args()

    test = BarcodeTest(args.device_path)
    try:
        await test.run_test()
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test error: {e}")
    finally:
        await test.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
