import logging
import json
import asyncio
from typing import Optional, Tuple
import time
from transitions import Machine
from proto.mqtt import MQTTLogger
from controller import Controller, GameConfig

class IDPState:
    """IDP states definition"""
    IDLE = 'idle'
    DETECTING = 'detecting'
    PROCESSING = 'processing'
    RESULT_READY = 'result_ready'
    ERROR = 'error'
    TIMEOUT = 'timeout'

class IDPConnector(Controller):
    """Controls IDP (Image Detection Processing) operations with state machine"""
    
    # Define states
    states = [
        IDPState.IDLE,
        IDPState.DETECTING,
        IDPState.PROCESSING,
        IDPState.RESULT_READY,
        IDPState.ERROR,
        IDPState.TIMEOUT
    ]
    
    # Define transitions
    transitions = [
        {
            'trigger': 'start_detection',
            'source': IDPState.IDLE,
            'dest': IDPState.DETECTING,
            'before': 'before_detection',
            'after': 'after_detection'
        },
        {
            'trigger': 'process_result',
            'source': IDPState.DETECTING,
            'dest': IDPState.PROCESSING,
            'conditions': ['is_valid_response']
        },
        {
            'trigger': 'complete_processing',
            'source': IDPState.PROCESSING,
            'dest': IDPState.RESULT_READY,
            'conditions': ['is_valid_result']
        },
        {
            'trigger': 'handle_timeout',
            'source': [IDPState.DETECTING, IDPState.PROCESSING],
            'dest': IDPState.TIMEOUT,
            'before': 'before_timeout'
        },
        {
            'trigger': 'handle_error',
            'source': '*',
            'dest': IDPState.ERROR,
            'before': 'before_error'
        },
        {
            'trigger': 'reset',
            'source': '*',
            'dest': IDPState.IDLE,
            'before': 'before_reset'
        }
    ]

    def __init__(self, config: GameConfig):
        super().__init__(config)
        self.mqtt_client = MQTTLogger(
            client_id=f"idp_controller_{config.room_id}",
            broker=config.broker_host,
            port=config.broker_port
        )
        
        # Initialize state machine
        self.machine = Machine(
            model=self,
            states=self.states,
            transitions=self.transitions,
            initial=IDPState.IDLE,
            auto_transitions=False,
            send_event=True
        )
        
        # State data
        self.response_received = False
        self.last_response = None
        self.dice_result = None
        self.current_round_id = None
        self.error_message = None
        self.detection_start_time = None
        self.timeout_duration = 4  # seconds

    async def initialize(self):
        """Initialize IDP controller"""
        if not self.mqtt_client.connect():
            raise Exception("Failed to connect to MQTT broker")
        self.mqtt_client.start_loop()
        
        # Set message handling callback
        self.mqtt_client.client.on_message = self._on_message
        self.mqtt_client.subscribe("ikg/idp/dice/response")
        self.logger.info("IDP controller initialized")

    def _on_message(self, client, userdata, message):
        """Handle received messages"""
        try:
            payload = message.payload.decode()
            self.logger.info(f"Received message on {message.topic}: {payload}")
            
            # Process message
            self._process_message(message.topic, payload)
            
        except Exception as e:
            self.logger.error(f"Error in _on_message: {e}")

    def _process_message(self, topic: str, payload: str):
        """Process received message"""
        try:
            self.logger.info(f"Processing message from {topic}: {payload}")
            
            if topic == "ikg/idp/dice/response":
                response_data = json.loads(payload)
                if "response" in response_data and response_data["response"] == "result":
                    if "arg" in response_data and "res" in response_data["arg"]:
                        dice_result = response_data["arg"]["res"]
                        # Check if it's a valid dice result (three numbers)
                        if isinstance(dice_result, list) and len(dice_result) == 3 and all(isinstance(x, int) for x in dice_result):
                            self.dice_result = dice_result
                            self.response_received = True
                            self.last_response = payload
                            self.logger.info(f"Got valid dice result: {self.dice_result}")
                            return  # Return immediately, no need to wait for more results
                        else:
                            self.logger.info(f"Received invalid result: {dice_result}, continuing to wait...")
                    
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse message JSON: {e}")
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")

    def before_detection(self, event):
        """Actions before starting detection"""
        self.response_received = False
        self.last_response = None
        self.dice_result = None
        self.detection_start_time = time.time()

    def after_detection(self, event):
        """Actions after starting detection"""
        self.current_round_id = event.kwargs.get('round_id')
        command = {
            "command": "detect",
            "arg": {
                "round_id": self.current_round_id,
                "input": "rtmp://192.168.88.213:1935/live/r456_dice",
                "output": "https://pull-tc.stream.iki-utl.cc/live/r456_dice.flv"
            }
        }
        self.mqtt_client.publish("ikg/idp/dice/command", json.dumps(command))

    def is_valid_response(self, event):
        """Check if received response is valid"""
        try:
            response_data = json.loads(self.last_response)
            return ("response" in response_data and 
                   response_data["response"] == "result" and 
                   "arg" in response_data and 
                   "res" in response_data["arg"])
        except:
            return False

    def is_valid_result(self, event) -> bool:
        """Check if processed result is valid"""
        try:
            if (isinstance(self.dice_result, list) and 
                len(self.dice_result) == 3 and 
                all(isinstance(x, int) for x in self.dice_result)):
                return True
            return False
        except:
            return False

    def before_timeout(self, event):
        """Actions before timeout"""
        self.logger.warning(f"Detection timeout after {self.timeout_duration}s")
        command = {
            "command": "timeout",
            "arg": {}
        }
        self.mqtt_client.publish("ikg/idp/dice/command", json.dumps(command))

    def before_error(self, event):
        """Actions before error state"""
        self.error_message = event.kwargs.get('error', 'Unknown error')
        self.logger.error(f"Entering error state: {self.error_message}")

    def before_reset(self, event):
        """Actions before reset"""
        self.response_received = False
        self.last_response = None
        self.dice_result = None
        self.current_round_id = None
        self.error_message = None
        self.detection_start_time = None

    async def detect(self, round_id: str) -> Tuple[bool, Optional[list]]:
        """Send detect command and wait for response"""
        try:
            # Reset state if needed
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
            
            # Set timeout duration
            timeout = 4  # for demo
            start_time = asyncio.get_event_loop().time()
            retry_interval = 4  
            attempt = 1
            
            while (asyncio.get_event_loop().time() - start_time) < timeout:
                # Send detect command
                self.logger.info(f"Sending detect command (attempt {attempt})")
                self.mqtt_client.publish("ikg/idp/dice/command", json.dumps(command))
                
                # Wait for response loop
                wait_end = min(
                    start_time + timeout,  # Don't exceed total timeout time
                    asyncio.get_event_loop().time() + retry_interval  # Wait time before next retry
                )
                
                while asyncio.get_event_loop().time() < wait_end:
                    if self.dice_result is not None:
                        self.logger.info(f"Received dice result on attempt {attempt}: {self.dice_result}")
                        return True, self.dice_result
                    await asyncio.sleep(0.5)  # Short sleep to avoid CPU overload
                
                attempt += 1
            
            # Timeout handling
            elapsed = asyncio.get_event_loop().time() - start_time
            self.logger.warning(f"No valid response received within {elapsed:.2f}s after {attempt-1} attempts")
            command = {
                "command": "timeout",
                "arg": {}
            }
            self.mqtt_client.publish("ikg/idp/dice/command", json.dumps(command))
            if self.last_response:
                self.logger.warning(f"Last response was: {self.last_response}")
            return True, [""]  # Timeout returns default value
            
        except Exception as e:
            self.logger.error(f"Error in detect: {e}")
            return False, None

    async def cleanup(self):
        """Cleanup IDP controller resources"""
        self.mqtt_client.stop_loop()
        self.mqtt_client.disconnect()
        self.logger.info("IDP controller cleaned up")
