import unittest
from unittest.mock import Mock, patch
from src.refactoring.main import main
from src.refactoring.communication.los_communication import LOSCommunication
from src.refactoring.communication.roulette_communication import RouletteCommunication

class TestIntegration(unittest.TestCase):

    @patch('src.refactoring.main.GUI')
    @patch('src.refactoring.main.SDPStateMachine')
    @patch('src.refactoring.main.RouletteCommunication')
    @patch('src.refactoring.main.LOSCommunication')
    def test_los_to_roulette_communication(self, mock_los, mock_roulette, mock_state, mock_gui):
        # Test Scenario 1
        # LOS sends Game Parameters Settings Command to SDP via HTTP, and SDP forwards the command to Roulette via Serial Port.
        # The roulette then changes its game parameters accordingly. 
        # The roulette then sends the Polling Results back to SDP via Serial Port, and SDP forwards the results to LOS via HTTP.

        # Setup mocks
        mock_los_instance = Mock(spec=LOSCommunication)
        mock_roulette_instance = Mock(spec=RouletteCommunication)
        mock_los.return_value = mock_los_instance
        mock_roulette.return_value = mock_roulette_instance

        # Run main function
        main()

        # Simulate LOS sending command
        test_command = "SET_GAME_PARAMS:min_bet=1:max_bet=100"
        mock_los_instance.handle_http_request(test_command)

        # Check if command was forwarded to Roulette
        mock_roulette_instance.send_command.assert_called_once_with(test_command)

        # Simulate Roulette sending polling results
        test_result = "*X:1:400:25:0:441:0"
        mock_roulette_instance.polling_results.put(test_result)
        mock_roulette_instance.process_polling_results()

        # Check if results were forwarded to LOS
        mock_los_instance.handle_http_request.assert_called_with(test_result)

        # Check if state was updated
        mock_state.return_value.update_state.assert_called()

        # Check if GUI was updated
        mock_gui.return_value.add_message.assert_called()
