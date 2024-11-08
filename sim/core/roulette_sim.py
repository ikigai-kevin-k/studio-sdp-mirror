import time
import os
import pty
import threading
import random
import logging


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
                logging.FileHandler("../log/sim/roulette_sim.log", mode="w"),
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
        self.thread = threading.Thread(target=self.roulette_main_thread, args=(self.masterRoulettePort,))
        self.thread.daemon = True
        self.thread.start()


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
        max2 = 21
        max3 = 16
        max4 = 43
        max5 = 4
        max6 = 10

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

        # import pdb; pdb.set_trace()

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
                    # assert (self.current_game_state == "table_closed" 
                    #         or self.current_game_state == "start_game") and \
                    #         (self.current_data_protocol_mode == "power_setting_mode"  or \
                    #          self.current_data_protocol_mode == "game_mode") and \
                    #         self.current_power_state == "on"
                    
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
                    # assert self.current_data_protocol_mode == "game_mode" and \
                    #        (self.current_game_state == "start_game" or\
                    #         self.current_game_state == "winning_number" or\
                    #         self.current_game_state == "place_bet") and \
                    #        self.current_power_state == "on"
                    
                    # if self.current_game_state == "table_closed":
                    #     if self.x6_state_transition_waiting_counter < self.P0_MAX_DELAY:
                    #         self.x6_state_transition_waiting_counter += 1
                    #     else:
                    #         raise Exception(f"{RED}P0 delay time too long, there may be something wrong.{RESET}")
                    if self.current_game_state == "start_game":
                        self.current_game_state = "place_bet"
                        self.reset_state_transition_waiting_counter()
                        return
                    
                    elif self.current_game_state == "winning_number":
                        self.current_game_state = "place_bet"
                        self.reset_state_transition_waiting_counter()
                        return
                    
                    elif self.current_game_state == "place_bet":
                        if self.x2_state_transition_waiting_counter < self.X2_MAX_WAITING_TIME:
                            self.x2_state_transition_waiting_counter += 1
                            return
                        else:
                            # self.force_restart_game()
                            raise Exception(f"{RED}state transition time too long, there may be something wrong.{RESET}")
                except Exception as e:
                    log_with_color(f"Error asserting state transition: {e}")
                    raise Exception("state transition error, close the program.")

            elif "*X;3" in data:
                try:
                    # assert self.current_game_state == "place_bet" or\
                    #        self.current_game_state == "ball_launch"
                    
                    if self.current_game_state == "place_bet":
                        self.current_game_state = "ball_launch"
                        self.reset_state_transition_waiting_counter()
                        return
                    elif self.current_game_state == "ball_launch":
                        if self.x3_state_transition_waiting_counter < self.X3_MAX_WAITING_TIME:
                            self.x3_state_transition_waiting_counter += 1
                            return
                        else:
                            # self.force_restart_game()
                            raise Exception(f"{RED}state transition time too long, there may be something wrong.{RESET}")
                except Exception as e:
                    log_with_color(f"Error asserting state transition: {e}")
                    raise Exception("state transition error, close the program.")
            elif "*X;4" in data:
                try:
                    # assert self.current_game_state == "ball_launch" or \
                    #        self.current_game_state == "no_more_bet"
                    
                    if self.current_game_state == "ball_launch":
                        self.current_game_state = "no_more_bet"
                        self.reset_state_transition_waiting_counter()
                        return
                    elif self.current_game_state == "no_more_bet":
                        if self.x4_state_transition_waiting_counter < self.X4_MAX_WAITING_TIME:
                            self.x4_state_transition_waiting_counter += 1
                            return
                        else:
                            # self.force_restart_game()
                            raise Exception(f"{RED}state transition time too long, there may be something wrong.{RESET}")
                except Exception as e:
                    log_with_color(f"Error asserting state transition: {e}")
                    raise Exception("state transition error, close the program.")
            elif "*X;5" in data or data.strip().isdigit():
                try:
                    # assert self.current_game_state == "no_more_bet" or\
                    #        self.current_game_state == "winning_number"
                    if self.current_game_state == "no_more_bet":
                        self.current_game_state = "winning_number"
                        self.reset_state_transition_waiting_counter()
                        return
                    elif self.current_game_state == "winning_number":
                        if self.x5_state_transition_waiting_counter < self.X5_MAX_WAITING_TIME:
                            self.x5_state_transition_waiting_counter += 1
                            return
                        else:
                            # self.force_restart_game()
                            raise Exception(f"{RED}state transition time too long, there may be something wrong.{RESET}")
                except Exception as e:
                    log_with_color(f"Error asserting state transition: {e}")
                    raise Exception("state transition error, close the program.")

            elif "*X;6" in data:
                try:
                    # assert self.current_game_state == "start_game"\
                    #       or self.current_game_state == "place_bet"\
                    #       or self.current_game_state == "ball_launch"\
                    #       or self.current_game_state == "no_more_bet"\
                    #       or self.current_game_state == "winning_number"
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

    def read_ss2_protocol_log(self, file_name):# line_number):
        """
        This is a utility function to read the protocol log file.
        Should be moved to a utility module.
        """
        try:
            with open(file_name, "r") as file:
               
                for _ in range(self.line_number - 1):
                    next(file)
                
                line = next(file, None)
                if line:
                    return line.strip()
                else:
                    log_with_color("No more lines to read")
                    self.reset_state_transition_waiting_counter()
                    return ""       
        except Exception as e:
            log_with_color(f"Error reading log file: {e}")
            return ""

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

    def roulette_main_thread(self, master):
        self.line_number = 1

        while True:
            try:
                log_with_color(f"{GREEN}Line number: {self.line_number}{RESET}")
                print("\n")
                self.roulette_state_display()
                data = self.read_ss2_protocol_log(LOG_FILE_NAME)#,self.line_number)
  
                if not data:
                    log_with_color("Reached end of log file. Terminating program...")
                    break
                try:
                    self.state_discriminator(data)
                    self.roulette_write_data_to_sdp(data)
                    self.roulette_read_data_from_sdp()
                except Exception as e:
                    log_with_color(f"Error processing line {self.line_number}: {e}")
                    break
                
                self.line_number += 1
                time.sleep(self.LOG_FREQUENCY)
                
            except OSError as e:
                log_with_color(f"Serial port error: {e}")
                break

class TestRouletteSimulatorNonArcade(RouletteSimulator):


    def __init__(self):
        self.line_number = 1
        super().__init__()

    def check_receive_force_restart_game(self,data):
        """
        Read from the log line containing "*R"
        """
        if "*R" in data:
            self.reset_state_transition_waiting_counter()
            self.current_game_state = "start_game"
            self.current_data_protocol_mode = "game_mode"
            self.current_power_state = "on"
            """
            Simulate the *R\r\n command 
            While encountering the WF, append the *R\r\n command to the log file
            """
            print(f"{YELLOW}*R{RESET}")
            print(f"{YELLOW}*R ok{RESET}")
            self.line_number = 3 # from game start state
            return True
        else:
            return False

    def roulette_main_thread(self, master):
        def create_round_timer():
            timer_state = {
                'time_line_start': 0,
                'time_line_end': 0,
                'first_x2_line': False,
                'first_x5_line': False,
                'game_round_time_cost': 0
                }
        
            def update_timer(data):
                if "*X;2" in data and not timer_state['first_x2_line']:
                    timer_state['time_line_start'] = time.time()
                    timer_state['first_x2_line'] = True
                elif "*X;5" in data and not timer_state['first_x5_line']:
                    timer_state['time_line_end'] = time.time()
                    timer_state['first_x5_line'] = True
                elif "*X;5" in data and timer_state['first_x2_line'] and timer_state['first_x5_line']:
                    timer_state['game_round_time_cost'] = timer_state['time_line_end'] - timer_state['time_line_start']
                    print(f"{YELLOW}time_line_cost:{RESET}", timer_state['game_round_time_cost'])
                    # Reset timer state
                    timer_state['time_line_start'] = -1
                    timer_state['time_line_end'] = -1
                    timer_state['first_x2_line'] = False
                    timer_state['first_x5_line'] = False
            
                return timer_state['game_round_time_cost']
            
            return update_timer

        round_timer = create_round_timer()
        self.line_number = 1

        while True:
            try:
                log_with_color(f"{GREEN}Line number: {self.line_number}{RESET}")
                print("\n")
                self.roulette_state_display()
                data = self.read_ss2_protocol_log(LOG_FILE_NAME)

                if not data:
                    log_with_color("Reached end of log file. Terminating program...")
                    break
                
                try:
                    if self.check_receive_force_restart_game(data):
                        continue
                    
                    # Update timer
                    round_timer(data)
                    
                    self.state_discriminator(data)
                    self.roulette_write_data_to_sdp(data)
                    self.roulette_read_data_from_sdp()

                # Need press "*u 1\r\n" to continue the game(to continue the while loop)

                except Exception as e:
                    log_with_color(f"Error processing line {self.line_number}: {e}")
                    break
            
                self.line_number += 1
                time.sleep(self.LOG_FREQUENCY)
            
            except OSError as e:
                log_with_color(f"Serial port error: {e}")
                break

    def roulette_main_thread_v1(self, master):
        """
        Split the force restart command from the state_discriminator to a separate function,
        called `check_receive_force_restart_game`.
        Added `check_receive_force_restart_game` to the roulette_main_thread.
        """
        game_round_time_cost = 0
        first_x2_line = False
        first_x5_line = False
        while True:
            try:
                log_with_color(f"{GREEN}Line number: {self.line_number}{RESET}")
                print("\n")
                self.roulette_state_display()
                data = self.read_ss2_protocol_log(LOG_FILE_NAME)#,self.line_number)
                
                """
                When first encounter "*X;2", start the timer
                When encounter the end of the "*X;5", stop the timer
                Calculate the time cost of each game round
                Reset the timer
                """
                if "*X;2" in data and not first_x2_line:
                    time_line_start = time.time()
                    first_x2_line = True
                elif "*X;5" in data and not first_x5_line:
                    time_line_end = time.time()
                    first_x5_line = True
                elif "*X;5" in data and first_x2_line and first_x5_line:
                    game_round_time_cost = time_line_end - time_line_start
                    print(f"{YELLOW}time_line_cost:{RESET}",game_round_time_cost)
                    time_line_start = -1
                    time_line_end = -1
                    first_x2_line = False
                    first_x5_line = False

                if not data:
                    log_with_color("Reached end of log file. Terminating program...")
                    break
                try:
                    if self.check_receive_force_restart_game(data):
                        continue
                    self.state_discriminator(data)
                    self.roulette_write_data_to_sdp(data)
                    self.roulette_read_data_from_sdp()
                
                if "*X;6" in data:
                    while True:
                        user_input = input("Press *u 1 to continue the next game:")
                        if user_input == "*u 1\r\n":
                            break   

                except Exception as e:
                    log_with_color(f"Error processing line {self.line_number}: {e}")
                    break
                
                self.line_number += 1
                time.sleep(self.LOG_FREQUENCY)
                
            except OSError as e:
                log_with_color(f"Serial port error: {e}")
                break

     
    # def state_discriminator(self):

    #     """
    #     """
    #     data = protocol_log_line

    #     print("\n")
    #     print("log line:",data)
    #     print("current_data_protocol_mode:",self.current_data_protocol_mode)
    #     print("current_game_state:",self.current_game_state)
    #     print("current_power_state:",self.current_power_state)

    #     if "*X;" in data:
    #         print(f"{GREEN}X1 state transition waiting counter:{RESET}",self.x1_state_transition_waiting_counter)
    #         print(f"{GREEN}X2 state transition waiting counter:{RESET}",self.x2_state_transition_waiting_counter)
    #         print(f"{GREEN}X3 state transition waiting counter:{RESET}",self.x3_state_transition_waiting_counter)
    #         print(f"{GREEN}X4 state transition waiting counter:{RESET}",self.x4_state_transition_waiting_counter)
    #         print(f"{GREEN}X5 state transition waiting counter:{RESET}",self.x5_state_transition_waiting_counter)
    #         print(f"{GREEN}X6 state transition waiting counter:{RESET}",self.x6_state_transition_waiting_counter)
    #         print(f"{GREEN}P0 delay counter:{RESET}",self.p0_delay_counter)
            
    #         if "*X;1" in data:
    #             try:
    #                 if self.current_game_state == "table_closed":
    #                     self.current_data_protocol_mode = "game_mode"
    #                     self.current_game_state = "start_game"
    #                     self.reset_state_transition_waiting_counter()
    #                     return
    #                 elif self.current_game_state == "start_game":
    #                     if self.x1_state_transition_waiting_counter < self.X1_MAX_WAITING_TIME:
    #                         self.x1_state_transition_waiting_counter += 1
    #                         return
    #                     else:
    #                         raise Exception(f"{RED}state transition time too long, there may be something wrong.{RESET}")
    #             except Exception as e:
    #                 log_with_color(f"Error asserting state transition: {e}")
    #                 raise Exception("state transition error, close the program.")
            
    #         elif "*X;2" in data:
    #             try:
    #                 if self.current_game_state == "start_game":
    #                     self.current_game_state = "place_bet"
    #                     self.reset_state_transition_waiting_counter()
    #                     return
                    
    #                 elif self.current_game_state == "winning_number":
    #                     self.current_game_state = "place_bet"
    #                     self.reset_state_transition_waiting_counter()
    #                     return
                    
    #                 elif self.current_game_state == "place_bet":
    #                     if self.x2_state_transition_waiting_counter < self.X2_MAX_WAITING_TIME:
    #                         self.x2_state_transition_waiting_counter += 1
    #                         return
    #                     else:
    #                         raise Exception(f"{RED}state transition time too long, there may be something wrong.{RESET}")
    #             except Exception as e:
    #                 log_with_color(f"Error asserting state transition: {e}")
    #                 raise Exception("state transition error, close the program.")

    #         elif "*X;3" in data:
    #             try:
    #                 if self.current_game_state == "place_bet":
    #                     self.current_game_state = "ball_launch"
    #                     self.reset_state_transition_waiting_counter()
    #                     return
    #                 elif self.current_game_state == "ball_launch":
    #                     if self.x3_state_transition_waiting_counter < self.X3_MAX_WAITING_TIME:
    #                         self.x3_state_transition_waiting_counter += 1
    #                         return
    #                     else:
    #                         # self.force_restart_game()
    #                         raise Exception(f"{RED}state transition time too long, there may be something wrong.{RESET}")
    #             except Exception as e:
    #                 log_with_color(f"Error asserting state transition: {e}")
    #                 raise Exception("state transition error, close the program.")
    #         elif "*X;4" in data:
    #             try:
    #                 # assert self.current_game_state == "ball_launch" or \
    #                 #        self.current_game_state == "no_more_bet"
                    
    #                 if self.current_game_state == "ball_launch":
    #                     self.current_game_state = "no_more_bet"
    #                     self.reset_state_transition_waiting_counter()
    #                     return
    #                 elif self.current_game_state == "no_more_bet":
    #                     if self.x4_state_transition_waiting_counter < self.X4_MAX_WAITING_TIME:
    #                         self.x4_state_transition_waiting_counter += 1
    #                         return
    #                     else:
    #                         # self.force_restart_game()
    #                         raise Exception(f"{RED}state transition time too long, there may be something wrong.{RESET}")
    #             except Exception as e:
    #                 log_with_color(f"Error asserting state transition: {e}")
    #                 raise Exception("state transition error, close the program.")
    #         elif "*X;5" in data or data.strip().isdigit():
    #             try:
    #                 # assert self.current_game_state == "no_more_bet" or\
    #                 #        self.current_game_state == "winning_number"
    #                 if self.current_game_state == "no_more_bet":
    #                     self.current_game_state = "winning_number"
    #                     self.reset_state_transition_waiting_counter()
    #                     return
    #                 elif self.current_game_state == "winning_number":
    #                     if self.x5_state_transition_waiting_counter < self.X5_MAX_WAITING_TIME:
    #                         self.x5_state_transition_waiting_counter += 1
    #                         return
    #                     else:
    #                         # self.force_restart_game()
    #                         raise Exception(f"{RED}state transition time too long, there may be something wrong.{RESET}")
    #             except Exception as e:
    #                 log_with_color(f"Error asserting state transition: {e}")
    #                 raise Exception("state transition error, close the program.")

    #         elif "*X;6" in data:
    #             try:
    #                 if self.current_game_state != "table_closed":
    #                     self.current_game_state = "table_closed"
    #                     self.reset_state_transition_waiting_counter()
    #                     return
    #                 else:
    #                     if self.x6_state_transition_waiting_counter < self.X6_MAX_WAITING_TIME:
    #                         self.x6_state_transition_waiting_counter += 1
    #                         return
    #                     else:
    #                         # self.force_close_table()
    #                         raise Exception(f"{RED}state transition time too long, there may be something wrong.{RESET}")
    #             except Exception as e:
    #                 log_with_color(f"Error asserting state transition: {e}")
    #                 raise Exception("state transition error, close the program.")

    #         else:
    #             log_with_color(f"unknown game state: {data}")
    #             raise Exception("unknown game state, close the program.")

    #     elif "*R" in data:
    #         self.force_restart_game()

    #     elif "*o" in data:
    #         self.current_data_protocol_mode = "operation_mode"
    #         """
    #         Operation mode
    #         """
    #         pass
    #     elif "*F" in data:
    #         self.current_data_protocol_mode = "self_test_mode"
    #         """
    #         Self-test mode
    #         """
    #         pass
    #     elif "*P" in data:
    #         """
    #         Power setting mode
    #         """
            
    #         if "*P 1" in data and self.current_power_state == "off":
    #             """add a condition: the next line is *P OK"""
    #             self.current_power_state = "on"
    #             """In arcade mode, power on will trigger table open"""
    #             self.current_data_protocol_mode = "power_setting_mode"
    #             return
            
    #         elif "*P 0" in data and self.current_power_state == "on":
    #             """add a condition: the next line is *P OK"""
    #             self.current_power_state = "off"
    #             """off will trigger table force close"""
    #             self.current_game_state = "table_closed"
    #             self.current_data_protocol_mode = "power_setting_mode"

    #             if "*X:6" not in data and self.p0_delay_counter < self.P0_MAX_DELAY:
    #                 self.p0_delay_counter += 1
    #             else:
    #                 raise Exception(f"{RED}P0 delay time too long, there may be something wrong.{RESET}")
    #             return
            
    #         elif "*P OK" in data:
    #             pass
    #             return
    #         else:
    #             log_with_color(data)
    #             raise Exception("unknown power state.")            

    #     elif "*C" in data:
    #         self.current_data_protocol_mode = "calibration_mode"
    #         """
    #         Calibration mode
    #         """
    #         pass
    #     elif "*W" in data:
    #         self.current_data_protocol_mode = "warning_flag_mode"
    #         """
    #         Warning flag mode
    #         Restart the game
    #         """
    #         # self.game_state_transition_to("start_game")
    #         self.current_game_state = "start_game"
    #         pass
    #     elif "*M" in data:
    #         self.current_data_protocol_mode = "statistics_mode"
    #         """
    #         Statistics mode
    #         """
    #         pass

    #     elif data.strip().isdigit():                 
    #         """
    #         The number of the winning number
    #         """
    #         pass
    #     else:
    #         log_with_color(data)
    #         raise Exception("unknown protocol log type.")


    

if __name__ == "__main__":

    global LOG_FILE_NAME
    LOG_FILE_NAME = "../log/ss2/ss2_protocol2.log"
    try:
        roulette = TestRouletteSimulatorNonArcade()
        # roulette = RouletteSimulator()
        log_with_color(f"Roulette simulator is running. Virtual port: {roulette.slaveRoulettePort}")
        log_with_color("Press Ctrl+C to stop the simulator.")

        stop_event = threading.Event()
        try:
            stop_event.wait()  # wait for interrupt signal           
        except KeyboardInterrupt:
            log_with_color("Stopping roulette simulator by keyboard interrupt...")
            
    except Exception as e:
        log_with_color(f"Unexpected error: {e}")
        log_with_color("Roulette simulator terminated.")
