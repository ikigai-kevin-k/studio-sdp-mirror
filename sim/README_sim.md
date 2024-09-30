# Usage
```bash
python LOS_server_sim.py
python roulette_sim.py # record the port number
python SDP_client_sim.py /dev/ttyps{port number}
python manager_sim.py
```

## Expected output:

The simulation execution order is as follows:
1. LOS_server_sim.py
2. roulette_sim.py
3. SDP_client_sim.py

### LOS_server_sim.py
```
(.venv) kevin.k@MacBook-Pro ~/s/sim (sdp)> python LOS_server_sim.py 
 * Serving Flask app 'LOS_server_sim'
 * Debug mode: on
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://10.13.81.73:5000
Press CTRL+C to quit
127.0.0.1 - - [27/Sep/2024 16:16:14] "GET /get_game_parameters HTTP/1.1" 200 -
127.0.0.1 - - [27/Sep/2024 16:16:19] "GET /get_game_parameters HTTP/1.1" 200 -
127.0.0.1 - - [27/Sep/2024 16:16:24] "GET /get_game_parameters HTTP/1.1" 200 -
```
### roulette_sim.py
```
(.venv) kevin.k@MacBook-Pro ~/s/sim (sdp)> python roulette_sim.py 
Created virtual serial port: /dev/ttys038
Roulette simulator is running. Virtual port: /dev/ttys038
Press Ctrl+C to stop the simulator.
Roulette simulator sent: *X:2:552:24:0:439:1
Roulette simulator sent: *X:3:361:25:0:281:0
Roulette simulator sent: *X:1:438:24:1:009:1
Roulette simulator sent: *X:3:138:26:0:489:1
Roulette simulator sent: *X:2:960:27:1:234:1
Roulette simulator sent: *X:1:623:28:1:561:1
Roulette simulator sent: *X:2:052:26:0:031:1
Roulette simulator sent: *X:1:773:26:1:433:1
Game status: running
Game mode: standard
Last updated: 1727428680.836295
```

### SDP_client_sim.py
```
(.venv) kevin.k@MacBook-Pro ~/s/sim (sdp)> python SDP_client_sim.py /dev/ttys038 
/Users/kevin.k/studio-sdp-roulette/.venv/lib/python3.9/site-packages/urllib3/__init__.py:35: NotOpenSSLWarning: urllib3 v2 only supports OpenSSL 1.1.1+, currently the 'ssl' module is compiled with 'LibreSSL 2.8.3'. See: https://github.com/urllib3/urllib3/issues/3020
  warnings.warn(
Game status: running
Game mode: standard
Last updated: 1727424972.313292
---
Received from roulette: *X:2:149:25:0:753:0
Received from roulette: *X:3:547:28:1:687:0
Received from roulette: *X:3:479:26:0:199:0
Received from roulette: *X:2:536:24:1:287:0
Received from roulette: *X:1:886:27:1:882:0
```

### manager_sim.py

Currently, the simulated behavior is send set_game_parameter request to the LOS server simulator every 2 seconds. (enable/disable manual end game)

```
Manager simulator started. Press Ctrl+C to stop.
Successfully set manual_end_game to True
Successfully set manual_end_game to False
Successfully set manual_end_game to True
Successfully set manual_end_game to False
```


Then the LOS server will receive like:
```bash
127.0.0.1 - - [30/Sep/2024 09:34:09] "GET /get_game_parameters HTTP/1.1" 200 -
127.0.0.1 - - [30/Sep/2024 09:34:14] "GET /get_game_parameters HTTP/1.1" 200 -
127.0.0.1 - - [30/Sep/2024 09:34:19] "GET /get_game_parameters HTTP/1.1" 200 -
127.0.0.1 - - [30/Sep/2024 09:34:19] "POST /set_game_parameter HTTP/1.1" 200 -
127.0.0.1 - - [30/Sep/2024 09:34:21] "POST /set_game_parameter HTTP/1.1" 200 -
127.0.0.1 - - [30/Sep/2024 09:34:23] "POST /set_game_parameter HTTP/1.1" 200 -
127.0.0.1 - - [30/Sep/2024 09:34:24] "GET /get_game_parameters HTTP/1.1" 200 -
127.0.0.1 - - [30/Sep/2024 09:34:25] "POST /set_game_parameter HTTP/1.1" 200 -
```
The SDP client will receive like:
```bash
---
Received from roulette: *X:3:961:25:0:516:1
Game status: running
Game mode: standard
Last updated: 1727660462.052375
Manual end game: False
---
Game status: running
Game mode: standard
Last updated: 1727660467.0561721
Manual end game: True
Sent to roulette: *X:1:000:24:0:000:1
---
Received from roulette: *X:3:432:25:1:878:1
Game status: running
Game mode: standard
Last updated: 1727660472.0612428
Manual end game: True
---
Game status: running
Game mode: standard
Last updated: 1727660477.0663218
Manual end game: False
Sent to roulette: *X:1:000:24:0:000:0
---
Received from roulette: *X:2:194:28:0:232:0
Game status: running
Game mode: standard
Last updated: 1727660482.071397
Manual end game: False
---
Game status: running
Game mode: standard
Last updated: 1727660487.07647
Manual end game: True
Sent to roulette: *X:1:000:24:0:000:1
---
Received from roulette: *X:2:660:27:0:024:1
Game status: running
Game mode: standard
Last updated: 1727660492.078322
Manual end game: True
---
Game status: running
Game mode: standard
Last updated: 1727660497.08193
Manual end game: False
Sent to roulette: *X:1:000:24:0:000:0
---
Received from roulette: *X:3:529:26:1:769:1
Game status: running
Game mode: standard
Last updated: 1727660502.086847
Manual end game: False
---
Game status: running
Game mode: standard
Last updated: 1727660507.088604
Manual end game: True
Sent to roulette: *X:1:000:24:0:000:1
---
Received from roulette: *X:3:991:27:1:975:1
Game status: running
Game mode: standard
Last updated: 1727660512.093677
Manual end game: True
---
```
