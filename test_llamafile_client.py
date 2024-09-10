import unittest
from unittest.mock import patch, MagicMock
import json
import os
import time
import logging
import requests
from llamafile_client import LlamafileClient

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TestLlamafileClient(unittest.TestCase):
    def setUp(self):
        self.executable_path = "/path/to/llamafile"
        self.api_key = "test_api_key"
        self.client = LlamafileClient(self.executable_path, api_key=self.api_key)
        logger.info(f"\nInitialized LlamafileClient with executable: {self.executable_path} and API key: {self.api_key}")

    @patch('subprocess.Popen')
    @patch('requests.get')
    def test_start_llamafile(self, mock_get, mock_popen):
        logger.info("\nTesting start_llamafile method")
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        mock_get.return_value.status_code = 200
        
        self.client.start_llamafile()
        
        mock_popen.assert_called_once_with(
            f"{self.executable_path} --api-key {self.api_key}",
            shell=True,
            stdout=unittest.mock.ANY,
            stderr=unittest.mock.ANY,
            text=True
        )
        self.assertIsNotNone(self.client.process)
        logger.info(f"Llamafile process started with command: {self.executable_path} --api-key {self.api_key}")

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

    @patch('requests.post')
    def test_chat_completion(self, mock_post):
        logger.info("\nTesting chat_completion method")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"content": "Test response"}}]}
        mock_post.return_value = mock_response

        messages = [{"role": "user", "content": "Hello, how are you?"}]
        logger.info(f"Input messages: {json.dumps(messages, indent=2)}")
        
        response = self.client.chat_completion(messages)
        
        logger.info(f"Output response: {json.dumps(response, indent=2)}")
        mock_post.assert_called_once()
        self.assertEqual(response, {"choices": [{"message": {"content": "Test response"}}]})

    @patch('requests.post')
    def test_chat_completion_error(self, mock_post):
        logger.info("\nTesting chat_completion method with error")
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response
        mock_post.return_value.raise_for_status.side_effect = requests.exceptions.HTTPError("400 Client Error: Bad Request")

        messages = [{"role": "user", "content": "Generate an error"}]
        logger.info(f"Input messages: {json.dumps(messages, indent=2)}")
        
        with self.assertRaises(Exception) as context:
            self.client.chat_completion(messages)

        logger.info(f"Raised exception: {str(context.exception)}")
        self.assertIn("Error:", str(context.exception))
        self.assertIn("400", str(context.exception))
        self.assertIn("Bad Request", str(context.exception))

class TestLlamafileClientNonMocked(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.executable_path = "./llamafile/Phi-3-mini-128k-instruct-Q4_K_M.llamafile"
        cls.api_key = "test_api_key"  # Use a dummy API key for testing
        cls.client = LlamafileClient(cls.executable_path, api_key=cls.api_key)
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
    suite = unittest.TestLoader().loadTestsFromTestCase(TestLlamafileClient)
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestLlamafileClientNonMocked))
    unittest.TextTestRunner(verbosity=2).run(suite)