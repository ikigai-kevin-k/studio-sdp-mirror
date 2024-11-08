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
###  3. <a name='Plan'></a>Plan

####  3.1. <a name='RewriteLOSrequest'></a>Rewrite LOS request

####  3.2. <a name='SDP'></a>SDP 側錄影片並上傳

目前設定是開3條thread: Upload, Record, Game(State Machine + VideoPlay)

Design:
```bash
     PlayStart    PlayEnd
Ｇame|------------|------------|------------|
     |            |            |
     |            |            |
     v            v            v
      RecordStart  RecordEnd
Record|------------|-------------|-----------|
                   ｜             |           |
                   ｜             |           |
                   v              v           v
                   UpStart        UpEnd
Upload             |-------|      |------|    |------|
```

```python
"""
Pseudo Code
"""
from threading import Thread, Event
import queue

class ThreadManager:
    def __init__(self):
        # Event for thread synchronization
        self.play_start_event = Event()
        self.play_end_event = Event()
        self.record_start_event = Event()
        self.record_end_event = Event()
        self.upload_start_event = Event()
        
        # Queue for storing video data
        self.video_queue = queue.Queue()
        
        # Initialize three threads
        self.game_thread = Thread(target=self.game_loop)
        self.record_thread = Thread(target=self.record_loop)
        self.upload_thread = Thread(target=self.upload_loop)

    def game_loop(self):
        while True:
            # Game Start
            self.play_start_event.set()
            self.record_start_event.set()
            
            # Game Running...
            
            # Game End
            self.play_end_event.set()
            self.record_end_event.set()

    def record_loop(self):
        while True:
            # Wait for game start signal
            self.record_start_event.wait()
            
            # Start recording
            current_video = []
            while not self.record_end_event.is_set():
                # Record video frame
                # current_video.append(frame)
                pass
                
            # Record End, put video into queue
            self.video_queue.put(current_video)
            self.upload_start_event.set()
            
            # Reset event
            self.record_start_event.clear()
            self.record_end_event.clear()

    def upload_loop(self):
        while True:
            # Wait for upload start signal
            self.upload_start_event.wait()
            
            # Get video from queue and upload
            video = self.video_queue.get()
            # Execute upload operation
            
            # Reset event
            self.upload_start_event.clear()
```
