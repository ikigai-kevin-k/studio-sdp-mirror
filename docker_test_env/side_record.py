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
        """
        目前先儲存到本地
        確保recorder跟uploader這一路是通的
        """
        print("start upload")

class SDPClient:
    """
    SDP作為client發送遊戲開始/結束事件
    根據輪盤模擬器的狀態機:
    - GAME_START 對應 start_game 狀態
    - GAME_END 對應 winning_number 狀態

    目前驗證條件:
    - SDP讀完所有log之後應該會有完整的六輪遊戲的影片儲存到本地
    
    SDPClient與TestRouletteSimulatorNonArcade game flow的獨立性:
    - 如果要讓side recorder module跟遊戲模組之間的獨立性越高越好,可以在main loop中在初始化SDPClient之後,
      再初始化TestRouletteSimulatorNonArcade,然後開始運行game loop,
      不斷去polling TestRouletteSimulatorNonArcade的self.current_game_state,
      然後不斷更新SDPClient的self.current_state.
    """
    def __init__(self):
        self.ws = None
        self.current_state = None

    async def connect(self):
        self.ws = await websockets.connect('ws://localhost:8765')

    async def send_game_event(self, event):
        if self.ws:
            # 記錄當前狀態
            self.current_state = event
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
    
    game_round_numbrer = 5 # for test
    game_round = 0 # for test
    
    try:
        # 初始化SDP客戶端
        sdp = SDPClient()
        await sdp.connect()
            
        while game_round < game_round_numbrer:

            # 模擬遊戲流程 - 對應輪盤狀態機的狀態轉換
            await sdp.send_game_event("GAME_START")  # 對應 start_game 狀態
            await asyncio.sleep(2)  # 等待一個完整的遊戲回合 (約42秒)
            """
            實際上這邊需要一直去監聽SDP TestRouletteSimulatorNonArcade的狀態self.current_game_state
            """
            await sdp.send_game_event("GAME_END")    # 對應 winning_number 狀態
            await asyncio.sleep(1)  # 等待上傳完成
            
            game_round += 1

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