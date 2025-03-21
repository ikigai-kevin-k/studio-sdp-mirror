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

    def _on_message(self, client, userdata, message):
        """Handle received messages"""
        try:
            payload = message.payload.decode()
            self.logger.info(f"Received message on {message.topic}: {payload}")
            
            # Process message
            self._process_message(message.topic, payload)
            
        except Exception as e:
            self.logger.error(f"Error in _on_message: {e}")
            self.handle_error()

    def _process_message(self, topic: str, payload: str):
        """Process received message"""
        try:
            if topic == "ikg/idp/dice/response":
                response_data = json.loads(payload)
                if "response" in response_data and response_data["response"] == "result":
                    if "arg" in response_data and "res" in response_data["arg"]:
                        self.last_response = payload
                        if self.state == IDPState.DETECTING:
                            self.process_result()
                            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse message JSON: {e}")
            self.handle_error()
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            self.handle_error()

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

    def is_valid_result(self, event):
        """Check if processed result is valid"""
        try:
            response_data = json.loads(self.last_response)
            dice_result = response_data["arg"]["res"]
            if (isinstance(dice_result, list) and 
                len(dice_result) == 3 and 
                all(isinstance(x, int) for x in dice_result)):
                self.dice_result = dice_result
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
        """Start detection process"""
        try:
            # Reset state if needed
            if self.state != IDPState.IDLE:
                self.reset()
            
            # Start detection
            self.start_detection(round_id=round_id)
            
            # Wait for result with timeout
            while True:
                if self.state == IDPState.RESULT_READY:
                    return True, self.dice_result
                elif self.state in [IDPState.ERROR, IDPState.TIMEOUT]:
                    return False, None
                elif time.time() - self.detection_start_time > self.timeout_duration:
                    self.handle_timeout()
                    return False, None
                    
                await asyncio.sleep(0.1)
                
        except Exception as e:
            self.logger.error(f"Error in detect: {e}")
            self.handle_error(error=str(e))
            return False, None

    async def cleanup(self):
        """Cleanup IDP controller resources"""
        self.mqtt_client.stop_loop()
        self.mqtt_client.disconnect()
