import socket

def plc_client():
    host = '127.0.0.1'
    port = 12345

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))

    print(f"已連接到PLC模擬器 {host}:{port}")

    try:
        while True:
            data = client_socket.recv(1024).decode()
            if not data:
                break
            print(f"接收到的PLC數據: {data}")
    except KeyboardInterrupt:
        print("客戶端正在關閉...")
    finally:
        client_socket.close()

if __name__ == "__main__":
    plc_client()