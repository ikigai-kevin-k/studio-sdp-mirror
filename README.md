<!-- vscode-markdown-toc -->
-  [New features](#Newfeatures)
-  [Checklist After Receiving the Physical Machine](#ChecklistAfterReceivingthePhysicalMachine)
	-  [Setup and Configuration Phase](#SetupandConfigurationPhase)
	-  [Gameplay Phase](#GameplayPhase)
-  [Question List](#QuestionList)
-  [Plan](#Plan)
	-  [Rewrite LOS request](#RewriteLOSrequest)
	-  [SDP 側錄影片並上傳](#SDP)

<!-- vscode-markdown-toc-config
	numbering=true
	autoSave=true
	/vscode-markdown-toc-config -->
<!-- /vscode-markdown-toc -->
##  1. <a name='Usage'></a>Usage

Open four terminals, run the following commands in the following order, respectively:
```bash
cd sim/core/
python3 LOS_server_sim.py
python3 SDP_client_sim.py
python3 manager_sim.py
python3 roulette_sim.py
```
The SDP CLI interface:
![SDP CLI](img/sdp-interface-cli.png)
The terminal log with color:
![terminal log with color](img/correct_log.png)

##  1. <a name='Newfeatures'></a>New features
1. Added `check_receive_force_restart_game` to the roulette_main_thread.
2. Split the force restart command from the state_discriminator to a separate function,
    called `check_receive_force_restart_game`.
Log example of force restart:
![alt text](sim/img/force-restart.png)

3.The game round timer:
![alt text](sim/img/game-round-timer.png)

##  2. <a name='ChecklistAfterReceivingthePhysicalMachine'></a>Checklist After Receiving the Physical Machine

###  2.1. <a name='SetupandConfigurationPhase'></a>Setup and Configuration Phase

- Verify successful configuration of *o 1157, which corresponds to arcade mode parameters
- Confirm ability to adjust GPH parameters
- Check for early firing related commands, verify if early firing is possible by reducing *T t (set wheel deceleration distance to firing position)
- Verify functionality of *F self test command - should be executable during startup and after on-site troubleshooting
- Confirm proper operation of *T S (get wheel speed) and *T N (get rotor direction) commands according to Mihail's designed game flow
- Check for any instances of commands not receiving responses (no "ok" response)

###  2.2. <a name='GameplayPhase'></a>Gameplay Phase

- Check if the issue exists where game number remains unchanged after a round (as seen in previous logs)
- Verify state machine implementation matches roulette_sim
- In non-arcade mode, verify proper functionality of *u 1 (manual restart) command
- Check for instances of missing log entries
- Verify there are no cases of complete log reception failure


###  2.3. <a name='QuestionList'></a>Question List

- Check to Temo for considering the live error scenario handling by the flow manager

- SDP-Roulette connection timeout handling

###  3. <a name='Plan'></a>Plan

####  3.1. <a name='RewriteLOSrequest'></a>Rewrite LOS request

####  3.2. <a name='SDP'></a>SDP 側錄影片並上傳

目前設定是開3條thread: Upload, Recorder, SDP

Temporary use desktop camera as video source.

Design:
```bash
     PlayStart    PlayEnd
SDP   |-------------|------------|------------|
      |             |                
      |             |                
      v             v                
      RecordStart  RecordEnd
Recorder|------------|-------------|-----------|
                     ｜             |
                     ｜             |           
                     v              v           
                   UpStart   UpEnd  UpStrt UpldEnd
Uploader             |-------|      |------|    |------|
```

Event通訊機制為WebSocket：
- SDP作為client發送遊戲開始/結束事件
- Server端包含Recorder和Uploader的邏輯

通訊流程：
- 當Server收到"GAME_START"時，直接調用Recorder開始錄製
- 當收到"GAME_END"時，停止錄製並自動觸發上傳流程

使用異步方式處理所有通訊：
- 使用async/await確保非阻塞操作
- Recorder和Uploader都改為異步類
(不使用Thread設計，改為純異步操作，可以更好地處理並發情況)

#### Desktop Camera Recording

To be moved to the individual repository.

![Desktop Camera Recording](output.gif)

## Docker Image Build
requirements.txt
```
requirements:
blinker==1.8.2
certifi==2024.8.30
charset-normalizer==3.4.0
click==8.1.7
Flask==3.0.3
idna==3.10
itsdangerous==2.2.0
Jinja2==3.1.4
MarkupSafe==3.0.2
numpy==2.1.3
opencv-python==4.10.0.84
pyserial==3.5
requests==2.32.3
urllib3==2.2.3
websockets==14.0
Werkzeug==3.0.6
```

Current issue: 

In the docker container, the camera source cannot be found.
```
kevin.k@MacBook-Pro ~/s/docker_test_env (dev/kevin/SI-11/real-log-non-arcade) [127]> docker run -p 5000:5000 --privileged studio-sdp-roulette
[ WARN:0@0.008] global cap_v4l.cpp:999 open VIDEOIO(V4L2:/dev/video0): can't open camera by index
[ERROR:0@0.008] global obsensor_uvc_stream_channel.cpp:158 getStreamChannelGroup Camera index out of range
```

## LOS-SDP interface discussion
[draft](https://ikigaians.atlassian.net/wiki/spaces/Crystal/pages/221315107/LOS+-+SDP+interface+draft)
![alt text](draft-note.png)


```
curl -X GET -H "Content-Type: application/json" \
  -H "Bearer: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c" \
  https://los.url/v1/service/sdp/table/ABO-001

{
  "gameCode": "ABO-001",
  "roundId": "ABO-001-20241010-123000000",
  "state": "opened"
}
```
的實作方式的pseudo code
```python
import requests
from dataclasses import dataclass
from typing import Optional

@dataclass
class GameResponse:
    gameCode: str
    roundId: str
    state: str

class SDP_API_Client:
    def __init__(self, base_url: str, bearer_token: str):
        self.base_url = base_url
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {bearer_token}"
        }
    
    def get_game_status(self, game_code: str) -> Optional[GameResponse]:
        try:
            url = f"{self.base_url}/v1/service/sdp/table/{game_code}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()  # 如果狀態碼不是 2xx 會拋出異常
            
            data = response.json()
            return GameResponse(**data)
            
        except requests.exceptions.RequestException as e:
            print(f"請求失敗: {e}")
            return None

# 使用示例
def main():
    # 替換成實際的 URL 和 token
    base_url = "https://los.url"
    bearer_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    
    client = SDP_API_Client(base_url, bearer_token)
    result = client.get_game_status("ABO-001")
    
    if result:
        print(f"遊戲代碼: {result.gameCode}")
        print(f"局號: {result.roundId}")
        print(f"狀態: {result.state}")

if __name__ == "__main__":
    main()
```
