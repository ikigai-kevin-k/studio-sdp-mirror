import serial
import threading
import time
from datetime import datetime
import sys
sys.path.append('.')  # ensure los_api can be imported
from los_api.vr.api_v2_vr import start_post_v2, deal_post_v2, finish_post_v2, broadcast_post_v2
from los_api.vr.api_v2_uat_vr import start_post_v2_uat, deal_post_v2_uat, finish_post_v2_uat, broadcast_post_v2_uat
from los_api.vr.api_v2_prd_vr import start_post_v2_prd, deal_post_v2_prd, finish_post_v2_prd, broadcast_post_v2_prd
from los_api.vr.api_v2_stg_vr import start_post_v2_stg, deal_post_v2_stg, finish_post_v2_stg, broadcast_post_v2_stg
import json

ser = serial.Serial(
    port='/dev/ttyUSB0',
    baudrate=9600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1
)

def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

def log_to_file(message, direction):
    with open('self-test.log', 'a', encoding='utf-8') as f:
        timestamp = get_timestamp()
        f.write(f"[{timestamp}] {direction} {message}\n")

# load table config
def load_table_config():
    with open('conf/table-config-vip-roulette-v2.json', 'r') as f:
        return json.load(f)

# add LOS API related variables
tables = load_table_config()
x2_count = 0
x5_count = 0
x3_count = 0  # add *X;3 counter
last_x2_time = 0
last_x5_time = 0
start_post_sent = False
deal_post_sent = False  # add flag to track deal_post
first_u1_sent = False  # add flag to track first *u 1

# add time related variables
start_time = 0
launch_time = 0
deal_time = 0
finish_time = 0

def log_time_intervals(finish_to_start, start_to_launch, launch_to_deal, deal_to_finish):
    """Log time intervals to a separate file"""
    with open('time_intervals_vip.log', 'a', encoding='utf-8') as f:
        timestamp = get_timestamp()
        f.write(f"[{timestamp}]\n")
        f.write(f"finish_to_start_time: {finish_to_start}\n")
        f.write(f"start_to_launch_time: {start_to_launch}\n")
        f.write(f"launch_to_deal_time: {launch_to_deal}\n")
        f.write(f"deal_to_finish_time: {deal_to_finish}\n")
        f.write("-" * 50 + "\n")

def read_from_serial():
    global x2_count, x5_count, x3_count, last_x2_time, last_x5_time, start_post_sent, deal_post_sent, first_u1_sent
    global start_time, launch_time, deal_time, finish_time
    
    while True:
        if ser.in_waiting > 0:
            data = ser.readline().decode('utf-8').strip()
            print("Receive >>>", data)
            log_to_file(data, "Receive >>>")
            
            # handle *X;3 count
            if "*X;3" in data and first_u1_sent and not deal_post_sent:
                x3_count += 1
                print(f"*X;3 計數: {x3_count}/50")
                if x3_count == 1:
                    launch_time = time.time()  # record launch time
                # when 50 *X;3 are collected, send second *u 1 command
                if x3_count >= 50:
                    print("\n已收集到 50 個 *X;3，發送第二個 *u 1 指令...")
                    ser.write(("*u 1\r\n").encode())
                    log_to_file("*u 1", "Send <<<")
                    print("已發送第二個 *u 1 指令\n")
                    x3_count = 0  # reset counter for next round
            
            # handle *X;2 count
            elif "*X;2" in data:
                current_time = time.time()
                if current_time - last_x2_time > 5:
                    x2_count = 1
                else:
                    x2_count += 1
                last_x2_time = current_time
                
                if x2_count >= 2 and not start_post_sent:
                    print("\n================Start================")
                    try:
                        start_time = time.time()  # record start time
                        
                        # check if it is the first round
                        if finish_time == 0:
                            finish_time = start_time
                        finish_to_start_time = start_time - finish_time
                        
                        # execute start_post for each table
                        for table in tables:
                            post_url = f"{table['post_url']}{table['game_code']}"
                            round_id, betPeriod = start_post(post_url, token)
                            if round_id != -1:
                                table['round_id'] = round_id
                                print(f"成功呼叫 start_post for {table['name']}，round_id: {round_id}, betPeriod: {betPeriod}")
                            else:
                                print(f"呼叫 start_post 失敗 for {table['name']}")

                        start_post_sent = True
                        deal_post_sent = False  # reset deal_post flag
                        first_u1_sent = False  # reset first *u 1 flag
                        x3_count = 0  # reset *X;3 counter
                        
                        # send first *u 1 command after start_post is successfully sent
                        print("\nsend first *u 1 command...")
                        ser.write(("*u 1\r\n").encode())
                        log_to_file("*u 1", "Send <<<")
                        first_u1_sent = True  # mark first *u 1 as sent
                        print("sent first *u 1 command\n")
                    except Exception as e:
                        print(f"error sending start_post: {e}")
                    print("======================================\n")
            
            # handle *X;5 count
            elif "*X;5" in data and not deal_post_sent:  # only handle when deal_post is not sent
                current_time = time.time()
                if current_time - last_x5_time > 5:
                    x5_count = 1
                else:
                    x5_count += 1
                last_x5_time = current_time
                
                if x5_count == 5:  # handle when the first *X;5 is received
                    try:
                        parts = data.split(';')
                        if len(parts) >= 4:
                            win_num = int(parts[3])
                            print(f"win_num: {win_num}")
                            
                            print("\n================Deal================")
                            deal_time = time.time()  # record deal time
                            try:
                                # execute deal_post for each table
                                for table in tables:
                                    post_url = f"{table['post_url']}{table['game_code']}"
                                    deal_post(post_url, token, table['round_id'], str(win_num))
                                    print(f"deal_post for {table['name']}: {win_num}")
                                deal_post_sent = True  # mark deal_post as sent
                            except Exception as e:
                                print(f"error sending deal_post: {e}")
                            print("======================================\n")
                            
                            print("\n================Finish================")
                            try:
                                finish_time = time.time()  # record finish time
                                
                                # calculate time intervals for each stage
                                start_to_launch_time = launch_time - start_time
                                launch_to_deal_time = deal_time - launch_time
                                deal_to_finish_time = finish_time - deal_time
                                
                                # log time intervals to file
                                log_time_intervals(finish_to_start_time, start_to_launch_time, 
                                                 launch_to_deal_time, deal_to_finish_time)
                                
                                # execute finish_post for each table
                                for table in tables:
                                    post_url = f"{table['post_url']}{table['game_code']}"
                                    finish_post(post_url, token)
                                    print(f"finish_post for {table['name']}")

                                # reset all flags and counters
                                start_post_sent = False
                                first_u1_sent = False
                                x2_count = 0
                                x3_count = 0
                                x5_count = 0
                            except Exception as e:
                                print(f"error sending finish_post: {e}")
                            print("======================================\n")
                            
                    except Exception as e:
                        print(f"error parsing win_num: {e}")

def send_command_and_wait(command, timeout=2):
    """Send a command and wait for the expected response"""
    ser.write((command + '\r\n').encode())
    log_to_file(command, "Send <<<")
    
    # Get command type (H, S, T, or R)
    cmd_type = command[-1].lower()
    
    # Wait for response
    start_time = time.time()
    while (time.time() - start_time) < timeout:
        if ser.in_waiting > 0:
            response = ser.readline().decode('utf-8').strip()
            print("Receive >>>", response)
            log_to_file(response, "Receive >>>")
            
            # Check if this is the response we're waiting for
            if response.startswith(f"*T {cmd_type}"):
                # Parse the value from response
                parts = response.split()
                if len(parts) > 2:  # Make sure we have values after "*T x"
                    return ' '.join(parts[2:])  # Return only the values
        time.sleep(0.1)
    return None

def get_config():
    """Get all configuration parameters from terminal"""
    print("\nGetting configuration parameters...")
    
    # Store results
    config_results = {
        "*T H - GPH": None,
        "*T S - Wheel Speed": None,
        "*T T - Deceleration Distance": None,
        "*T R - In-rim Jet Duration": None
    }
    
    # Define commands and their descriptions
    commands = [
        ("*T H", "*T H - GPH"),
        ("*T S", "*T S - Wheel Speed"),
        ("*T T", "*T T - Deceleration Distance"),
        ("*T R", "*T R - In-rim Jet Duration")
    ]
    
    # Execute each command and collect responses
    for cmd, desc in commands:
        print(f"\nQuerying {desc}...")
        value = send_command_and_wait(cmd)
        if value:
            config_results[desc] = value  # only store the value part
            print(f"Stored value: {desc} = {value}")  # for debugging
        time.sleep(0.5)  # Add delay between commands
    
    # Print all results together
    print("\n=== Configuration Parameters ===")
    print("-" * 50)
    for desc, value in config_results.items():
        if value:
            print(f"{desc}: {value}")
        else:
            print(f"{desc}: No valid response")
    print("-" * 50)

def write_to_serial():
    while True:
        try:
            text = input("Send <<< ")
            if text.lower() in ["get_config", "gc"]:  # add "gc" as an abbreviation
                get_config()
            else:
                ser.write((text + '\r\n').encode())
                log_to_file(text, "Send <<<")
        except KeyboardInterrupt:
            break

# create and start read thread
read_thread = threading.Thread(target=read_from_serial)
read_thread.daemon = True
read_thread.start()

# main thread handles writing
try:
    write_to_serial()
except KeyboardInterrupt:
    print("\nprogram terminated")
finally:
    ser.close()