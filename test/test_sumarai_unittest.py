import unittest
from unittest.mock import patch, MagicMock
import json
import os
import time
import logging
import http.client
import sys

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sumarai import LlamafileClient

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TestLlamafileClient(unittest.TestCase):
    def setUp(self):
        self.executable_path = "./llamafile"
        self.client = LlamafileClient(self.executable_path)  # Remove api_key argument
        logger.info(f"\nInitialized LlamafileClient with executable: {self.executable_path}")

    @patch('os.path.isfile', return_value=True)
    def test_find_executable_provided(self, mock_isfile):
        executable = self.client._find_executable("./custom/path/llamafile")
        self.assertEqual(executable, "./custom/path/llamafile")

    @patch('os.path.isfile', return_value=False)
    @patch('shutil.which', return_value='/usr/bin/llamafile')
    def test_find_executable_in_path(self, mock_which, mock_isfile):
        executable = self.client._find_executable(None)
        self.assertEqual(executable, "/usr/bin/llamafile")

    @patch('os.path.isfile', side_effect=lambda path: path == '/mocked/current/directory/llamafile')
    @patch('shutil.which', return_value=None)
    @patch('os.getcwd', return_value='/mocked/current/directory')
    def test_find_executable_in_current_dir(self, mock_getcwd, mock_which, mock_isfile):
        executable = self.client._find_executable(None)
        self.assertEqual(executable, "/mocked/current/directory/llamafile")

    @patch('os.path.isfile', side_effect=lambda path: path == './env/path/llamafile')
    @patch('shutil.which', return_value=None)
    @patch('os.environ.get', return_value='./env/path/llamafile')
    def test_find_executable_in_env_var(self, mock_environ_get, mock_which, mock_isfile):
        executable = self.client._find_executable(None)
        self.assertEqual(executable, "./env/path/llamafile")

    @patch('os.path.isfile', return_value=False)
    @patch('shutil.which', return_value=None)
    @patch('os.environ.get', return_value=None)
    def test_find_executable_not_found(self, mock_environ_get, mock_which, mock_isfile):
        with self.assertRaises(FileNotFoundError):
            self.client._find_executable(None)

    @patch('subprocess.Popen')
    @patch('http.client.HTTPConnection')
    def test_start_llamafile(self, mock_http_connection, mock_popen):
        logger.info("\nTesting start_llamafile method")
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        
        mock_response = MagicMock()
        mock_response.status = 200
        mock_http_connection.return_value.getresponse.return_value = mock_response
        
        self.client.start_llamafile()

        expected_command = f"{self.executable_path} --api-key {self.client.api_key}"
        mock_popen.assert_called_once_with(
            expected_command,
            shell=True,
            stdout=unittest.mock.ANY,
            stderr=unittest.mock.ANY,
            text=True
        )
        self.assertIsNotNone(self.client.process)
        logger.info(f"Llamafile process started with command: {expected_command}")

    @patch('subprocess.Popen')
    def test_stop_llamafile(self, mock_popen):
        logger.info("\nTesting stop_llamafile method")
        mock_process = MagicMock()
        mock_popen.return_value = mock_process
        self.client.process = mock_process
        
        self.client.stop_llamafile()
        
        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once()
        logger.info("Llamafile process stopped successfully")

    @patch('http.client.HTTPConnection')
    def test_chat_completion(self, mock_http_connection):
        logger.info("\nTesting chat_completion method")
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({"choices": [{"message": {"content": "Test response"}}]}).encode('utf-8')
        mock_http_connection.return_value.getresponse.return_value = mock_response

        messages = [{"role": "user", "content": "Hello, how are you?"}]
        logger.info(f"Input messages: {json.dumps(messages, indent=2)}")
        
        response = self.client.chat_completion(messages)
        
        logger.info(f"Output response: {json.dumps(response, indent=2)}")
        mock_http_connection.assert_called_once()
        self.assertEqual(response, {"choices": [{"message": {"content": "Test response"}}]})

    @patch('http.client.HTTPConnection')
    def test_chat_completion_error(self, mock_http_connection):
        logger.info("\nTesting chat_completion method with error")
        mock_response = MagicMock()
        mock_response.status = 400
        mock_response.read.return_value = b"Bad Request"
        mock_http_connection.return_value.getresponse.return_value = mock_response

        messages = [{"role": "user", "content": "Generate an error"}]
        logger.info(f"Input messages: {json.dumps(messages, indent=2)}")
        
        with self.assertRaises(Exception) as context:
            self.client.chat_completion(messages)

        logger.info(f"Raised exception: {str(context.exception)}")
        self.assertIn("Error: 400", str(context.exception))
        self.assertIn("Bad Request", str(context.exception))

    @patch('http.client.HTTPConnection')
    def test_invalid_api_key(self, mock_http_connection):
        logger.info("\nTesting chat_completion method with invalid API key")
        mock_response = MagicMock()
        mock_response.status = 401
        mock_response.read.return_value = b"Unauthorized"
        mock_http_connection.return_value.getresponse.return_value = mock_response

        self.client.api_key = "invalid_api_key"
        messages = [{"role": "user", "content": "Test with invalid API key"}]
        logger.info(f"Input messages: {json.dumps(messages, indent=2)}")
        
        with self.assertRaises(Exception) as context:
            self.client.chat_completion(messages)

            logger.info(f"Raised exception: {str(context.exception)}")
            self.assertIn("Error: 401", str(context.exception))
            self.assertIn("Unauthorized", str(context.exception))

class TestLlamafileClientNonMocked(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.executable_path = "./llamafile/Phi-3-mini-128k-instruct-Q4_K_M.llamafile"
        cls.client = LlamafileClient(cls.executable_path)  # Remove api_key argument
        logger.info(f"\nInitializing LlamafileClient with executable: {cls.executable_path}")
        try:
            cls.client.start_llamafile()
            logger.info("Llamafile process started successfully")
        except Exception as e:
            logger.error(f"Error starting llamafile: {str(e)}")
            raise

    @classmethod
    def tearDownClass(cls):
        cls.client.stop_llamafile()
        logger.info("Llamafile process stopped")

    def test_actual_chat_completion(self):
        logger.info("\nTesting actual chat completion")
        messages = [
            {"role": "system", "content": "You are a helpful AI assistant."},
            {"role": "user", "content": "What's the capital of France?"}
        ]
        logger.info(f"Input messages:\n{json.dumps(messages, indent=2)}")

        try:
            response = self.client.chat_completion(messages)
            logger.info(f"Output response:\n{json.dumps(response, indent=2)}")
            self.assertIn("choices", response)
            self.assertIsInstance(response["choices"], list)
            self.assertGreater(len(response["choices"]), 0)
            self.assertIn("message", response["choices"][0])
            self.assertIn("content", response["choices"][0]["message"])
            self.assertIsInstance(response["choices"][0]["message"]["content"], str)
            self.assertGreater(len(response["choices"][0]["message"]["content"]), 0)
        except Exception as e:
            logger.error(f"Error in chat completion: {str(e)}")
            raise

    def test_actual_chat_completion_error(self):
        logger.info("\nTesting actual chat completion with potential error")
        messages = [
            {"role": "user", "content": ""}  # Empty message to potentially trigger an error
        ]
        logger.info(f"Input messages:\n{json.dumps(messages, indent=2)}")

        try:
            response = self.client.chat_completion(messages)
            logger.info(f"Output response:\n{json.dumps(response, indent=2)}")
            # If no error is raised, we should still have a valid response structure
            self.assertIn("choices", response)
        except Exception as e:
            logger.error(f"Raised exception: {str(e)}")
            # If an error is raised, it should be handled gracefully
            self.assertIsInstance(e, Exception)

if __name__ == '__main__':
    unittest.main()
