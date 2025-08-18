#!/usr/bin/env python3
"""
Test file for Git hooks
This file is used to test the pre-commit and pre-push hooks
"""


def hello_world():
    """Simple function to test hooks"""
    message = "Hello, World!"
    print(message)
    return message


def calculate_sum(a, b):
    """Calculate sum of two numbers"""
    result = a + b
    return result


if __name__ == "__main__":
    hello_world()
    print(f"Sum: {calculate_sum(5, 3)}")
