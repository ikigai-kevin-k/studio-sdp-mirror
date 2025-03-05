import logging
import json
import asyncio
from typing import Optional, Tuple, List
from dataclasses import dataclass
import time
from mqtt_wrapper import MQTTLogger
from controller import Controller, GameConfig

class IDPController(Controller):
    """Controls IDP (Image Detection Processing) operations"""
    def __init__(self, config: GameConfig):
        super().__init__(config)
        self.mqtt_client = MQTTLogger(
            client_id=f"idp_controller_{config.room_id}",
            broker=config.broker_host,
            port=config.broker_port
        )
        self.response_received = False
        self.last_response = None
        self.dice_result = None

    async def initialize(self):
        """Initialize IDP controller"""
        if not self.mqtt_client.connect():
            raise Exception("Failed to connect to MQTT broker")
        self.mqtt_client.start_loop()
        
        # 設置訊息處理回調
        self.mqtt_client.client.on_message = self._on_message
        self.mqtt_client.subscribe("ikg/idp/dice/response")

    def _on_message(self, client, userdata, message):
        """Handle received messages"""
        try:
            payload = message.payload.decode()
            self.logger.info(f"Received message on {message.topic}: {payload}")
            
            # 處理訊息
            self._process_message(message.topic, payload)
            
        except Exception as e:
            self.logger.error(f"Error in _on_message: {e}")

    def _process_message(self, topic, payload):
        """Process received message"""
        try:
            self.logger.info(f"Processing message from {topic}: {payload}")
            
            if topic == "ikg/idp/dice/response":
                response_data = json.loads(payload)
                if "response" in response_data and response_data["response"] == "result":
                    if "arg" in response_data and "res" in response_data["arg"]:
                        dice_result = response_data["arg"]["res"]
                        # 檢查是否為有效的骰子結果 (三個數字)
                        if isinstance(dice_result, list) and len(dice_result) == 3 and all(isinstance(x, int) for x in dice_result):
                            self.dice_result = dice_result
                            self.response_received = True
                            self.last_response = payload
                            self.logger.info(f"Got valid dice result: {self.dice_result}")
                            return  # 立即返回，不再等待更多結果
                        else:
                            self.logger.info(f"Received invalid result: {dice_result}, continuing to wait...")
                    
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse message JSON: {e}")
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")

    def detect(self, round_id: str) -> Tuple[bool, Optional[list]]:
        """Send detect command and wait for response"""
        try:
            # 重置狀態
            self.response_received = False
            self.last_response = None
            self.dice_result = None
            
            command = {
                "command": "detect",
                "arg": {
                    "round_id": round_id,
                    "input": "rtmp://192.168.88.213:1935/live/r456_dice",
                    "output": "https://pull-tc.stream.iki-utl.cc/live/r456_dice.flv"
                }
            }
            
            # 設定超時時限
            timeout = 4 # for demo
            start_time = asyncio.get_event_loop().time()
            retry_interval = 4  
            attempt = 1
            
            while (asyncio.get_event_loop().time() - start_time) < timeout:
                # 發送檢測命令
                self.logger.info(f"Sending detect command (attempt {attempt})")
                self.mqtt_client.publish("ikg/idp/dice/command", json.dumps(command))
                
                # 等待回應的小循環
                wait_end = min(
                    start_time + timeout,  # 不超過總超時時間
                    asyncio.get_event_loop().time() + retry_interval  # 下次重試前的等待時間
                )
                
                while asyncio.get_event_loop().time() < wait_end:
                    if self.dice_result is not None:
                        self.logger.info(f"Received dice result on attempt {attempt}: {self.dice_result}")
                        return True, self.dice_result
                    #  asyncio.sleep(0.05)  # 短暫休眠，避免 CPU 過度使用
                    time.sleep(0.5)
                
                attempt += 1
            
            # 超時處理
            elapsed = asyncio.get_event_loop().time() - start_time
            self.logger.warning(f"No valid response received within {elapsed:.2f}s after {attempt-1} attempts")
            command = {
                "command": "timeout",
                "arg":{
                }
            }
            self.mqtt_client.publish("ikg/idp/dice/command", json.dumps(command))
            if self.last_response:
                self.logger.warning(f"Last response was: {self.last_response}")
            return True, [""]  # 超時時返回預設值
            
        except Exception as e:
            self.logger.error(f"Error in detect: {e}")
            return False, None

    async def cleanup(self):
        """Cleanup IDP controller resources"""
        self.mqtt_client.stop_loop()
        self.mqtt_client.disconnect()

class ShakerController(Controller):
    """Controls dice shaker operations"""
    def __init__(self, config: GameConfig):
        super().__init__(config)
        # Use different MQTT settings for shaker
        self.mqtt_client = MQTTLogger(
            client_id=f"shaker_controller_{config.room_id}",
            broker="192.168.88.250",  # Specific broker for shaker
            port=config.broker_port
        )
        self.mqtt_client.client.username_pw_set("PFC", "wago")  # Specific credentials for shaker

    async def initialize(self):
        """Initialize shaker controller"""
        if not self.mqtt_client.connect():
            raise Exception("Failed to connect to MQTT broker")
        self.mqtt_client.start_loop()
        self.mqtt_client.subscribe("ikg/shaker/response")

    async def shake(self, round_id: str):
        """Shake the dice using Billy-II settings"""
        # Use the same command format as in quick_shaker_test.py
        cmd = "/cycle/?pattern=0&parameter1=10&parameter2=0&amplitude=0.41&duration=6"
        topic = "ikg/sicbo/Billy-II/listens"
        # topic = "ikg/sicbo/Billy-I/listens" # temporary
        
        self.mqtt_client.publish(topic, cmd)
        self.mqtt_client.publish(topic, "/state")
        self.logger.info(f"Shake command sent for round {round_id}")

    async def shake_rpi(self, round_id: str):
        """Shake the dice"""
        command = {
            "command": "shake",
            "arg": {
                "round_id": round_id
            }
        }
        self.mqtt_client.publish("ikg/shaker/command", json.dumps(command))
        self.logger.info(f"Shake command sent for round {round_id}")

    async def cleanup(self):
        """Cleanup shaker controller resources"""
        self.mqtt_client.stop_loop()
        self.mqtt_client.disconnect()

class BarcodeController(Controller):
    """Controls barcode scanner operations"""
    def __init__(self, config: GameConfig):
        super().__init__(config)
        # HID 鍵盤掃描碼對照表
        self.hid_keycode = {
            0x00: None, 
            0x04: 'A', 0x05: 'B', 0x06: 'C', 0x07: 'D', 0x08: 'E',
            0x09: 'F', 0x0A: 'G', 0x0B: 'H', 0x0C: 'I', 0x0D: 'J',
            0x0E: 'K', 0x0F: 'L', 0x10: 'M', 0x11: 'N', 0x12: 'O',
            0x13: 'P', 0x14: 'Q', 0x15: 'R', 0x16: 'S', 0x17: 'T',
            0x18: 'U', 0x19: 'V', 0x1A: 'W', 0x1B: 'X', 0x1C: 'Y',
            0x1D: 'Z', 0x1E: '1', 0x1F: '2', 0x20: '3', 0x21: '4',
            0x22: '5', 0x23: '6', 0x24: '7', 0x25: '8', 0x26: '9',
            0x27: '0', 0x28: 'ENTER'
        }

        # 修飾鍵對照表
        self.modifier_keys = {
            0x01: 'LCTRL',
            0x02: 'LSHIFT',
            0x04: 'LALT',
            0x08: 'LWIN',
            0x10: 'RCTRL',
            0x20: 'RSHIFT',
            0x40: 'RALT',
            0x80: 'RWIN'
        }
        
        self.device_path = None
        self.is_running = False
        self.current_line = []  # 儲存當前行的字符
        self.callback = None  # 用於處理掃描結果的回調函數

    def decode_hid_data(self, data: bytes) -> Tuple[List[str], List[str]]:
        """解碼 HID 數據"""
        modifier = data[0]
        mods = []
        if modifier:
            for bit, name in self.modifier_keys.items():
                if modifier & bit:
                    mods.append(name)
        
        keys = []
        for i in range(2, len(data)):
            if data[i] != 0x00:
                key = self.hid_keycode.get(data[i], f'UNKNOWN({hex(data[i])})')
                if key:
                    keys.append(key)
        
        return mods, keys

    async def initialize(self, device_path: str, callback=None):
        """初始化條碼掃描器"""
        self.device_path = device_path
        self.callback = callback
        self.is_running = True
        
        # 啟動掃描處理的非同步任務
        asyncio.create_task(self._read_barcode())
        self.logger.info(f"Barcode scanner initialized with device: {device_path}")

    async def _read_barcode(self):
        """讀取條碼掃描器數據的非同步方法"""
        try:
            while self.is_running:
                with open(self.device_path, 'rb') as f:
                    while self.is_running:
                        data = f.read(8)  # HID 報告的標準長度
                        if data:
                            mods, keys = self.decode_hid_data(data)
                            
                            if keys:
                                for key in keys:
                                    if key == 'ENTER':
                                        # 當遇到 ENTER 時，處理當前行
                                        if self.current_line:
                                            barcode = ''.join(self.current_line)
                                            self.logger.info(f"Scanned barcode: {barcode}")
                                            if self.callback:
                                                await self.callback(barcode)
                                        self.current_line = []
                                    else:
                                        # 一般按鍵，加入當前行
                                        self.current_line.append(key)
                        
                        await asyncio.sleep(0.001)  # 短暫休眠避免 CPU 過度使用
                        
        except Exception as e:
            self.logger.error(f"Error reading barcode: {e}")
        finally:
            self.logger.info("Barcode reading stopped")

    async def cleanup(self):
        """清理資源"""
        self.is_running = False
        self.logger.info("Barcode controller cleanup completed")

    def set_callback(self, callback):
        """設置處理掃描結果的回調函數"""
        self.callback = callback 