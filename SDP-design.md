# SDP-design

The main features of this architecture are:

- SDPStateMachine class: Manages the SDP state.
- LOSCommunication class:
    - Listens for LOS command events
    - Processes LOS commands
    - Updates the SDP state machine
    - Forwards commands to the roulette machine
- RouletteCommunication class:
    - Polls the roulette machine
    - Processes roulette machine polling results
    - Updates the SDP state machine
    - Forwards results back to LOS if necessary
- Main loop:
    - Uses multithreading to handle LOS communication and roulette machine communication in parallel
    - Periodically prints the current SDP state

This design allows the SDP to simultaneously handle commands from LOS and polling results from the roulette machine. The state machine is used to track the current system state and update it when necessary.

## Mocked LOS Design
Enumerate all possible LOS command events. (Kimi will provide them next week)
