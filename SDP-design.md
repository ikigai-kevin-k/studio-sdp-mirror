# SDP-design

## Thread execution priority in the SDP main loop:
```
Main loop:


    LOS-to-SDP communication: 

        Listen to the LOS command events.

        Update the SDP state machine status and forward to the roulette machine.
    
    Roulette-to-SDP communication:

        Get Roulette polling results.

        Update the SDP state machine status, and forward back to the LOS (if necessary).
```

## Design the mocked LOS

Enumerate all possible LOS command events. (Kimi will provide them next week)
