import serial
import time
import os
import pty
import threading
import random

def create_virtual_serial_port():
    master, slave = pty.openpty()
    s_name = os.ttyname(slave)
    return master, s_name

def generate_protocol_data():
    x = random.randint(1, 3)  # 假设 x 可以是 1, 2, 或 3
    y = random.randint(0, 999)
    z = random.randint(24, 28)
    a = random.randint(0, 1)
    b = random.randint(0, 999)
    c = random.randint(0, 1)
    return f"*X:{x:01d}:{y:03d}:{z:02d}:{a:01d}:{b:03d}:{c:01d}\r\n"

def virtual_serial_thread(master):
    while True:
        try:
            data = generate_protocol_data().encode()
            os.write(master, data)
            print(f"Roulette simulator sent: {data.decode().strip()}")
            time.sleep(1)
        except OSError:
            break

def main():
    master, slave_name = create_virtual_serial_port()
    print(f"Created virtual serial port: {slave_name}")

    thread = threading.Thread(target=virtual_serial_thread, args=(master,))
    thread.daemon = True
    thread.start()

    print(f"Roulette simulator is running. Virtual port: {slave_name}")
    print("Press Ctrl+C to stop the simulator.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping roulette simulator...")

if __name__ == "__main__":
    main()
