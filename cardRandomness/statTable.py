"""
Serial Correlation Detection Algorithm Implementation

This module implements the algorithm described in statTable.tex for detecting
serial correlation in sequences using a 10×10 cumulative counting matrix.

The algorithm:
1. Constructs a 10×10 cumulative counting matrix M over 100 rounds
2. Calculates normalized frequencies f_{p,v} from the matrix
3. Assumes uniform distribution for the frequencies
4. Detects anomalies by comparing the standard deviation against a threshold
"""

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import argparse
from typing import Tuple, Optional
from utils import generate_random_sequence


class SerialCorrelationDetector:
    """
    Serial correlation detector using cumulative counting matrix approach.

    This class implements the algorithm for detecting serial correlation
    in sequences of 10 possible values over 100 rounds.
    """

    def __init__(self, matrix_size: int = 10, rounds: int = 100):
        """
        Initialize the serial correlation detector.

        Args:
            matrix_size (int): Size of the matrix (default: 10)
            rounds (int): Number of rounds to run (default: 100)
        """
        self.matrix_size = matrix_size
        self.rounds = rounds
        self.matrix = np.zeros((self.matrix_size, self.matrix_size), dtype=int)
        self.frequencies = None
        self.threshold = self._calculate_threshold()

    def _calculate_threshold(self) -> float:
        """
        Calculate the threshold based on the matrix dimensions.

        Threshold formula: ((n*n-1)/12)^0.5, where n = p × v (matrix dimensions)

        Returns:
            float: Threshold value
        """
        n = self.matrix_size * self.matrix_size  # n = p × v
        return np.sqrt((n * n - 1) / 12)

    def run_100_rounds(self) -> np.ndarray:
        """
        Run 100 rounds of sequence generation and build cumulative matrix.

        Each round generates a sequence of length 10 with unique values 0-9.
        For each value v appearing at position p, increment M[p,v] by 1.

        Returns:
            np.ndarray: 10×10 cumulative counting matrix
        """
        # Initialize matrix
        self.matrix = np.zeros((self.matrix_size, self.matrix_size), dtype=int)

        print(f"Running {self.rounds} rounds of sequence generation...")

        for round_num in range(self.rounds):
            # Generate sequence of length 10 with unique values 0-9
            sequence = generate_random_sequence(
                self.matrix_size, num_values=self.matrix_size
            )

            # For each position p and value v in the sequence
            for p, v in enumerate(sequence):
                # Increment M[p,v] by 1
                self.matrix[p, v] += 1

            if (round_num + 1) % 20 == 0:
                print(f"Completed {round_num + 1} rounds...")

        print(f"Completed all {self.rounds} rounds!")
        return self.matrix

    def calculate_frequencies(self) -> np.ndarray:
        """
        Calculate the normalized frequencies f_{p,v}.

        f_{p,v} = M_{p,v} / Σ M_{p,v}

        Returns:
            np.ndarray: Matrix of normalized frequencies
        """
        if self.matrix is None:
            raise ValueError(
                "Matrix must be built first using run_100_rounds()"
            )

        # Calculate total sum of all matrix elements
        total_sum = np.sum(self.matrix)

        # Calculate frequencies
        self.frequencies = self.matrix.astype(float) / total_sum

        return self.frequencies

    def encode_positions(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Encode 10x10 matrix positions (p,v) to linear index i = 1,...,100.

        For 10x10 matrix: i = p * 10 + v + 1 (where p,v are 0-based)
        This gives i = 1,...,100 for positions (0,0) to (9,9)

        Returns:
            Tuple[np.ndarray, np.ndarray]: (encoded_indices, frequencies_1d)
        """
        if self.frequencies is None:
            raise ValueError("Frequencies must be calculated first")

        # Create encoded indices: i = p * matrix_size + v + 1
        encoded_indices = []
        frequencies_1d = []

        for p in range(self.matrix_size):
            for v in range(self.matrix_size):
                i = p * self.matrix_size + v + 1  # i = 1,...,100
                encoded_indices.append(i)
                frequencies_1d.append(self.frequencies[p, v])

        return np.array(encoded_indices), np.array(frequencies_1d)

    def calculate_expected_value_and_std(self) -> Tuple[float, float]:
        """
        Calculate E(i) = Σ(i * f_i) and STD(i) for the encoded positions.

        STD(i) formula: sqrt(Σ f_i * (i - E(i))^2), where i is the re-encoded position (p,v)
        i = 1,...,p×v

        Returns:
            Tuple[float, float]: (expected_value, standard_deviation)
        """
        encoded_indices, frequencies_1d = self.encode_positions()

        # Calculate E(i) = Σ(i * f_i)
        expected_value = np.sum(encoded_indices * frequencies_1d)

        # Calculate STD(i) = sqrt(Σ f_i * (i - E(i))^2)
        variance = np.sum(
            frequencies_1d * (encoded_indices - expected_value) ** 2
        )
        std_dev = np.sqrt(variance)

        return expected_value, std_dev

    def detect_anomalies(self) -> Tuple[bool, float, float, float, float]:
        """
        Detect anomalies using the new method with position encoding.

        Returns:
            Tuple[bool, float, float, float, float]:
            (is_anomaly, expected_value, std_dev, threshold, warning_message)
        """
        if self.frequencies is None:
            raise ValueError("Frequencies must be calculated first")

        # Calculate expected value and standard deviation
        expected_value, std_dev = self.calculate_expected_value_and_std()

        # Check if standard deviation exceeds threshold
        is_anomaly = std_dev > self.threshold

        warning_message = ""
        if is_anomaly:
            warning_message = f"WARNING: STD(i) = {std_dev:.4f} > {self.threshold} (threshold)"
        else:
            warning_message = (
                f"OK: STD(i) = {std_dev:.4f} <= {self.threshold} (threshold)"
            )

        return (
            is_anomaly,
            expected_value,
            std_dev,
            self.threshold,
            warning_message,
        )

    def run_complete_analysis(self) -> dict:
        """
        Run complete analysis: 100 rounds, calculate frequencies, detect anomalies.

        Returns:
            dict: Analysis results including anomaly detection
        """
        # Run 100 rounds and build matrix
        matrix = self.run_100_rounds()

        # Calculate frequencies
        frequencies = self.calculate_frequencies()

        # Detect anomalies using new method
        is_anomaly, expected_value, std_dev, threshold, warning_message = (
            self.detect_anomalies()
        )

        # Calculate additional statistics
        mean_freq = np.mean(frequencies)
        min_freq = np.min(frequencies)
        max_freq = np.max(frequencies)

        return {
            "rounds": self.rounds,
            "matrix_shape": matrix.shape,
            "is_anomaly": is_anomaly,
            "expected_value": expected_value,
            "std_deviation": std_dev,
            "threshold": threshold,
            "warning_message": warning_message,
            "mean_frequency": mean_freq,
            "min_frequency": min_freq,
            "max_frequency": max_freq,
            "frequency_range": max_freq - min_freq,
        }

    def create_heatmap(
        self, save_path: Optional[str] = None, show_plot: bool = True
    ):
        """
        Create a heatmap of the frequency matrix f_{p,v} with top 10 values highlighted.

        Args:
            save_path (str, optional): Path to save the plot
            show_plot (bool): Whether to display the plot
        """
        if self.frequencies is None:
            raise ValueError("Frequencies must be calculated first")

        plt.figure(figsize=(12, 10))

        # Create heatmap using seaborn
        ax = sns.heatmap(
            self.frequencies,
            annot=True,
            fmt=".4f",
            cmap="viridis",
            cbar_kws={"label": "Frequency f_{p,v}"},
        )

        # Find top 10 highest frequency values and their positions
        flat_frequencies = self.frequencies.flatten()
        top_10_indices = np.argsort(flat_frequencies)[-10:][
            ::-1
        ]  # Top 10, descending order

        # Convert flat indices back to (p, v) coordinates
        top_10_positions = []
        top_10_values = []

        for idx in top_10_indices:
            p = idx // self.matrix_size
            v = idx % self.matrix_size
            top_10_positions.append((p, v))
            top_10_values.append(flat_frequencies[idx])

        # Highlight top 10 positions with red rectangles
        for i, (p, v) in enumerate(top_10_positions):
            # Create rectangle around the cell
            rect = plt.Rectangle(
                (v, p),
                1,
                1,
                fill=False,
                edgecolor="red",
                linewidth=2,
                alpha=0.8,
            )
            ax.add_patch(rect)

            # Add ranking number in the corner
            ax.text(
                v + 0.1,
                p + 0.1,
                f"#{i+1}",
                color="red",
                fontweight="bold",
                fontsize=8,
                bbox=dict(
                    boxstyle="round,pad=0.2", facecolor="white", alpha=0.8
                ),
            )

        plt.title(
            f"Frequency Heatmap f_{{p,v}} (Top 10 Highlighted)\n10×10 Matrix ({self.rounds} rounds)",
            fontsize=14,
        )
        plt.xlabel("Value v (0-9)", fontsize=12)
        plt.ylabel("Position p (0-9)", fontsize=12)

        # Add grid
        plt.grid(True, alpha=0.3)

        # Print top 10 values information
        print("\nTop 10 Highest Frequency Values:")
        print("-" * 50)
        for i, ((p, v), value) in enumerate(
            zip(top_10_positions, top_10_values)
        ):
            print(f"#{i+1:2d}: Position ({p},{v}) = {value:.6f}")

        # Save the plot if path is provided
        if save_path:
            plt.savefig(
                save_path, dpi=300, bbox_inches="tight", facecolor="white"
            )
            print(f"\nHeatmap saved to: {save_path}")

        # Show the plot if requested
        if show_plot:
            plt.show()
        else:
            plt.close()

    def visualize_matrix(
        self, save_path: Optional[str] = None, show_plot: bool = True
    ):
        """
        Visualize the cumulative counting matrix M.

        Args:
            save_path (str, optional): Path to save the plot
            show_plot (bool): Whether to display the plot
        """
        if self.matrix is None:
            raise ValueError("Matrix must be built first")

        plt.figure(figsize=(10, 8))

        # Create heatmap of the counting matrix
        sns.heatmap(
            self.matrix,
            annot=True,
            fmt="d",
            cmap="Blues",
            cbar_kws={"label": "Count M_{p,v}"},
        )

        plt.title(
            f"Cumulative Counting Matrix M_{{p,v}}\n10×10 Matrix ({self.rounds} rounds)",
            fontsize=14,
        )
        plt.xlabel("Value v (0-9)", fontsize=12)
        plt.ylabel("Position p (0-9)", fontsize=12)

        # Add grid
        plt.grid(True, alpha=0.3)

        # Save the plot if path is provided
        if save_path:
            plt.savefig(
                save_path, dpi=300, bbox_inches="tight", facecolor="white"
            )
            print(f"Matrix visualization saved to: {save_path}")

        # Show the plot if requested
        if show_plot:
            plt.show()
        else:
            plt.close()

    def print_analysis_summary(self, results: dict):
        """
        Print a summary of the analysis results.

        Args:
            results (dict): Results from run_complete_analysis()
        """
        print("=" * 70)
        print("SERIAL CORRELATION DETECTION ANALYSIS (10×10 CASE)")
        print("=" * 70)
        print(f"Rounds: {results['rounds']}")
        print(f"Matrix Shape: {results['matrix_shape']}")
        matrix_size = results["matrix_shape"][
            0
        ]  # Get matrix size from results
        n = matrix_size * matrix_size  # n = p × v
        print(f"Threshold: {results['threshold']:.4f} (({n}²-1)/12)^0.5")
        print(f"Expected Value E(i): {results['expected_value']:.4f}")
        print(f"Standard Deviation STD(i): {results['std_deviation']:.4f}")
        print(f"Anomaly Detected: {'YES' if results['is_anomaly'] else 'NO'}")
        print("-" * 70)
        print(f"Status: {results['warning_message']}")
        print("-" * 70)
        print("Frequency Statistics:")
        print(f"  Mean: {results['mean_frequency']:.6f}")
        print(f"  Min:  {results['min_frequency']:.6f}")
        print(f"  Max:  {results['max_frequency']:.6f}")
        print(f"  Range: {results['frequency_range']:.6f}")
        print("=" * 70)


def demo_10x10_analysis(rounds: int = 100):
    """
    Demonstrate the 10×10 matrix analysis with specified rounds.

    Args:
        rounds (int): Number of rounds to run (default: 100)
    """
    print(f"Demo: 10×10 Matrix Analysis ({rounds} rounds)")
    print("-" * 50)

    # Create detector for 10×10 case
    detector = SerialCorrelationDetector(matrix_size=10, rounds=rounds)

    # Run complete analysis
    results = detector.run_complete_analysis()

    # Print results
    detector.print_analysis_summary(results)

    # Generate and save visualizations
    print("\nGenerating visualizations...")
    counting_filename = f"counting_matrix_10x10_{rounds}rounds.png"
    frequency_filename = f"frequency_heatmap_10x10_{rounds}rounds.png"

    detector.visualize_matrix(save_path=counting_filename, show_plot=False)
    detector.create_heatmap(save_path=frequency_filename, show_plot=False)

    return detector, results


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Serial Correlation Detection Algorithm Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 statTable.py                    # Run with default 100 rounds
  python3 statTable.py --rounds 50        # Run with 50 rounds
  python3 statTable.py -r 200             # Run with 200 rounds
        """,
    )

    parser.add_argument(
        "--rounds",
        "-r",
        type=int,
        default=100,
        help="Number of rounds to run (default: 100)",
    )

    parser.add_argument(
        "--matrix-size",
        "-m",
        type=int,
        default=10,
        help="Matrix size (default: 10)",
    )

    return parser.parse_args()


if __name__ == "__main__":
    # Parse command line arguments
    args = parse_arguments()

    print("Serial Correlation Detection Algorithm Demo")
    print(f"10×10 Matrix Case with {args.rounds} Rounds")
    print("=" * 70)

    # Run demo
    try:
        # Demo: 10×10 analysis with specified rounds
        detector, results = demo_10x10_analysis(rounds=args.rounds)

        print("\n" + "=" * 70)
        print("ANALYSIS COMPLETE")
        print("=" * 70)
        print(f"Anomaly Detected: {'YES' if results['is_anomaly'] else 'NO'}")
        print(f"Expected Value E(i): {results['expected_value']:.4f}")
        print(f"Standard Deviation STD(i): {results['std_deviation']:.4f}")
        n = args.matrix_size * args.matrix_size  # n = p × v
        print(f"Threshold: {results['threshold']:.4f} (({n}²-1)/12)^0.5")
        print("=" * 70)
        print("\nVisualizations saved as PNG files:")
        print(
            f"- counting_matrix_10x10_{args.rounds}rounds.png (Cumulative counting matrix M)"
        )
        print(
            f"- frequency_heatmap_10x10_{args.rounds}rounds.png (Frequency heatmap f_{{p,v}})"
        )
        print("=" * 70)

    except Exception as e:
        print(f"Error during demo execution: {e}")
        import traceback

        traceback.print_exc()
