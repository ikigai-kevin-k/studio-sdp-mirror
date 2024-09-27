# Usage
```bash
python LOS_server_sim.py
python roulette_sim.py # record the port number
python SDP_client_sim.py /dev/ttyps{port number}
```

Expected output:
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


kevin.k@MacBook-Pro ~/s/sim (sdp)> python SDP_client_sim.py /dev/ttys038 
/Users/kevin.k/studio-sdp-roulette/.venv/lib/python3.9/site-packages/urllib3/__init__.py:35: NotOpenSSLWarning: urllib3 v2 only supports OpenSSL 1.1.1+, currently the 'ssl' module is compiled with 'LibreSSL 2.8.3'. See: https://github.com/urllib3/urllib3/issues/3020
  warnings.warn(
Game status: running
Game mode: standard
Last updated: 1727424972.313292
---
Received from roulette: *X:2:149:25:0:753:1
Received from roulette: *X:3:547:28:1:687:0
Received from roulette: *X:3:479:26:0:199:0
Received from roulette: *X:2:536:24:1:287:0
Received from roulette: *X:1:886:27:1:882:0
```