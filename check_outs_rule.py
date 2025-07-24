import itertools

# Card value mapping
CARD_VALUES = {
    'A': 1,
    '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
    '10': 0, 'J': 0, 'Q': 0, 'K': 0
}

# Calculate the baccarat hand point (only the unit digit)
def hand_point(cards):
    return sum(CARD_VALUES[c] for c in cards) % 10

# Check if hand is Natural (8 or 9 with first two cards)
def is_natural(cards):
    return len(cards) == 2 and hand_point(cards) in (8, 9)

# Player drawing rule
def player_draw_rule(player_cards):
    pt = hand_point(player_cards[:2])
    if pt <= 5:
        return True  # Player draws
    return False     # Player stands

# Banker drawing rule
def banker_draw_rule(banker_cards, player_cards, player_third_card=None):
    banker_pt = hand_point(banker_cards[:2])
    player_pt = hand_point(player_cards[:2])
    # Check for Natural
    if is_natural(player_cards[:2]) or is_natural(banker_cards[:2]):
        return False  # No one draws
    # Banker simple rules
    if banker_pt <= 2:
        return True
    if banker_pt == 3:
        if player_third_card is None:
            return False
        return player_third_card != 8
    if banker_pt == 4:
        if player_third_card is None:
            return False
        return 2 <= player_third_card <= 7
    if banker_pt == 5:
        if player_third_card is None:
            return False
        return 4 <= player_third_card <= 7
    if banker_pt == 6:
        if player_third_card is None:
            return False
        return player_third_card in (6, 7)
    return False  # 7 or above, banker stands

# Helper to get third card value if player draws
def get_player_third_card(player_cards):
    if player_draw_rule(player_cards):
        return CARD_VALUES[player_cards[2]] if len(player_cards) > 2 else None
    return None

# Test cases for dealer process
def test_banker_dealing():
    # Each test: (player_cards, banker_cards, expected_banker_draw)
    tests = [
        # Natural cases
        (['A', '8'], ['5', '2'], False),  # Player Natural 9
        (['4', '4'], ['K', '9'], False),  # Banker Natural 9
        # Player stands, banker <=2 must draw
        (['7', '7'], ['2', 'Q'], True),   # Banker 2
        # Player draws, banker 3, player third card 8 (banker should NOT draw)
        (['2', '2', '8'], ['A', '2'], False),
        # Player draws, banker 3, player third card not 8 (banker should draw)
        (['2', '2', '7'], ['A', '2'], True),
        # Banker 4, player third card 2-7 (should draw)
        (['2', '2', '2'], ['2', '2'], True),
        (['2', '2', '7'], ['2', '2'], True),
        # Banker 4, player third card not 2-7 (should not draw)
        (['2', '2', '8'], ['2', '2'], False),
        (['2', '2', 'A'], ['2', '2'], False),  # 將 '1' 改為 'A'
        # Banker 5, player third card 4-7 (should draw)
        (['2', '2', '4'], ['3', '2'], True),
        (['2', '2', '7'], ['3', '2'], True),
        # Banker 5, player third card not 4-7 (should not draw)
        (['2', '2', '2'], ['3', '2'], False),
        (['2', '2', '8'], ['3', '2'], False),
        # Banker 6, player third card 6 or 7 (should draw)
        (['2', '2', '6'], ['4', '2'], True),
        (['2', '2', '7'], ['4', '2'], True),
        # Banker 6, player third card not 6 or 7 (should not draw)
        (['2', '2', '5'], ['4', '2'], False),
        (['2', '2', '8'], ['4', '2'], False),
        # Banker 7 always stands
        (['2', '2', '6'], ['4', '3'], False),
    ]
    for idx, (player_cards, banker_cards, expected) in enumerate(tests):
        player_third_card = None
        if len(player_cards) > 2:
            player_third_card = CARD_VALUES[player_cards[2]]
        result = banker_draw_rule(banker_cards, player_cards, player_third_card)
        print(f"Test {idx+1}: Player {player_cards}, Banker {banker_cards} => Banker Draw? {result} (Expected: {expected})", end=' ')
        if result == expected:
            print("✅")
        else:
            print("❌")

if __name__ == "__main__":
    test_banker_dealing() 