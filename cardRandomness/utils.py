"""
Utility functions for sequence comparison and card mapping.

This module provides functions for mapping numbers to card representations
and generating random sequences for testing purposes.
"""

import random
from typing import List


def map_number_to_card(number: int) -> str:
    """
    Map a number (0-415) to a card representation.
    Format: {suit}{rank}{deck_num}
    suit: S, D, H, C
    rank: 2-10, J, Q, K, A
    deck_num: 1-8

    Args:
        number (int): Number from 0 to 415

    Returns:
        str: Card representation (e.g., "S21", "D103", "HA8")
    """
    if not 0 <= number <= 415:
        raise ValueError("Number must be between 0 and 415")

    # Calculate suit, rank, and deck number
    deck_num = (number // 52) + 1  # 1-8
    card_in_deck = number % 52

    suit_idx = card_in_deck // 13  # 0-3
    rank_idx = card_in_deck % 13  # 0-12

    # Map suit indices to suit symbols
    suits = ["S", "D", "H", "C"]  # Spades, Diamonds, Hearts, Clubs
    suit = suits[suit_idx]

    # Map rank indices to rank symbols
    ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
    rank = ranks[rank_idx]

    return f"{suit}{rank}{deck_num}"


def map_sequence_to_cards(sequence: List[int]) -> List[str]:
    """
    Convert a sequence of numbers to card representations.

    Args:
        sequence (list): List of numbers from 0 to 415

    Returns:
        list: List of card representations
    """
    return [map_number_to_card(num) for num in sequence]


def generate_random_sequence(length: int, num_values: int = 416) -> List[int]:
    """
    Generate a random sequence with specified length using sampling without
    replacement.

    Args:
        length (int): Length of the sequence (must be <= num_values)
        num_values (int): Number of possible values to choose from

    Returns:
        list: Random sequence with unique values (sampling without replacement)
    """
    if length > num_values:
        raise ValueError(
            f"Length ({length}) cannot be greater than number of values "
            f"({num_values})"
        )

    # Create a list of all possible values and randomly sample without
    # replacement
    all_values = list(range(num_values))
    return random.sample(all_values, length)


def generate_card_sequence(length: int) -> List[str]:
    """
    Generate a random sequence of card representations.

    Args:
        length (int): Length of the sequence (must be <= 416)

    Returns:
        list: List of card representations
    """
    number_sequence = generate_random_sequence(length)
    return map_sequence_to_cards(number_sequence)
