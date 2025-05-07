import serial
import threading
import time

ser = serial.Serial(
    port='/dev/ttyUSB0',
    baudrate=9600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1
)

def read_from_serial():
    while True:
        if ser.in_waiting > 0:
            data = ser.readline().decode('utf-8').strip()
            print("Receive >>>", data)
        time.sleep(0.1)

def write_to_serial():
    while True:
        try:
            text = input("Send <<< ")
            ser.write((text + '\r\n').encode())
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