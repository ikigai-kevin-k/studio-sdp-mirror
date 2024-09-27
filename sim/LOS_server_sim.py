from flask import Flask, jsonify
import time
import threading

app = Flask(__name__)

game_parameters = {
    "game_status": "running",
    "game_mode": "standard"
}

def update_game_parameters():
    global game_parameters
    while True:
        # here can add logic to update game parameters
        game_parameters["last_updated"] = time.time()
        time.sleep(5)  # currently hardcoded

@app.route('/get_game_parameters', methods=['GET'])
def get_game_parameters():
    return jsonify(game_parameters)

if __name__ == '__main__':
    update_thread = threading.Thread(target=update_game_parameters)
    update_thread.start()
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)