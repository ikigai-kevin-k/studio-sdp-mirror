class APIToProtocolTranslator:
    """
    Usage example:

    translator = APIToProtocolTranslator()

    # Switch game mode
    api_request = {
        "reverse_wheel": True,
        "modify_wheel_speed": True,
        "automatic_status_outputs": True,
        "move_game_delay": True
    }
    roulette_protocol = translator.translate_game_mode(api_request)
    print("Game Mode Protocol:", roulette_protocol)

    # Switch to manual_end_game
    manual_end_game = True
    end_game_protocol = translator.translate_manual_end_game(manual_end_game)
    print("Manual End Game Protocol:", end_game_protocol)
    
    ---

    Output:

    Game Mode Protocol: *o 1157

    Manual End Game Protocol: *X:1:000:24:0:000:1
    """
    def __init__(self):
        self.mode_mapping = {
            "reverse_wheel": 1,
            "user_game_start": 2,
            "modify_wheel_speed": 4,
            "disable_single_winning_number": 16,
            "automatic_status_outputs": 128,
            "output_error_messages": 256,
            "move_game_delay": 1024
        }

    def translate_game_mode(self, api_request):
        """
        Let LOS's API request be translated into Roulette's game protocol
        :param api_request: A dictionary containing game mode settings
        :return: A string in Roulette protocol format
        """
        mode_value = 0
        for key, value in api_request.items():
            if key in self.mode_mapping and value:
                mode_value += self.mode_mapping[key]

        return f"*o {mode_value}\r\n"

    def translate_manual_end_game(self, manual_end_game):
        """
        Let manual_end_game setting be translated into Roulette's game protocol
        :param manual_end_game: A boolean value representing whether to manually end the game
        :return: A string in Roulette protocol format
        """
        x, y, z, a, b = 1, 0, 24, 0, 0  # 默認值
        c = 1 if manual_end_game else 0
        return f"*X:{x:01d}:{y:03d}:{z:02d}:{a:01d}:{b:03d}:{c:01d}\r\n"

# Usage example
translator = APIToProtocolTranslator()

# Switch game mode
api_request = {
    "reverse_wheel": True,
    "modify_wheel_speed": True,
    "automatic_status_outputs": True,
    "move_game_delay": True
}
roulette_protocol = translator.translate_game_mode(api_request)
print("Game Mode Protocol:", roulette_protocol)

# Switch to manual_end_game
manual_end_game = True
end_game_protocol = translator.translate_manual_end_game(manual_end_game)
print("Manual End Game Protocol:", end_game_protocol)
