import time
import os
import pty
import threading
import random
import logging
import asyncio
import websockets
import argparse
import analogist as ao
import generator as gen  # 新增這行導入


#  color constants
RED = '\033[91m'
GREEN = '\033[92m'
RESET = '\033[0m'
YELLOW = '\033[93m'  
BLUE = '\033[94m'    
MAGENTA = '\033[95m'  
GRAY = '\033[90m'     

class ColorfulLogger(logging.Logger):
    def __init__(self):
        super().__init__(name="roulette_sim_colorful_logger")
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler("./roulette_sim.log", mode="w"),
                logging.StreamHandler()
            ]
        )

    def log_with_color(self,message):
        self.info(message)

colorful_logger = ColorfulLogger()
log_with_color = colorful_logger.log_with_color

class StateMachine:
    """
    Refer to Cammegh SS2 Owner's handbook, p.49,
    First, implement the naive state transition logic without any external interruptions and internal errors.

    """
    P1_MAX_WAITING_TIME = 2
    P0_MAX_WAITING_TIME = 2

    P0_MAX_DELAY = 5
    # state transition waiting time
    X1_MAX_WAITING_TIME = 17
    X2_MAX_WAITING_TIME = 21
    X3_MAX_WAITING_TIME = 16
    X4_MAX_WAITING_TIME = 43
    X5_MAX_WAITING_TIME = 4
    X6_MAX_WAITING_TIME = 100

    LOG_FREQUENCY = 0.5 # default: 0.5s 1 times

    def __init__(self):
        self.data_protocol_modes = ["power_setting_mode","game_mode","operation_mode","self_test_mode","calibration_mode", "warning_flag_mode", "statistics_mode"]
        self.power_states = ["off","on"]
        self.game_states = ["table_closed","start_game","place_bet","ball_launch","no_more_bet","winning_number"]
        
        self.current_game_state = "table_closed"
        self.current_data_protocol_mode = "power_setting_mode"
        self.current_power_state = "off"

        self.p0_delay_counter = 0

        self.x1_state_transition_waiting_counter = 0
        self.x2_state_transition_waiting_counter = 0
        self.x3_state_transition_waiting_counter = 0
        self.x4_state_transition_waiting_counter = 0
        self.x5_state_transition_waiting_counter = 0
        self.x6_state_transition_waiting_counter = 0



class RouletteSimulator(StateMachine):
    """
    TODO:
    - We need to add a timer to check the physical time cost of each game round 
      whether exceeds the expected time cost (default: 1 minute)
      What is the range of tolerance?
    """

    def __init__(self):
        super().__init__()
        self.line_number = 1
        self.masterRoulettePort, self.slaveRoulettePort = self.create_virtual_serial_port()
        self.task = None

    async def start(self):
        """啟動模拟器"""
        self.task = asyncio.create_task(self.roulette_main_thread(self.masterRoulettePort))

    def create_virtual_serial_port(self):
        master, slave = pty.openpty()
        s_name = os.ttyname(slave)
        return master, s_name

    def reset_state_transition_waiting_counter(self):
        self.x1_state_transition_waiting_counter = 0
        self.x2_state_transition_waiting_counter = 0
        self.x3_state_transition_waiting_counter = 0
        self.x4_state_transition_waiting_counter = 0
        self.x5_state_transition_waiting_counter = 0
        self.x6_state_transition_waiting_counter = 0
        self.p0_delay_counter = 0

    def force_restart_game(self):
        """
        Read from the log line containing "*X;1"
        """
        self.reset_state_transition_waiting_counter()
        self.current_game_state = "start_game"
        self.current_data_protocol_mode = "game_mode"
        self.current_power_state = "on"
        self.read_ss2_protocol_log(LOG_FILE_NAME,3)
        pass

    def force_close_table(self):
        """
        Read from the log line containing "*X;6"
        """
        self.current_game_state = "table_closed"
        pass

    def force_power_off(self):
        """
        Read from the log line containing "*P 0"
        """
        self.current_power_state = "off"
        pass

    def power_on(self):
        """
        Read from the log line containing "*P 1"
        """
        self.current_power_state = "on"
        pass

    def warning_flag_handler(self,data):
        """
        Read from the log line containing "*W"
        """
        def num_to_sum(warning_flag_number):
            if warning_flag_number <= 0 or warning_flag_number > 15:
                return "number must be between 1 and 15"
            
            bases = [1, 2, 4, 8]
            result = []
            
            for base in bases:
                if n >= base:
                    result.append(str(base))
                    n -= base
            return result 
        
        warning_flag_number = int(data.split(";")[4])
        if not warning_flag_number:
            return
        else:
            warning_flag_list = num_to_sum(warning_flag_number)
            if  1 in warning_flag_list or\
                2 in warning_flag_list or\
                4 in warning_flag_list or\
                8 in warning_flag_list:
                log_with_color(f"{RED}Ball removed, not sensed{RESET}")
                self.force_restart_game()

    def state_discriminator(self,protocol_log_line):
        """
        When read one line of the protocol log, determine the current state of the roulette.
        """

        """
        TODO:
        - Add assertions to check the consistency of the state transitions between the state machine and the protocol log
            - Currently, consider the state transition without time delay
            - Assert the current game state whether obeys the expected state transition logic  
        """
        """
        Observation:
            p1 p0 1  2  3  4  5  6
        r1  2     17 13 16 34 3
        r2           21 15 35 4
        r3           15 16 43 3
        r4           12 14 34 3
        r5           18 16 36 3
        r6           16 14 36 3
        r7           3
               2     5           10

        maxp1 = 2
        maxp0 = 2
        maxx1 = 17
        max2 = 21 # 10.5
        max3 = 16 # 8
        max4 = 43 # 21.5
        max5 = 4 # 2
        max6 = 10 # 5

        21+16+43+4 = 84 ～ 42 seconds

        TODO:
        - State transition waiting counter
            - If the current state = the previous state, waiting counter + 1 
            - While the waiting counter > max_waiting_counter, raise an error
            - While the state changes, reset the waiting counter
        """
        data = protocol_log_line

        print("\n")
        print("log line:",data)
        print("current_data_protocol_mode:",self.current_data_protocol_mode)
        print("current_game_state:",self.current_game_state)
        print("current_power_state:",self.current_power_state)

        if "*X;" in data:
            print(f"{GREEN}X1 state transition waiting counter:{RESET}",self.x1_state_transition_waiting_counter)
            print(f"{GREEN}X2 state transition waiting counter:{RESET}",self.x2_state_transition_waiting_counter)
            print(f"{GREEN}X3 state transition waiting counter:{RESET}",self.x3_state_transition_waiting_counter)
            print(f"{GREEN}X4 state transition waiting counter:{RESET}",self.x4_state_transition_waiting_counter)
            print(f"{GREEN}X5 state transition waiting counter:{RESET}",self.x5_state_transition_waiting_counter)
            print(f"{GREEN}X6 state transition waiting counter:{RESET}",self.x6_state_transition_waiting_counter)
            print(f"{GREEN}P0 delay counter:{RESET}",self.p0_delay_counter)
            
            if "*X;1" in data:
                try:
                    if self.current_game_state == "table_closed":
                        self.current_data_protocol_mode = "game_mode"
                        self.current_game_state = "start_game"
                        self.reset_state_transition_waiting_counter()
                        return
                    elif self.current_game_state == "start_game":
                        if self.x1_state_transition_waiting_counter < self.X1_MAX_WAITING_TIME:
                            self.x1_state_transition_waiting_counter += 1
                            return
                        else:
                            # self.force_restart_game()
                            raise Exception(f"{RED}state transition time too long, there may be something wrong.{RESET}")
                except Exception as e:
                    log_with_color(f"Error asserting state transition: {e}")
                    raise Exception("state transition error, close the program.")
            
            elif "*X;2" in data:
                try:
                    if self.current_game_state == "start_game":
                        self.current_game_state = "place_bet"
                        self.reset_state_transition_waiting_counter()
                        print("Place Bet State, Send Start Record Event to Recorder")
                        return
                    
                    elif self.current_game_state == "winning_number":
                        self.current_game_state = "place_bet"
                        self.reset_state_transition_waiting_counter()
                        print("Place Bet State, Send Start Record Event to Recorder")
                        return
                    
                    elif self.current_game_state == "place_bet":
                        if self.x2_state_transition_waiting_counter < self.X2_MAX_WAITING_TIME:
                            self.x2_state_transition_waiting_counter += 1
                            return
                        else:
                            raise Exception(f"{RED}state transition time too long, there may be something wrong.{RESET}")
                except Exception as e:
                    log_with_color(f"Error asserting state transition: {e}")
                    raise Exception("state transition error, close the program.")

            elif "*X;3" in data:
                try:
                    if self.current_game_state == "place_bet":
                        self.current_game_state = "ball_launch"
                        self.reset_state_transition_waiting_counter()
                        return
                    elif self.current_game_state == "ball_launch":
                        if self.x3_state_transition_waiting_counter < self.X3_MAX_WAITING_TIME:
                            self.x3_state_transition_waiting_counter += 1
                            return
                        else:
                            raise Exception(f"{RED}state transition time too long, there may be something wrong.{RESET}")
                except Exception as e:
                    log_with_color(f"Error asserting state transition: {e}")
                    raise Exception("state transition error, close the program.")
            elif "*X;4" in data:
                try:
                    if self.current_game_state == "ball_launch":
                        self.current_game_state = "no_more_bet"
                        self.reset_state_transition_waiting_counter()
                        return
                    elif self.current_game_state == "no_more_bet":
                        if self.x4_state_transition_waiting_counter < self.X4_MAX_WAITING_TIME:
                            self.x4_state_transition_waiting_counter += 1
                            return
                        else:
                            raise Exception(f"{RED}state transition time too long, there may be something wrong.{RESET}")
                except Exception as e:
                    log_with_color(f"Error asserting state transition: {e}")
                    raise Exception("state transition error, close the program.")
            elif "*X;5" in data or data.strip().isdigit():
                try:
                    if self.current_game_state == "no_more_bet":
                        self.current_game_state = "winning_number"
                        self.reset_state_transition_waiting_counter()
                        print("Winning Number State, Send End Record Event to Recorder")
                        return
                    elif self.current_game_state == "winning_number":
                        if self.x5_state_transition_waiting_counter < self.X5_MAX_WAITING_TIME:
                            self.x5_state_transition_waiting_counter += 1
                            return
                        else:
                            raise Exception(f"{RED}state transition time too long, there may be something wrong.{RESET}")
                except Exception as e:
                    log_with_color(f"Error asserting state transition: {e}")
                    raise Exception("state transition error, close the program.")

            elif "*X;6" in data:
                try:
                    if self.current_game_state != "table_closed":
                        self.current_game_state = "table_closed"
                        self.reset_state_transition_waiting_counter()
                        return
                    else:
                        if self.x6_state_transition_waiting_counter < self.X6_MAX_WAITING_TIME:
                            self.x6_state_transition_waiting_counter += 1
                            return
                        else:
                            # self.force_close_table()
                            raise Exception(f"{RED}state transition time too long, there may be something wrong.{RESET}")
                except Exception as e:
                    log_with_color(f"Error asserting state transition: {e}")
                    raise Exception("state transition error, close the program.")

            else:
                log_with_color(f"unknown game state: {data}")
                raise Exception("unknown game state, close the program.")
            
        elif "*o" in data:
            self.current_data_protocol_mode = "operation_mode"
            """
            Operation mode
            """
            pass
        elif "*F" in data:
            self.current_data_protocol_mode = "self_test_mode"
            """
            Self-test mode
            """
            pass
        elif "*P" in data:
            """
            Power setting mode
            """
            
            if "*P 1" in data and self.current_power_state == "off":
                """add a condition: the next line is *P OK"""
                self.current_power_state = "on"
                """In arcade mode, power on will trigger table open"""
                self.current_data_protocol_mode = "power_setting_mode"
                return
            
            elif "*P 0" in data and self.current_power_state == "on":
                """add a condition: the next line is *P OK"""
                self.current_power_state = "off"
                """off will trigger table force close"""
                self.current_game_state = "table_closed"
                self.current_data_protocol_mode = "power_setting_mode"

                if "*X:6" not in data and self.p0_delay_counter < self.P0_MAX_DELAY:
                    self.p0_delay_counter += 1
                else:
                    raise Exception(f"{RED}P0 delay time too long, there may be something wrong.{RESET}")
                return
            
            elif "*P OK" in data:
                pass
                return
            else:
                log_with_color(data)
                raise Exception("unknown power state.")            

        elif "*C" in data:
            self.current_data_protocol_mode = "calibration_mode"
            """
            Calibration mode
            """
            pass
        elif "*W" in data:
            self.current_data_protocol_mode = "warning_flag_mode"
            """
            Warning flag mode
            Restart the game
            """
            # self.game_state_transition_to("start_game")
            self.current_game_state = "start_game"
            pass
        elif "*M" in data:
            self.current_data_protocol_mode = "statistics_mode"
            """
            Statistics mode
            """
            pass

        elif data.strip().isdigit():                 
            """
            The number of the winning number
            """
            pass
        else:
            log_with_color(data)
            raise Exception("unknown protocol log type.")

    def read_ss2_protocol_log(self, file_name):
        try:
            with open(file_name, "r") as file:
                lines = file.readlines()
                if self.line_number <= len(lines):
                    line = lines[self.line_number - 1]
                    log_with_color(f"讀取到數據: {line.strip()}")  # 添加調試信息
                    return line.strip()
                else:
                    log_with_color("到達文件末尾")
                    return None
        except Exception as e:
            log_with_color(f"讀取文件錯誤: {e}")
            return None

    def roulette_state_display(self):
        log_with_color(f"{RESET}Current{GREEN} {YELLOW}game state:{RESET} {self.current_game_state}{RESET}")
        log_with_color(f"{RESET}Current{GREEN} {BLUE}data protocol mode:{RESET} {self.current_data_protocol_mode}{RESET}")
        if self.current_power_state == "on":
            log_with_color(f"{RESET}Current{GREEN} {MAGENTA}power state:{RESET} {GREEN}{self.current_power_state}{RESET}")
        elif self.current_power_state == "off":
            log_with_color(f"{RESET}Current{RED} {MAGENTA}power state:{RESET} {RED}{self.current_power_state}{RESET}")
    
    def roulette_write_data_to_sdp(self,data):
        os.write(self.masterRoulettePort, data.encode())
        log_with_color(f"Roulette simulator sent to SDP: {data.encode().strip()}")

    def roulette_read_data_from_sdp(self):
        read_data = os.read(self.masterRoulettePort, 1024) # 1024 is the buffer size
        if read_data:
            log_with_color(f"Roulette supposed to be received from SDP: {read_data.decode().strip()}")

    async def roulette_main_thread(self, master):
        log_with_color("start roulette_main_thread")
        
        if not os.path.exists(LOG_FILE_NAME):
            log_with_color(f"error: log file {LOG_FILE_NAME} not found")
            return
            
        while True:
            try:
                data = self.read_ss2_protocol_log(LOG_FILE_NAME)
                if not data:
                    log_with_color("read completed, exit loop")
                    break
                    
                log_with_color(f"process line {self.line_number} data: {data}")
                
                try:
                    self.state_discriminator(data)
                    await self.update_sdp_state()
                    self.roulette_write_data_to_sdp(data)
                    self.roulette_read_data_from_sdp()
                except Exception as e:
                    log_with_color(f"error processing data: {e}")
                    break
                    
                self.line_number += 1
                await asyncio.sleep(self.LOG_FREQUENCY)  # 使用 await
                
            except Exception as e:
                log_with_color(f"main loop error: {e}")
                break
                
        log_with_color("roulette_main_thread end")

class TestRouletteSimulator(RouletteSimulator):
    def __init__(self, recorder_port=8765, room_id=1):
        print(f"Initializing TestRouletteSimulatorNonArcade with port {recorder_port}, room {room_id}")
        super().__init__()
        self.recorder_port = recorder_port
        self.room_id = room_id
        self.websocket = None
        self.running = True
        self.game_state = "game_start"
        self.current_number = None
        self.heartbeat_task = None
        self.connection_enabled = True  # 新增連接狀態標記
        
    async def send_heartbeat(self):
        """發送心跳信號到recorder"""
        while self.running:
            try:
                if self.websocket:
                    await self.websocket.send("heartbeat")
                await asyncio.sleep(1)  # 每秒發送一次心跳
            except Exception as e:
                print(f"心跳發送錯誤: {e}")
                break

    async def toggle_connection(self, enabled):
        """切換連接狀態"""
        self.connection_enabled = enabled
        if not enabled:
            self.game_state = "error_state"
            if self.websocket:
                await self.websocket.send("error_state")
            print("模擬斷訊: 已停用連接")
        else:
            self.game_state = "game_start" 
            if self.websocket:
                await self.websocket.send("game_start")
            print("恢復連接: 已啟用連接")

    async def run_game_cycle(self):
        """模擬一個完整的輪盤遊戲週期"""
        try:
            # 檢查連接狀態
            if not self.connection_enabled:
                print("連接已停用，等待恢復...")
                await asyncio.sleep(1)
                return
                
            # 開始新局
            if self.game_state == "game_start":
                print("game start")
                self.game_state = "place_bet"
                await asyncio.sleep(2)  # 等待下注時間
            
            # 下注階段
            elif self.game_state == "place_bet":
                print("place_bet")
                self.game_state = "no_more_bets"
                await asyncio.sleep(1)
            
            # 停止下注
            elif self.game_state == "no_more_bets":
                # 通知 Recorder 開始錄製
                await self.websocket.send("start_recording")
                print("no_more_bets")
                # 生成隨機中獎號碼 (0-36)
                self.current_number = random.randint(0, 36)
                self.game_state = "winning_number"
                await asyncio.sleep(3)
            
            # 顯示中獎號碼
            elif self.game_state == "winning_number":
                print(f"winning number: {self.current_number}")
                # 通知 Recorder 停止錄製
                await self.websocket.send("stop_recording")
                self.game_state = "place_bet"
                await asyncio.sleep(2)
            
            print(f"current game state: {self.game_state}")
            
        except Exception as e:
            print(f"game cycle error: {str(e)}")
            raise
    
    async def cleanup(self):
        """清理資源"""
        print("cleaning up...")
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                print(f"close websocket error: {str(e)}")
        self.running = False
        print("cleaning up completed")

    async def start(self):
        print("Starting simulator...")
        try:
            uri = f"ws://localhost:{self.recorder_port}"
            print(f"Connecting to recorder at {uri}")
            
            async with websockets.connect(uri) as websocket:
                self.websocket = websocket
                print(f"Connected to recorder at {uri}")
                
                # 啟動心跳任務
                self.heartbeat_task = asyncio.create_task(self.send_heartbeat())
                
                # 新增: 啟動命令處理任務
                command_task = asyncio.create_task(self.handle_commands())
                
                while self.running:
                    try:
                        await self.run_game_cycle()
                        await asyncio.sleep(0.1)
                    except asyncio.CancelledError:
                        print("Game cycle cancelled")
                        break
                    except Exception as e:
                        print(f"Error in game cycle: {e}")
                        break
                        
        except Exception as e:
            print(f"Connection error: {e}")
            raise
        finally:
            print("Cleaning up...")
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
            await self.cleanup()

    async def handle_commands(self):
        """處理用戶輸入的命令"""
        while self.running:
            try:
                command = await asyncio.get_event_loop().run_in_executor(
                    None, input, "輸入命令 (enable/disable/quit): "
                )
                
                if command.lower() == "disable":
                    await self.toggle_connection(False)
                elif command.lower() == "enable":
                    await self.toggle_connection(True)
                elif command.lower() == "quit":
                    self.running = False
                    break
                else:
                    print("未知命令。可用命令: enable, disable, quit")
                    
            except Exception as e:
                print(f"命令處理錯誤: {e}")
                continue

class DiceShaker:
    """骰子震動器控制類別"""
    
    def __init__(self, recorder_port=8765):
        self.recorder_port = recorder_port
        self.websocket = None
        self.running = True
        self.shaking_state = "stopped"  # 'stopped' 或 'shaking'
        self.heartbeat_task = None
        self.piout = ao.AController(pwm_freq=200000, sample_freq_hz=1000)
        self.shake_task = None  # 新增：用於控制震動任務
        
        # 初始化 generator 的 logger
        gen.log = gen.init_logger(3)  # 直接傳入數值參數，不使用關鍵字參數
    
    async def start_shaking(self):
        """開始震動"""
        if self.shaking_state == "stopped":
            self.shaking_state = "shaking"
            log_with_color("開始震動骰子")
            
            # 使用 generator.py 中的 genMeander 函數
            wave_gen = gen.genMeander(
                time_sec=5,
                freq_hz=10, 
                smoothing_msec=20,
                amp=0.8,
                sampling_freq=gen.SAMPLING_FREQ_HZ
            )
            
            # 使用 plot_and_generate 來顯示波形
            plotted_wave = gen.plot_and_generate(
                gen.genMeander,
                5, 10, 20, 0.8, gen.SAMPLING_FREQ_HZ
            )
            
            # 創建新的震動任務
            self.shake_task = asyncio.create_task(self.piout.runRoll(plotted_wave))

    async def stop_shaking(self):
        """停止震動"""
        if self.shaking_state == "shaking":
            self.shaking_state = "stopped"
            log_with_color("停止震動骰子")
            
            # 取消正在執行的震動任務
            if self.shake_task and not self.shake_task.done():
                self.shake_task.cancel()
                try:
                    await self.shake_task
                except asyncio.CancelledError:
                    pass
            
            # 設置輸出為0
            await self.piout.run(duty=0, timeSec=0.1)

    async def cleanup(self):
        """清理資源"""
        log_with_color("清理 DiceShaker 資源...")
        await self.stop_shaking()
        self.piout.close()
        self.running = False

async def test_dice_shaker():
    """測試 DiceShaker 功能的主程式"""
    shaker = DiceShaker()
    
    try:
        print("開始測試 DiceShaker...")
        
        # 測試震動循環
        for i in range(3):  # 執行3輪測試
            print(f"\n開始第 {i+1} 輪震動測試")
            print("開始震動 (5秒)...")
            await shaker.start_shaking()
            
            print("等待震動完成 (2秒)...")
            await asyncio.sleep(2)
            
            print("停止震動...")
            await shaker.stop_shaking()
            
            print("暫停 (1秒)...")
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\n收到中斷信號")
    except Exception as e:
        print(f"錯誤: {str(e)}")
    finally:
        await shaker.cleanup()
        print("測試完成")

async def main(port=None, room_id=None):
    # 如果參數是通過命令行傳入的
    if port is None or room_id is None:
        parser = argparse.ArgumentParser(description='SDP Server')
        parser.add_argument('--recorder-port', type=int, required=True,
                          help='Port number of the recorder server')
        parser.add_argument('--room-id', type=int, required=True,
                          help='Room ID for the instance')
        args = parser.parse_args()
        port = args.recorder_port
        room_id = args.room_id
    
    print(f"Starting SDP simulator with recorder port: {port}, room id: {room_id}")
    
    roulette = TestRouletteSimulator(
        recorder_port=port,
        room_id=room_id
    )
    
    try:
        print("Initializing roulette simulator...")
        await roulette.start()
    except KeyboardInterrupt:
        print("Stopping roulette simulator...")
        await roulette.cleanup()
    except Exception as e:
        print(f"Error running roulette simulator: {str(e)}")
        await roulette.cleanup()
        raise

if __name__ == "__main__":
    # 新增命令行參數解析
    parser = argparse.ArgumentParser(description='Dice Shaker Test')
    parser.add_argument('--test-shaker', action='store_true',
                      help='Run dice shaker test')
    parser.add_argument('--recorder-port', type=int, default=8765,
                      help='Port number of the recorder server')
    parser.add_argument('--room-id', type=int, default=1,
                      help='Room ID for the instance')
    
    args = parser.parse_args()
    
    if args.test_shaker:
        asyncio.run(test_dice_shaker())
    else:
        # 原有的 roulette simulator 邏輯
        asyncio.run(main(args.recorder_port, args.room_id))