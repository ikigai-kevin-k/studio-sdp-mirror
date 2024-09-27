import unittest
from unittest.mock import Mock
from src.refactoring.state_machine import SDPStateMachine

class TestStateMachine(unittest.TestCase):

    def setUp(self):
        self.gui = Mock()
        self.state_machine = SDPStateMachine(self.gui)

    def test_serial_data_processing(self):
        # Test Case 1: Serial Data Processing Functionality
        test_data = "ROULETTE_ID_1_DATA_441"
        self.state_machine.update_state(test_data)
        self.assertEqual(self.state_machine.state, test_data)
        self.gui.update_state.assert_called_once_with(test_data)

    def test_state_transition(self):
        # Test Case 2: State Machine Transition
        initial_state = "IDLE"
        new_state = "PROCESSING"
        self.assertEqual(self.state_machine.state, initial_state)
        self.state_machine.update_state(new_state)
        self.assertEqual(self.state_machine.state, new_state)
        self.gui.update_state.assert_called_once_with(new_state)
