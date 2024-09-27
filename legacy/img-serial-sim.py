import pty
import os
import serial
import time
import cv2
import numpy as np

def create_virtual_serial_port():
    master, slave = pty.openpty()
    port_name = os.ttyname(slave)
    print(f"Created virtual serial port: {port_name}")
    return master, slave, port_name

def generate_synthetic_video_frame(frame_number):
    # Create a 320x240 black image (smaller for less data)
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    
    # Add a moving white rectangle
    x = frame_number % 280  # Move across 280 pixels (320 - 40)
    cv2.rectangle(frame, (x, 100), (x + 40, 140), (255, 255, 255), -1)
    
    # Add frame number text
    cv2.putText(frame, f"Frame: {frame_number}", (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    return frame

def send_synthetic_video_data(serial_port):
    frame_number = 0
    while True:
        frame = generate_synthetic_video_frame(frame_number)
        
        # Encode frame to JPEG with lower quality
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
        data = buffer.tobytes()
        
        # Send frame size followed by frame data
        size = len(data)
        try:
            serial_port.write(size.to_bytes(4, byteorder='big'))
            serial_port.write(data)
            print(f"Sent frame {frame_number}, size: {size} bytes")
            
            # save every 30 frames to file
            if frame_number % 30 == 0:  # 每30帧保存一次
                cv2.imwrite(f'sent_frame_{frame_number}.jpg', frame)
        except serial.SerialException as e:
            print(f"Error sending data: {e}")
            break
        
        frame_number += 1
        time.sleep(0.1)  # Reduce to 10 FPS for testing

def receive_video_data(serial_port):
    frame_count = 0
    while True:
        try:
            # Read frame size
            size_bytes = serial_port.read(4)
            if not size_bytes:
                print("No data received, exiting.")
                break
            size = int.from_bytes(size_bytes, byteorder='big')
            print(f"Receiving frame {frame_count}, size: {size} bytes")
            
            # Read frame data
            data = serial_port.read(size)
            if len(data) != size:
                print(f"Incomplete frame received. Expected {size} bytes, got {len(data)} bytes.")
                continue
            
            if frame is not None and frame_count % 30 == 0:  # save every 30 frames to file
                cv2.imwrite(f'received_frame_{frame_count}.jpg', frame)

            # Decode JPEG data to image
            frame = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
            if frame is None:
                print("Failed to decode image.")
                continue
            
            # Display the frame
            cv2.imshow('Received Video', frame)
            frame_count += 1
            
            # Break the loop if 'q' is pressed
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        except serial.SerialException as e:
            print(f"Error receiving data: {e}")
            break
        except Exception as e:
            print(f"Unexpected error in receive_video_data: {e}")
    
    print(f"Total frames received: {frame_count}")

def main():
    master, slave, port_name = create_virtual_serial_port()
    
    try:
        # Set up the sender (synthetic data generator)
        sender_serial = serial.Serial(port_name, 115200)  # Use a standard baud rate
        print(f"Sender opened on {port_name} at {sender_serial.baudrate} bps")
        
        # Set up the receiver
        receiver_serial = serial.Serial(port_name, 115200)
        print(f"Receiver opened on {port_name} at {receiver_serial.baudrate} bps")
        
        # Start sending synthetic video data in a separate thread
        import threading
        sender_thread = threading.Thread(target=send_synthetic_video_data, args=(sender_serial,))
        sender_thread.daemon = True
        sender_thread.start()
        
        # Receive and display video data
        receive_video_data(receiver_serial)
    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        cv2.destroyAllWindows()
        if 'sender_serial' in locals():
            sender_serial.close()
        if 'receiver_serial' in locals():
            receiver_serial.close()
        os.close(master)
        os.close(slave)

    # Check if any frames were displayed
    if cv2.getWindowProperty('Received Video', cv2.WND_PROP_VISIBLE) < 1:
        print("Warning: No video window was displayed.")

if __name__ == "__main__":
    main()