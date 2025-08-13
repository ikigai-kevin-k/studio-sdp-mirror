# the dealing order is like this:
# player card1, banker card1, player card2, banker card2, player card3, banker card3
# the idp (image data processor) will send the card position on the table to the dealing_order_check.py
# but the idp has not implement yet, so we will use the mock data to test the dealing_order_check.py
# and the dealing_order_check.py will check if the dealing order is correct

from typing import List


def check_dealing_order(card_faces: List[str], outs: bool = False) -> bool:
    """
    Check if the dealing order is correct based on card faces (empty string means not dealt).
    Args:
        card_faces (List[str]): List of card faces in the order they were dealt. Each element is a string (e.g., 'AC', '2D', '')
        outs (bool): If True, consider outs (third card) cases. If False, only check for the first four cards.
    Returns:
        bool: True if the dealing order is correct (no skipped positions before a card is dealt), False otherwise.
    """
    # Define the expected number of cards for non-outs and outs
    expected_len = 6 if outs else 4
    if len(card_faces) < expected_len:
        return False
    # Only check up to expected_len
    faces = card_faces[:expected_len]
    found_empty = False
    for face in faces:
        if face == "":
            found_empty = True
        elif found_empty:
            # If a card appears after an empty slot, order is wrong
            return False
    return True


# Mock data for testing (simulate the data that would be sent by the idp)
mock_data_non_outs = ["KD", "6H", "5C", "JS", "", ""]  # 4 cards, no outs
mock_data_outs = ["KD", "6H", "5C", "JS", "JD", "QS"]  # 6 cards, with outs
mock_data_wrong = ["KD", "", "5C", "JS", "", ""]  # Skipped position (should be False)
mock_data_partial = ["KD", "6H", "", "", "", ""]  # Only first two cards

if __name__ == "__main__":
    # Test with mock data for non-outs
    print(
        "Test non-outs (should be True):",
        check_dealing_order(mock_data_non_outs, outs=False),
    )
    # Test with mock data for outs
    print("Test outs (should be True):", check_dealing_order(mock_data_outs, outs=True))
    # Test with wrong order (skipped position)
    print(
        "Test wrong order (should be False):",
        check_dealing_order(mock_data_wrong, outs=False),
    )
    # Test with partial data (not enough cards)
    print(
        "Test partial (should be False):",
        check_dealing_order(mock_data_partial, outs=False),
    )
