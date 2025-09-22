import serial
import threading
import time
from datetime import datetime

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

def read_from_serial():
    while True:
        if ser.in_waiting > 0:
            data = ser.readline().decode('utf-8').strip()
            print("Receive >>>", data)
            log_to_file(data, "Receive >>>")
        time.sleep(0.1)

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
