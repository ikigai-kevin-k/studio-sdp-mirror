import asyncio
import logging
import json
import time
from typing import Optional
import requests
import argparse

from controller import GameType, GameConfig
from gameStateController import create_game_state_controller
from deviceController import IDPController, ShakerController
from mqttController import MQTTController

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SDPGame:
    """Main game class for SDP"""
    def __init__(self, config: GameConfig):
        self.config = config
        self.logger = logging.getLogger("SDPGame")
        
        # 初始化控制器
        self.game_controller = create_game_state_controller(config.game_type)
        self.mqtt_controller = MQTTController(
            client_id=f"sdp_controller_{config.room_id}",
            broker=config.broker_host,
            port=config.broker_port
        )
        self.idp_controller = IDPController(config)
        self.shaker_controller = ShakerController(config)
        self.running = False
        
        # LOS API configuration
        self.los_url = 'https://crystal-los.iki-cit.cc/v1/service/sdp/table/'
        self.game_code = config.room_id
        self.token = 'E5LN4END9Q'
        self.url = f"{self.los_url}{self.game_code}"

    async def initialize(self):
        """Initialize all controllers"""
        try:
            await self.mqtt_controller.initialize()
            await self.idp_controller.initialize()
            await self.shaker_controller.initialize()
            
            # 為 SicBo 遊戲設置 MQTT 控制器
            if self.config.game_type == GameType.SICBO:
                await self.game_controller.set_mqtt_controller(self.mqtt_controller)
                
            self.logger.info("All controllers initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            return False

    async def run_self_test(self):
        """Run self test for all components"""
        self.logger.info("Starting self test...")
        
        # 測試 MQTT 連接
        try:
            await self.mqtt_controller.initialize()
            self.logger.info("MQTT connection test passed")
        except Exception as e:
            self.logger.error(f"MQTT connection test failed: {e}")
            return False

        # 測試 IDP 控制器
        try:
            await self.idp_controller.initialize()
            self.logger.info("IDP controller test passed")
        except Exception as e:
            self.logger.error(f"IDP controller test failed: {e}")
            await self.mqtt_controller.cleanup()
            return False

        # 測試搖骰器控制器
        try:
            await self.shaker_controller.initialize()
            self.logger.info("Shaker controller test passed")
        except Exception as e:
            self.logger.error(f"Shaker controller test failed: {e}")
            await self.mqtt_controller.cleanup()
            await self.idp_controller.cleanup()
            return False

        self.logger.info("All self tests passed successfully")
        return True

    async def start(self):
        """Start the game system"""
        self.logger.info(f"Starting SDP game system for {self.config.game_type}")
        self.running = True
        
        try:
            # Initialize all controllers
            await self.initialize()
            
            while self.running:
                # Start new round
                round_id = await self.start_game_round()
                if round_id:
                    await self.run_game_round(round_id)
                await asyncio.sleep(0.1)
                
        except Exception as e:
            self.logger.error(f"Error in game system: {e}")
        finally:
            await self.cleanup()

    async def start_game_round(self) -> Optional[str]:
        """Start a new game round using LOS API"""
        try:
            headers = {
                'accept': 'application/json',
                'Bearer': f'Bearer {self.token}',
                'x-signature': 'los-local-signature',
                'Content-Type': 'application/json'
            }
            response = requests.post(f'{self.url}/start', headers=headers, json={})
            
            if response.status_code == 200:
                data = response.json()
                round_id = data.get('data', {}).get('table', {}).get('tableRound', {}).get('roundId')
                return round_id
            return None
        except Exception as e:
            self.logger.error(f"Error starting game round: {e}")
            return None

    async def run_game_round(self, round_id: str):
        """Run a specific game round"""
        try:
            if self.config.game_type == GameType.SICBO:
                # Execute SicBo game round
                await self.game_controller.transition_to(SicBoState.START_GAME)
                await self.game_controller.handle_current_state()
                
                await self.game_controller.transition_to(SicBoState.PLACE_BET)
                await self.game_controller.handle_current_state()
                
                await self.game_controller.transition_to(SicBoState.SHAKE_DICE)
                await self.shaker_controller.shake(round_id)
                await self.game_controller.handle_current_state()
                
                await self.game_controller.transition_to(SicBoState.DETECT_RESULT)
                result = await self.idp_controller.detect(round_id)
                await self.game_controller.handle_current_state()
                
                await self.game_controller.transition_to(SicBoState.WINNING_NUMBER)
                await self.game_controller.handle_current_state()
                
            # Add other game types here as needed
            
        except Exception as e:
            self.logger.error(f"Error in game round {round_id}: {e}")
            if self.config.game_type == GameType.SICBO:
                await self.game_controller.transition_to(SicBoState.ERROR)
            await self.game_controller.handle_current_state()

    async def cleanup(self):
        """Cleanup all resources"""
        self.logger.info("Cleaning up resources")
        # 按照初始化的相反順序進行清理
        await self.shaker_controller.cleanup()
        await self.idp_controller.cleanup()
        await self.mqtt_controller.cleanup()
        if hasattr(self.game_controller, 'cleanup'):
            await self.game_controller.cleanup()

    async def stop(self):
        """Stop the game system"""
        self.logger.info("Stopping game system")
        self.running = False
        await self.cleanup()

async def main():
    # 設置命令列參數
    parser = argparse.ArgumentParser(description='SDP Game System')
    parser.add_argument('--self-test-only', action='store_true',
                      help='Run self test only and exit')
    parser.add_argument('--broker', type=str, default='206.53.48.180',
                      help='MQTT broker address')
    parser.add_argument('--port', type=int, default=1883,
                      help='MQTT broker port')
    parser.add_argument('--game-type', type=str, choices=['roulette', 'sicbo', 'blackjack'],
                      default='sicbo', help='Game type to run')
    
    args = parser.parse_args()

    # 設置日誌
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 創建遊戲配置
    config = GameConfig(
        game_type=GameType(args.game_type),
        room_id="SDP-003",  # 使用固定的 room_id
        broker_host=args.broker,
        broker_port=args.port
    )

    # 創建遊戲實例
    game = SDPGame(config)

    try:
        if args.self_test_only:
            # 只運行自我測試
            if await game.run_self_test():
                logging.info("Self test completed successfully")
            else:
                logging.error("Self test failed")
        else:
            # 正常遊戲流程
            if await game.initialize():
                # TODO: 實現完整的遊戲循環
                pass
    except KeyboardInterrupt:
        logging.info("Game interrupted by user")
    except Exception as e:
        logging.error(f"Game error: {e}")
    finally:
        await game.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
