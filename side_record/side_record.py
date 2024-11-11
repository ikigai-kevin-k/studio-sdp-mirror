"""
Pseudo Code with WebSocket implementation
"""
import asyncio
import websockets
# import signal

class WebSocketServer:
    def __init__(self):
        self.port = 8765
        self.recorder = None
        self.uploader = None
        
    async def handler(self, websocket):
        async for message in websocket:
            print(f"收到消息: {message}")
            if message == "GAME_START":
                if self.recorder:
                    await self.recorder.start_recording()
            elif message == "GAME_END":
                if self.recorder:
                    video_data = await self.recorder.stop_recording()
                    if self.uploader:
                        await self.uploader.start_upload(video_data)

class Recorder:
    def __init__(self):
        self.is_recording = False
        self.current_video = []
        self.cap = None

    async def start_recording(self):
        self.is_recording = True
        self.current_video = []
        
        async def video_record():
            import cv2
            from datetime import datetime
            
            self.cap = cv2.VideoCapture(0)  # 0 表示默認攝像頭
            if not self.cap.isOpened():
                print("無法開啟攝像頭")
                return
                
            # 使用 mp4v 編碼，輸出 MP4 格式
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f'recording_{timestamp}.mp4'  # 改為 .mp4 副檔名
            fps = 20.0
            frame_size = (int(self.cap.get(3)), int(self.cap.get(4)))
            out = cv2.VideoWriter(output_file, fourcc, fps, frame_size)
            
            while self.is_recording:
                ret, frame = self.cap.read()
                if ret:
                    out.write(frame)
                    await asyncio.sleep(0.01)  # 避免阻塞事件循環
                
            # 清理資源
            out.release()
            self.cap.release()
            self.current_video.append(output_file)
        
        # 在背景啟動錄製
        asyncio.create_task(video_record())
        print("開始錄製")

    async def stop_recording(self):
        self.is_recording = False
        if self.cap:
            self.cap.release()
        print("停止錄製")
        return self.current_video

class Uploader:
    async def start_upload(self, video_data):
        # 上傳邏輯...
        print("start upload")

class SDPClient:
    """
    SDP作為client發送遊戲開始/結束事件
    將原本的SDP改為WebSocket client
    目前先寫一個假的SDP
    """
    def __init__(self):
        self.ws = None

    async def connect(self):
        self.ws = await websockets.connect('ws://localhost:8765')

    async def send_game_event(self, event):
        if self.ws:
            print(f"SDP發送事件: {event}")
            await self.ws.send(event)
            
    async def close(self):
        if self.ws:
            await self.ws.close()

async def main():
    # 初始化服務器端
    server = WebSocketServer()
    server.recorder = Recorder()
    server.uploader = Uploader()
    
    # 啟動服務器
    server_task = await websockets.serve(server.handler, "localhost", 8765)
    
    try:
        # 初始化SDP客戶端
        sdp = SDPClient()
        await sdp.connect()
        
        # 模擬遊戲流程
        await sdp.send_game_event("GAME_START")
        await asyncio.sleep(2)  # 模擬遊戲進行2秒
        await sdp.send_game_event("GAME_END")
        await asyncio.sleep(1)  # 等待上傳完成
        
        # 關閉連接
        await sdp.close()
        
    except Exception as e:
        print(f"發生錯誤: {e}")
    finally:
        # 修正關閉服務器的方式
        server_task.close()
        await server_task.wait_closed()

if __name__ == "__main__":
    # 運行主程序
    asyncio.run(main())