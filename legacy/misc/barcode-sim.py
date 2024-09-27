import cv2
from pyzbar import pyzbar
from PIL import Image, ImageDraw
import numpy as np

def read_barcodes(frame):
    barcodes = pyzbar.decode(frame)
    for barcode in barcodes:
        x, y , w, h = barcode.rect
        barcode_info = barcode.data.decode('utf-8')
        cv2.rectangle(frame, (x, y),(x+w, y+h), (0, 255, 0), 2)
        
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(frame, barcode_info, (x + 6, y - 6), font, 0.5, (255, 255, 255), 1)
        
        print("Barcode:", barcode_info)
    return frame

def generate_barcode(data):
    from barcode import Code128
    from barcode.writer import ImageWriter
    
    # 生成条形码
    my_code = Code128(data, writer=ImageWriter())
    my_code.save("synthetic_barcode")
    
    # 打开生成的条形码图像
    barcode_img = Image.open("synthetic_barcode.png")
    return cv2.cvtColor(np.array(barcode_img), cv2.COLOR_RGB2BGR)

def main():
    camera = cv2.VideoCapture(0)
    ret, frame = camera.read()
    
    # 生成合成条形码
    synthetic_barcode = generate_barcode("TEST123456")
    
    while ret:
        ret, frame = camera.read()
        
        # 将合成条形码添加到帧中
        h, w, _ = synthetic_barcode.shape
        frame[10:10+h, 10:10+w] = synthetic_barcode
        
        frame = read_barcodes(frame)
        cv2.imshow('Barcode/QR code reader', frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break
    
    camera.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()