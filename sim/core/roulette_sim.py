import time
import os
import pty
import threading
import random
import logging

# 在文件开头添加颜色常量
RED = '\033[91m'
GREEN = '\033[92m'
RESET = '\033[0m'
YELLOW = '\033[93m'   # 黄色
BLUE = '\033[94m'     # 蓝色
MAGENTA = '\033[95m'  # 紫色
GRAY = '\033[90m'     # 灰色

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("roulette_sim.log"),
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
        self.current_game_state = new_game_state
        """
        Duration, refer to log and video
        """ 

    def normal_state_machine(self):
        """
        Transition logic (without perturbations):
        1->2->3->4->5->1... until 6 interrupts
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
                self.transition("start_game")
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
        data = protocol_log_line

        if "*X;" in data:
            self.current_data_protocol_mode = f"{GREEN}game_mode{RESET}"

            if "*X;1" in data and self.current_game_state == "idle":
                self.game_state_transition_to("start_game")
            elif "*X;2" in data and self.current_game_state == "start_game":
                self.game_state_transition_to("place_bet")
            elif "*X;3" in data and self.current_game_state == "place_bet":
                self.game_state_transition_to("ball_launch")
            elif "*X;4" in data and self.current_game_state == "ball_launch":
                self.game_state_transition_to("no_more_bet")
            elif "*X;5" in data and self.current_game_state == "no_more_bet":
                self.game_state_transition_to("winning_number")
            elif "*X;6":
                self.game_state_transition_to("table_closed")
                self.game_state_transition_to("idle")
            else:
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
            self.current_data_protocol_mode = f"{MAGENTA}power_setting_mode{RESET}"
            """
            Power setting mode
            """
            if "*P 1" in data and self.current_power_state == "off":
                """add a confition: the next line is *P OK"""
                self.current_power_state = "on"
                """In arcade mode, power on will trigger table open"""
                self.game_state_transition_to("idle")
                self.game_state_transition_to("start_game")
            elif "*P 0" in data:
                """add a condition: the next line is *P OK"""
                self.current_power_state = "off"
                """off will trigger table force close"""
                self.game_state_transition_to("table_closed")
                self.game_state_transition_to("idle")
            elif "*P OK" in data:
                pass
            else:
                log_with_color(data)
                raise Exception("unknown power state.")
                                

        elif "*C" in data:
            self.current_data_protocol_mode = f"{BLUE}calibration_mode{RESET}"
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
            self.game_state_transition_to("start_game")
            pass
        elif "*M" in data:
            self.current_data_protocol_mode = "statistics_mode"
            """
            Statistics mode
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
                # 使用for循环跳过之前的行
                for _ in range(line_number - 1):
                    next(file)
                # 读取当前行
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
    log_file_name = "../log/ss2_protocol2.log"
    try:
        roulette = RouletteSimulator()
        roulette.roulette_main_thread(roulette.masterRoulettePort)
        log_with_color(f"Roulette simulator is running. Virtual port: {roulette.slaveRoulettePort}")
        log_with_color("Press Ctrl+C to stop the simulator.")

        while True:
            pass # keep the thread alive
    except KeyboardInterrupt:
        log_with_color("Stopping roulette simulator by keyboard interrupt...")
