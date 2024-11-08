<!-- vscode-markdown-toc -->
* [Usage](#Usage)
* [New features:](#Newfeatures:)
* [Checklist After Receiving the Physical Machine](#ChecklistAfterReceivingthePhysicalMachine)
	* [Setup and Configuration Phase](#SetupandConfigurationPhase)
	* [Gameplay Phase](#GameplayPhase)

<!-- vscode-markdown-toc-config
	numbering=true
	autoSave=true
	/vscode-markdown-toc-config -->
<!-- /vscode-markdown-toc -->##  1. <a name='Usage'></a>Usage

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

##  2. <a name='Newfeatures:'></a>New features:
1. Added `check_receive_force_restart_game` to the roulette_main_thread.
2. Split the force restart command from the state_discriminator to a separate function,
    called `check_receive_force_restart_game`.
Log example of force restart:
![alt text](sim/img/force-restart.png)

3.The game round timer:
![alt text](sim/img/game-round-timer.png)

##  3. <a name='ChecklistAfterReceivingthePhysicalMachine'></a>Checklist After Receiving the Physical Machine

###  3.1. <a name='SetupandConfigurationPhase'></a>Setup and Configuration Phase

- Verify successful configuration of *o 1157, which corresponds to arcade mode parameters
- Confirm ability to adjust GPH parameters
- Check for early firing related commands, verify if early firing is possible by reducing *T t (set wheel deceleration distance to firing position)
- Verify functionality of *F self test command - should be executable during startup and after on-site troubleshooting
- Confirm proper operation of *T S (get wheel speed) and *T N (get rotor direction) commands according to Mihail's designed game flow
- Check for any instances of commands not receiving responses (no "ok" response)

###  3.2. <a name='GameplayPhase'></a>Gameplay Phase

- Check if the issue exists where game number remains unchanged after a round (as seen in previous logs)
- Verify state machine implementation matches roulette_sim
- In non-arcade mode, verify proper functionality of *u 1 (manual restart) command
- Check for instances of missing log entries
- Verify there are no cases of complete log reception failure