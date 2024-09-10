import argparse
import requests
import subprocess
import time
import atexit
import json
import os
import logging
from requests.exceptions import RequestException

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class LlamafileClient:
    def __init__(self, executable_path, api_key=None, host="http://localhost", port=8080):
        self.executable_path = executable_path
        self.api_key = api_key
        self.base_url = f"{host}:{port}"
        self.process = None

    def start_llamafile(self):
        cmd = f"{self.executable_path}"
        if self.api_key:
            cmd += f" --api-key {self.api_key}"
        logger.debug(f"Starting llamafile with command: {cmd}")
        try:
            self.process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            atexit.register(self.stop_llamafile)
            logger.debug("Waiting for llamafile to start...")
            self._wait_for_server()
            logger.debug("Llamafile started successfully")
        except Exception as e:
            logger.exception("Error starting llamafile")
            raise

    def _wait_for_server(self, timeout=60, check_interval=1):
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{self.base_url}/v1/models")
                if response.status_code == 200:
                    logger.debug("Server is ready")
                    return
            except RequestException:
                pass
            
            if self.process.poll() is not None:
                stdout, stderr = self.process.communicate()
                logger.error(f"Llamafile process exited unexpectedly. Exit code: {self.process.returncode}")
                logger.error(f"stdout: {stdout}")
                logger.error(f"stderr: {stderr}")
                raise Exception("Llamafile failed to start")
            
            time.sleep(check_interval)
        
        raise TimeoutError("Server did not become ready within the timeout period")

    def stop_llamafile(self):
        if self.process:
            logger.debug("Stopping llamafile process")
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logger.warning("Llamafile process did not terminate, forcing kill")
                self.process.kill()
            logger.debug("Llamafile process stopped")

    def chat_completion(self, messages, model="local-model"):
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        data = {
            "model": model,
            "messages": messages
        }

        logger.debug(f"Sending chat completion request to {self.base_url}/v1/chat/completions")
        try:
            response = requests.post(f"{self.base_url}/v1/chat/completions", 
                                     headers=headers, 
                                     json=data,
                                     timeout=30)
            response.raise_for_status()
            return response.json()
        except RequestException as e:
            logger.error(f"Error in chat completion request: {str(e)}")
            raise Exception(f"Error: {e.response.status_code if e.response else 'No response'}, {e.response.text if e.response else str(e)}")

def main():
    parser = argparse.ArgumentParser(description="Llamafile API Client")
    parser.add_argument("--executable", required=True, help="Path to the llamafile executable")
    parser.add_argument("--api-key", help="API key for authentication (optional)")
    parser.add_argument("--message", required=True, help="Message to send to the API")
    args = parser.parse_args()

    client = LlamafileClient(args.executable, api_key=args.api_key)
    client.start_llamafile()

    try:
        messages = [{"role": "user", "content": args.message}]
        response = client.chat_completion(messages)
        print(json.dumps(response, indent=2))
    except Exception as e:
        logger.exception("An error occurred")
    finally:
        client.stop_llamafile()

if __name__ == "__main__":
    main()