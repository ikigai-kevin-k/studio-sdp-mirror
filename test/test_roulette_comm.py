import unittest
from unittest.mock import Mock, patch
from src.refactoring.communication.roulette_communication import RouletteCommunication

class TestRouletteCommunication(unittest.TestCase):

    def setUp(self):
        self.state_machine = Mock()
        self.los_comm = Mock()
        self.roulette_comm = RouletteCommunication(self.state_machine, self.los_comm)

    @patch('serial.Serial')
    def test_serial_port_communication(self, mock_serial):
        # Test Case 1: Check Serial Port Communication OK
        self.roulette_comm.initialize_serial()
        mock_serial.assert_called_once()
        self.assertIsNotNone(self.roulette_comm.serial_port)

    def test_get_polling_results(self):
        # Test Case 2: Get Roulette Polling Results
        test_result = "*X:1:400:25:0:441:0"
        self.roulette_comm.polling_results.put(test_result)
        with patch.object(self.roulette_comm, 'parse_result') as mock_parse:
            self.roulette_comm.process_polling_results()
            mock_parse.assert_called_once_with(test_result)
            self.state_machine.update_state.assert_called_once()
