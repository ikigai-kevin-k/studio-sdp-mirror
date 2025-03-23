import logging
import asyncio
import time
from typing import Optional, Dict, List, Tuple
from transitions.extensions.asyncio import AsyncMachine
from controller import BaseGameStateController, GameType, GameConfig, SicBoState
from proto.mqtt import MQTTLogger, MQTTConnector
from device.idp import IDPConnector
from los_api.api import (
    start_post, 
    deal_post, 
    finish_post, 
    cancel_post,
    get_roundID,  # 確保正確導入
)

class ShakerConnector:
    """Controls dice shaker operations"""
    def __init__(self, config: GameConfig):
        self.config = config
        self.mqtt_client = MQTTLogger(
            client_id=f"shaker_controller_{config.room_id}",
            broker="192.168.88.250",  # Specific broker for shaker
            port=config.broker_port
        )
        self.mqtt_client.client.username_pw_set("PFC", "wago")  # Specific credentials for shaker
        self.logger = logging.getLogger("ShakerConnector")

    async def initialize(self):
        """Initialize shaker controller"""
        if not self.mqtt_client.connect():
            raise Exception("Failed to connect to MQTT broker")
        self.mqtt_client.start_loop()
        self.mqtt_client.subscribe("ikg/shaker/response")

    async def shake(self, round_id: str):
        """Shake the dice using Billy-II settings"""
        cmd = "/cycle/?pattern=0&parameter1=10&parameter2=0&amplitude=0.41&duration=6"
        topic = "ikg/sicbo/Billy-II/listens"
        
        self.mqtt_client.publish(topic, cmd)
        self.mqtt_client.publish(topic, "/state")
        self.logger.info(f"Shake command sent for round {round_id}")

    async def cleanup(self):
        """Cleanup shaker controller resources"""
        self.mqtt_client.stop_loop()
        self.mqtt_client.disconnect()

class DiceShakerController(BaseGameStateController):
    """Controls SicBo game state transitions with integrated shaker control"""
    
    states = [
        SicBoState.WAITING_START,
        SicBoState.SHAKING,
        SicBoState.DETECTING,
        SicBoState.RESULT_READY,
        SicBoState.ERROR
    ]
    
    transitions = [
        {
            'trigger': 'start_game',
            'source': '*',
            'dest': SicBoState.WAITING_START,
            'before': 'before_start_game'
        },
        {
            'trigger': 'start_shake',
            'source': SicBoState.WAITING_START,
            'dest': SicBoState.SHAKING,
            'before': 'before_shake'
        },
        {
            'trigger': 'start_detect',
            'source': SicBoState.SHAKING,
            'dest': SicBoState.DETECTING,
            'before': 'before_detect'
        },
        {
            'trigger': 'set_result',
            'source': SicBoState.DETECTING,
            'dest': SicBoState.RESULT_READY,
            'conditions': ['is_valid_result'],
            'before': 'before_set_result'
        },
        {
            'trigger': 'handle_error',
            'source': '*',
            'dest': SicBoState.ERROR,
            'before': 'before_error'
        }
    ]

    def __init__(self, config: GameConfig):
        # 先初始化基本屬性
        self.config = config
        self.logger = logging.getLogger("DiceShakerController")
        
        # 從配置中讀取時間控制參數
        self.shake_duration = config.shake_duration
        self.detect_wait_time = config.detect_wait_time
        self.result_duration = config.result_duration
        
        # 初始化 LOS API 相關參數
        self.los_url = config.los_base_url
        self.los_token = config.los_token
        self.room_id = config.room_id
        
        # 初始化設備控制器
        self.mqtt = MQTTConnector(f"sicbo_controller_{config.room_id}", 
                                config.broker_host, 
                                config.broker_port)
        self.idp = IDPConnector(config)
        self.shaker = ShakerConnector(config)
        
        # 遊戲狀態變數
        self.current_round_id: Optional[str] = None
        self.dice_result: Optional[List[int]] = None
        self.error_message: Optional[str] = None
        self.bet_period: Optional[int] = None

        # 最後才調用父類初始化
        super().__init__(GameType.SICBO)
        
        # 使用 AsyncMachine 替代 Machine
        self.machine = AsyncMachine(
            model=self,
            states=self.states,
            transitions=self.transitions,
            initial=SicBoState.WAITING_START,
            auto_transitions=False,
            send_event=True
        )

    def _setup_state_handlers(self) -> Dict:
        """Setup state transition handlers"""
        return {
            SicBoState.WAITING_START: self._handle_waiting_start,
            SicBoState.SHAKING: self._handle_shaking,
            SicBoState.DETECTING: self._handle_detecting,
            SicBoState.RESULT_READY: self._handle_result_ready,
            SicBoState.ERROR: self._handle_error
        }

    def _initialize_state(self):
        """Initialize state based on game type"""
        self.current_state = SicBoState.WAITING_START

    async def _handle_waiting_start(self):
        """Handle waiting start state"""
        self.logger.info("Waiting for game start...")

    async def _handle_shaking(self):
        """Handle shaking state"""
        self.logger.info("Shaking dice...")

    async def _handle_detecting(self):
        """Handle detecting state"""
        self.logger.info("Detecting dice result...")

    async def _handle_result_ready(self):
        """Handle result ready state"""
        self.logger.info("Result is ready")

    async def _handle_error(self):
        """Handle error state"""
        self.logger.error(f"Error state: {self.error_message}")

    async def initialize(self) -> bool:
        """Initialize all controllers"""
        try:
            # 初始化每個控制器
            await self.mqtt.initialize()
            await self.idp.initialize()
            await self.shaker.initialize()
            self.logger.info("All controllers initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Initialization error: {e}")
            return False

    def before_start_game(self, event):
        """Actions before starting new game"""
        self.current_round_id = None
        self.dice_result = None
        self.error_message = None

    def before_shake(self, event):
        """Actions before shaking dice"""
        self.current_round_id = event.kwargs.get('round_id')

    async def before_detect(self, event):
        """Actions before detecting dice"""
        await asyncio.sleep(self.config.shake_duration)

    def before_set_result(self, event):
        """Actions before setting result"""
        self.dice_result = event.kwargs.get('result')

    def before_error(self, event):
        """Actions before entering error state"""
        self.error_message = event.kwargs.get('error', 'Unknown error')
        self.logger.error(f"Error occurred: {self.error_message}")

    def is_valid_result(self, event) -> bool:
        """Validate dice detection result"""
        result = event.kwargs.get('result')
        return (isinstance(result, list) and 
                len(result) == 3 and 
                all(isinstance(x, int) and 1 <= x <= 6 for x in result))

    async def run_game_round(self) -> bool:
        """Run a complete game round"""
        try:
            # 檢查是否有未完成的局
            game_code = self.room_id
            get_url = self.config.los_get_url.format(game_code=game_code)
            post_url = self.config.los_post_url.format(game_code=game_code)
            
            round_id, status, bet_period = get_roundID(get_url, self.config.los_token)
            if round_id != "-1" and status not in ["finished", "cancelled"]:
                self.logger.warning(f"Found unfinished round {round_id} with status {status}")
                if status == "bet-stopped":
                    cancel_post(post_url, self.config.los_token)
                    await asyncio.sleep(1)  # 等待取消操作完成
            
            # 開始新局
            round_start_time = time.time()  # 記錄回合開始時間
            await self.to_waiting_start()
            
            # 呼叫 start_post API
            self.logger.info(f"Calling start_post with URL: {post_url}")
            round_id, bet_period = start_post(post_url, self.config.los_token)
            self.current_round_id = round_id
            self.bet_period = bet_period
            
            if self.current_round_id == "-1":
                error_msg = f"Failed to get round ID from {post_url}"
                self.logger.error(error_msg)
                await self.to_error()
                return False
            
            self.logger.info(f"Starting new round: {self.current_round_id}")
            
            # 計算下注時間
            betting_duration = bet_period + 0.5 - 4 - 2  # 0.5 for avoiding result faster than stream display
            self.logger.info(f"Waiting for betting period ({betting_duration:.1f} seconds)...")
            await asyncio.sleep(betting_duration)
            
            # 開始搖骰子
            await self.to_shaking()
            await self.shaker.shake(self.current_round_id)
            SHAKE_TIME = 7  # 7 seconds
            await asyncio.sleep(SHAKE_TIME + 0.5)  # 加 0.5 秒緩衝
            
            # 開始偵測
            await self.to_detecting()
            
            # 等待 IDP 偵測結果
            max_retries = 1  # 最大重試次數
            retry_count = 0
            
            while retry_count < max_retries:
                self.logger.info(f"Testing detect command... (attempt {retry_count + 1})")
                success, result = await self.idp.detect(self.current_round_id)
                
                # 檢查結果是否有效
                is_valid_result = (
                    success and 
                    result and 
                    isinstance(result, list) and 
                    all(isinstance(x, int) and x > 0 for x in result)
                )
                
                if is_valid_result:
                    self.dice_result = result
                    await self.to_result_ready()
                    
                    # 呼叫 deal_post API，修改結果格式
                    self.logger.info(f"Calling deal_post with result: {result}")
                    # await asyncio.sleep(0.25)  # 等待 0.25 秒再發送結果
                    deal_post(post_url, self.config.los_token, self.current_round_id, result)  # 直接傳遞整個結果陣列
                    finish_post(post_url, self.config.los_token)
                    
                    # 等待 3 秒後結束回合
                    await asyncio.sleep(3)
                    return True
                else:
                    self.logger.info("Invalid result received, retrying shake and detect...")
                    # 重新搖骰
                    await self.shaker.shake(self.current_round_id)
                    await asyncio.sleep(SHAKE_TIME + 0.5)
                    retry_count += 1
                    
                    if retry_count >= max_retries:
                        self.logger.error("Max retries reached, cancelling round")
                        await self.to_error()
                        cancel_post(post_url, self.config.los_token)
                        return False
                
        except Exception as e:
            self.logger.error(f"Game round error: {str(e)}")
            await self.to_error()
            if status == "bet-stopped":
                cancel_post(post_url, self.config.los_token)
            return False

    async def to_waiting_start(self):
        """Transition to waiting start state"""
        await self.trigger('start_game')

    async def to_shaking(self):
        """Transition to shaking state"""
        await self.trigger('start_shake', round_id=self.current_round_id)

    async def to_detecting(self):
        """Transition to detecting state"""
        await self.trigger('start_detect')

    async def to_result_ready(self):
        """Transition to result ready state"""
        await self.trigger('set_result', result=self.dice_result)

    async def to_error(self):
        """Transition to error state"""
        await self.trigger('handle_error', error="Game error")

    async def start(self):
        """Start the dice shaker controller"""
        self.logger.info("Starting Dice Shaker controller")
        try:
            # 先初始化
            if not await self.initialize():
                raise Exception("Failed to initialize controllers")
            
            # 開始主迴圈
            while True:
                try:
                    await self.run_game_round()
                    await asyncio.sleep(1)  # 每局之間暫停 1 秒
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"Game round error: {e}")
                    await asyncio.sleep(1)
        except Exception as e:
            self.logger.error(f"Start error: {e}")
            raise
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Cleanup all resources"""
        try:
            # 如果有進行中的局，嘗試取消
            if self.current_round_id and self.current_round_id != "-1":
                self.logger.info(f"Cancelling current round {self.current_round_id}")
                cancel_post(self.config.los_post_url, self.config.los_token)
                await asyncio.sleep(1)
            
            await self.mqtt.cleanup()
            await self.idp.cleanup()
            await self.shaker.cleanup()
            self.logger.info("All resources cleaned up")
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")
