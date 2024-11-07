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