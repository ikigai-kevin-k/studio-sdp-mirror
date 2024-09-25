# studio-sdp-roulette

### Requirements
* Python 3.9+ (only tested on 3.9)
* PySerial (imported as serial)
* For MacOS, due to depreciation of system-level pip install, need to create venv for pip installation:
```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install pyserial
```

## Overview Architecture

![](overview.png)

## SDP (serial data processor) design

## sdp-prototype.py 

Serail data processor main module.
See the [design doc](SDP-design.md) for more details.

### Usage
```bash
python3 sdp-prototype.py
```

## Misc: serial-port-sim.py: 
The aim of this script is to create a virtual serial port and send data
to simulate the behavior from/to the Roulette machine and the LOC computer.
Currently the both two ends of serial ports are created on the same MacOS notebook,
hence it is a loopback.
The data is generated following the specified game protocol format:
*X:{x:01d}:{y:03d}:{z:02d}:{a:01d}:{b:03d}:{c:01d}
The specific ranges of each fields in the game protocol is going to be checked.

### Usage
```bash
python3 serial-port-sim.py
```
The demonstrative output shows as below:
![](demo.png)
