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

New features:
1. Added `check_receive_force_restart_game` to the roulette_main_thread.
2. Split the force restart command from the state_discriminator to a separate function,
    called `check_receive_force_restart_game`.
Log example of force restart:
![alt text](sim/img/force-restart.png)

The game round timer:
![alt text](sim/img/game-round-timer.png)

## Checklist After Receiving the Physical Machine

### Setup and Configuration Phase

- Verify successful configuration of *o 1157, which corresponds to arcade mode parameters
- Confirm ability to adjust GPH parameters
- Check for early firing related commands, verify if early firing is possible by reducing *T t (set wheel deceleration distance to firing position)
- Verify functionality of *F self test command - should be executable during startup and after on-site troubleshooting
- Confirm proper operation of *T S (get wheel speed) and *T N (get rotor direction) commands according to Mihail's designed game flow
- Check for any instances of commands not receiving responses (no "ok" response)

### Gameplay Phase

- Check if the issue exists where game number remains unchanged after a round (as seen in previous logs)
- Verify state machine implementation matches roulette_sim
- In non-arcade mode, verify proper functionality of *u 1 (manual restart) command
- Check for instances of missing log entries
- Verify there are no cases of complete log reception failure