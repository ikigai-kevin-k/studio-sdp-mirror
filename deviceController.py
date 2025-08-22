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
            # broker=config.broker_host,
            # broker="192.168.88.213",
            # broker="192.168.88.180",
            # broker="206.53.48.180", # orginal vps broker
            broker="192.168.88.180",  # new strong pc broker
            port=config.broker_port,
        )
        self.response_received = False
        self.last_response = None
        self.dice_result = None
        self.mqtt_client.client.username_pw_set("PFC", "wago")

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
                if (
                    "response" in response_data
                    and response_data["response"] == "result"
                ):
                    if "arg" in response_data and "res" in response_data["arg"]:
                        dice_result = response_data["arg"]["res"]
                        # 檢查是否為有效的骰子結果 (三個數字)
                        if (
                            isinstance(dice_result, list)
                            and len(dice_result) == 3
                            and all(isinstance(x, int) for x in dice_result)
                        ):
                            self.dice_result = dice_result
                            self.response_received = True
                            self.last_response = payload
                            self.logger.info(
                                f"Got valid dice result: {self.dice_result}"
                            )
                            return  # 立即返回，不再等待更多結果
                        else:
                            self.logger.info(
                                f"Received invalid result: {dice_result}, continuing to wait..."
                            )

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse message JSON: {e}")
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")

    async def detect(self, round_id: str) -> Tuple[bool, Optional[list]]:
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
                    "input": "rtmp://192.168.88.50:1935/live/r217_sb",
                    "output": "https://pull-tc.stream.iki-utl.cc/live/r456_dice.flv",
                },
            }

            # 設定超時時限
            timeout = 5  # for demo
            start_time = asyncio.get_event_loop().time()
            retry_interval = 5
            attempt = 1

            while (asyncio.get_event_loop().time() - start_time) < timeout:
                # 發送檢測命令
                self.logger.info(f"Sending detect command (attempt {attempt})")
                self.mqtt_client.publish("ikg/idp/dice/command", json.dumps(command))

                # 等待回應的小循環
                wait_end = min(
                    start_time + timeout,  # 不超過總超時時間
                    asyncio.get_event_loop().time()
                    + retry_interval,  # 下次重試前的等待時間
                )

                while asyncio.get_event_loop().time() < wait_end:
                    if self.dice_result is not None:
                        self.logger.info(
                            f"Received dice result on attempt {attempt}: {self.dice_result}"
                        )
                        return True, self.dice_result
                    # 使用 asyncio.sleep 替代 time.sleep，避免阻塞事件循環
                    await asyncio.sleep(0.5)

                attempt += 1

            # 超時處理
            elapsed = asyncio.get_event_loop().time() - start_time
            self.logger.warning(
                f"No valid response received within {elapsed:.2f}s after {attempt-1} attempts"
            )
            command = {"command": "timeout", "arg": {}}
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
            # broker="192.168.88.250",  # Specific broker for shaker
            # broker="192.168.88.213",
            broker="192.168.88.180",
            # broker="206.53.48.180",
            # broker="rnd-al.local",
            port=config.broker_port,
        )
        self.mqtt_client.client.username_pw_set(
            "PFC", "wago"
        )  # Specific credentials for shaker

        # 搖骰器狀態追蹤
        self.shaker_state = None  # 當前搖骰器狀態 (S0, S1, S2, S90)
        self.state_received = False  # 是否收到狀態回應
        self.all_messages = []  # 儲存所有收到的訊息

    def _on_message(self, client, userdata, message):
        """Handle received messages from shaker"""
        try:
            payload = message.payload.decode()
            self.logger.info(f"[MQTT] Topic: {message.topic}")
            self.logger.info(f"[MQTT] Payload: {payload}")

            # 儲存訊息
            self.all_messages.append(
                {
                    "topic": message.topic,
                    "payload": payload,
                    "time": time.strftime("%H:%M:%S"),
                }
            )

            # 檢查搖骰器狀態回應
            if message.topic == "ikg/sicbo/Billy-III/listens":
                if payload == "/state":
                    self.logger.info("[STATUS] State request sent")
            elif message.topic == "ikg/sicbo/Billy-III/says":
                if payload.startswith("S"):  # 檢查狀態回應 (S0, S1, S2, S90)
                    self.shaker_state = payload
                    self.state_received = True
                    if payload == "S0":
                        self.logger.info("[STATUS] Shaker is IDLE")
                    elif payload == "S1":
                        self.logger.info("[STATUS] Shaker is SHAKING")
                    elif payload == "S2":
                        self.logger.info("[STATUS] Shaker received SHAKE COMMAND")
                    elif payload == "S90":
                        self.logger.warning(
                            "[STATUS] Shaker has MULTIPLE ERRORS in motion program"
                        )
                    else:
                        self.logger.info(
                            f"[STATUS] Received unknown state response: {payload}"
                        )

            self.logger.info("-" * 50)

        except Exception as e:
            self.logger.error(f"Error in _on_message: {e}")

    async def initialize(self):
        """Initialize shaker controller"""
        if not self.mqtt_client.connect():
            raise Exception("Failed to connect to MQTT broker")
        self.mqtt_client.start_loop()

        # 設置訊息處理回調
        self.mqtt_client.client.on_message = self._on_message

        # 訂閱搖骰器相關主題
        topics_to_subscribe = [
            "ikg/sicbo/Billy-III/listens",
            "ikg/sicbo/Billy-III/says",
            "ikg/sicbo/Billy-III/status",
            "ikg/sicbo/Billy-III/response",
            "ikg/sicbo/Billy-III/#",  # Billy-III 的所有子主題
        ]

        for topic in topics_to_subscribe:
            self.mqtt_client.subscribe(topic)
            self.logger.info(f"Subscribed to: {topic}")

    async def shake(self, round_id: str):
        """Shake the dice using Billy-III settings and monitor state changes"""
        # 重置狀態追蹤
        self.all_messages = []
        self.state_received = False
        self.shaker_state = None

        # Use the same command format as in quick_shaker_test.py
        cmd = "/cycle/?pattern=0&parameter1=10&parameter2=0&amplitude=0.41&duration=9.59"  # for current dice pc setting
        topic = "ikg/sicbo/Billy-III/listens"
        # topic = "ikg/sicbo/Billy-I/listens" # temporary

        # 先檢查當前狀態
        self.logger.info("Checking current shaker state...")
        self.mqtt_client.publish(topic, "/state")

        # 等待狀態回應
        timeout = 10  # 10 秒超時
        start_time = time.time()
        while not self.state_received and (time.time() - start_time) < timeout:
            await asyncio.sleep(0.1)

        if not self.state_received:
            self.logger.warning("Did not receive initial state response")
        else:
            self.logger.info(f"Initial shaker state: {self.shaker_state}")

        # 發送搖動命令
        self.logger.info(f"Sending shake command for round {round_id}")
        self.mqtt_client.publish(topic, cmd)

        # reset state tracking, but keep shaker_state
        self.state_received = False
        # self.shaker_state = None  # don't reset, so wait_for_s0_state can detect current state

        # 等待搖動開始 (S2 -> S1)
        self.logger.info("Waiting for shake command to be received (S2)...")
        timeout = 3  # 增加到 3 秒超時，考慮網路延遲
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            if self.shaker_state == "S2":
                self.logger.info("✓ Shake command received by shaker")
                break
            elif self.shaker_state == "S90":
                self.logger.error("⚠ Shaker has motion program errors")
                return False
            await asyncio.sleep(0.05)  # 減少到 0.05 秒，更頻繁檢查

        if self.shaker_state != "S2":
            self.logger.warning(
                "Did not receive S2 (shake command received) within timeout"
            )

        # wait for shaking to complete (S1 -> S0)
        self.logger.info("Waiting for shaking to complete (S1 -> S0)...")
        # according to shake duration, calculate a reasonable timeout
        shake_duration = 9.59  # actual shake duration
        network_delay = 2.0    # estimated network delay
        timeout = shake_duration + network_delay  # about 12 seconds
        
        self.logger.info(f"Expected shake duration: {shake_duration}s, timeout set to: {timeout}s")
        
        start_time = time.time()
        last_state = None
        
        while (time.time() - start_time) < timeout:
            current_state = self.shaker_state
            
            # record state changes
            if current_state != last_state:
                if current_state == "S0":
                    self.logger.info("✓ Shaking completed successfully")
                    break
                elif current_state == "S1":
                    self.logger.info("→ Shaker is now SHAKING (S1)")
                elif current_state == "S2":
                    self.logger.info("→ Shaker is still in S2 state")
                elif current_state == "S90":
                    self.logger.error("⚠ Shaker has motion program errors during shaking")
                    return False
                
                last_state = current_state
            
            # if shake duration exceeded, actively check state
            elapsed_time = time.time() - start_time
            if elapsed_time > shake_duration and current_state != "S0":
                self.logger.info(f"Shake duration ({shake_duration}s) exceeded, actively checking state...")
                self.mqtt_client.publish("ikg/sicbo/Billy-III/listens", "/state")
                await asyncio.sleep(0.1)  # wait for state response
            
            await asyncio.sleep(0.05)  # reduce to 0.05 seconds, more frequent checks

        if self.shaker_state != "S0":
            self.logger.warning("Shaking may not have completed properly")
            # even if not reaching S0, try to check shaker state one more time
            self.logger.info("Attempting to check shaker state one more time...")
            await asyncio.sleep(0.5)  # reduced from 1 to 0.5 second
            self.mqtt_client.publish("ikg/sicbo/Billy-III/listens", "/state")
            await asyncio.sleep(0.2)  # reduced from 0.5 to 0.2 second

        # 輸出訊息摘要
        self.logger.info("\nShake Operation Summary:")
        for msg in self.all_messages:
            self.logger.info(
                f"Time: {msg['time']} - Topic: {msg['topic']} - Payload: {msg['payload']}"
            )

        # ensure final state is set correctly
        if self.shaker_state == "S0":
            self.logger.info("✓ Shake operation completed successfully with S0 state")
        else:
            self.logger.info(f"Final shaker state: {self.shaker_state}")
        
        self.logger.info(f"Shake operation completed for round {round_id}")
        
        # if already S0, ensure state_received is True
        if self.shaker_state == "S0":
            self.state_received = True
        
        return True

    async def wait_for_s0_state(self, timeout: float = 15.0) -> bool:
        """
        Wait for shaker to reach S0 (IDLE) state
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if S0 state reached, False if timeout
        """
        self.logger.info("Waiting for shaker to reach S0 (IDLE) state...")
        
        # if current state is S0, return immediately
        if self.shaker_state == "S0":
            self.logger.info("✓ Shaker is already in S0 (IDLE) state")
            return True
        
        # Reset state tracking
        self.state_received = False
        
        # send state request once to check current state
        self.logger.info("Sending state request to check current shaker state...")
        self.mqtt_client.publish("ikg/sicbo/Billy-III/listens", "/state")
        await asyncio.sleep(0.1)  # minimal wait time for faster response
        
        # check if S0 state is received
        if self.shaker_state == "S0":
            self.logger.info("✓ Shaker reached S0 (IDLE) state")
            return True
        
        # if not S0, wait for state change with minimal polling
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            if self.shaker_state == "S0":
                self.logger.info("✓ Shaker reached S0 (IDLE) state")
                return True
            elif self.shaker_state == "S90":
                self.logger.error("⚠ Shaker has motion program errors")
                return False
            elif self.shaker_state in ["S1", "S2"]:
                self.logger.info(f"Shaker is in {self.shaker_state} state, waiting for S0...")
            
            # only send one more state request if we haven't received any response
            if not self.state_received and (time.time() - start_time) > 1:  # reduced from 3 to 1 second
                self.logger.info("No state response received, sending one more state request...")
                self.mqtt_client.publish("ikg/sicbo/Billy-III/listens", "/state")
                self.state_received = True  # prevent further requests
            
            await asyncio.sleep(0.02)  # reduced from 0.05 to 0.02 for faster response
        
        self.logger.warning(f"Timeout waiting for S0 state after {timeout}s")
        return False

    async def shake_rpi(self, round_id: str):
        """Shake the dice"""
        command = {"command": "shake", "arg": {"round_id": round_id}}
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
        # HID keyboard scan code table
        self.hid_keycode = {
            0x00: None,
            0x04: "A",
            0x05: "B",
            0x06: "C",
            0x07: "D",
            0x08: "E",
            0x09: "F",
            0x0A: "G",
            0x0B: "H",
            0x0C: "I",
            0x0D: "J",
            0x0E: "K",
            0x0F: "L",
            0x10: "M",
            0x11: "N",
            0x12: "O",
            0x13: "P",
            0x14: "Q",
            0x15: "R",
            0x16: "S",
            0x17: "T",
            0x18: "U",
            0x19: "V",
            0x1A: "W",
            0x1B: "X",
            0x1C: "Y",
            0x1D: "Z",
            0x1E: "1",
            0x1F: "2",
            0x20: "3",
            0x21: "4",
            0x22: "5",
            0x23: "6",
            0x24: "7",
            0x25: "8",
            0x26: "9",
            0x27: "0",
            0x28: "ENTER",
        }

        # 修飾鍵對照表
        self.modifier_keys = {
            0x01: "LCTRL",
            0x02: "LSHIFT",
            0x04: "LALT",
            0x08: "LWIN",
            0x10: "RCTRL",
            0x20: "RSHIFT",
            0x40: "RALT",
            0x80: "RWIN",
        }

        self.device_path = None
        self.is_running = False
        self.is_paused = False  # add new pause flag
        self.current_line = []  # store current line of characters
        self.callback = None  # callback function for processing scan results
        self.pause_timestamp = None  # record pause timestamp

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
                key = self.hid_keycode.get(data[i], f"UNKNOWN({hex(data[i])})")
                if key:
                    keys.append(key)

        return mods, keys

    async def initialize(self, device_path: str, callback=None):
        """initialize barcode scanner"""
        self.device_path = device_path
        self.callback = callback
        self.is_running = True

        # 啟動掃描處理的非同步任務
        asyncio.create_task(self._read_barcode())
        self.logger.info(f"Barcode scanner initialized with device: {device_path}")

    async def _read_barcode(self):
        """read barcode scanner data asynchronously"""
        try:
            while self.is_running:
                with open(self.device_path, "rb") as f:
                    while self.is_running:
                        # check if paused
                        if self.is_paused:
                            await asyncio.sleep(0.1)  # wait longer when paused
                            continue
                        data = f.read(8)  # HID report standard length
                        if data:
                            mods, keys = self.decode_hid_data(data)
                            self.logger.debug(
                                f"[LOG] Raw HID data: {data.hex()} mods: {mods} keys: {keys} current_line: {self.current_line}"
                            )
                            if keys:
                                for key in keys:
                                    # check if paused before processing any key
                                    if self.is_paused:
                                        self.logger.debug(
                                            f"Ignored key during pause: {key}"
                                        )
                                        continue
                                    if key == "ENTER":
                                        # when encounter ENTER, process current line
                                        self.logger.debug(
                                            f"[LOG] ENTER detected, current_line before join: {self.current_line}"
                                        )
                                        if self.current_line:
                                            barcode = "".join(self.current_line)
                                            self.logger.info(
                                                f"[LOG] Barcode to process: '{barcode}' (len={len(barcode)})"
                                            )
                                            # only process barcode when not paused
                                            if not self.is_paused:
                                                self.logger.info(
                                                    f"Scanned barcode: {barcode}"
                                                )
                                                if self.callback:
                                                    await self.callback(barcode)
                                            else:
                                                self.logger.info(
                                                    f"Ignored barcode during pause: {barcode}"
                                                )
                                        else:
                                            self.logger.warning(
                                                f"[LOG] ENTER detected but current_line is empty!"
                                            )
                                        self.current_line = []
                                    else:
                                        # normal key, add to current line
                                        self.logger.debug(
                                            f"[LOG] Appending key: {key} to current_line: {self.current_line}"
                                        )
                                        if not self.is_paused:
                                            self.current_line.append(key)
                                        else:
                                            # ignore all key input during pause
                                            self.logger.debug(
                                                f"Ignored key during pause: {key}"
                                            )
                                        self.current_line.append(key)
                        await asyncio.sleep(0.001)  # short sleep to avoid CPU overload
        except Exception as e:
            import traceback

            self.logger.error(
                f"Error reading barcode: {e}\n[LOG] current_line at error: {self.current_line}\nTraceback: {traceback.format_exc()}"
            )
        finally:
            self.logger.info("Barcode reading stopped")

    async def cleanup(self):
        """cleanup resources"""
        self.is_running = False
        self.logger.info("Barcode controller cleanup completed")

    def set_callback(self, callback):
        """set callback function for processing scan results"""
        self.callback = callback

    def pause_scanning(self):
        """pause barcode scanning"""
        import time

        self.is_paused = True
        self.pause_timestamp = time.time()
        # clear current line buffer to prevent partial data being retained
        self.current_line = []
        self.logger.info(
            f"Barcode scanning paused and buffer cleared at {self.pause_timestamp}"
        )

    def resume_scanning(self):
        """resume barcode scanning"""
        import time

        self.is_paused = False
        self.pause_timestamp = None
        # ensure buffer is empty
        self.current_line = []
        self.logger.info(f"Barcode scanning resumed at {time.time()}")
