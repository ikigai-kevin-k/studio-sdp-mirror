import serial
import time
import json
import os
from datetime import datetime

# Serial port configuration
SERIAL_PORT = '/dev/ttyUSB0'
BAUDRATE = 9600
TIMEOUT = 1

# Commands to query
COMMANDS = [
    "*T D",
    "*T P",
    "*T Q",
    "*T K",
    "*T I",
    "*T J",
    "*T R",
    "*T S",
    "*T T",
    "*T N",
    "*T M",
    "*T H",
    "*T Z",
    "*T G"
]

def get_timestamp():
    """Get formatted timestamp"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

def log_to_file(message, direction):
    """Log message to file"""
    with open('roulette_params.log', 'a', encoding='utf-8') as f:
        timestamp = get_timestamp()
        f.write(f"[{timestamp}] {direction} {message}\n")

def send_command_and_wait(ser, command, timeout=2):
    """Send a command and wait for the expected response"""
    try:
        # Send command
        ser.write((command + '\r\n').encode())
        log_to_file(command, "Send <<<")
        print(f"Send <<< {command}")
        
        # Get command type for *T commands
        if command.startswith("*T "):
            cmd_type = command[-1].upper()
        else:
            cmd_type = None
        
        # Wait for response
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            if ser.in_waiting > 0:
                response = ser.readline().decode('utf-8', errors='ignore').strip()
                if response:
                    print(f"Receive >>> {response}")
                    log_to_file(response, "Receive >>>")
                    
                    # Check if this is the response we're waiting for
                    # Response comes back in lowercase (e.g., send *T H, receive *T h 161)
                    if cmd_type and response.lower().startswith(f"*t {cmd_type.lower()}"):
                        # Parse the value from response
                        parts = response.split()
                        if len(parts) > 2:
                            return ' '.join(parts[2:])  # Return only the values
                        return response
                    elif not cmd_type:
                        # For non-*T commands, return any response
                        return response
            time.sleep(0.1)
        
        return None
    except Exception as e:
        print(f"Error sending command {command}: {e}")
        log_to_file(f"Error: {e}", "ERROR >>>")
        return None

def get_all_parameters(ser):
    """Get all configuration parameters from roulette controller"""
    print("\n" + "=" * 60)
    print("Getting Roulette Controller Parameters")
    print("=" * 60)
    
    # Store results
    results = {}
    
    # Execute each command and collect responses
    for i, command in enumerate(COMMANDS, 1):
        print(f"\n[{i}/{len(COMMANDS)}] Querying {command}...")
        value = send_command_and_wait(ser, command, timeout=3)
        if value:
            results[command] = value
            print(f"✓ {command}: {value}")
        else:
            results[command] = "No response"
            print(f"✗ {command}: No response or timeout")
        
        # Add delay between commands to avoid overwhelming the device
        time.sleep(0.5)
    
    # Print all results together
    print("\n" + "=" * 60)
    print("=== All Parameters ===")
    print("=" * 60)
    for command, value in results.items():
        print(f"{command:10s}: {value}")
    print("=" * 60)
    
    return results

def main():
    """Main function"""
    ser = None
    try:
        # Initialize serial connection
        print(f"Connecting to serial port: {SERIAL_PORT}")
        ser = serial.Serial(
            port=SERIAL_PORT,
            baudrate=BAUDRATE,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=TIMEOUT
        )
        print(f"✓ Serial connection established successfully")
        log_to_file(f"Serial connection established: {SERIAL_PORT}", "INFO >>>")
        
        # Wait a moment for connection to stabilize
        time.sleep(0.5)
        
        # Get all parameters
        results = get_all_parameters(ser)
        
        # Save parameters to JSON file
        params_file = os.path.join(os.path.dirname(__file__), 'params.json')
        try:
            with open(params_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"\n✓ Parameters saved to {params_file}")
            log_to_file(f"Parameters saved to {params_file}", "INFO >>>")
        except Exception as e:
            print(f"\n✗ Error saving parameters to JSON: {e}")
            log_to_file(f"Error saving parameters to JSON: {e}", "ERROR >>>")
        
        # Log summary
        log_to_file("Parameter retrieval completed", "INFO >>>")
        print("\n✓ All parameters retrieved successfully")
        
    except serial.SerialException as e:
        print(f"✗ Serial port error: {e}")
        log_to_file(f"Serial port error: {e}", "ERROR >>>")
        return 1
    except KeyboardInterrupt:
        print("\n\nProgram interrupted by user")
        log_to_file("Program interrupted by user", "INFO >>>")
        return 1
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        log_to_file(f"Unexpected error: {e}", "ERROR >>>")
        return 1
    finally:
        # Close serial connection safely
        if ser and ser.is_open:
            try:
                ser.close()
                print("\n✓ Serial port closed successfully")
                log_to_file("Serial port closed", "INFO >>>")
            except Exception as e:
                print(f"✗ Error closing serial port: {e}")
                log_to_file(f"Error closing serial port: {e}", "ERROR >>>")
    
    return 0

if __name__ == "__main__":
    exit(main())

