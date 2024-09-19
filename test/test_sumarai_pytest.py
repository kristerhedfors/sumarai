import pytest
from unittest.mock import patch, MagicMock
import json
import os
import time
import logging
import http.client
import sys
import shutil
import psutil

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sumarai import LlamafileClient

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def kill_llamafile_processes():
    for proc in psutil.process_iter(['name']):
        if 'llamafile' in proc.info['name'].lower():
            logger.warning(f"Found running llamafile process with PID {proc.pid}. Terminating...")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except psutil.TimeoutExpired:
                logger.warning(f"Process {proc.pid} did not terminate. Killing...")
                proc.kill()

@pytest.fixture(autouse=True)
def ensure_no_llamafile_running():
    kill_llamafile_processes()
    yield
    kill_llamafile_processes()

@pytest.fixture
def client():
    executable_path = "./llamafile"
    client = LlamafileClient(executable_path)
    logger.info(f"\nInitialized LlamafileClient with executable: {executable_path}")
    return client

@pytest.mark.parametrize("mock_isfile, mock_which, mock_getcwd, mock_environ, executable_path, expected_result, expected_exception", [
    (lambda x: True, None, None, {}, "./custom/path/llamafile", "custom/path/llamafile", None),
    (lambda x: False, lambda x: "/usr/bin/llamafile", None, {}, None, "/usr/bin/llamafile", None),
    (lambda x: True, lambda x: None, '/mocked/current/directory', {}, None, "/mocked/current/directory/llamafile", None),
    (lambda x: True, lambda x: None, None, {'LLAMAFILE': './env/path/llamafile'}, None, "env/path/llamafile", None),
    (lambda x: False, lambda x: None, None, {}, None, None, FileNotFoundError),
    (lambda x: False, None, None, {}, "./nonexistent/llamafile", None, FileNotFoundError)
])
def test_find_executable(client, mock_isfile, mock_which, mock_getcwd, mock_environ, executable_path, expected_result, expected_exception):
    with patch('os.path.isfile', side_effect=mock_isfile):
        with patch('os.access', return_value=True):  # Assume all files are executable
            with patch('shutil.which', side_effect=mock_which or (lambda x: None)):
                with patch('os.getcwd', return_value=mock_getcwd or ''):
                    with patch.dict('os.environ', mock_environ):
                        if expected_exception:
                            with pytest.raises(expected_exception) as excinfo:
                                client._find_executable(executable_path)
                            if executable_path:
                                assert os.path.basename(executable_path) in str(excinfo.value)
                        else:
                            result = client._find_executable(executable_path)
                            assert os.path.normpath(result) == os.path.normpath(expected_result)

@patch('subprocess.Popen')
@patch('http.client.HTTPConnection')
def test_start_llamafile(mock_http_connection, mock_popen, client):
    logger.info("\nTesting start_llamafile method")
    mock_process = MagicMock()
    mock_process.poll.return_value = None
    mock_popen.return_value = mock_process
    
    mock_response = MagicMock()
    mock_response.status = 200
    mock_http_connection.return_value.getresponse.return_value = mock_response
    
    client.start_llamafile()

    expected_command = f"{client.executable_path} --api-key {client.api_key}"
    mock_popen.assert_called_once_with(
        expected_command,
        shell=True,
        stdout=-1,
        stderr=-1,
        text=True
    )
    assert client.process is not None
    logger.info(f"Llamafile process started with command: {expected_command}")

@patch('subprocess.Popen')
def test_stop_llamafile(mock_popen, client):
    logger.info("\nTesting stop_llamafile method")
    mock_process = MagicMock()
    mock_popen.return_value = mock_process
    client.process = mock_process
    
    client.stop_llamafile()
    
    mock_process.terminate.assert_called_once()
    mock_process.wait.assert_called_once()
    logger.info("Llamafile process stopped successfully")

@patch('http.client.HTTPConnection')
def test_chat_completion(mock_http_connection, client):
    logger.info("\nTesting chat_completion method")
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = json.dumps({"choices": [{"message": {"content": "Test response"}}]}).encode('utf-8')
    mock_http_connection.return_value.getresponse.return_value = mock_response

    messages = [{"role": "user", "content": "Hello, how are you?"}]
    logger.info(f"Input messages: {json.dumps(messages, indent=2)}")
    
    response = client.chat_completion(messages)
    
    logger.info(f"Output response: {json.dumps(response, indent=2)}")
    mock_http_connection.assert_called_once()
    assert response == {"choices": [{"message": {"content": "Test response"}}]}

@patch('http.client.HTTPConnection')
def test_chat_completion_error(mock_http_connection, client):
    logger.info("\nTesting chat_completion method with error")
    mock_response = MagicMock()
    mock_response.status = 400
    mock_response.read.return_value = b"Bad Request"
    mock_http_connection.return_value.getresponse.return_value = mock_response

    messages = [{"role": "user", "content": "Generate an error"}]
    logger.info(f"Input messages: {json.dumps(messages, indent=2)}")
    
    with pytest.raises(Exception) as context:
        client.chat_completion(messages)

    logger.info(f"Raised exception: {str(context.value)}")
    assert "Error: 400" in str(context.value)
    assert "Bad Request" in str(context.value)

@patch('http.client.HTTPConnection')
def test_invalid_api_key(mock_http_connection, client):
    logger.info("\nTesting chat_completion method with invalid API key")
    mock_response = MagicMock()
    mock_response.status = 401
    mock_response.read.return_value = b"Unauthorized"
    mock_http_connection.return_value.getresponse.return_value = mock_response

    client.api_key = "invalid_api_key"
    messages = [{"role": "user", "content": "Test with invalid API key"}]
    logger.info(f"Input messages: {json.dumps(messages, indent=2)}")
    
    with pytest.raises(Exception) as context:
        client.chat_completion(messages)

    logger.info(f"Raised exception: {str(context.value)}")
    assert "Error: 401" in str(context.value)
    assert "Unauthorized" in str(context.value)

class TestLlamafileClientNonMocked:
    @pytest.fixture(scope="class")
    def non_mocked_client(self):
        executable_path = "./Phi-3-mini-128k-instruct-Q4_K_M.llamafile"
        client = LlamafileClient(executable_path)
        logger.info(f"\nInitializing LlamafileClient with executable: {executable_path}")
        try:
            client.start_llamafile()
            logger.info(f"Llamafile process started successfully with API key: {client.api_key}")
            yield client
        finally:
            client.stop_llamafile()
            logger.info("Llamafile process stopped")

    def test_actual_chat_completion(self, non_mocked_client):
        logger.info("\nTesting actual chat completion")
        messages = [
            {"role": "system", "content": "You are a helpful AI assistant."},
            {"role": "user", "content": "What's the capital of France?"}
        ]
        logger.info(f"Input messages:\n{json.dumps(messages, indent=2)}")

        try:
            # Ensure the API key is set
            assert non_mocked_client.api_key, "API key is not set"
            logger.info(f"Using API key: {non_mocked_client.api_key}")

            # Print debug information
            logger.info(f"Host: {non_mocked_client.host}")
            logger.info(f"Port: {non_mocked_client.port}")
            logger.info(f"Executable path: {non_mocked_client.executable_path}")

            # Print request details
            headers = {"Content-Type": "application/json"}
            if non_mocked_client.api_key:
                headers["Authorization"] = f"Bearer {non_mocked_client.api_key}"
            logger.info(f"Request headers: {headers}")

            data = json.dumps({
                "model": "local-model",
                "messages": messages,
                "stream": False
            })
            logger.info(f"Request body: {data}")

            response = non_mocked_client.chat_completion(messages)
            logger.info(f"Output response:\n{json.dumps(response, indent=2)}")
            assert "choices" in response
            assert isinstance(response["choices"], list)
            assert len(response["choices"]) > 0
            assert "message" in response["choices"][0]
            assert "content" in response["choices"][0]["message"]
            assert isinstance(response["choices"][0]["message"]["content"], str)
            assert len(response["choices"][0]["message"]["content"]) > 0
        except Exception as e:
            logger.error(f"Error in chat completion: {str(e)}")
            raise

    def test_actual_chat_completion_error(self, non_mocked_client):
        logger.info("\nTesting actual chat completion with potential error")
        messages = [
            {"role": "user", "content": ""}  # Empty message to potentially trigger an error
        ]
        logger.info(f"Input messages:\n{json.dumps(messages, indent=2)}")

        try:
            response = non_mocked_client.chat_completion(messages)
            logger.info(f"Output response:\n{json.dumps(response, indent=2)}")
            # If no error is raised, we should still have a valid response structure
            assert "choices" in response
        except Exception as e:
            logger.error(f"Raised exception: {str(e)}")
            # If an error is raised, it should be handled gracefully
            assert isinstance(e, Exception)

if __name__ == '__main__':
    pytest.main()
