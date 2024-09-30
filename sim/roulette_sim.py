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

    game_states = list(range(1, 8))
    game_numbers = list(range(1,256))
    last_winning_numbers = list(range(0,37))
    warning_flags = list(range(0,16))
    rotor_speeds = list(range(10,541))
    rotor_directions = [0,1]

    x = random.choice(game_states) 
    y = random.choice(game_numbers) 
    z = random.choice(last_winning_numbers)
    a = hex(random.choice(warning_flags))
    b = random.choice(rotor_speeds)
    c = random.choice(rotor_directions)

    return f"*X:{x:01d}:{y:03d}:{z:02d}:{a}:{b:03d}:{c:01d}\r\n"

def virtual_serial_thread(master):
    while True:
        try:
            # Send data
            data = generate_protocol_data().encode()
            os.write(master, data)
            print(f"Roulette simulator sent: {data.decode().strip()}")

            # Read data (if any)
            read_data = os.read(master, 1024)
            if read_data:
                print(f"Roulette simulator received: {read_data.decode().strip()}")
                # Here you can process the received data and update the simulator's state

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
