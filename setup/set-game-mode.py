# for speed roulette
# *o 135
# *T h 161
# *T s 16.0 18.0
# *T t 1475
# *T r 23000 23000
# *T n 3999
# *T m 2.0

# for vip roulette
# *o 1167
# *T h 150
# *T s 16.0 18.0
# *T t 1475
# *T r 33000 36000
# *T n 3600
# *T m 2.0


import sys
import os
import threading
import serial
import time
import json

# 創建新的串口實例
ser = serial.Serial(
    port='/dev/ttyUSB0',
    baudrate=9600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1
)

def load_parameters():
    """Load parameters from JSON file"""
    try:
        with open('roulette_params.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Error: roulette_params.json not found")
        sys.exit(1)
    except json.JSONDecodeError:
        print("Error: Invalid JSON format in roulette_params.json")
        sys.exit(1)

def send_command_and_wait(command, timeout=2):
    """Send a command and wait for the expected response"""
    ser.write((command + '\r\n').encode())
    print(f"Send <<< {command}")
    
    # Get command type (H, S, T, or R)
    cmd_type = command[-1].lower()
    
    # Wait for response
    start_time = time.time()
    while (time.time() - start_time) < timeout:
        if ser.in_waiting > 0:
            response = ser.readline().decode('utf-8').strip()
            print("Receive >>>", response)
            
            # Check if this is the response we're waiting for
            if response.startswith(f"*T {cmd_type}"):
                # Parse the value from response
                parts = response.split()
                if len(parts) > 2:  # Make sure we have values after "*T x"
                    return ' '.join(parts[2:])  # Return only the values
        time.sleep(0.1)
    return None

def set_roulette_mode(mode_params):
    """Set parameters for a specific roulette mode"""
    commands = [
        f"*o {mode_params['operation_mode']}",
        f"*T h {mode_params['gph']}",
        f"*T s {mode_params['wheel_speed']}",
        f"*T t {mode_params['deceleration_distance']}",
        f"*T r {mode_params['in_rim_jet_duration']}",
        f"*T n {mode_params['T_n']}",
        f"*T m {mode_params['T_m']}"
    ]
    
    for cmd in commands:
        print(f"\nSetting {cmd}...")
        response = send_command_and_wait(cmd)
        if response:
            print(f"Successfully set {cmd}")
        else:
            print(f"Failed to set {cmd}")
        time.sleep(0.5)  # Add delay between commands

def main():
    # Load parameters at startup
    params = load_parameters()
    
    while True:
        print("\n=== Roulette Mode Selector ===")
        print("1. Speed Roulette")
        print("2. VIP Roulette")
        print("3. Exit")
        
        choice = input("\nEnter your choice (1-3): ")
        
        if choice == "1":
            print("\nSetting Speed Roulette parameters...")
            set_roulette_mode(params['speed_roulette'])
        elif choice == "2":
            print("\nSetting VIP Roulette parameters...")
            set_roulette_mode(params['vip_roulette'])
        elif choice == "3":
            print("Exiting program...")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n程式結束")
    finally:
        ser.close()