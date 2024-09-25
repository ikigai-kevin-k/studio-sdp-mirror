import serial
import time
import sys
import glob
import os
import pty
import threading
import random


def list_serial_ports():
    """ List all available serial ports """
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*') + glob.glob('/dev/cu.*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result

def create_virtual_serial_port():
    """Create a virtual serial port pair"""
    master, slave = pty.openpty()
    s_name = os.ttyname(slave)
    return master, s_name

def generate_protocol_data():
    """Generate data following the specified protocol format"""
    x = 1
    y = random.randint(0, 999)
    z = random.randint(24, 28)
    a = random.randint(0, 1)
    b = random.randint(0, 999)
    c = random.randint(0, 1)
    return f"*X:{x:01d}:{y:03d}:{z:02d}:{a:01d}:{b:03d}:{c:01d}\r\n"

def virtual_serial_thread(master):
    """Handle read and write operations for the virtual serial port"""
    while True:
        try:
            # Generate and send data every second
            data = generate_protocol_data().encode()
            os.write(master, data)
            print(f"Virtual serial port sent: {data.decode().strip()}")
            time.sleep(1)
        except OSError:
            break

def main():

    """
    The aim of this script is to create a virtual serial port and send data
    to simulate the behavior from/to the Roulette machine and the LOC computer.
    Currently the both two ends of serial ports are created on the same IOS notebook,
    hence it is a loopback.
    The data is generated following the specified game protocol format:
    *X:{x:01d}:{y:03d}:{z:02d}:{a:01d}:{b:03d}:{c:01d}
    The specific ranges of each fields in the game protocol is going to be checked
    """ 

    # Create virtual serial port
    master, slave_name = create_virtual_serial_port()
    print(f"Created virtual serial port: {slave_name}")

    # Start virtual serial port thread
    thread = threading.Thread(target=virtual_serial_thread, args=(master,))
    thread.daemon = True
    thread.start()

    baud_rate = 9600
    timeout = 1  # 1 second timeout

    try:
        # Open the virtual serial port
        with serial.Serial(slave_name, baud_rate, timeout=timeout,
                           parity=serial.PARITY_NONE,
                           stopbits=serial.STOPBITS_ONE,
                           bytesize=serial.EIGHTBITS,
                           xonxoff=False,
                           rtscts=False) as ser:
            print(f"Connected to virtual serial port {slave_name}, baud rate: {baud_rate}")

            while True:
                # Read data
                if ser.in_waiting > 0:
                    data = ser.readline()
                    print(f"Received: {data.decode().strip()}")

                # Check if user wants to quit
                if input("Press 'q' to quit, or any other key to continue: ").lower() == 'q':
                    break

    except serial.SerialException as e:
        print(f"Unable to open virtual serial port {slave_name}: {e}")

if __name__ == "__main__":
    main()