import pytest
from unittest.mock import patch, MagicMock, call
import sys
import os
import json

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sumarai import LlamafileClient, interactive_shell, main

@pytest.fixture
def mock_client():
    return MagicMock(spec=LlamafileClient)

def create_stream_response(content):
    response = MagicMock()
    response.__iter__.return_value = [
        f'data: {json.dumps({"choices": [{"delta": {"content": chunk}}]})}\n\n'.encode('utf-8')
        for chunk in content.split()
    ] + [f'data: {json.dumps({"choices": [{"finish_reason": "stop"}]})}\n\n'.encode('utf-8')]
    return response

@pytest.fixture
def default_prompt():
    return "You are a helpful AI assistant. Respond to the user's queries concisely and accurately."

@patch('builtins.input')
@patch('builtins.print')
def test_interactive_shell_exit(mock_print, mock_input, mock_client, default_prompt):
    mock_input.return_value = 'exit'
    interactive_shell(mock_client, default_prompt)
    mock_client.chat_completion.assert_not_called()
    mock_print.assert_any_call("Exiting interactive shell.")

@patch('builtins.input')
@patch('builtins.print')
def test_interactive_shell_single_interaction(mock_print, mock_input, mock_client, default_prompt):
    mock_input.side_effect = ['Hello, AI!', 'exit']
    mock_client.chat_completion.return_value = create_stream_response("Hello, human! How can I assist you today?")

    interactive_shell(mock_client, default_prompt)

    mock_client.chat_completion.assert_called_once()
    expected_calls = [
        call('AI: ', end='', flush=True),
    ] + [
        call(word, end='', flush=True)
        for word in "Hello, human! How can I assist you today?".split()
    ] + [call()]  # for the newline after response
    mock_print.assert_has_calls(expected_calls, any_order=False)

@patch('builtins.input')
@patch('builtins.print')
def test_interactive_shell_multiple_interactions(mock_print, mock_input, mock_client, default_prompt):
    mock_input.side_effect = ['First question', 'Second question', 'exit']
    mock_client.chat_completion.side_effect = [
        create_stream_response("First answer"),
        create_stream_response("Second answer")
    ]

    interactive_shell(mock_client, default_prompt)

    assert mock_client.chat_completion.call_count == 2
    expected_calls = [
        call('AI: ', end='', flush=True),
        call('First', end='', flush=True),
        call('answer', end='', flush=True),
        call(),
        call('AI: ', end='', flush=True),
        call('Second', end='', flush=True),
        call('answer', end='', flush=True),
        call()
    ]
    mock_print.assert_has_calls(expected_calls, any_order=False)

@patch('builtins.input')
@patch('builtins.print')
def test_interactive_shell_error_handling(mock_print, mock_input, mock_client, default_prompt):
    mock_input.side_effect = ['Trigger error', 'exit']
    mock_client.chat_completion.side_effect = Exception('API Error')

    interactive_shell(mock_client, default_prompt)

    mock_client.chat_completion.assert_called_once()
    mock_print.assert_any_call('An error occurred: API Error')

@patch('sys.exit')
@patch('logging.getLogger')
@patch('argparse.ArgumentParser.parse_args')
def test_main_nonexistent_llamafile(mock_parse_args, mock_get_logger, mock_exit):
    # Mocking command-line arguments
    mock_args = MagicMock()
    mock_args.llamafile = '/nonexistent/path/to/llamafile'
    mock_args.debug = False
    mock_args.stop = False
    mock_args.status = False
    mock_args.service = False
    mock_args.files = []
    mock_parse_args.return_value = mock_args

    # Mocking logger
    mock_logger = MagicMock()
    mock_get_logger.return_value = mock_logger

    # Call the main function
    main()

    # Assert that the error was logged and the program exited
    mock_logger.error.assert_called_with("Error: Specified executable path /nonexistent/path/to/llamafile not found or not executable.")
    mock_exit.assert_called_with(1)

if __name__ == '__main__':
    pytest.main()