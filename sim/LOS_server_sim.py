from flask import Flask, jsonify, request
import time
import threading

app = Flask(__name__)


"""
Recall API design:
{ 
# ... (Other API fields)
"roulette_details":  {
   "game_state":  # 1~6
   "warning_flag":  # 1,2,4,8 and their sum
   "game_mode":  # 1,2,4,16,128,256,1024
   }
# ... (Other API fields)
}

2024/10/02 Modified:
game_parameters:
- 重新命名last_updated為timestamp
- 重新命名game_parameters為extra_game_parameter
- 刪除了roulette_open直接用game_state來判斷是否可以get/set game parameter
- 註解中註明了value的取值範圍
"""

# In production enviroment, the game parameters should be stored in database
game_parameters = {
    "timestamp": time.time(),
    # game status 要改名成game_state以貼合owner handbook
    "game_state": "1", # 1~6
    "game_mode": "1", # 1,2,4,16,128,256,1024
    "warning_flag": "0", # 0,1,2,4,8 and their sum, i.e. 0~15
    "extra_game_parameter": {
        "manual_end_game": False, # 目前對應到arcade mode (fully-automatic)
    }
}

def update_game_parameters():
    global game_parameters
    while True:
        # here can add logic to update game parameters
        game_parameters["timestamp"] = time.time()
        time.sleep(5)  # currently hardcoded

@app.route('/get_game_parameters', methods=['GET'])
def get_game_parameters():
    if game_parameters["game_state"] != "6":
        return jsonify(game_parameters)
    else:
        return jsonify({"status": "error", "message": "Roulette is not open"}), 403

@app.route('/set_game_parameter', methods=['POST'])
def set_game_parameter():
    # if game is not closed, then we can set the game parameter
    if game_parameters["game_state"] != "6":
        data = request.json
        if 'manual_end_game' in data:
            if isinstance(data['manual_end_game'], bool):
                game_parameters["extra_game_parameter"]['manual_end_game'] = data['manual_end_game']
                return jsonify({"status": "success", "message": "Game parameter updated"}), 200
            else:
                return jsonify({"status": "error", "message": "Invalid value for manual_end_game"}), 400
        else:
            return jsonify({"status": "error", "message": "Invalid parameter"}), 400
    else:
        return jsonify({"status": "error", "message": "Cannot set parameters when game is closed"}), 403

@app.route('/set_power_off', methods=['POST'])
def set_power_off():
    game_parameters["game_state"] = "6"
    return jsonify({"status": "success", "message": "Game power off"}), 200

@app.route('/set_power_on', methods=['POST'])
def set_power_on():
    game_parameters["game_state"] = "1"
    return jsonify({"status": "success", "message": "Game power on"}), 200
if __name__ == '__main__':
    update_thread = threading.Thread(target=update_game_parameters)
    update_thread.start()
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)