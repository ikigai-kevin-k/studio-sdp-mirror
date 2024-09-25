# SDP-design

## Thread execution priority in the SDP main loop:
```
Main loop:
    LOS-to-SDP communication: listen to the LOS command events, update the SDP state machine status and forward to the roulette machine.
    Roulette-to-SDP communication: Get polling results, update the SDP state machine status, and forward back to the LOS if necessary.
```

## Design the mocked LOS

Enumerate all possible LOS command events.
