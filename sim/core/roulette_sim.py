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

    def __init__(self):
        super().__init__()
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
        pass

    def force_close_table(self):
        pass

    def warning_flag_handler(self):
        pass

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

    def read_ss2_protocol_log(self, file_name, line_number):
        """
        This is a utility function to read the protocol log file.
        Should be moved to a utility module.
        """
        try:
            with open(file_name, "r") as file:
               
                for _ in range(line_number - 1):
                    next(file)
                
                line = next(file, None)
                if line:
                    return line.strip()
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
        line_number = 1
        while True:
            try:
                log_with_color(f"{GREEN}Line number: {line_number}{RESET}")
                print("\n")
                self.roulette_state_display()
                data = self.read_ss2_protocol_log(log_file_name,line_number)
  
                if not data:
                    log_with_color("Reached end of log file. Terminating program...")
                    break
                try:
                    self.state_discriminator(data)
                    self.roulette_write_data_to_sdp(data)
                    self.roulette_read_data_from_sdp()
                except Exception as e:
                    log_with_color(f"Error processing line {line_number}: {e}")
                    break
                
                line_number += 1
                time.sleep(self.LOG_FREQUENCY)
                
            except OSError as e:
                log_with_color(f"Serial port error: {e}")
                break

if __name__ == "__main__":

    global log_file_name 
    log_file_name = "../log/ss2/ss2_protocol2.log"
    try:
        roulette = RouletteSimulator()
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
