import serial
import threading
import time
from datetime import datetime
import sys
sys.path.append('.')  # 確保可以導入 los_api
from los_api.vr.api_v2_vr import start_post_v2, deal_post_v2, finish_post_v2, broadcast_post_v2
from los_api.vr.api_v2_uat_vr import start_post_v2_uat, deal_post_v2_uat, finish_post_v2_uat, broadcast_post_v2_uat
from los_api.vr.api_v2_prd_vr import start_post_v2_prd, deal_post_v2_prd, finish_post_v2_prd, broadcast_post_v2_prd
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

# 讀取 table 配置
def load_table_config():
    with open('conf/table-config-vip-roulette.json', 'r') as f:
        return json.load(f)

# 新增 LOS API 相關變數
tables = load_table_config()
x2_count = 0
x5_count = 0
x3_count = 0  # 新增 *X;3 計數器
last_x2_time = 0
last_x5_time = 0
start_post_sent = False
deal_post_sent = False  # 新增標記，用於追蹤 deal_post 是否已發送
first_u1_sent = False  # 新增標記，用於追蹤第一個 *u 1 是否已發送

# 新增時間相關變數
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
            
            # 處理 *X;3 計數
            if "*X;3" in data and first_u1_sent and not deal_post_sent:
                x3_count += 1
                print(f"*X;3 計數: {x3_count}/50")
                if x3_count == 1:
                    launch_time = time.time()  # 記錄發射時間
                # 當收集到 50 個 *X;3 時，發送第二個 *u 1 指令
                if x3_count >= 50:
                    print("\n已收集到 50 個 *X;3，發送第二個 *u 1 指令...")
                    ser.write(("*u 1\r\n").encode())
                    log_to_file("*u 1", "Send <<<")
                    print("已發送第二個 *u 1 指令\n")
                    x3_count = 0  # 重置計數器，以便下一輪使用
            
            # 處理 *X;2 計數
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
                        start_time = time.time()  # 記錄開始時間
                        
                        # 檢查是否為第一局
                        if finish_time == 0:
                            finish_time = start_time
                        finish_to_start_time = start_time - finish_time
                        
                        # 為每個 table 執行 start_post
                        for table in tables:
                            post_url = f"{table['post_url']}{table['game_code']}"
                            round_id, betPeriod = start_post(post_url, token)
                            if round_id != -1:
                                table['round_id'] = round_id
                                print(f"成功呼叫 start_post for {table['name']}，round_id: {round_id}, betPeriod: {betPeriod}")
                            else:
                                print(f"呼叫 start_post 失敗 for {table['name']}")

                        start_post_sent = True
                        deal_post_sent = False  # 重置 deal_post 標記
                        first_u1_sent = False  # 重置第一個 *u 1 標記
                        x3_count = 0  # 重置 *X;3 計數器
                        
                        # 在成功發送 start_post 後自動發送第一個 *u 1 指令
                        print("\n發送第一個 *u 1 指令...")
                        ser.write(("*u 1\r\n").encode())
                        log_to_file("*u 1", "Send <<<")
                        first_u1_sent = True  # 標記第一個 *u 1 已發送
                        print("已發送第一個 *u 1 指令\n")
                    except Exception as e:
                        print(f"start_post 錯誤: {e}")
                    print("======================================\n")
            
            # 處理 *X;5 計數
            elif "*X;5" in data and not deal_post_sent:  # 只在未發送 deal_post 時處理
                current_time = time.time()
                if current_time - last_x5_time > 5:
                    x5_count = 1
                else:
                    x5_count += 1
                last_x5_time = current_time
                
                if x5_count == 5:  # 在第一個 *X;5 時處理
                    try:
                        parts = data.split(';')
                        if len(parts) >= 4:
                            win_num = int(parts[3])
                            print(f"本局中獎號碼: {win_num}")
                            
                            print("\n================Deal================")
                            deal_time = time.time()  # 記錄開獎時間
                            try:
                                # 為每個 table 執行 deal_post
                                for table in tables:
                                    post_url = f"{table['post_url']}{table['game_code']}"
                                    deal_post(post_url, token, table['round_id'], str(win_num))
                                    print(f"成功傳送開獎結果 for {table['name']}: {win_num}")
                                deal_post_sent = True  # 標記 deal_post 已發送
                            except Exception as e:
                                print(f"deal_post 錯誤: {e}")
                            print("======================================\n")
                            
                            print("\n================Finish================")
                            try:
                                finish_time = time.time()  # 記錄結束時間
                                
                                # 計算各階段時間間隔
                                start_to_launch_time = launch_time - start_time
                                launch_to_deal_time = deal_time - launch_time
                                deal_to_finish_time = finish_time - deal_time
                                
                                # 記錄時間間隔到檔案
                                log_time_intervals(finish_to_start_time, start_to_launch_time, 
                                                 launch_to_deal_time, deal_to_finish_time)
                                
                                # 為每個 table 執行 finish_post
                                for table in tables:
                                    post_url = f"{table['post_url']}{table['game_code']}"
                                    finish_post(post_url, token)
                                    print(f"成功結束本局遊戲 for {table['name']}")

                                # 重置所有標記和計數器
                                start_post_sent = False
                                first_u1_sent = False
                                x2_count = 0
                                x3_count = 0
                                x5_count = 0
                            except Exception as e:
                                print(f"finish_post 錯誤: {e}")
                            print("======================================\n")
                            
                    except Exception as e:
                        print(f"解析中獎號碼錯誤: {e}")

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
            config_results[desc] = value  # 只存數值部分
            print(f"Stored value: {desc} = {value}")  # 用於調試
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
            if text.lower() in ["get_config", "gc"]:  # 新增 "gc" 作為縮寫
                get_config()
            else:
                ser.write((text + '\r\n').encode())
                log_to_file(text, "Send <<<")
        except KeyboardInterrupt:
            break

# 創建並啟動讀取線程
read_thread = threading.Thread(target=read_from_serial)
read_thread.daemon = True
read_thread.start()

# 主線程處理寫入
try:
    write_to_serial()
except KeyboardInterrupt:
    print("\n程式結束")
finally:
    ser.close()