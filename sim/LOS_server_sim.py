from flask import Flask, jsonify, request
import time
import threading

app = Flask(__name__)

# In production enviroment, the game parameters should be stored in database
game_parameters = {
    "last_updated": time.time(),
    "game_status": "running", # two states: running/closed, temporary value, the actual value should be referred from owner handbook
    "game_mode": "standard", # temporary value, the actual value should be referred from owner handbook
    "game_parameters": {
        "manual_end_game": False, # temporary value, the actual value should be referred from owner handbook
    },
    "roulette_open": True  # to represent whether the roulette is open
}

def update_game_parameters():
    global game_parameters
    while True:
        # here can add logic to update game parameters
        game_parameters["last_updated"] = time.time()
        time.sleep(5)  # currently hardcoded

@app.route('/get_game_parameters', methods=['GET'])
def get_game_parameters():
    if game_parameters["roulette_open"]:
        return jsonify(game_parameters)
    else:
        return jsonify({"status": "error", "message": "Roulette is not open"}), 403

@app.route('/set_game_parameter', methods=['POST'])
def set_game_parameter():
    if game_parameters["roulette_open"]:
        print(game_parameters["roulette_open"]) # for debugging
        data = request.json
        if 'manual_end_game' in data:
            if isinstance(data['manual_end_game'], bool):
                game_parameters['game_parameters']['manual_end_game'] = data['manual_end_game']
                return jsonify({"status": "success", "message": "Game parameter updated"}), 200
            else:
                return jsonify({"status": "error", "message": "Invalid value for manual_end_game"}), 400
        else:
            return jsonify({"status": "error", "message": "Invalid parameter"}), 400
    else:
        return jsonify({"status": "error", "message": "Cannot set parameters when game is closed"}), 403

if __name__ == '__main__':
    update_thread = threading.Thread(target=update_game_parameters)
    update_thread.start()
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)