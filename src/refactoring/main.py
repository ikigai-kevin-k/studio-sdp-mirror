import threading
from gui import GUI
from state_machine import SDPStateMachine
from communication.los_communication import LOSCommunication
from communication.roulette_communication import RouletteCommunication
from processors.sdp import SDP
from processors.idp import IDP
import os

def main():
    gui = GUI(None, None, None)
    state_machine = SDPStateMachine(gui)
    roulette_comm = RouletteCommunication(state_machine, None, gui)
    los_comm = LOSCommunication(state_machine, roulette_comm)
    
    sdp = SDP(state_machine, los_comm, roulette_comm)
    idp = IDP(state_machine, los_comm) # no need to implement yet
    
    los_comm.add_processor(sdp)
    los_comm.add_processor(idp) # no need to implement yet
    
    roulette_comm.los_comm = los_comm

    gui.state_machine = state_machine
    gui.los_comm = los_comm
    gui.roulette_comm = roulette_comm

    roulette_comm.initialize_serial()
    los_comm.start_communication() # use http protocol 

    # Create and start threads
    threads = [
        threading.Thread(target=los_comm.process_commands), # main loop processes commands from LOS
        threading.Thread(target=roulette_comm.poll_roulette),
        threading.Thread(target=roulette_comm.process_polling_results)
    ]

    for thread in threads:
        thread.daemon = True
        thread.start()

    # Run GUI (currently exists display issue)
    print("Starting GUI...")
    gui.run()

    print("GUI closed. Cleaning up...")
    # Clean up resources
    if roulette_comm.serial_port:
        roulette_comm.serial_port.close()
    if roulette_comm.master:
        os.close(roulette_comm.master)
    if roulette_comm.slave:
        os.close(roulette_comm.slave)

if __name__ == "__main__":
    main()