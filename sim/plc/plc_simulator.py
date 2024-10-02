import socket
import random
import time

def plc_simulator():
    host = '127.0.0.1'
    port = 12345

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(1)

    print(f"PLC模擬器正在監聽 {host}:{port}")

    while True:
        client_socket, address = server_socket.accept()
        print(f"來自 {address} 的連接")

        try:
            while True:
                # 模擬PLC數據
                temperature = random.uniform(20, 30)
                pressure = random.uniform(1, 2)
                data = f"溫度:{temperature:.2f},壓力:{pressure:.2f}"
                
                client_socket.send(data.encode())
                time.sleep(1)  # 每秒發送一次數據
        except:
            print("客戶端斷開連接")
            client_socket.close()

if __name__ == "__main__":
    plc_simulator()