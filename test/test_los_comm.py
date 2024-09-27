import unittest
from unittest.mock import Mock, patch
from src.refactoring.communication.los_communication import LOSCommunication

class TestLOSCommunication(unittest.TestCase):

    def setUp(self):
        self.state_machine = Mock()
        self.roulette_comm = Mock()
        self.los_comm = LOSCommunication(self.state_machine, self.roulette_comm)

    def test_http_communication(self):
        # Test Case 1: Check HTTP communication OK
        mock_processor = Mock()
        self.los_comm.add_processor(mock_processor)
        
        self.los_comm.handle_http_request("test_request")
        
        mock_processor.handle_http_request.assert_called_once_with("test_request")

    def test_websocket_communication(self):
        # Test Case 2: Check WebSocket Communication OK
        mock_processor = Mock()
        self.los_comm.add_processor(mock_processor)
        
        self.los_comm.handle_websocket_message("test_message")
        
        mock_processor.handle_websocket_message.assert_called_once_with("test_message")

    def test_receive_game_parameters(self):
        # Test Case 3: Receive Game Parameters Settings Command from LOS
        test_command = "SET_GAME_PARAMS:min_bet=1:max_bet=100"
        self.los_comm.command_queue.put(test_command)
        
        mock_processor = Mock()
        self.los_comm.add_processor(mock_processor)
        
        # only execute once loop
        self.los_comm.process_commands()
        
        mock_processor.process_data.assert_called_once()