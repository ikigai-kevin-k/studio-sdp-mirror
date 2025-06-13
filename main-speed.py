import serial
import threading
import time
from datetime import datetime
import sys
import random
import json
import asyncio
import websockets
sys.path.append('.')  # 確保可以導入 los_api
from los_api.sr.api_v2_sr import start_post_v2, deal_post_v2, finish_post_v2, broadcast_post_v2
from los_api.sr.api_v2_uat_sr import start_post_v2_uat, deal_post_v2_uat, finish_post_v2_uat, broadcast_post_v2_uat
from los_api.sr.api_v2_prd_sr import start_post_v2_prd, deal_post_v2_prd, finish_post_v2_prd, broadcast_post_v2_prd
from concurrent.futures import ThreadPoolExecutor

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
    with open('self-test-2api.log', 'a', encoding='utf-8') as f:
        timestamp = get_timestamp()
        f.write(f"[{timestamp}] {direction} {message}\n")

# 讀取 table 配置
def load_table_config():
    with open('conf/table-config-speed-roulette.json', 'r') as f:
        return json.load(f)

# 新增 LOS API 相關變數
tables = load_table_config()
x2_count = 0
x5_count = 0
isLaunch = 0
last_x2_time = 0
last_x5_time = 0
start_post_sent = False
deal_post_sent = False
finish_post_time = 0
token = 'E5LN4END9Q'
ws_client = None
ws_connected = False

# WebSocket 連接函數
async def connect_to_recorder(uri='ws://localhost:8765'):
    """連接到 stream recorder 的 WebSocket 服務器"""
    global ws_client, ws_connected
    try:
        ws_client = await websockets.connect(uri)
        ws_connected = True
        print(f"[{get_timestamp()}] 已連接到 stream recorder: {uri}")
        log_to_file(f"已連接到 stream recorder: {uri}", "WebSocket >>>")
        return True
    except Exception as e:
        print(f"[{get_timestamp()}] 連接到 stream recorder 失敗: {e}")
        log_to_file(f"連接到 stream recorder 失敗: {e}", "WebSocket >>>")
        ws_connected = False
        return False

# 發送 WebSocket 訊息函數
async def send_to_recorder(message):
    """發送訊息到 stream recorder"""
    global ws_client, ws_connected
    if not ws_connected or not ws_client:
        print(f"[{get_timestamp()}] 未連接到 stream recorder，嘗試重新連接...")
        log_to_file("未連接到 stream recorder，嘗試重新連接...", "WebSocket >>>")
        await connect_to_recorder()
        
    if ws_connected:
        try:
            await ws_client.send(message)
            response = await ws_client.recv()
            print(f"[{get_timestamp()}] Recorder 回應: {response}")
            log_to_file(f"Recorder 回應: {response}", "WebSocket >>>")
            return True
        except Exception as e:
            print(f"[{get_timestamp()}] 發送訊息到 recorder 失敗: {e}")
            log_to_file(f"發送訊息到 recorder 失敗: {e}", "WebSocket >>>")
            ws_connected = False
            return False
    return False

# 啟動 WebSocket 連接的異步函數
async def init_websocket():
    """初始化 WebSocket 連接"""
    await connect_to_recorder()

# 在主線程中啟動 WebSocket 連接
def start_websocket():
    """在主線程中啟動 WebSocket 連接"""
    asyncio.run(init_websocket())

# 在單獨的線程中啟動 WebSocket 連接
websocket_thread = threading.Thread(target=start_websocket)
websocket_thread.daemon = True
websocket_thread.start()

# 發送開始錄製訊息的函數
def send_start_recording(round_id):
    """發送開始錄製訊息"""
    asyncio.run(send_to_recorder(f"start_recording:{round_id}"))

# 發送停止錄製訊息的函數
def send_stop_recording():
    """發送停止錄製訊息"""
    # 使用線程來執行異步操作，避免阻塞主線程
    threading.Thread(target=lambda: asyncio.run(send_to_recorder("stop_recording"))).start()

def read_from_serial():
    global x2_count, x5_count, last_x2_time, last_x5_time, start_post_sent, deal_post_sent, start_time, deal_post_time, finish_post_time, isLaunch, tables, token
    while True:
        if ser.in_waiting > 0:
            data = ser.readline().decode('utf-8').strip()
            print("Receive >>>", data)
            log_to_file(data, "Receive >>>")
            
            # 處理 *X;2 計數
            if "*X;2" in data:
                current_time = time.time()
                if current_time - last_x2_time > 5:
                    x2_count = 1
                else:
                    x2_count += 1
                last_x2_time = current_time
                
                # 檢查 warning_flag 是否為 8，如果是則發送 broadcast_post
                try:
                    parts = data.split(';')
                    if len(parts) >= 5:  # 確保有足夠的部分來獲取 warning_flag
                        warning_flag = parts[4]
                        current_time = time.time()
                        
                        # 檢查 warning_flag 是否需要發送 broadcast
                        if int(warning_flag) == 8 or int(warning_flag) == 2 or warning_flag == 'A':
                            # 檢查是否已經過了 10 秒或是第一次發送
                            if not hasattr(execute_broadcast_post, 'last_broadcast_time') or \
                               (current_time - execute_broadcast_post.last_broadcast_time) >= 10:
                                
                                print(f"\n檢測到 warning_flag 不等於0，發送 broadcast_post 通知重新發射...")
                                log_to_file("檢測到 warning_flag 不等於0，發送 broadcast_post 通知重新發射", "Broadcast >>>")
                                
                                # 對每個桌子發送 broadcast_post
                                with ThreadPoolExecutor(max_workers=len(tables)) as executor:
                                    futures = [executor.submit(execute_broadcast_post, table, token) for table in tables]
                                    for future in futures:
                                        future.result()  # 等待所有請求完成
                                
                                # 更新最後發送時間
                                execute_broadcast_post.last_broadcast_time = current_time
                            else:
                                print(f"已在 {current_time - execute_broadcast_post.last_broadcast_time:.1f} 秒前發送過 broadcast，等待時間間隔...")
                except Exception as e:
                    print(f"解析 warning_flag 或發送 broadcast_post 錯誤: {e}")
                    log_to_file(f"解析 warning_flag 或發送 broadcast_post 錯誤: {e}", "Error >>>")
                
                if x2_count >= 1 and not start_post_sent:
                    time.sleep(2) # for the show result animation time
                    print("\n================Start================")
                    
                    try:
                        start_time = time.time()
                        print(f"start_time: {start_time}")
                        log_to_file(f"start_time: {start_time}", "Receive >>>")
                        
                        if finish_post_time == 0:
                            finish_post_time = start_time
                        finish_to_start_time = start_time - finish_post_time
                        print(f"finish_to_start_time: {finish_to_start_time}")
                        log_to_file(f"finish_to_start_time: {finish_to_start_time}", "Receive >>>")

                        # 非同步處理所有 table 的 start_post
                        with ThreadPoolExecutor(max_workers=len(tables)) as executor:
                            futures = [executor.submit(execute_start_post, table, token) for table in tables]
                            for future in futures:
                                future.result()  # 等待所有請求完成

                        start_post_sent = True
                        deal_post_sent = False

                        print("\n發送 *u 1 指令...")
                        ser.write(("*u 1\r\n").encode())
                        log_to_file("*u 1", "Send <<<")
                        print("已發送 *u 1 指令\n")
                        
                        # 在發送 *u 1 指令後兩秒開始錄製
                        if tables and len(tables) > 0 and 'round_id' in tables[0]:
                            round_id = tables[0]['round_id']
                            print(f"[{get_timestamp()}] 準備開始錄製 round_id: {round_id}，將在兩秒後開始")
                            log_to_file(f"準備開始錄製 round_id: {round_id}，將在兩秒後開始", "WebSocket >>>")
                            # 使用線程延遲執行錄製，避免阻塞主流程
                            threading.Timer(2.0, lambda: send_start_recording(round_id)).start()
                    except Exception as e:
                        print(f"start_post 錯誤: {e}")
                    print("======================================\n")
            
            elif "*X;3" in data and not isLaunch:
                ball_launch_time = time.time()
                print(f"ball_launch_time: {ball_launch_time}")
                log_to_file(f"ball_launch_time: {ball_launch_time}", "Receive >>>")
                isLaunch = 1

                start_to_launch_time = ball_launch_time - start_time
                print(f"start_to_launch_time: {start_to_launch_time}")
                log_to_file(f"start_to_launch_time: {start_to_launch_time}", "Receive >>>")
                
                # 移除在球發射時開始錄製的程式碼，因為已經在 *u 1 指令後兩秒開始錄製了

            # 處理 *X;5 計數
            elif "*X;5" in data and not deal_post_sent:
                current_time = time.time()
                if current_time - last_x5_time > 5:
                    x5_count = 1
                else:
                    x5_count += 1
                last_x5_time = current_time
                
                if x5_count == 1:
                    try:
                        parts = data.split(';')
                        if len(parts) >= 4:
                            win_num = int(parts[3])
                            print(f"本局中獎號碼: {win_num}")

                            print("\n================Deal================")
                            
                            try:
                                deal_post_time = time.time()
                                print(f"deal_post_time: {deal_post_time}")
                                log_to_file(f"deal_post_time: {deal_post_time}", "Receive >>>")
                                
                                launch_to_deal_time = deal_post_time - ball_launch_time
                                print(f"launch_to_deal_time: {launch_to_deal_time}")
                                log_to_file(f"launch_to_deal_time: {launch_to_deal_time}", "Receive >>>")

                                # 停止錄製 - 改為非阻塞方式執行
                                print(f"[{get_timestamp()}] 停止錄製")
                                log_to_file("停止錄製", "WebSocket >>>")
                                send_stop_recording()  # 現在這個函數不會阻塞主線程

                                # 非同步處理所有 table 的 deal_post
                                with ThreadPoolExecutor(max_workers=len(tables)) as executor:
                                    futures = [executor.submit(execute_deal_post, table, token, win_num) for table in tables]
                                    for future in futures:
                                        future.result()  # 等待所有請求完成

                                deal_post_sent = True
                            except Exception as e:
                                print(f"deal_post 錯誤: {e}")
                            
                            print("======================================\n")
                            
                            # time.sleep(1)
                            print("\n================Finish================")
                            
                            try:
                                finish_post_time = time.time()
                                print(f"finish_post_time: {finish_post_time}")
                                log_to_file(f"finish_post_time: {finish_post_time}", "Receive >>>")
                                
                                deal_to_finish_time = finish_post_time - deal_post_time
                                print(f"deal_to_finish_time: {deal_to_finish_time}")
                                log_to_file(f"deal_to_finish_time: {deal_to_finish_time}", "Receive >>>")

                                log_to_file("Summary:", "Receive >>>")
                                log_to_file(f"start_to_launch_time: {start_to_launch_time}", "Receive >>>")
                                log_to_file(f"launch_to_deal_time: {launch_to_deal_time}", "Receive >>>")
                                log_to_file(f"deal_to_finish_time: {deal_to_finish_time}", "Receive >>>")
                                log_to_file(f"finish_to_start_time: {finish_to_start_time}", "Receive >>>")

                                log_time_intervals(finish_to_start_time, start_to_launch_time, 
                                                 launch_to_deal_time, deal_to_finish_time)

                                # 非同步處理所有 table 的 finish_post
                                with ThreadPoolExecutor(max_workers=len(tables)) as executor:
                                    futures = [executor.submit(execute_finish_post, table, token) for table in tables]
                                    for future in futures:
                                        future.result()  # 等待所有請求完成

                                # 重置所有標記和計數器
                                start_post_sent = False
                                x2_count = 0
                                x5_count = 0
                                isLaunch = 0
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

def log_time_intervals(finish_to_start, start_to_launch, launch_to_deal, deal_to_finish):
    """Log time intervals to a separate file"""
    with open('time_intervals-2api.log', 'a', encoding='utf-8') as f:
        timestamp = get_timestamp()
        f.write(f"[{timestamp}]\n")
        f.write(f"finish_to_start_time: {finish_to_start}\n")
        f.write(f"start_to_launch_time: {start_to_launch}\n")
        f.write(f"launch_to_deal_time: {launch_to_deal}\n")
        f.write(f"deal_to_finish_time: {deal_to_finish}\n")
        f.write("-" * 50 + "\n")
    
    # 檢查時間間隔是否超過限制
    try:
        error_message = None
        if finish_to_start > 4:
            error_message = f"Assertion Error: finish_to_start_time ({finish_to_start:.2f}s) > 4s"
        elif start_to_launch > 20:
            error_message = f"Assertion Error: start_to_launch_time ({start_to_launch:.2f}s) > 20s"
        elif launch_to_deal > 20:
            error_message = f"Assertion Error: launch_to_deal_time ({launch_to_deal:.2f}s) > 20s"
        elif deal_to_finish > 2:
            error_message = f"Assertion Error: deal_to_finish_time ({deal_to_finish:.2f}s) > 2s"
        
        if error_message:
            # 獲取當前 round_id
            current_round_id = "unknown"
            if tables and len(tables) > 0 and 'round_id' in tables[0]:
                current_round_id = tables[0]['round_id']
            
            # 記錄錯誤到日誌檔案，包含 round_id
            with open('assertion_errors.log', 'a', encoding='utf-8') as f:
                timestamp = get_timestamp()
                f.write(f"[{timestamp}] Round ID: {current_round_id} - {error_message}\n")
            
            # 同時記錄到主日誌檔案
            log_to_file(f"{error_message} (Round ID: {current_round_id})", "ERROR >>>")
            
            # 輸出錯誤訊息到控制台，但不終止程式
            print(f"\n[{get_timestamp()}] {error_message} (Round ID: {current_round_id})")
            print("時間間隔超出限制，但程式繼續執行")
            
            # 移除終止程式的部分
            # sys.exit(1)
    except Exception as e:
        log_to_file(f"檢查時間間隔時發生錯誤: {e}", "ERROR >>>")
        print(f"檢查時間間隔時發生錯誤: {e}")

def execute_finish_post(table, token):
    try:
        post_url = f"{table['post_url']}{table['game_code']}"
        result = finish_post(post_url, token)
        print(f"成功結束本局遊戲 for {table['name']}")
        return result
    except Exception as e:
        print(f"執行 finish_post 錯誤 for {table['name']}: {e}")
        return None

def execute_start_post(table, token):
    try:
        post_url = f"{table['post_url']}{table['game_code']}"
        round_id, betPeriod = start_post(post_url, token)
        if round_id != -1:
            table['round_id'] = round_id
            print(f"成功呼叫 start_post for {table['name']}，round_id: {round_id}, betPeriod: {betPeriod}")
            return round_id, betPeriod
        else:
            print(f"呼叫 start_post 失敗 for {table['name']}")
            return -1, 0
    except Exception as e:
        print(f"執行 start_post 錯誤 for {table['name']}: {e}")
        return -1, 0

def execute_deal_post(table, token, win_num):
    try:
        post_url = f"{table['post_url']}{table['game_code']}"
        result = deal_post(post_url, token, table['round_id'], str(win_num))
        print(f"成功傳送開獎結果 for {table['name']}: {win_num}")
        return result
    except Exception as e:
        print(f"執行 deal_post 錯誤 for {table['name']}: {e}")
        return None

def execute_broadcast_post(table, token):
    """執行 broadcast_post 通知重新發射"""
    try:
        post_url = f"{table['post_url']}{table['game_code']}"
        result = broadcast_post(post_url, token, "roulette.relaunch", "players", 20)
        print(f"成功發送 broadcast_post (relaunch) for {table['name']}")
        log_to_file(f"成功發送 broadcast_post (relaunch) for {table['name']}", "Broadcast >>>")
        return result
    except Exception as e:
        print(f"執行 broadcast_post 錯誤 for {table['name']}: {e}")
        log_to_file(f"執行 broadcast_post 錯誤 for {table['name']}: {e}", "Error >>>")
        return None

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