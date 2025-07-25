import serial
import time
import logging
import serial.rs485
import serial.tools.list_ports
import multiprocessing
from multiprocessing import Queue
import sys

# Configuration
serialport = str(sys.argv[1]) if len(sys.argv) > 1 else "/dev/ttyACM0"
serialbaudrate = 115200  # Changed from 9600 to 115200
spincount = 1
logfile = "HuxleyLogfile.log"

logging.basicConfig(filename=logfile, level=logging.INFO, filemode='a', format="%(asctime)s:%(levelname)s: %(message)s")
logging.getLogger().addHandler(logging.StreamHandler())

def list_available_ports():
    """List all available serial ports on the system"""
    print("Searching for available serial ports...")
    ports = serial.tools.list_ports.comports()
    
    if not ports:
        print("No serial ports found on the system.")
        return []
    
    print(f"Found {len(ports)} serial port(s):")
    for i, port in enumerate(ports, 1):
        print(f"{i}. {port.device} - {port.description}")
        if port.hwid:
            print(f"   Hardware ID: {port.hwid}")
        if port.manufacturer:
            print(f"   Manufacturer: {port.manufacturer}")
        if port.product:
            print(f"   Product: {port.product}")
        print()
    
    return [port.device for port in ports]

class FireWheel:
    def __init__(self):
        print(32 * "*"  + "\nSTARTING SATURN POLL APPLICATION\n" + 32 * "*")
        
        # List available ports before proceeding
        available_ports = list_available_ports()
        
        if not available_ports:
            print("No serial ports available. Exiting...")
            sys.exit(1)
        
        # Check if the specified port exists
        if serialport not in available_ports:
            print(f"Warning: Specified port '{serialport}' not found in available ports.")
            print(f"Available ports: {available_ports}")
            print("Please check your port specification.")
        
        self.last_time = int(round(time.time() * 1000))
        self.last_fire_time = int(round(time.time() * 1000))
        self.Process = multiprocessing.Process(target=self.send_command)
        self.thread_queue = Queue()
        self.error_flag = 0
        self.seq = ""

        # Opening Serial with correct baudrate
        print(f"Opening Serial Port with baudrate: {serialbaudrate}")
        try:
            self.ser = serial.rs485.RS485(
                port=serialport, 
                baudrate=serialbaudrate, 
                stopbits=serial.STOPBITS_ONE, 
                parity=serial.PARITY_NONE, 
                bytesize=serial.EIGHTBITS, 
                timeout=0, 
                rtscts=0
            )
            self.ser.rs485_mode = serial.rs485.RS485Settings(False, True)
            print(f"Serial Port Opened on port {serialport} with baudrate {serialbaudrate}")
        except serial.SerialException as e:
            print("Something Went Wrong! \n" + str(e))
            print("EXITING!")
            quit()

        print(f"Serial port open: {self.ser.is_open}")
        self.ser.flush()
        self.ser.flushInput()
        self.ser.flushOutput()

    def close_serial(self):
        print("Closing Serial Port")
        self.ser.close()
        print("Serial Port Closed")

    def send_command(self):
        print("Starting TCS polling...")
        while True:
            sr2hexcommand = bytearray.fromhex("01 30 32 02 53 52 32 03 7f 04")
            try:
                while True:
                    print(f"Sending TCS command: {sr2hexcommand.hex()}")
                    self.ser.write(sr2hexcommand)
                    self.readData()
                    time.sleep(0.2)
            except serial.SerialException as e:
                print("Something bad happened: " + str(e))
                self.ser.close()

    def readData(self):
        data = self.ser.readline()
        if data:
            print(f"Received: {data}")
            logging.info(f"Received data: {data}")
        else:
            print("No data received")

if __name__ == "__main__":
    app = FireWheel()
    try:
        app.send_command()
    except KeyboardInterrupt:
        print("\nStopping application...")
        app.close_serial() 