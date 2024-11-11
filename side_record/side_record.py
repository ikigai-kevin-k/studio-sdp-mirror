"""
expected output is like the following,
加入timestamp是為了確認sdp/recorder/uploader之間完全異步:
```
[16:26:49.341] 開始第 1 輪遊戲
[16:26:49.342] SDP發送事件: GAME_START
[16:26:49.342] WebSocket收到消息: GAME_START
[16:26:49.342] 開始處理錄製請求
[16:26:49.342] Recorder開始錄製
[16:26:50.343] 開始錄製
[16:26:51.801] SDP發送事件: GAME_END
[16:26:51.802] WebSocket收到消息: GAME_END
[16:26:51.802] 開始處理停止錄製請求
[16:26:51.802] Recorder停止錄製
[16:26:52.813] 完成第 1 輪遊戲
[16:26:52.813] 開始第 2 輪遊戲
[16:26:52.813] SDP發送事件: GAME_START
[16:26:52.908] 停止錄製
[16:26:52.908] Uploader開始上傳
[16:26:52.908] WebSocket收到消息: GAME_START
[16:26:52.910] 開始處理錄製請求
[16:26:52.910] Recorder開始錄製
[16:26:53.911] 開始錄製
[16:26:54.815] SDP發送事件: GAME_END
[16:26:54.815] WebSocket收到消息: GAME_END
[16:26:54.815] 開始處理停止錄製請求
[16:26:54.815] Recorder停止錄製
[16:26:54.910] Uploader完成上傳
[16:26:55.815] 完成第 2 輪遊戲
[16:26:55.815] 開始第 3 輪遊戲
[16:26:55.815] SDP發送事件: GAME_START
[16:26:55.917] 停止錄製
[16:26:55.917] Uploader開始上傳
[16:26:55.917] WebSocket收到消息: GAME_START
[16:26:55.920] 開始處理錄製請求
[16:26:55.920] Recorder開始錄製
[16:26:56.921] 開始錄製
[16:26:57.834] SDP發送事件: GAME_END
[16:26:57.834] WebSocket收到消息: GAME_END
[16:26:57.834] 開始處理停止錄製請求
[16:26:57.834] Recorder停止錄製
[16:26:57.936] Uploader完成上傳
[16:26:58.835] 完成第 3 輪遊戲
[16:26:58.835] 開始第 4 輪遊戲
[16:26:58.835] SDP發送事件: GAME_START
[16:26:58.889] 停止錄製
[16:26:58.889] Uploader開始上傳
[16:26:58.889] WebSocket收到消息: GAME_START
[16:26:58.890] 開始處理錄製請求
[16:26:58.890] Recorder開始錄製
[16:26:59.890] 開始錄製
[16:27:01.221] SDP發送事件: GAME_END
[16:27:01.221] Uploader完成上傳
[16:27:01.222] WebSocket收到消息: GAME_END
[16:27:01.222] 開始處理停止錄製請求
[16:27:01.222] Recorder停止錄製
[16:27:02.227] 完成第 4 輪遊戲
[16:27:02.228] 開始第 5 輪遊戲
[16:27:02.228] SDP發送事件: GAME_START
[16:27:02.324] 停止錄製
[16:27:02.324] Uploader開始上傳
[16:27:02.324] WebSocket收到消息: GAME_START
[16:27:02.326] 開始處理錄製請求
[16:27:02.326] Recorder開始錄製
[16:27:03.327] 開始錄製
[16:27:04.239] SDP發送事件: GAME_END
[16:27:04.239] WebSocket收到消息: GAME_END
[16:27:04.239] 開始處理停止錄製請求
[16:27:04.239] Recorder停止錄製
[16:27:04.342] Uploader完成上傳
[16:27:05.244] 完成第 5 輪遊戲
[16:27:05.348] 停止錄製
[16:27:05.348] Uploader開始上傳
```
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
            print(f"[{self._get_timestamp()}] WebSocket收到消息: {message}")
            if message == "GAME_START":
                if self.recorder:
                    asyncio.create_task(self._handle_recording_start())
            elif message == "GAME_END":
                if self.recorder:
                    asyncio.create_task(self._handle_recording_end())
    
    async def _handle_recording_start(self):
        print(f"[{self._get_timestamp()}] 開始處理錄製請求")
        await self.recorder.start_recording()
        
    async def _handle_recording_end(self):
        print(f"[{self._get_timestamp()}] 開始處理停止錄製請求")
        video_data = await self.recorder.stop_recording()
        if self.uploader:
            asyncio.create_task(self.uploader.start_upload(video_data))
            
    def _get_timestamp(self):
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S.%f")[:-3]

class Recorder:
    def __init__(self):
        self.is_recording = False
        self.current_video = []
        self.cap = None

    async def start_recording(self):
        print(f"[{self._get_timestamp()}] Recorder開始錄製")
        await asyncio.sleep(1)  # 模擬初始化延遲
        self.is_recording = True
        self.current_video = []
        
        async def video_record():
            import cv2
            from datetime import datetime
            
            self.cap = cv2.VideoCapture(0)  # 0 表示默認攝像頭
            if not self.cap.isOpened():
                print(f"[{self._get_timestamp()}] 無法開啟攝像頭")
                return
                
            # 使用 mp4v 編碼，輸出 MP4 格式
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f'recording_{timestamp}.mp4'
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
            """
            TODO:
            - 將影片上傳到CDN
            -  recorder通知uploader把影片上傳到一個假的CDN server
                - 目前可以存到本地的另一個資料夾路徑
            """
        
        # 在背景啟動錄製
        asyncio.create_task(video_record())
        print(f"[{self._get_timestamp()}] 開始錄製")

    async def stop_recording(self):
        print(f"[{self._get_timestamp()}] Recorder停止錄製")
        await asyncio.sleep(1)  # 模擬結束延遲
        self.is_recording = False
        if self.cap:
            self.cap.release()
        print(f"[{self._get_timestamp()}] 停止錄製")
        return self.current_video

    def _get_timestamp(self):
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S.%f")[:-3]

class Uploader:
    async def start_upload(self, video_data):
        print(f"[{self._get_timestamp()}] Uploader開始上傳")
        await asyncio.sleep(2)  # 模擬上傳延遲
        print(f"[{self._get_timestamp()}] Uploader完成上傳")
        
    def _get_timestamp(self):
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S.%f")[:-3]

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
            print(f"[{self._get_timestamp()}] SDP發送事件: {event}")
            await self.ws.send(event)
            
    async def close(self):
        if self.ws:
            await self.ws.close()

    def _get_timestamp(self):
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S.%f")[:-3]

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
            print(f"[{server._get_timestamp()}] 開始第 {game_round + 1} 輪遊戲")
            await sdp.send_game_event("GAME_START")
            await asyncio.sleep(2)
            await sdp.send_game_event("GAME_END")
            await asyncio.sleep(1)
            print(f"[{server._get_timestamp()}] 完成第 {game_round + 1} 輪遊戲")
            
            game_round += 1

        # 關閉連接
        await sdp.close()
            
    except Exception as e:
        print(f"[{server._get_timestamp()}] 發生錯誤: {e}")
    finally:
        # 修正關閉服務器的方式
        server_task.close()
        await server_task.wait_closed()

if __name__ == "__main__":
    # 運行主程序
    asyncio.run(main())