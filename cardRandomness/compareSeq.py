#!/usr/bin/env python3
"""
Sequence Comparison Algorithm Implementation

This module implements the sequence comparison algorithm described in
comapareSeq.tex. The algorithm compares two sequences and finds the longest
matching subsequences.
"""

from typing import List, Tuple
from utils import generate_card_sequence


def compare_sequences(
    seq1: List, seq2: List
) -> List[Tuple[int, int, List, int]]:
    """
    Compare two sequences and find the longest matching subsequence.

    Args:
        seq1: First sequence to compare
        seq2: Second sequence to compare

    Returns:
        List containing the longest matching subsequence as a tuple:
        (i, j, subsequence, length) where:
        - i: starting position in seq1
        - j: starting position in seq2
        - subsequence: the matching subsequence from seq2
        - length: length of the matching subsequence
        Returns empty list if no matches found.
    """
    best_match = None
    best_length = 0

    # Traverse all possible position combinations
    for i in range(len(seq1)):
        for j in range(len(seq2)):
            # Check if elements match
            if seq2[j] == seq1[i]:
                # Find the longest matching subsequence starting from this
                # position
                match_length = find_longest_match(seq1, seq2, i, j)

                if match_length > best_length:
                    # Extract the matching subsequence from seq2
                    subsequence = seq2[j : j + match_length]
                    best_match = (i, j, subsequence, match_length)
                    best_length = match_length

                    # Issue warning if the match is not complete
                    if i + match_length < len(seq1) and j + match_length < len(
                        seq2
                    ):
                        if seq1[i + match_length] != seq2[j + match_length]:
                            print("⚠️  WARNING: Partial match found!")
                            print(
                                f"   Position: seq1[{i}:{i+match_length}] "
                                f"and seq2[{j}:{j+match_length}]"
                            )
                            print(
                                f"   Next elements differ: "
                                f"seq1[{i+match_length}]="
                                f"{seq1[i+match_length]} vs "
                                f"seq2[{j+match_length}]="
                                f"{seq2[j+match_length]}"
                            )
                            print()

    return [best_match] if best_match else []


def find_longest_match(
    seq1: List, seq2: List, start_i: int, start_j: int
) -> int:
    """
    Find the length of the longest matching subsequence starting from given
    positions.

    Args:
        seq1: First sequence
        seq2: Second sequence
        start_i: Starting position in seq1
        start_j: Starting position in seq2

    Returns:
        Length of the longest matching subsequence
    """
    match_length = 0

    # Recursively check subsequent elements
    while (
        start_i + match_length < len(seq1)
        and start_j + match_length < len(seq2)
        and seq1[start_i + match_length] == seq2[start_j + match_length]
    ):
        match_length += 1

    return match_length


def print_comparison_results(
    seq1: List, seq2: List, results: List[Tuple[int, int, List, int]]
):
    """
    Print the comparison results in a formatted way.

    Args:
        seq1: First sequence
        seq2: Second sequence
        results: Results from compare_sequences function
    """
    print(f"Sequence 1: {seq1}")
    print(f"Sequence 2: {seq2}")
    print("-" * 50)

    if not results:
        print("No matching subsequences found.")
        return

    if results:
        print("Found longest matching subsequence:")
        print()
        pos1, pos2, subsequence, length = results[0]
        print("Longest Match:")
        print(
            f"  Position in seq1: [{pos1}:{pos1+length}] = "
            f"{seq1[pos1:pos1+length]}"
        )
        print(f"  Position in seq2: [{pos2}:{pos2+length}] = {subsequence}")
        print(f"  Length: {length}")
        print()

        # Show warning for long matches after displaying results
        if length >= 3:
            print("⚠️  WARNING: Long matching subsequence found!")
            print(f"   Length: {length}")
            print(f"   Position in seq1: [{pos1}:{pos1+length}]")
            print(f"   Position in seq2: [{pos2}:{pos2+length}]")
            print(f"   Subsequence: {subsequence}")
            print()


def main():
    """
    Main function demonstrating the sequence comparison algorithm.
    """
    print("Sequence Comparison Algorithm Demo")
    print("=" * 50)
    print()

    # Test case 1: Random card sequences
    print("Test Case 1: Random Card Sequences")
    seq1_cards = generate_card_sequence(10)
    seq2_cards = generate_card_sequence(10)
    results1 = compare_sequences(seq1_cards, seq2_cards)
    print_comparison_results(seq1_cards, seq2_cards, results1)

    # Test case 2: Shifted card sequences
    print("Test Case 2: Shifted Card Sequences")
    seq1_shifted = generate_card_sequence(10)
    # Create seq2 by shifting seq1 right by 3 positions and adding 3 random
    # cards at the beginning that don't appear in the shifted subsequence
    shifted_subseq = seq1_shifted[:-3]  # The part that will be shifted

    # Generate random cards that are not in the shifted subsequence
    random_prefix = []
    attempts = 0
    while len(random_prefix) < 3 and attempts < 100:
        candidate = generate_card_sequence(1)[0]
        if candidate not in shifted_subseq:
            random_prefix.append(candidate)
        attempts += 1

    # If we couldn't find 3 unique cards, use the first 3 from a larger sample
    if len(random_prefix) < 3:
        all_random = generate_card_sequence(20)
        random_prefix = [
            card for card in all_random if card not in shifted_subseq
        ][:3]

    # Remove last 3 cards and add prefix
    seq2_shifted = random_prefix + shifted_subseq
    results2 = compare_sequences(seq1_shifted, seq2_shifted)
    print_comparison_results(seq1_shifted, seq2_shifted, results2)


if __name__ == "__main__":
    main()
