import logging
import json
import asyncio
import sys
import os
from typing import Optional, Tuple, List
from dataclasses import dataclass
import time
from mqtt.mqtt_wrapper import MQTTLogger
from controller import Controller, GameConfig

# Import send_sicbo_no_shake_error from ws_err_sig_sbe
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "studio_api"))
try:
    from ws_err_sig_sbe import send_sicbo_no_shake_error
except ImportError:
    send_sicbo_no_shake_error = None


class IDPController(Controller):
    """Controls IDP (Image Detection Processing) operations"""

    def __init__(self, config: GameConfig):
        super().__init__(config)
        self.mqtt_client = MQTTLogger(
            client_id=f"idp_controller_{config.room_id}",
            # broker=config.broker_host,
            # broker="192.168.88.213",
            # broker="192.168.88.54",
            # broker="206.53.48.180", # orginal vps broker
            broker="192.168.88.54", 
            port=config.broker_port,
        )
        self.response_received = False
        self.last_response = None
        self.dice_result = None
        self.mqtt_client.client.username_pw_set("PFC", "wago")
        self._error_signal_task = None  # Track async error signal task
        self._error_signal_sent_for_current_cycle = False  # Track if error signal sent for current shake cycle
        self._error_signal_count = 0  # Track error signal send count (0 = not sent, 1 = first (warn), 2 = second (error))

    async def initialize(self):
        """Initialize IDP controller"""
        try:
            # Connect to MQTT broker
            if not self.mqtt_client.connect():
                raise Exception("Failed to connect to MQTT broker")

            # Start MQTT loop
            self.mqtt_client.start_loop()

            # Wait a moment for connection to stabilize
            await asyncio.sleep(1)

            # set message processing callback
            self.mqtt_client.client.on_message = self._on_message
            self.mqtt_client.subscribe("ikg/idp/SBO-001/response")

            self.logger.info("IDP controller initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize IDP controller: {e}")
            raise

    def _on_message(self, client, userdata, message):
        """Handle received messages"""
        try:
            payload = message.payload.decode()
            self.logger.info(f"Received message on {message.topic}: {payload}")

            # process message
            self._process_message(message.topic, payload)

        except Exception as e:
            self.logger.error(f"Error in _on_message: {e}")

    def _process_message(self, topic, payload):
        """Process received message"""
        try:
            self.logger.info(f"Processing message from {topic}: {payload}")

            if topic == "ikg/idp/SBO-001/response":
                response_data = json.loads(payload)
                if (
                    "response" in response_data
                    and response_data["response"] == "result"
                ):
                    if (
                        "arg" in response_data
                        and "res" in response_data["arg"]
                    ):
                        dice_result = response_data["arg"]["res"]
                        error_code = response_data["arg"].get("err", 0)
                        
                        # Check if error code is -3 (NO SHAKE error)
                        if error_code == -3:
                            self.logger.warning(
                                f"Received error code -3 (NO SHAKE) from IDP response"
                            )
                            # Send error signal to WebSocket server
                            self._send_no_shake_error_signal()
                        
                        # check if the dice result is valid (three numbers)
                        if (
                            error_code == 0
                            and isinstance(dice_result, list)
                            and len(dice_result) == 3
                            and all(isinstance(x, int) for x in dice_result)
                        ):
                            self.dice_result = dice_result
                            self.response_received = True
                            self.last_response = payload
                            self.logger.info(
                                f"Got valid dice result: {self.dice_result}"
                            )
                            return  # return immediately, don't wait for more results
                        else:
                            if error_code != 0:
                                self.logger.info(
                                    f"Received error code {error_code}, continuing to wait..."
                                )
                            else:
                                self.logger.info(
                                    f"Received invalid result: {dice_result}, continuing to wait..."
                                )

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse message JSON: {e}")
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")

    def reset_error_signal_flag(self):
        """Reset error signal flag at the start of a new shake cycle"""
        self._error_signal_sent_for_current_cycle = False
        self._error_signal_count = 0
        self.logger.debug("Reset error signal flag and count for new shake cycle")

    def _send_no_shake_error_signal(self):
        """Send SICBO_NO_SHAKE error signal to WebSocket server
        
        First time sends with signalType='warn', second time sends with signalType='error'
        """
        # Determine signal type based on send count
        if self._error_signal_count == 0:
            signal_type = "warn"  # First time
            self._error_signal_count = 1
        elif self._error_signal_count == 1:
            signal_type = "error"  # Second time
            self._error_signal_count = 2
        else:
            # Already sent twice, skip
            self.logger.info(
                f"Error signal already sent twice for this shake cycle, skipping"
            )
            return

        if send_sicbo_no_shake_error is None:
            self.logger.warning(
                "send_sicbo_no_shake_error function not available, skipping error signal"
            )
            return
        
        def _run_async_signal():
            """Run async error signal in a separate thread"""
            try:
                # Run the async function in a new event loop with signal_type
                asyncio.run(send_sicbo_no_shake_error(signal_type=signal_type))
                self.logger.info(
                    f"Sent SICBO_NO_SHAKE error signal with signalType={signal_type}"
                )
            except Exception as e:
                self.logger.error(
                    f"Failed to send SICBO_NO_SHAKE error signal: {e}"
                )
        
        try:
            # Try to get running loop first
            try:
                loop = asyncio.get_running_loop()
                # If loop is running, we need to schedule the coroutine
                # Use run_coroutine_threadsafe if we're in a different thread
                # Otherwise, create a task
                import threading
                if threading.current_thread() is threading.main_thread():
                    # We're in the main thread with running loop
                    self._error_signal_task = asyncio.create_task(
                        send_sicbo_no_shake_error(signal_type=signal_type)
                    )
                    self._error_signal_sent_for_current_cycle = True
                    self.logger.info(
                        f"Scheduled SICBO_NO_SHAKE error signal to be sent with signalType={signal_type}"
                    )
                else:
                    # We're in a different thread (MQTT callback thread), use run_coroutine_threadsafe
                    future = asyncio.run_coroutine_threadsafe(
                        send_sicbo_no_shake_error(signal_type=signal_type), loop
                    )
                    self._error_signal_task = future
                    self._error_signal_sent_for_current_cycle = True
                    self.logger.info(
                        f"Scheduled SICBO_NO_SHAKE error signal to be sent (threadsafe) with signalType={signal_type}"
                    )
            except RuntimeError:
                # No running loop, run in new thread to avoid blocking
                import threading
                thread = threading.Thread(target=_run_async_signal, daemon=True)
                thread.start()
                self._error_signal_sent_for_current_cycle = True
                self.logger.info(
                    f"Started thread to send SICBO_NO_SHAKE error signal with signalType={signal_type}"
                )
        except Exception as e:
            self.logger.error(
                f"Failed to send SICBO_NO_SHAKE error signal: {e}"
            )

    async def detect(self, round_id: str) -> Tuple[bool, Optional[list]]:
        """Send detect command and wait for response"""
        try:
            # reset state
            self.response_received = False
            self.last_response = None
            self.dice_result = None

            command = {
                "command": "detect",
                "arg": {
                    "round_id": round_id,
                    "input": "rtmp://192.168.88.54:1935/live/r14_sb",
                    "output": "https://pull-tc.stream.iki-utl.cc/live/r456_dice.flv",
                },
            }

            # set timeout limit
            timeout = 5  # for demo
            start_time = asyncio.get_event_loop().time()
            retry_interval = 5
            attempt = 1

            while (asyncio.get_event_loop().time() - start_time) < timeout:
                # send detect command
                self.logger.info(f"Sending detect command (attempt {attempt})")
                self.mqtt_client.publish(
                    "ikg/idp/SBO-001/command", json.dumps(command)
                )

                # wait for response in small loop
                wait_end = min(
                    start_time + timeout,  # don't exceed total timeout
                    asyncio.get_event_loop().time()
                    + retry_interval,  # wait time before next retry
                )

                while asyncio.get_event_loop().time() < wait_end:
                    if self.dice_result is not None:
                        self.logger.info(
                            f"Received dice result on attempt {attempt}: {self.dice_result}"
                        )
                        return True, self.dice_result
                    # use asyncio.sleep instead of time.sleep to avoid blocking event loop
                    await asyncio.sleep(0.5)

                attempt += 1

            # timeout handling
            elapsed = asyncio.get_event_loop().time() - start_time
            self.logger.warning(
                f"No valid response received within {elapsed:.2f}s after {attempt-1} attempts"
            )
            command = {"command": "timeout", "arg": {}}
            self.mqtt_client.publish(
                "ikg/idp/SBO-001/command", json.dumps(command)
            )
            if self.last_response:
                self.logger.warning(f"Last response was: {self.last_response}")
            return True, [""]  # return default values on timeout

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
            broker="192.168.88.54",
            # broker="206.53.48.180",
            # broker="rnd-al.local",
            port=config.broker_port,
        )
        self.mqtt_client.client.username_pw_set(
            "PFC", "wago"
        )  # Specific credentials for shaker

        # shaker state tracking
        self.shaker_state = None  # current shaker state (S0, S1, S2, S90)
        self.state_received = False  # whether received state response
        self.all_messages = []  # store all received messages

    def _on_message(self, client, userdata, message):
        """Handle received messages from shaker"""
        try:
            payload = message.payload.decode()
            self.logger.info(f"[MQTT] Topic: {message.topic}")
            self.logger.info(f"[MQTT] Payload: {payload}")

            # store message
            self.all_messages.append(
                {
                    "topic": message.topic,
                    "payload": payload,
                    "time": time.strftime("%H:%M:%S"),
                }
            )

            # check shaker state response
            if message.topic == "ikg/sicbo/Billy-III/listens":
                if payload == "/state":
                    self.logger.info("[STATUS] State request sent")
            elif message.topic == "ikg/sicbo/Billy-III/says":
                if payload.startswith(
                    "S"
                ):  # check state response (S0, S1, S2, S90)
                    self.shaker_state = payload
                    self.state_received = True
                    if payload == "S0":
                        self.logger.info("[STATUS] Shaker is IDLE")
                    elif payload == "S1":
                        self.logger.info("[STATUS] Shaker is SHAKING")
                    elif payload == "S2":
                        self.logger.info(
                            "[STATUS] Shaker received SHAKE COMMAND"
                        )
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
        try:
            # Connect to MQTT broker
            if not self.mqtt_client.connect():
                raise Exception("Failed to connect to MQTT broker")

            # Start MQTT loop
            self.mqtt_client.start_loop()

            # Wait a moment for connection to stabilize
            await asyncio.sleep(1)

            # set message processing callback
            self.mqtt_client.client.on_message = self._on_message

            # subscribe to shaker related topics
            topics_to_subscribe = [
                "ikg/sicbo/Billy-III/listens",
                "ikg/sicbo/Billy-III/says",
                "ikg/sicbo/Billy-III/status",
                "ikg/sicbo/Billy-III/response",
                "ikg/sicbo/Billy-III/#",  # all subtopics of Billy-III
            ]

            for topic in topics_to_subscribe:
                self.mqtt_client.subscribe(topic)
                self.logger.info(f"Subscribed to: {topic}")

            self.logger.info("Shaker controller initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize shaker controller: {e}")
            raise

    async def shake(self, round_id: str):
        """Shake the dice using Billy-III settings and monitor state changes"""
        # reset state tracking
        self.all_messages = []
        self.state_received = False
        self.shaker_state = None

        # Use the same command format as in quick_shaker_test.py
        cmd = "/cycle/?pattern=0&parameter1=10&parameter2=0&amplitude=0.41&duration=9.59"  # for current dice pc setting
        topic = "ikg/sicbo/Billy-III/listens"
        # topic = "ikg/sicbo/Billy-I/listens" # temporary

        # check current state
        self.logger.info("Checking current shaker state...")
        self.mqtt_client.publish(topic, "/state")

        # wait for state response
        timeout = 10  # 10 seconds timeout
        start_time = time.time()
        while not self.state_received and (time.time() - start_time) < timeout:
            await asyncio.sleep(0.2)  # Increased from 0.1 to 0.2 to reduce message frequency

        if not self.state_received:
            self.logger.warning("Did not receive initial state response")
        else:
            self.logger.info(f"Initial shaker state: {self.shaker_state}")

        # send shake command
        self.logger.info(f"Sending shake command for round {round_id}")
        self.mqtt_client.publish(topic, cmd)

        # reset state tracking, but keep shaker_state
        self.state_received = False

        # improved state monitoring logic: not rely on fixed state sequence
        self.logger.info("Monitoring shaker state changes...")

        # record shake start time
        expected_shake_duration = 9.59  # actual shake duration
        network_delay = 2.0  # estimated network delay
        # extra buffer time
        total_timeout = expected_shake_duration + network_delay + 5.0

        self.logger.info(
            f"Expected shake duration: {expected_shake_duration}s, "
            f"total timeout: {total_timeout}s"
        )

        # state tracking variables
        last_state = self.shaker_state
        state_changes = []
        shake_command_received = False
        shaking_started = False
        shaking_completed = False

        start_time = time.time()
        while (time.time() - start_time) < total_timeout:
            current_state = self.shaker_state
            elapsed_time = time.time() - start_time

            # record state changes
            if current_state != last_state and current_state is not None:
                state_changes.append(
                    {
                        "time": elapsed_time,
                        "state": current_state,
                        "timestamp": time.strftime("%H:%M:%S"),
                    }
                )

                self.logger.info(
                    f"State change detected: {last_state} → {current_state} "
                    f"at {elapsed_time:.2f}s"
                )

                # update state flags
                if current_state == "S2":
                    shake_command_received = True
                    self.logger.info("✓ Shake command received by shaker (S2)")
                elif current_state == "S1":
                    shaking_started = True
                    self.logger.info("✓ Shaking started (S1)")
                elif current_state == "S0":
                    shaking_completed = True
                    self.logger.info("✓ Shaking completed successfully (S0)")
                    break
                elif current_state == "S90":
                    self.logger.error(
                        "⚠ Shaker has motion program errors (S90)"
                    )
                    return False

                last_state = current_state

            # actively check state (if no state changes for a while)
            if elapsed_time > 2.0 and not self.state_received:
                self.logger.info(
                    "No state response received, sending state request..."
                )
                self.mqtt_client.publish(topic, "/state")
                await asyncio.sleep(0.2)  # Increased from 0.1 to 0.2 to reduce message frequency

            # if shake duration exceeded, actively check state
            if (
                elapsed_time > expected_shake_duration
                and not shaking_completed
            ):
                self.logger.info(
                    f"Shake duration ({expected_shake_duration}s) exceeded, actively checking state..."
                )
                self.mqtt_client.publish(topic, "/state")
                await asyncio.sleep(0.2)  # Increased from 0.1 to 0.2 to reduce message frequency

            await asyncio.sleep(0.05)  # check frequency

        # analyze shake result
        self.logger.info("\n=== Shake Operation Analysis ===")
        self.logger.info(
            f"Total monitoring time: {time.time() - start_time:.2f}s"
        )
        self.logger.info(f"State changes detected: {len(state_changes)}")

        for change in state_changes:
            self.logger.info(
                f"  {change['timestamp']} ({change['time']:.2f}s): {change['state']}"
            )

        # check if shake completed
        if shaking_completed:
            self.logger.info("✓ Shake operation completed successfully")
            return True
        else:
            # even if not completed, try final state check
            self.logger.info("Attempting final state check...")
            self.mqtt_client.publish(topic, "/state")
            await asyncio.sleep(0.5)

            if self.shaker_state == "S0":
                self.logger.info("✓ Final check: Shaker reached S0 state")
                return True
            else:
                self.logger.warning(f"Final shaker state: {self.shaker_state}")

                # analyze state changes
                if not shake_command_received:
                    self.logger.error(
                        "❌ Shake command was not received by shaker"
                    )
                elif not shaking_started:
                    self.logger.error(
                        "❌ Shaking did not start after command received"
                    )
                elif not shaking_completed:
                    self.logger.error(
                        "❌ Shaking started but did not complete"
                    )

                return False

        # output message summary
        self.logger.info("\nShake Operation Summary:")
        for msg in self.all_messages:
            self.logger.info(
                f"Time: {msg['time']} - Topic: {msg['topic']} - Payload: {msg['payload']}"
            )

        self.logger.info(f"Shake operation completed for round {round_id}")
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
        self.logger.info(
            "Sending state request to check current shaker state..."
        )
        self.mqtt_client.publish("ikg/sicbo/Billy-III/listens", "/state")
        await asyncio.sleep(0.2)  # Increased from 0.1 to 0.2 to reduce message frequency

        # check if S0 state is received
        if self.shaker_state == "S0":
            self.logger.info("✓ Shaker reached S0 (IDLE) state")
            return True

        # improved state waiting logic
        start_time = time.time()
        last_state = self.shaker_state
        state_changes = []

        while (time.time() - start_time) < timeout:
            current_state = self.shaker_state
            elapsed_time = time.time() - start_time

            # record state changes
            if current_state != last_state and current_state is not None:
                state_changes.append(
                    {"time": elapsed_time, "state": current_state}
                )

                self.logger.info(
                    f"State change: {last_state} → {current_state} "
                    f"at {elapsed_time:.2f}s"
                )

                if current_state == "S0":
                    self.logger.info("✓ Shaker reached S0 (IDLE) state")
                    return True
                elif current_state == "S90":
                    self.logger.error("⚠ Shaker has motion program errors")
                    return False
                elif current_state in ["S1", "S2"]:
                    self.logger.info(
                        f"Shaker is in {current_state} state, waiting for S0..."
                    )

                last_state = current_state

            # actively check state (if no state changes for a while)
            if elapsed_time > 2.0 and not self.state_received:
                self.logger.info(
                    "No state response received, sending state request..."
                )
                self.mqtt_client.publish(
                    "ikg/sicbo/Billy-III/listens", "/state"
                )
                await asyncio.sleep(0.2)  # Increased from 0.1 to 0.2 to reduce message frequency

            await asyncio.sleep(0.02)  # check frequency

        # timeout
        self.logger.warning(f"Timeout waiting for S0 state after {timeout}s")

        # provide diagnostic information
        if state_changes:
            self.logger.info("State changes observed during wait:")
            for change in state_changes:
                self.logger.info(f"  {change['time']:.2f}s: {change['state']}")
        else:
            self.logger.info("No state changes observed during wait")

        self.logger.info(f"Final shaker state: {self.shaker_state}")
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
        self.logger.info(
            f"Barcode scanner initialized with device: {device_path}"
        )

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
                                            barcode = "".join(
                                                self.current_line
                                            )
                                            self.logger.info(
                                                f"[LOG] Barcode to process: '{barcode}' (len={len(barcode)})"
                                            )
                                            # only process barcode when not paused
                                            if not self.is_paused:
                                                self.logger.info(
                                                    f"Scanned barcode: {barcode}"
                                                )
                                                if self.callback:
                                                    await self.callback(
                                                        barcode
                                                    )
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
                        await asyncio.sleep(
                            0.001
                        )  # short sleep to avoid CPU overload
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


class BaccaratIDPController(Controller):
    """Controls Baccarat IDP (Image Detection Processing) operations"""

    def __init__(self, config: GameConfig):
        super().__init__(config)
        self.mqtt_client = MQTTLogger(
            client_id=f"baccarat_idp_controller_{config.room_id}",
            broker="192.168.20.10",  # Baccarat-specific broker
            port=1883,  # Baccarat-specific port
        )
        self.response_received = False
        self.last_response = None
        self.baccarat_result = None
        self.mqtt_client.client.username_pw_set("PFC", "wago")

    async def initialize(self):
        """Initialize Baccarat IDP controller"""
        if not self.mqtt_client.connect():
            raise Exception("Failed to connect to MQTT broker")
        self.mqtt_client.start_loop()

        # Set message handling callback
        self.mqtt_client.client.on_message = self._on_message
        self.mqtt_client.subscribe("ikg/idp/BAC-001/response")

    def _on_message(self, client, userdata, message):
        """Handle received messages"""
        try:
            payload = message.payload.decode()
            self.logger.info(f"Received message on {message.topic}: {payload}")

            # Process message
            self._process_message(message.topic, payload)

        except Exception as e:
            self.logger.error(f"Error in _on_message: {e}")

    def _process_message(self, topic, payload):
        """Process received message"""
        try:
            self.logger.info(f"Processing message from {topic}: {payload}")

            if topic == "ikg/idp/BAC-001/response":
                response_data = json.loads(payload)
                if (
                    "response" in response_data
                    and response_data["response"] == "result"
                ):
                    if (
                        "arg" in response_data
                        and "res" in response_data["arg"]
                    ):
                        baccarat_result = response_data["arg"]["res"]
                        # Check if it's a valid baccarat result (6 cards)
                        if (
                            isinstance(baccarat_result, list)
                            and len(baccarat_result) == 6
                        ):
                            self.baccarat_result = baccarat_result
                            self.response_received = True
                            self.last_response = payload
                            self.logger.info(
                                f"Got valid baccarat result: {self.baccarat_result}"
                            )

                            # Send timeout command after receiving valid result
                            timeout_command = {"command": "timeout", "arg": {}}
                            self.mqtt_client.publish(
                                "ikg/idp/BAC-001/command",
                                json.dumps(timeout_command),
                            )
                            self.logger.info(
                                "Sent timeout command after receiving valid result"
                            )

                            return  # Return immediately, don't wait for more results
                        else:
                            self.logger.info(
                                f"Received invalid result: {baccarat_result}, "
                                f"continuing to wait..."
                            )

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse message JSON: {e}")
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")

    async def detect(self, round_id: str) -> Tuple[bool, Optional[list]]:
        """Send detect command and wait for response"""
        try:
            # Reset state
            self.response_received = False
            self.last_response = None
            self.baccarat_result = None

            command = {
                "command": "detect",
                "arg": {
                    "round_id": round_id,
                    "input": "rtmp://192.168.20.10:1935/live/r111_baccarat",
                },
            }

            # Set timeout limit
            timeout = 5  # for demo
            start_time = asyncio.get_event_loop().time()
            retry_interval = 5
            attempt = 1

            while (asyncio.get_event_loop().time() - start_time) < timeout:
                # Send detection command
                self.logger.info(f"Sending detect command (attempt {attempt})")
                self.mqtt_client.publish(
                    "ikg/idp/BAC-001/command", json.dumps(command)
                )

                # Wait for response in small loop
                wait_end = min(
                    start_time + timeout,  # Don't exceed total timeout
                    asyncio.get_event_loop().time()
                    + retry_interval,  # Wait time before next retry
                )

                while asyncio.get_event_loop().time() < wait_end:
                    if self.baccarat_result is not None:
                        self.logger.info(
                            f"Received baccarat result on attempt {attempt}: "
                            f"{self.baccarat_result}"
                        )
                        return True, self.baccarat_result
                    # Use asyncio.sleep instead of time.sleep to avoid blocking event loop
                    await asyncio.sleep(0.5)

                attempt += 1

            # Timeout handling
            elapsed = asyncio.get_event_loop().time() - start_time
            self.logger.warning(
                f"No valid response received within {elapsed:.2f}s "
                f"after {attempt-1} attempts"
            )
            command = {"command": "timeout", "arg": {}}
            self.mqtt_client.publish(
                "ikg/idp/BAC-001/command", json.dumps(command)
            )
            if self.last_response:
                self.logger.warning(f"Last response was: {self.last_response}")
            return True, [""] * 6  # Return default values on timeout

        except Exception as e:
            self.logger.error(f"Error in detect: {e}")
            return False, None

    async def cleanup(self):
        """Cleanup Baccarat IDP controller resources"""
        self.mqtt_client.stop_loop()
        self.mqtt_client.disconnect()
