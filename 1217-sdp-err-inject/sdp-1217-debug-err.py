import time
import os
import pty
import threading
import random
import logging
import asyncio
import websockets
import argparse


#  color constants
RED = '\033[91m'
GREEN = '\033[92m'
RESET = '\033[0m'
YELLOW = '\033[93m'  
BLUE = '\033[94m'    
MAGENTA = '\033[95m'  
GRAY = '\033[90m'     

# Plan
# Self-test mode
# Plan:
# - Err 2 and WF1: No ball detected
# - Err 3: No ball position/winning number detected
# - Err 1/2/3/21/22/23: Sensor stuck
# - Err 4: Invalid ball direction
# - Err 1: Hardware fault
# - Err 5: Motor drive issue
# - Err 6: Encoder failutre or Wheel Miscalibration
# - Err 7/8: Ball drop failure 


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
        self.injection_server = None
        self.injection_port = 8764  # 注入服務器的端口
        self.running = True
        self.debug_mode = False
        self.log_file_name = "ss2_protocol2.log"
        self.error_state = None
        self.nmb_stuck_detected = False
        self.f2_counter = 0
        self.x4_state_transition_waiting_counter = 0

    async def start(self):
        """啟動模擬器"""
        try:
            # 啟動注入服務器
            await self.start_injection_server()
            await asyncio.sleep(1)  # 等待服務器完全啟動
            
            if self.debug_mode:
                log_with_color(f"{YELLOW}正在啟動調試模式...{RESET}")
                await self.debug_console()
            else:
                if not os.path.exists(self.log_file_name):
                    log_with_color(f"錯誤：找不到日誌文件 {self.log_file_name}")
                    return
                self.task = asyncio.create_task(self.roulette_main_thread(self.masterRoulettePort))
                await self.task
                
        except Exception as e:
            log_with_color(f"啟動模擬器時出錯: {e}")
            raise
        finally:
            await self.cleanup()

    async def start_injection_server(self):
        """啟動注入服務器"""
        async def handle_injection(websocket, path):
            try:
                async for message in websocket:
                    log_with_color(f"收到注入數據: {message}")
                    try:
                        await self.handle_injection_data(message)
                        await websocket.send(f"已處理數據: {message}")
                    except Exception as e:
                        log_with_color(f"處理注入數據時出錯: {e}")
                        await websocket.send(f"錯誤: {str(e)}")
            except websockets.exceptions.ConnectionClosed:
                log_with_color("注入連接已關閉")

        try:
            self.injection_server = await websockets.serve(
                handle_injection,
                "localhost",
                self.injection_port
            )
            log_with_color(f"注入服務器已啟動於端口 {self.injection_port}")
        except Exception as e:
            log_with_color(f"啟動注入服務器失敗: {e}")
            raise
    # v1
    # async def start_injection_server(self):
    #     """啟動注入服務器"""
    #     async def handle_injection(websocket, path):
    #         try:
    #             async for message in websocket:
    #                 log_with_color(f"收到注入數據: {message}")
    #                 try:
    #                     # 處理注入的數據
    #                     self.state_discriminator(message)
    #                     await self.update_sdp_state()
    #                     self.roulette_write_data_to_sdp(message)
    #                     self.roulette_read_data_from_sdp()
    #                 except Exception as e:
    #                     log_with_color(f"處理注入數據時出錯: {e}")
    #         except websockets.exceptions.ConnectionClosed:
    #             log_with_color("注入連接已關閉")
    #     try:
    #         self.injection_server = await websockets.serve(
    #             handle_injection, 
    #             "localhost", 
    #             self.injection_port
    #         )
    #         log_with_color(f"注入服務器已啟動於端口 {self.injection_port}")
    #     except Exception as e:
    #         log_with_color(f"啟動注入服務器時出錯: {e}")
    #         raise

    async def handle_injection_data(self, data: str):
        """處理注入的數據"""
        try:
            self.state_discriminator(data)
            await self.update_sdp_state()
            self.roulette_write_data_to_sdp(data)
            response = self.roulette_read_data_from_sdp()
            log_with_color(f"注入數據處理結果: {response}")
        except Exception as e:
            log_with_color(f"處理注入數據時出錯: {e}")
            raise

    async def debug_console(self):
        """逐行調試模式的控制台"""
        # 清除屏幕
        print("\033[H\033[J")  # 清屏命令
        
        # 顯示歡迎信息
        print("\n" + "=" * 60)
        log_with_color(f"{YELLOW}歡迎使用輪盤模擬器調試模式{RESET}")
        log_with_color(f"{YELLOW}輸入 'exit' 退出程序{RESET}")
        print("-" * 60)
        
        # 顯示命令說明
        log_with_color(f"{GREEN}可用的協議命令：{RESET}")
        log_with_color(f"{BLUE}*P 1{RESET}    - 開機")
        log_with_color(f"{BLUE}*P 0{RESET}    - 關機")
        log_with_color(f"{BLUE}*X;1{RESET}    - 開始新局")
        log_with_color(f"{BLUE}*X;2{RESET}    - 下注階段")
        log_with_color(f"{BLUE}*X;3{RESET}    - 投球")
        log_with_color(f"{BLUE}*X;4{RESET}    - 停止下注")
        log_with_color(f"{BLUE}*X;5{RESET}    - 顯示中獎號碼")
        log_with_color(f"{BLUE}*X;6{RESET}    - 關閉賭桌")
        print("=" * 60 + "\n")

        while self.running:
            try:
                # 顯示當前狀態
                await self.display_current_state()
                
                # 等待用戶輸入
                user_input = input(f"{GREEN}>>> {RESET}").strip()
                
                if user_input.lower() == 'exit':
                    log_with_color(f"{YELLOW}退出調試模式...{RESET}")
                    self.running = False
                    break
                
                if not user_input:
                    continue
                
                # 處理命令
                try:
                    log_with_color(f"{BLUE}處理命令: {user_input}{RESET}")
                    self.state_discriminator(user_input)
                    await self.update_sdp_state()
                    response = self.roulette_read_data_from_sdp()
                    
                    if response:
                        log_with_color(f"{GREEN}響應: {response}{RESET}")
                    
                    print("-" * 60)
                    
                except Exception as e:
                    log_with_color(f"{RED}錯誤: {str(e)}{RESET}")
                
                await asyncio.sleep(0.1)
                
            except KeyboardInterrupt:
                log_with_color(f"\n{YELLOW}收到中斷信號，退出調試模式...{RESET}")
                self.running = False
                break
            except Exception as e:
                log_with_color(f"{RED}錯誤: {str(e)}{RESET}")
                continue

    async def display_current_state(self):
        """顯示當前狀態"""
        print("\n" + "=" * 60)
        log_with_color(f"{BLUE}當前狀態:{RESET}")
        log_with_color(f"  遊戲狀態: {YELLOW}{self.current_game_state}{RESET}")
        log_with_color(f"  協議模式: {MAGENTA}{self.current_data_protocol_mode}{RESET}")
        power_color = GREEN if self.current_power_state == "on" else RED
        log_with_color(f"  電源狀態: {power_color}{self.current_power_state}{RESET}")
        
        # 顯示錯誤狀態
        if self.error_state:
            log_with_color(f"  {RED}錯誤狀態: {self.error_state}{RESET}")
            if self.error_state == "Stuck NMB":
                log_with_color(f"  {RED}NMB 計數: {self.x4_state_transition_waiting_counter}/20{RESET}")
                if self.f2_counter > 0:
                    log_with_color(f"  {RED}F2 計數: {self.f2_counter}/5{RESET}")
        
        # 顯示計數器
        if self.x4_state_transition_waiting_counter > 0:
            log_with_color(f"  NMB 計數器: {self.x4_state_transition_waiting_counter}")
        
        print("=" * 60)

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
            Plan:
            - Add Arcade mode/Non arcade mode with/without *F logs
            """
            pass

        # add Stuck NMB
        # If NMB>10s



        elif "*T" in data:
            self.current_data_protocol_mode = "setting_mode"
            """
            Plan:
            - Add *T k to set the average time of ball spin per revolution
            """
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
            Plan:
            Add No ball detected: WF1
            Add Ball launch failed: WF 8
            Add Ball not reach position: WF 2
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

                             
        try:
            # 處理 No More Bet 卡住的情況
            if "*X;4" in data:
                if self.current_game_state == "no_more_bet":
                    self.x4_state_transition_waiting_counter += 1
                    log_with_color(f"{YELLOW}NMB 計數: {self.x4_state_transition_waiting_counter}/20{RESET}")
                    
                    if self.x4_state_transition_waiting_counter >= 20:
                        self.error_state = "Stuck NMB"
                        log_with_color(f"{RED}檢測到 NMB 卡住，等待 F2 信號確認{RESET}")
                else:
                    self.current_game_state = "no_more_bet"
                    self.x4_state_transition_waiting_counter = 0
                    self.f2_counter = 0
                return

            # 處理 *F 2 錯誤
            if "*F 2" in data:
                self.current_data_protocol_mode = "self_test_mode"
                if self.error_state == "Stuck NMB":
                    self.f2_counter += 1
                    log_with_color(f"{RED}F2 錯誤計數: {self.f2_counter}/5{RESET}")
                    
                    if self.f2_counter >= 5:
                        log_with_color(f"{RED}觸發 Stuck NMB 錯誤狀態，關閉賭桌{RESET}")
                        self.current_game_state = "table_closed"
                        self.reset_error_counters()
                return
            
            # 處理 *F 3 錯誤
            if "*F 3" in data:
                self.current_data_protocol_mode = "self_test_mode"
                self.error_state = "NO Ball Position/Winning Num Detected"
                # Plan
                # Retry 3 times
                # If still not detected, raise an error "Retry Failed"
                # Stop the game
                # Under Maintenance
                return
            
            if "*F 11" in data or "*F 12" in data or "*F 13" in data or\
                "*F 21" in data or "*F 22" in data or "*F 23" in data:
                self.current_data_protocol_mode = "self_test_mode"
                self.error_state = "Sensor Stuck"
                # Plan
                # If self.f11/12/13/21/22/23 > 10
                # Stop the game
                # Execute "*SP"
                return 
        
            if "*F 4" in data:
                self.current_data_protocol_mode = "self_test_mode"
                self.error_state = "Invalid ball direction"
                # Plan
                # retry 1 times
                # if still not valid, raise an error "Retry Failed"
                # Stop the game
                # Under Maintenance
                return
            
            if "*F 1" in data:
                self.current_data_protocol_mode = "self_test_mode"
                self.error_state = "Hardware Fault"
                # Stop the game
                # Under Maintenance
                # *V
                return
            
            if "*F 5" in data:
                self.current_data_protocol_mode = "self_test_mode"
                self.error_state = "Motor drive issue"
                # Plan
                # if f5 > 10
                # Stop the game
                # Under Maintenance
                return
            
            if "*F 6" in data:
                self.current_data_protocol_mode = "self_test_mode"
                self.error_state = "Encoder failutre/Wheel Nuscakubratuib"
                # Plan
                # if f6 > 10
                # Stop the game
                # Under Maintenance
                return
            
        
            if "*F 7" in data:
                self.current_data_protocol_mode = "self_test_mode"
                self.error_state = "Ball not reach position"
                # Plan
                # Stop the game
                # Under Maintenance
                return

            # 重置錯誤狀態的條件
            if any(cmd in data for cmd in ["*X;1", "*X;6", "*P 0", "*P 1"]):
                self.reset_error_counters()


        except Exception as e:
            log_with_color(f"{RED}狀態判斷錯誤: {str(e)}{RESET}")
            raise

    def reset_error_counters(self):
        """重置所有錯誤相關的計數器"""
        self.error_state = None
        self.nmb_stuck_detected = False
        self.f2_counter = 0
        self.x4_state_transition_waiting_counter = 0

    def read_ss2_protocol_log(self, file_name):
        try:
            with open(file_name, "r") as file:
                lines = file.readlines()
                # 第一輪完整讀取
                if self.line_number <= len(lines):
                    line = lines[self.line_number - 1]
                    log_with_color(f"讀取到數據: {line.strip()}")
                    return line.strip()
                else:
                    # 重置到第20行開始循環
                    self.line_number = 20
                    if self.line_number <= 85:  # 確保在指定範圍內
                        line = lines[self.line_number - 1]
                        log_with_color(f"循環讀取數據: {line.strip()}")
                        return line.strip()
                    else:
                        self.line_number = 20  # 超出範圍重置
                        return None
        except Exception as e:
            log_with_color(f"讀取文件錯誤: {e}")
            return None

    def roulette_write_data_to_sdp(self,data):
        os.write(self.masterRoulettePort, data.encode())
        log_with_color(f"Roulette simulator sent to SDP: {data.encode().strip()}")

    def roulette_read_data_from_sdp(self):
        read_data = os.read(self.masterRoulettePort, 1024) # 1024 is the buffer size
        if read_data:
            log_with_color(f"Roulette supposed to be received from SDP: {read_data.decode().strip()}")

    async def roulette_main_thread(self, master):
        log_with_color("開始主線程")
        
        while True:
            try:
                data = self.read_ss2_protocol_log(self.log_file_name)
                if not data:
                    log_with_color("讀取完成，退出循環")
                    break
                    
                log_with_color(f"處理第 {self.line_number} 行數據: {data}")
                
                try:
                    self.state_discriminator(data)
                    await self.update_sdp_state()
                    self.roulette_write_data_to_sdp(data)
                    self.roulette_read_data_from_sdp()
                except Exception as e:
                    log_with_color(f"處理數據時出錯: {e}")
                    break
                    
                self.line_number += 1
                await asyncio.sleep(self.LOG_FREQUENCY)
                
            except Exception as e:
                log_with_color(f"主循環錯誤: {e}")
                break   
                
        log_with_color("主線程結束")

    async def cleanup(self):
        """清理資源"""
        log_with_color("清理資源...")
        if self.injection_server:
            self.injection_server.close()
            await self.injection_server.wait_closed()
        self.running = False
        log_with_color("資源清理完成")

class TestRouletteSimulatorNonArcade(RouletteSimulator):
    def __init__(self, recorder_port, room_id):
        super().__init__()
        self.recorder_port = recorder_port
        self.room_id = room_id
        self.websocket = None
        self.debug_mode = False
        self.running = True
        log_with_color(f"Initializing TestRouletteSimulatorNonArcade with port {recorder_port}, room {room_id}")

    async def start(self):
        """啟動模擬器"""
        try:
            # 啟動注入服務器
            await self.start_injection_server()
            await asyncio.sleep(1)  # 等待服務器完全啟動
            
            if self.debug_mode:
                # 清除屏幕
                print("\033[H\033[J")
                
                # 顯示歡迎信息
                print("\n" + "=" * 60)
                log_with_color(f"{YELLOW}歡迎使用輪盤模擬器調試模式{RESET}")
                log_with_color(f"{YELLOW}輸入 'exit' 退出程序{RESET}")
                print("-" * 60)
                
                # 顯示命令說明
                log_with_color(f"{GREEN}可用的協議命令：{RESET}")
                log_with_color(f"{BLUE}*P 1{RESET}    - 開機")
                log_with_color(f"{BLUE}*P 0{RESET}    - 關機")
                log_with_color(f"{BLUE}*X;1{RESET}    - 開始新局")
                log_with_color(f"{BLUE}*X;2{RESET}    - 下注階段")
                log_with_color(f"{BLUE}*X;3{RESET}    - 投球")
                log_with_color(f"{BLUE}*X;4{RESET}    - 停止下注")
                log_with_color(f"{BLUE}*X;5{RESET}    - 顯示中獎號碼")
                log_with_color(f"{BLUE}*X;6{RESET}    - 關閉賭桌")
                print("=" * 60 + "\n")
                
                # 進入調試循環
                while self.running:
                    try:
                        # 顯示當前狀態
                        await self.display_current_state()
                        
                        # 等待用戶輸入
                        user_input = input(f"{GREEN}>>> {RESET}").strip()
                        
                        if user_input.lower() == 'exit':
                            log_with_color(f"{YELLOW}退出調試模式...{RESET}")
                            break
                        
                        if not user_input:
                            continue
                        
                        # 處理命令
                        try:
                            log_with_color(f"{BLUE}處理命令: {user_input}{RESET}")
                            self.state_discriminator(user_input)
                            await self.update_sdp_state()
                            response = self.roulette_read_data_from_sdp()
                            
                            if response:
                                log_with_color(f"{GREEN}響應: {response}{RESET}")
                            
                            print("-" * 60)
                            
                        except Exception as e:
                            log_with_color(f"{RED}錯誤: {str(e)}{RESET}")
                        
                        await asyncio.sleep(0.1)
                        
                    except KeyboardInterrupt:
                        log_with_color(f"\n{YELLOW}收到中斷信號，退出調試模式...{RESET}")
                        break
                    except Exception as e:
                        log_with_color(f"{RED}錯誤: {str(e)}{RESET}")
                        continue
            else:
                # 正常模式
                if not os.path.exists(self.log_file_name):
                    log_with_color(f"錯誤：找不到日誌文件 {self.log_file_name}")
                    return
                self.task = asyncio.create_task(self.roulette_main_thread(self.masterRoulettePort))
                await self.task
                
        except Exception as e:
            log_with_color(f"啟動模擬器時出錯: {e}")
            raise
        finally:
            await self.cleanup()

    async def display_current_state(self):
        """顯示當前狀態"""
        print("\n" + "=" * 60)
        log_with_color(f"{BLUE}當前狀態:{RESET}")
        log_with_color(f"  遊戲狀態: {YELLOW}{self.current_game_state}{RESET}")
        log_with_color(f"  協議模式: {MAGENTA}{self.current_data_protocol_mode}{RESET}")
        power_color = GREEN if self.current_power_state == "on" else RED
        log_with_color(f"  電源狀態: {power_color}{self.current_power_state}{RESET}")
        print("=" * 60)

async def main(port=None, room_id=None, debug=False):
    """
    Usage example:
    python sdp-1217-debug.py --recorder-port 8765 --room-id 1 --debug
    """
    if port is None or room_id is None:
        parser = argparse.ArgumentParser(description='SDP Server')
        parser.add_argument('--recorder-port', type=int, required=True,
                          help='Port number of the recorder server')
        parser.add_argument('--room-id', type=int, required=True,
                          help='Room ID for the instance')
        parser.add_argument('--debug', action='store_true',
                          help='Enable debug mode')
        args = parser.parse_args()
        port = args.recorder_port
        room_id = args.room_id
        debug = args.debug
    
    print(f"Starting SDP simulator with recorder port: {port}, room id: {room_id}, debug mode: {debug}")
    
    roulette = TestRouletteSimulatorNonArcade(
        recorder_port=port,
        room_id=room_id
    )
    roulette.debug_mode = debug  # 設置調試模式
    
    try:
        print("Initializing roulette simulator...")
        await roulette.start()
    except KeyboardInterrupt:
        print("\nStopping roulette simulator...")
    except Exception as e:
        print(f"Error running roulette simulator: {str(e)}")
        raise
    finally:
        await roulette.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()