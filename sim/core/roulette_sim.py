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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("../log/sim/roulette_sim.log", mode="w"),
        logging.StreamHandler()
    ]
)

def log_with_color(message):
    # clean_message = message.replace(RED, '').replace(GREEN, '').replace(YELLOW, '').replace(BLUE, '').replace(MAGENTA, '').replace(GRAY, '').replace(RESET, '')
    logging.info(message)
class StateMachine:
    """
    Refer to Cammegh SS2 Owner's handbook, p.49,
    First, implement the naive state transition logic without any external interruptions and internal errors.

    """

    def __init__(self):
        self.data_protocol_modes = ["idle","game_mode","operation_mode","self_test_mode", "power_setting_mode","calibration_mode", "warning_flag_mode", "statistics_mode"]
        self.power_states = ["on", "off"]
        self.game_states = ["start_game","place_bet","ball_launch","no_more_bet","winning_number","table_closed"]
        
        self.current_game_state = "idle"
        self.current_data_protocol_mode = None 
        self.current_power_state = "off"

    def game_state_transition_to(self, new_game_state):
        """
        Redundant function, depreciated
        """
        self.current_game_state = new_game_state
        """
        Duration, refer to log and video
        """ 

    def normal_state_machine(self):
        """
        Transition logic (without perturbations):
        1->2->3->4->5->2->3->4->5->... until 6 interrupts

        Depreciated: replaced by the state_discriminator in RouletteSimulator
        """
        match self.current_game_state:
            case "idle":
                self.transition("start_game")
                """
                Duration, refer to log and video
                """
                pass
            case "start_game":
                self.transition("place_bet")
                """
                Duration, refer to log and video
                """
                pass 
            case "place_bet":
                self.transition("ball_launch")
                """
                Duration, refer to log and video
                """
                pass
            case "ball_launch":
                self.transition("no_more_bet")
                """
                Duration, refer to log and video
                """
                pass
            case "no_more_bet":
                self.transition("winning_number")
                """
                Duration, refer to log and video
                """
                pass
            case "winning_number":
                self.transition("place_bet")
                """
                Duration, refer to log and video
                """
                pass
            case "table_closed":
                self.transition("idle")
                """
                Duration, refer to log and video
                """
                pass

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

        data = protocol_log_line
        previous_game_state = self.current_game_state
        previous_data_protocol_mode = self.current_data_protocol_mode
        print(data,previous_game_state)
        if "*X;" in data:
            self.current_data_protocol_mode = f"game_mode"

            if "*X;1" in data:
                try:
                    """
                    case 1: previous power state is on and
                            previous data protocol mode is power setting mode, and
                            previous game mode is idle
                    or
                    case 2: previous power state is on, and
                            previous data protocol mode is None, and
                            previous game mode is idle
                    or 
                    case 3: previous power state is on, and
                            previous data protocol mode is game_mode, and
                            previous game mode is table_closed
                    """

                    # assert((self.current_power_state == "on" and 
                    #             previous_data_protocol_mode == "power_setting_mode" and 
                    #             previous_game_state == "idle") or 
                    #         (self.current_power_state == "on" and 
                    #             previous_data_protocol_mode is None and 
                    #             previous_game_state == "idle") or
                    #         (self.current_power_state == "on" and 
                    #             previous_data_protocol_mode == "game_mode" and 
                    #             previous_game_state == "table_closed"))
                    assert previous_game_state == "idle"

                except Exception as e:
                    log_with_color(f"Error asserting state transition: {e}")
                    # print(data,previous_game_state)
                    os._exit(1)
                # self.game_state_transition_to("start_game")
                self.current_game_state = "start_game"
            elif "*X;2" in data:
                try:
                    assert previous_game_state == "idle"
                except Exception as e:
                    log_with_color(f"Error asserting state transition: {e}")
                    # print(data,previous_game_state)
                    os._exit(1)
                # self.game_state_transition_to("place_bet")
                self.current_game_state = "place_bet"
            elif "*X;3" in data:
                try:
                    assert previous_game_state == "start_game"\
                        or previous_game_state == "winning_number"
                except Exception as e:
                    log_with_color(f"Error asserting state transition: {e}")
                    # print(data,previous_game_state)
                    os._exit(1)
                # self.game_state_transition_to("ball_launch")
                self.current_game_state = "ball_launch"
            elif "*X;4" in data:
                try:
                    assert previous_game_state == "place_bet"
                except Exception as e:
                    log_with_color(f"Error asserting state transition: {e}")
                    # print(data,previous_game_state)
                    os._exit(1)
                # self.game_state_transition_to("no_more_bet")
                self.current_game_state = "no_more_bet"
            elif "*X;5" in data:
                try:
                    assert previous_game_state == "ball_launch"
                except Exception as e:
                    log_with_color(f"Error asserting state transition: {e}")
                    # print(data,previous_game_state)
                    os._exit(1)
                # self.game_state_transition_to("winning_number")
                self.current_game_state = "winning_number"
            elif "*X;6" in data:
                try:
                    assert previous_game_state == "start_game"\
                          or previous_game_state == "place_bet"\
                          or previous_game_state == "ball_launch"\
                          or previous_game_state == "no_more_bet"\
                          or previous_game_state == "winning_number"

                except Exception as e:
                    log_with_color(f"Error asserting state transition: {e}")
                    # print(data,previous_game_state)
                    os._exit(1)

                # self.game_state_transition_to("table_closed")
                self.current_game_state = "table_closed"
                # self.game_state_transition_to("idle")
                self.current_game_state = "idle"
            else:
                print(data,previous_game_state)
                raise Exception("unknown game state.")
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
            self.current_data_protocol_mode = f"power_setting_mode"
            """
            Power setting mode
            """
            if "*P 1" in data and self.current_power_state == "off":
                """add a confition: the next line is *P OK"""
                self.current_power_state = "on"
                """In arcade mode, power on will trigger table open"""
                # self.game_state_transition_to("idle")
                self.current_game_state = "idle"
                self.current_data_protocol_mode = "game_mode"
            elif "*P 0" in data and self.current_power_state == "on":
                """add a condition: the next line is *P OK"""
                self.current_power_state = "off"
                """off will trigger table force close"""
                # self.game_state_transition_to("table_closed")
                self.current_game_state = "table_closed"
                self.current_data_protocol_mode = None
            elif "*P OK" in data:
                self.current_data_protocol_mode = "power_setting_mode"
                self.current_power_state = "on"
                # self.game_state_transition_to('idle')
                self.current_game_state = "idle"
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
    
    def generate_protocol_data(self,mode):

        
        """
        This is a stateless protocol data generator, which means it does not consider the previous state of the roulette.
        When the stateful data generator has been implemented, this function should be removed.
        """

        """
        TODO:
        - The current protocol data only consider the *X command, need to add more types of commands, for example, 
            *o for operation mode
            *F for self-test mode
            *P for power setting
            *C for calibration
            *W for winning number statistics
            *M for pocket misfires statistics
        """

        match mode:
            case "X":

                """
                This part is to be deprecated when the stateful data generator is implemented.
                """

                game_states = list(range(1, 8))
                game_numbers = list(range(1,256))
                last_winning_numbers = list(range(0,37))
                warning_flags = list(range(0,16))
                rotor_speeds = list(range(10,541))
                rotor_directions = [0,1]

                game_state = random.choice(game_states)
                game_number = random.choice(game_numbers)
                last_winning_number = random.choice(last_winning_numbers)
                warning_flag = hex(random.choice(warning_flags))
                rotor_speed = random.choice(rotor_speeds)
                rotor_direction = random.choice(rotor_directions)

                return f"*X;{game_state:01d}:{game_number:03d}:{last_winning_number:02d}:{warning_flag}:{rotor_speed:03d}:{rotor_direction:01d}\r\n"

            case "o":
                """
                need to add the type behaviour of the operation mode here or in the casino_engineer_sim.py
                """
                pass
                return "*o\r\n"

            case "F":
                """
                need to add the type behaviour of the self-test mode here or in the casino_engineer_sim.py
                """
                pass
                return "*F\r\n"
            case "P":
                """
                need to add the type behaviour of the power setting mode here or in the casino_engineer_sim.py
                """
                pass
                return "*P\r\n"

            case "C":
                """
                need to add the type behaviour of the calibration mode here or in the casino_engineer_sim.py
                """
                pass
                return "*C\r\n"
            case "W":
                """
                need to add the type behaviour of the winning number statistics mode here or in the casino_engineer_sim.py
                """
                pass
                return "*W\r\n"
            case "M":
                """
                need to add the type behaviour of the pocket misfires statistics mode here or in the casino_engineer_sim.py
                """
                pass
                return "*M\r\n"
    
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
                self.roulette_state_display()
                data = self.read_ss2_protocol_log(log_file_name,line_number)
  
                if not data:
                    log_with_color("Reached end of log file. Terminating program...")
                    os._exit(0)  # 强制退出程序
                    
                try:
                    self.state_discriminator(data)
                    self.roulette_write_data_to_sdp(data)
                    self.roulette_read_data_from_sdp()
                except Exception as e:
                    log_with_color(f"Error processing line {line_number}: {e}")
                
                line_number += 1
                time.sleep(0.1)
                
            except OSError as e:
                log_with_color(f"Serial port error: {e}")
                break

if __name__ == "__main__":

    global log_file_name 
    log_file_name = "../log/ss2/ss2_protocol_instant_transition.log"
    try:
        roulette = RouletteSimulator()
        roulette.roulette_main_thread(roulette.masterRoulettePort)
        log_with_color(f"Roulette simulator is running. Virtual port: {roulette.slaveRoulettePort}")
        log_with_color("Press Ctrl+C to stop the simulator.")

        while True:
            pass # keep the thread alive
    except KeyboardInterrupt:
        log_with_color("Stopping roulette simulator by keyboard interrupt...")
    except Exception as e:
        log_with_color(f"Unexpected error: {e}")
