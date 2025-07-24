# the dealing order is like this:
# player card1, banker card1, player card2, banker card2, player card3, banker card3
# the idp (image data processor) will send the card position on the table to the dealing_order_check.py
# but the idp has not implement yet, so we will use the mock data to test the dealing_order_check.py
# and the dealing_order_check.py will check if the dealing order is correct

from typing import List

def check_dealing_order(card_positions: List[str], outs: bool = False) -> bool:
    """
    Check if the dealing order is correct.
    Args:
        card_positions (List[str]): List of card positions in the order they were dealt. Each element should be one of:
            'player1', 'banker1', 'player2', 'banker2', 'player3', 'banker3'
        outs (bool): If True, consider outs (third card) cases. If False, only check for the first four cards.
    Returns:
        bool: True if the dealing order is correct, False otherwise.
    """
    # Define the correct dealing order for non-outs and outs
    correct_order_non_outs = ['player1', 'banker1', 'player2', 'banker2']
    correct_order_outs = ['player1', 'banker1', 'player2', 'banker2', 'player3', 'banker3']

    if outs:
        expected_order = correct_order_outs
    else:
        expected_order = correct_order_non_outs

    # Only compare up to the length of expected_order
    if len(card_positions) < len(expected_order):
        return False
    for i, expected in enumerate(expected_order):
        if card_positions[i] != expected:
            return False
    return True

# Mock data for testing (simulate the data that would be sent by the idp)
mock_data_non_outs = ['player1', 'banker1', 'player2', 'banker2']
mock_data_outs = ['player1', 'banker1', 'player2', 'banker2', 'player3', 'banker3']
mock_data_wrong = ['player1', 'banker1', 'banker2', 'player2']

if __name__ == "__main__":
    # Test with mock data for non-outs
    print("Test non-outs (should be True):", check_dealing_order(mock_data_non_outs, outs=False))
    # Test with mock data for outs
    print("Test outs (should be True):", check_dealing_order(mock_data_outs, outs=True))
    # Test with wrong order
    print("Test wrong order (should be False):", check_dealing_order(mock_data_wrong, outs=False))