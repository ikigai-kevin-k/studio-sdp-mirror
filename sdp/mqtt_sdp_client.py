import logging
import time
import json
import requests
from datetime import datetime
from mqtt_wrapper import MQTTClientWrapper
from los_api.api import start_post, deal_post, finish_post

class MqttClient_SDP(MQTTClientWrapper):
    """SDP MQTT Client for sending test commands"""
    
    def __init__(self, client_id, broker, port, topic=None, keepalive=60):
        """Initialize SDP client"""
        super().__init__(client_id, broker, port, topic, keepalive)
        self.cmdTopic = None
        self.resTopic = None
        self.response_received = False
        self.last_response = None
        self.dice_result = None
        self.connected = False
        
        # LOS API 相關設定
        self.los_url = 'https://crystal-los.iki-cit.cc/v1/service/sdp/table/'
        self.game_code = 'SDP-003'
        self.token = 'E5LN4END9Q'
        self.url = self.los_url + self.game_code
        self.current_round_id = None
        self.is_round_active = False

    def on_connect(self, client, userdata, flags, rc):
        """當成功連接到 MQTT broker 時被呼叫"""
        if rc == 0:
            self.connected = True
            self.logger.info("Successfully connected to MQTT broker")
        else:
            self.connected = False
            self.logger.error(f"Failed to connect to MQTT broker with code: {rc}")

    def get_los_headers(self):
        """取得 LOS API 需要的 headers"""
        return {
            'accept': 'application/json',
            'Bearer': f'Bearer {self.token}',
            'x-signature': 'los-local-signature',
            'Content-Type': 'application/json'
        }

    def setup_topics(self, rx=None, tx=None):
        """設置訂閱和發布的主題"""
        if rx is None:
            rx = "ikg/idp/dice/response"  # 接收回應的主題
        if tx is None:
            tx = "ikg/idp/dice/command"   # 發送命令的主題
            
        self.cmdTopic = tx  # 用於發送命令
        self.resTopic = rx  # 用於接收回應
        self.subscribe(self.resTopic)  # 訂閱回應主題
        self.logger.info(f"Topics setup - Command: {self.cmdTopic}, Response: {self.resTopic}")

    def check_connection(self):
        """檢查 MQTT 連接狀態"""
        return self.connected and self.client.is_connected()

    async def wait_for_connection(self, timeout=10):
        """等待 MQTT 連接成功"""
        start_time = time.time()
        while not self.check_connection() and (time.time() - start_time) < timeout:
            await asyncio.sleep(0.1)
        return self.check_connection()

    def send_command(self, command):
        """Send command message"""
        try:
            self.logger.info(f"Sending command: {command}")
            result = self.publish(self.cmdTopic, json.dumps(command))
            
            # 在某些 MQTT 實現中，publish 成功時返回 None 是正常的
            # 只要沒有拋出異常，我們就認為發送成功
            self.logger.info(f"Command sent successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending command: {str(e)}")
            return False

    def process_message(self, topic, payload):
        """Process received message"""
        try:
            self.logger.info(f"Processing message from {topic}: {payload}")
            
            # 如果是 IDP 的回應
            if topic == self.resTopic:
                response_data = json.loads(payload)
                if "response" in response_data and response_data["response"] == "result":
                    if "arg" in response_data and "res" in response_data["arg"]:
                        dice_result_str = response_data["arg"]["res"]
                        self.dice_result = json.loads(dice_result_str)
                        self.response_received = True
                        self.last_response = payload
                        self.logger.info(f"Updated dice_result: {self.dice_result}")
                    
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse message JSON: {e}")
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")

    def _on_message(self, client, userdata, message):
        """Handle received messages"""
        try:
            payload = message.payload.decode()
            self.logger.info(f"Received message on {message.topic}: {payload}")
            
            # 處理訊息
            self.process_message(message.topic, payload)
            
        except Exception as e:
            self.logger.error(f"Error in _on_message: {e}")

    def send_detect_command(self, round_id, input_stream="https://192.168.88.213:8088/live/r1234_dice.flv", output_stream=""):
        """Send detect command"""
        try:
            # 重置狀態
            self.response_received = False
            self.last_response = None
            self.dice_result = None
            
            command = {
                "command": "detect",
                "arg": {
                    "round_id": round_id,
                    "input": input_stream,
                    "output": output_stream
                }
            }
            
            self.logger.info(f"Sending detect command for round {round_id}")
            
            # 發送命令
            if not self.send_command(command):
                self.logger.error("Failed to send detect command")
                return False, None
            
            self.logger.info("Waiting for IDP response...")
            
            # 等待回應
            timeout = 7
            start_time = time.time()
            
            while (time.time() - start_time) < timeout:
                if self.dice_result is not None:
                    self.logger.info(f"Received dice result in send_detect_command: {self.dice_result}")
                    return True, self.dice_result
                # time.sleep(0.1)
            
            self.logger.warning("No valid response received within timeout")
            if self.last_response:
                self.logger.warning(f"Last response was: {self.last_response}")
            return False, None
            
        except Exception as e:
            self.logger.error(f"Error in send_detect_command: {e}")
            return False, None

    async def start_game_round(self):
        """開始新的遊戲回合"""
        try:
            headers = self.get_los_headers()
            response = requests.post(f'{self.url}/start', headers=headers, json={})

            if response.status_code != 200:
                self.logger.error(f"Start round failed: {response.status_code} - {response.text}")
                return None

            try:
                response_data = response.json()
                round_id = response_data.get('data', {}).get('table', {}).get('tableRound', {}).get('roundId')
                
                if not round_id:
                    self.logger.error("Round ID not found in response")
                    return None
                
                self.logger.info(f"Successfully started round: {round_id}")
                return round_id
                
            except json.JSONDecodeError:
                self.logger.error("Failed to parse start response")
                return None
                
        except Exception as e:
            self.logger.error(f"Error starting round: {e}")
            return None

    async def send_deal_result(self, round_id, results):
        """發送骰子結果"""
        try:
            headers = self.get_los_headers()
            data = {
                "roundId": round_id,
                "sicBo": results
            }
            
            response = requests.post(f'{self.url}/deal', headers=headers, json=data)
            
            if response.status_code != 200:
                self.logger.error(f"Deal failed: {response.status_code} - {response.text}")
                return False
                
            self.logger.info(f"Successfully sent deal result for round {round_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending deal result: {e}")
            return False

    async def finish_round(self):
        """結束當前回合"""
        if not self.current_round_id:
            return True
            
        try:
            headers = self.get_los_headers()
            response = requests.post(f'{self.url}/finish', headers=headers, json={})
            
            if response.status_code != 200:
                self.logger.error(f"Finish round failed: {response.status_code} - {response.text}")
                return False
                
            self.logger.info(f"Successfully finished round {self.current_round_id}")
            self.current_round_id = None
            self.is_round_active = False
            return True
            
        except Exception as e:
            self.logger.error(f"Error finishing round: {e}")
            return False

    async def run_game_cycle(self):
        """執行一局遊戲的完整流程"""
        try:
            # 如果有未完成的回合，先等待 IDP 結果
            if self.current_round_id:
                self.logger.info(f"Waiting for previous round {self.current_round_id} to complete...")
                timeout = 0
                start_time = time.time()
                while not self.response_received and (time.time() - start_time) < timeout:
                    await asyncio.sleep(0.1)
                
                if self.response_received:
                    # 處理 IDP 結果
                    try:
                        result = json.loads(self.last_response)
                        dice_results = result.get('data', {}).get('results', [])
                        if dice_results:
                            await self.send_deal_result(self.current_round_id, dice_results)
                    except Exception as e:
                        self.logger.error(f"Error processing IDP response: {e}")
                
                # 無論是否收到結果，都重置回合狀態
                self.current_round_id = None
                self.is_round_active = False
                # await asyncio.sleep(2)

            # 開始新局
            self.logger.info("Starting new game round...")
            round_id = await self.start_game_round()
            if not round_id:
                self.logger.error("Failed to start new round")
                # await asyncio.sleep(5)
                return False

            self.current_round_id = round_id
            self.is_round_active = True
            self.response_received = False
            self.last_response = None

            # 通知骰子震動
            self.logger.info("Notifying shaker to execute...")
            shake_command = {
                "command": "shake",
                "arg": {
                    "round_id": round_id
                }
            }
            self.send_command(shake_command)
            # await asyncio.sleep(5)  # 等待骰子停止

            # 請求 IDP 辨識
            self.logger.info("Requesting IDP detection...")
            detect_command = {
                "command": "detect",
                "arg": {
                    "round_id": round_id
                }
            }
            self.send_command(detect_command)

            return True

        except Exception as e:
            self.logger.error(f"Error in game cycle: {e}")
            return False

    async def run_self_test(self, betting_duration=8, shake_duration=7, result_duration=4):
        """執行自我測試，確認與 Shaker Client 的連接和控制"""
        self.logger.info("Starting self test...")
        
        try:
            # 1. 等待 MQTT 連接
            self.logger.info("Waiting for MQTT connection...")
            if not await self.wait_for_connection():
                self.logger.error("MQTT connection test failed: Could not connect to broker")
                return False
            self.logger.info("MQTT connection test: OK")

            while True:  # 無限循環執行遊戲流程
                try:
                    # 2. 測試 LOS API 連接
                    self.logger.info("Testing LOS API connection...")
                    response = start_post(self.url, self.token)
                    if isinstance(response, tuple):
                        round_id = response[0]  # 只取得 round_id 字串，不要 tuple
                    else:
                        round_id = response
                    
                    if round_id == -1:
                        self.logger.error("LOS API connection test failed: Could not start new round")
                        continue
                    self.logger.info(f"LOS API connection test: OK, round_id: {round_id}")
                    
                    # 3. 測試發送 shake 命令
                    self.logger.info(f"Testing shake command with round ID: {round_id}")
                    shake_command = {
                        "command": "shake",
                        "arg": {
                            "round_id": round_id  # 使用字串格式的 round_id
                        }
                    }
                    
                    betting_time_to_last_bet_duration = betting_duration
                    time.sleep(betting_time_to_last_bet_duration)

                    if not self.send_command(shake_command):
                        self.logger.error("Failed to send shake command")
                        continue
                    
                    self.logger.info("Shake command sent, waiting for execution...")
                    await asyncio.sleep(shake_duration)  # 等待骰子執行
                    
                    # 4. 測試發送 detect 命令
                    self.logger.info("Testing detect command...")
                    success, dice_result = self.send_detect_command(round_id, input_stream="https://192.168.88.213:8088/live/r1234_dice.flv", output_stream="")
                    
                    if not success or dice_result is None:
                        self.logger.error("Failed to get dice result")
                        continue
                    
                    self.logger.info(f"Received dice result: {dice_result}")
                    
                    # 5. 發送結果到 LOS API
                    self.logger.info("Sending deal result to LOS API...")
                    headers = self.get_los_headers()
                    deal_data = {
                        "roundId": round_id,  # 使用字串格式的 round_id
                        "sicBo": dice_result
                    }
                    
                    deal_response = requests.post(f'{self.url}/deal', 
                                                headers=headers, 
                                                json=deal_data)
                    
                    if deal_response.status_code != 200:
                        self.logger.error(f"Deal failed: {deal_response.status_code} - {deal_response.text}")
                        continue
                        
                    self.logger.info("Deal result sent successfully")
                    time.sleep(result_duration)  # 等待結果處理
                    
                    # 6. 結束回合
                    self.logger.info("Finishing round...")
                    finish_response = requests.post(f'{self.url}/finish', 
                                                  headers=headers, 
                                                  json={})
                    
                    if finish_response.status_code != 200:
                        self.logger.error(f"Finish failed: {finish_response.status_code} - {finish_response.text}")
                        continue
                        
                    self.logger.info("Round finished successfully")
                    
                    # 7. 等待一段時間後開始下一輪
                    self.logger.info("Waiting before starting next round...")

                    time.sleep(2)    

                except Exception as e:
                    self.logger.error(f"Error in game cycle: {e}")
                    continue
            
        except KeyboardInterrupt:
            self.logger.info("Self test interrupted by user")
            return True
        except Exception as e:
            self.logger.error(f"Self test failed with error: {str(e)}")
            return False

async def main():
    """Main function"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    broker = "206.53.48.180"
    client_id = "sdp_client"
    
    sdp_client = MqttClient_SDP(client_id, broker, 1883)
    
    try:
        # 連接到 MQTT broker
        sdp_client.connect()
        sdp_client.start_loop()
        
        # 設置主題
        sdp_client.setup_topics(
            rx="ikg/idp/dice/response",
            tx="ikg/idp/dice/command"
        )
        
        # 執行自我測試
        self_test_result = await sdp_client.run_self_test()
        if not self_test_result:
            sdp_client.logger.error("Self test failed, exiting...")
            return
        
        sdp_client.logger.info("Self test passed, starting main loop...")
        
        # # 主要遊戲循環
        # while True:
        #     await sdp_client.run_game_cycle()
        #     # await asyncio.sleep(2)
            
    except KeyboardInterrupt:
        sdp_client.logger.info("MQTT client interrupted by user")
    finally:
        sdp_client.stop_loop()
        sdp_client.disconnect()

async def run_test():
    client = MqttClient_SDP("sdp_test_client", "206.53.48.180", 1883)
    try:
        client.connect()
        client.start_loop()
        
        # 設置正確的主題
        client.setup_topics(
            rx="ikg/idp/dice/response",  # 接收回應
            tx="ikg/idp/dice/command"    # 發送命令
        )
        
        if not await client.wait_for_connection():
            client.logger.error("Failed to connect to MQTT broker")
            return
            
        await client.run_self_test()
    finally:
        client.stop_loop()
        client.disconnect()

if __name__ == "__main__":
    import asyncio
    import argparse
    
    # 設置日誌級別為 DEBUG 以查看更多信息
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    parser = argparse.ArgumentParser(description='SDP MQTT Client')
    parser.add_argument('--self-test-only', action='store_true',
                      help='Run self test only and exit')
    parser.add_argument('--broker', type=str, default='206.53.48.180',
                      help='MQTT broker address')
    parser.add_argument('--port', type=int, default=1883,
                      help='MQTT broker port')
    parser.add_argument('--betting-duration', type=int, default=8,
                      help='Betting time duration in seconds')
    parser.add_argument('--shake-duration', type=int, default=7,
                      help='Shake duration in seconds')
    parser.add_argument('--result-duration', type=int, default=4,
                      help='Result display duration in seconds')
    
    args = parser.parse_args()
    
    if args.self_test_only:
        asyncio.run(run_test())
    else:
        # 修改 run_test 函數以接受新的參數
        async def run_test():
            client = MqttClient_SDP("sdp_test_client", args.broker, args.port)
            try:
                client.connect()
                client.start_loop()
                
                client.setup_topics(
                    rx="ikg/idp/dice/response",
                    tx="ikg/idp/dice/command"
                )
                
                if not await client.wait_for_connection():
                    client.logger.error("Failed to connect to MQTT broker")
                    return
                    
                await client.run_self_test(
                    betting_duration=args.betting_duration,
                    shake_duration=args.shake_duration,
                    result_duration=args.result_duration
                )
            finally:
                client.stop_loop()
                client.disconnect()

        asyncio.run(run_test())