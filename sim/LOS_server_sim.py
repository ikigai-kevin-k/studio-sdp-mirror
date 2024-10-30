from flask import Flask, jsonify, request
import time
import threading

app = Flask(__name__)

class LOSServerSimulator:
    """
    Recall API design:
    { 

    "roulette_protocol":  {
    "game_state":  # 1~6
    "game number": 1~255
    "last_winning_number": 0~36
    "warning_flag":  # 1,2,4,8 and their sum
    "rotor_speed":  # 0~999
    "rotor_direction":  # 0: clockwise, 1: counterclockwise
    }
    }
    """

    # In production enviroment, the game parameters should be stored in database
    game_parameters = {
        "timestamp": time.time(),
        "game_state": "1", # 1~6, if game is not set to stop (6), then game state will repeatly show from 1 to 5
        "game_number": "1", # 1~255
        "last_winning_number": "0", # 0~36
        "warning_flag": "0", # 0,1,2,4,8 and their sum, i.e. 0~15
        "rotor_speed": "0", # 0~999
        "rotor_direction": "0", # 0: clockwise, 1: counterclockwise
    }


    def los_update_game_parameters():
        """
        TODO: write a fake DB to update game parameters
        """
        global game_parameters
        while True:
            # here can add logic to update game parameters
            pass
            game_parameters["timestamp"] = time.time()
            print("game parameters updated")
            time.sleep(5)  # currently hardcoded


    @app.route('/get_game_parameters', methods=['GET'])
    def los_get_game_parameters_to_sdp():
        if game_parameters["game_state"] != "6":
            return jsonify(game_parameters)
        else:
            return jsonify({"status": "error", "message": "Roulette is not open, cannot get game parameters"}), 403

    # set game parameter only when game is closed
    @app.route('/set_power_off', methods=['POST'])
    def los_set_power_off_to_sdp():
        """
        Because we use arcade mode (fully-automatic), we don't set game parameters during game
        If game is closed, then we can set the game parameter
        """
        
        if game_parameters["game_state"] != "6":
            manager_request_data = request.json
            if 'set_power_off' in manager_request_data:
                if isinstance(manager_request_data['set_power_off'], bool):
                    game_parameters['set_power_off'] = manager_request_data['set_power_off']
                    return jsonify({"status": "success", "message": "set power off"}), 200
                else:
                    return jsonify({"status": "error", "message": "Invalid value for set_power_off"}), 400
            else:
                return jsonify({"status": "error", "message": "Invalid parameter"}), 400
        else:
            return jsonify({"status": "error", "message": "Cannot set power off when game is closed"}), 403

    @app.route('/set_power_on', methods=['POST'])
    def los_set_power_on_to_sdp():
        if game_parameters["game_state"] == "6":
            manager_request_data = request.json
            if isinstance(manager_request_data['set_power_on'], bool):
                game_parameters['set_power_on'] = manager_request_data['set_power_on']
                return jsonify({"status": "success", "message": "set power on"}), 200
            else:
                return jsonify({"status": "error", "message": "Invalid value for set_power_on"}), 400
        else:
            return jsonify({"status": "error", "message": "Cannot set power on when game is open"}), 403

if __name__ == '__main__':
    los = LOSServerSimulator()
    update_thread = threading.Thread(target=los.los_update_game_parameters)
    update_thread.start()
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)