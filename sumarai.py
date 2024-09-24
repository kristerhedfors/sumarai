#!/usr/bin/env python3
import logging
import argparse
import subprocess
import time
import atexit
import json
import os
import http.client
import shutil
import secrets
import sys
import signal
import re
from urllib.parse import urlparse

def clean_content(content):
    """
    Removes specific tags from the content.

    Args:
        content (str): The original content containing tags.

    Returns:
        str: The cleaned content without the specified tags.
    """
    # Define the patterns for tags you want to remove
    tags_to_remove = [
        r'<\|eot_id\|>',       # Specific tag to remove
        # Add more tags here as needed, e.g., r'<\|another_tag\|>'
    ]

    # Iterate over each tag pattern and remove it from the content
    for tag in tags_to_remove:
        content = re.sub(tag, '', content)

    return content


def configure_logging(debug_enabled):
    level = logging.DEBUG if debug_enabled else logging.INFO
    logging.basicConfig(level=level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class APIClient:
    """
    Abstract base class for API clients.
    """
    def chat_completion(self, messages, stream=False):
        raise NotImplementedError("Subclasses should implement this method.")

    def get_info(self):
        raise NotImplementedError("Subclasses should implement this method.")


class OpenAIClient(APIClient):
    """
    Client for OpenAI's Chat Completion API.
    """
    def __init__(self, api_key, model):
        self.logger = logging.getLogger(__name__)
        self.api_key = api_key
        self.model = model
        self.api_url = "https://api.openai.com/v1/chat/completions"

    def chat_completion(self, messages, stream=False):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        data = {
            "model": self.model,
            "messages": messages,
            "stream": stream
        }

        body = json.dumps(data)

        parsed_url = urlparse(self.api_url)
        conn = http.client.HTTPSConnection(parsed_url.hostname, parsed_url.port or 443, timeout=60)

        self.logger.debug(f"Sending chat completion request to {self.api_url}")
        self.logger.debug(f"Request headers: {headers}")
        self.logger.debug(f"Request body: {body}")

        try:
            conn.request("POST", parsed_url.path, body=body, headers=headers)
            response = conn.getresponse()

            if response.status != 200:
                error_response = response.read().decode('utf-8')
                raise Exception(f"Error: {response.status}, {error_response}")

            if stream:
                return response
            else:
                response_data = response.read().decode('utf-8')
                self.logger.debug(f"Response status: {response.status}")
                self.logger.debug(f"Response body: {response_data}")
                return json.loads(response_data)
        except Exception as e:
            self.logger.error(f"Error in OpenAI chat completion request: {str(e)}")
            raise
        finally:
            if not stream:
                conn.close()

    def get_info(self):
        # OpenAI API does not have a direct endpoint for model info in this context.
        # We'll return basic info.
        return {
            "api_type": "OpenAI",
            "model": self.model,
            "status": "Available",
            "api_url": self.api_url
        }


class LlamafileClient(APIClient):
    LLAMAFILE_DIR = os.path.join(os.path.expanduser("~"), ".llamafile")
    PID_FILE = os.path.join(LLAMAFILE_DIR, "llamafile.pid")
    API_KEY_FILE = os.path.join(LLAMAFILE_DIR, "api_key")

    def __init__(self, executable_path=None, api_key=None, host="localhost", port=8080, service_mode=False):
        self.logger = logging.getLogger(__name__)
        self.executable_path = self._find_executable(executable_path)
        self.service_mode = service_mode

        self.host = host
        self.port = port
        self.process = None

        if api_key:
            self.api_key = api_key
        elif os.path.exists(self.API_KEY_FILE):
            with open(self.API_KEY_FILE, 'r') as f:
                self.api_key = f.read().strip()
        else:
            self.api_key = secrets.token_hex(16)

    def _find_executable(self, executable_path):
        self.logger.debug("Starting search for llamafile executable")
        self.logger.debug(f"LLAMAFILE environment variable: {os.environ.get('LLAMAFILE')}")
        self.logger.debug(f"LLAMAFILE_PATH environment variable: {os.environ.get('LLAMAFILE_PATH')}")

        if executable_path:
            self.logger.debug(f"Checking specified executable path: {executable_path}")
            abs_path = os.path.abspath(executable_path)
            self.logger.debug(f"Absolute path: {abs_path}")
            if os.path.isfile(abs_path) and os.access(abs_path, os.X_OK):
                self.logger.debug(f"Using specified executable path: {abs_path}")
                return abs_path
            raise FileNotFoundError(f"Specified executable path {abs_path} not found or not executable.")

        self.logger.debug("Searching for llamafile in PATH")
        path_executable = shutil.which('llamafile')
        if path_executable:
            self.logger.debug(f"Found llamafile in PATH: {path_executable}")
            return path_executable
        self.logger.debug("llamafile not found in PATH")

        env_executable = os.environ.get('LLAMAFILE')
        if env_executable:
            self.logger.debug(f"Checking LLAMAFILE: {env_executable}")
            abs_path = os.path.abspath(env_executable)
            if os.path.isfile(abs_path) and os.access(abs_path, os.X_OK):
                self.logger.debug(f"Using llamafile from LLAMAFILE: {abs_path}")
                return abs_path
            else:
                self.logger.warning(f"LLAMAFILE set but file not found or not executable: {abs_path}")
        else:
            self.logger.debug("LLAMAFILE environment variable not set")

        env_executable = os.environ.get('LLAMAFILE_PATH')
        if env_executable:
            self.logger.debug(f"Checking LLAMAFILE_PATH: {env_executable}")
            abs_path = os.path.abspath(env_executable)
            if os.path.isfile(abs_path) and os.access(abs_path, os.X_OK):
                self.logger.debug(f"Using llamafile from LLAMAFILE_PATH: {abs_path}")
                return abs_path
            else:
                self.logger.warning(f"LLAMAFILE_PATH set but file not found or not executable: {abs_path}")
        else:
            self.logger.debug("LLAMAFILE_PATH environment variable not set")

        current_dir = os.getcwd()
        self.logger.debug(f"Searching for llamafile in current directory: {current_dir}")
        current_dir_executable = os.path.join(current_dir, 'llamafile')
        if os.path.isfile(current_dir_executable) and os.access(current_dir_executable, os.X_OK):
            self.logger.debug(f"Using llamafile from current directory: {current_dir_executable}")
            return current_dir_executable
        self.logger.debug("llamafile not found in current directory")

        self.logger.error("Llamafile executable not found in PATH, current directory, or environment variables.")
        raise FileNotFoundError("Llamafile executable not found.")

    def start_llamafile(self, daemon=False):
        if not self.executable_path:
            raise FileNotFoundError("Llamafile executable not found.")

        # Check if the service is already running
        if os.path.exists(self.PID_FILE):
            with open(self.PID_FILE, 'r') as f:
                pid = int(f.read())
            try:
                os.kill(pid, 0)  # Check if process is running
                self.logger.info("Llamafile service is already running with pid %d", pid)
                return
            except OSError:
                self.logger.warning("Stale pid-file found. Removing it.")
                os.remove(self.PID_FILE)

        cmd = f"{self.executable_path} --api-key {self.api_key}"
        self.logger.debug(f"Starting llamafile with command: {cmd}")
        try:
            if daemon and self.service_mode:
                self._start_daemon(cmd)
            else:
                self.process = subprocess.Popen(
                    cmd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                atexit.register(self.stop_llamafile)
                self.logger.debug("Waiting for llamafile to start...")
                self._wait_for_server()
                self.logger.debug("Llamafile started successfully")
        except Exception as e:
            self.logger.exception("Error starting llamafile")
            raise

    def _start_daemon(self, cmd):
        # Create the LLAMAFILE_DIR if it doesn't exist
        if self.service_mode:
            if not os.path.exists(self.LLAMAFILE_DIR):
                os.makedirs(self.LLAMAFILE_DIR, exist_ok=True)

        pid = os.fork()
        if pid > 0:
            os._exit(0)  # Exit first parent

        os.chdir("/")
        os.setsid()
        os.umask(0)

        pid = os.fork()  # Do second fork
        if pid > 0:
            os._exit(0)  # Exit from second parent

        sys.stdout.flush()
        sys.stderr.flush()

        with open('/dev/null', 'rb', 0) as f:
            os.dup2(f.fileno(), sys.stdin.fileno())
        with open('/dev/null', 'ab', 0) as f:
            os.dup2(f.fileno(), sys.stdout.fileno())
            os.dup2(f.fileno(), sys.stderr.fileno())

        # Start the process
        self.process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if self.service_mode:
            # Write the pid-file
            with open(self.PID_FILE, 'w') as f:
                f.write(str(self.process.pid))

            # Write the API key file with mode 0600
            with open(self.API_KEY_FILE, 'w') as f:
                f.write(self.api_key)
            os.chmod(self.API_KEY_FILE, 0o600)

        self.logger.debug("Daemon process started")

        # Wait for the process to exit
        self.process.wait()

        # Clean up the pid-file and API key file
        if self.service_mode:
            if os.path.exists(self.PID_FILE):
                os.remove(self.PID_FILE)
            if os.path.exists(self.API_KEY_FILE):
                os.remove(self.API_KEY_FILE)

    def _wait_for_server(self, timeout=60, check_interval=1):
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                conn = http.client.HTTPConnection(self.host, self.port, timeout=5)
                conn.request("GET", "/v1/models")
                response = conn.getresponse()
                if response.status == 200:
                    self.logger.debug("Server is ready")
                    conn.close()
                    return
            except Exception as e:
                pass
            finally:
                try:
                    conn.close()
                except Exception:
                    pass

            if self.process and self.process.poll() is not None:
                stdout, stderr = self.process.communicate()
                self.logger.error(f"Llamafile process exited unexpectedly. Exit code: {self.process.returncode}")
                self.logger.error(f"stdout: {stdout}")
                self.logger.error(f"stderr: {stderr}")
                raise Exception("Llamafile failed to start")

            time.sleep(check_interval)

        raise TimeoutError("Server did not become ready within the timeout period")

    def stop_llamafile(self):
        if self.process:
            self.logger.debug("Stopping llamafile process")
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.logger.warning("Llamafile process did not terminate, forcing kill")
                self.process.kill()
            self.logger.debug("Llamafile process stopped")
        else:
            if os.path.exists(self.PID_FILE):
                with open(self.PID_FILE, 'r') as f:
                    pid = int(f.read())
                try:
                    os.kill(pid, signal.SIGTERM)
                    self.logger.debug("Sent SIGTERM to process with pid %d", pid)
                except ProcessLookupError:
                    self.logger.warning("Process with pid %d not found", pid)
                # Remove pid-file and API key file
                if self.service_mode:
                    if os.path.exists(self.PID_FILE):
                        os.remove(self.PID_FILE)
                    if os.path.exists(self.API_KEY_FILE):
                        os.remove(self.API_KEY_FILE)
            else:
                self.logger.warning("Pid-file not found. Is the service running?")

    def chat_completion(self, messages, model=None, stream=False):
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        # Use the provided model or fallback to the client's model
        selected_model = model if model else "local-model"

        data = json.dumps({
            "model": selected_model,
            "messages": messages,
            "stream": stream
        }).encode('utf-8')

        self.logger.debug(f"Sending chat completion request to {self.host}:{self.port}/v1/chat/completions")
        self.logger.debug(f"Request headers: {headers}")
        self.logger.debug(f"Request body: {data}")

        try:
            conn = http.client.HTTPConnection(self.host, self.port, timeout=60)
            conn.request("POST", "/v1/chat/completions", body=data, headers=headers)
            response = conn.getresponse()

            if response.status != 200:
                error_response = response.read().decode('utf-8')
                raise Exception(f"Error: {response.status}, {error_response}")

            if stream:
                return response
            else:
                response_data = response.read().decode('utf-8')
                self.logger.debug(f"Response status: {response.status}")
                self.logger.debug(f"Response body: {response_data}")
                return json.loads(response_data)
        except Exception as e:
            self.logger.error(f"Error in chat completion request: {str(e)}")
            raise
        finally:
            if not stream:
                conn.close()

    def get_info(self):
        try:
            conn = http.client.HTTPConnection(self.host, self.port, timeout=5)
            conn.request("GET", "/v1/models")
            response = conn.getresponse()
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                model_info = data.get('data', [{}])[0]
                return {
                    "api_type": "Llamafile",
                    "model": model_info.get('id', 'Unknown'),
                    "status": "Running",
                    "executable_path": self.executable_path,
                    "host": self.host,
                    "port": self.port
                }
            else:
                return {
                    "api_type": "Llamafile",
                    "status": "Not Running",
                    "executable_path": self.executable_path,
                    "host": self.host,
                    "port": self.port
                }
        except Exception as e:
            return {
                "api_type": "Llamafile",
                "status": f"Error: {str(e)}",
                "executable_path": self.executable_path,
                "host": self.host,
                "port": self.port
            }
        finally:
            try:
                conn.close()
            except Exception:
                pass


class OllamaClient(APIClient):
    def __init__(self, model, host="localhost", port=11434):  # Updated port
        self.logger = logging.getLogger(__name__)
        self.model = model
        self.host = host
        self.port = port

    def _check_model_exists(self):
        """
        Check if the specified model exists in the Ollama service's model registry.
        """
        self.logger.debug(f"Checking if model '{self.model}' exists in Ollama service")
        try:
            conn = http.client.HTTPConnection(self.host, self.port, timeout=5)
            conn.request("GET", "/v1/models")
            response = conn.getresponse()

            if response.status != 200:
                raise Exception(f"Failed to retrieve models. Status: {response.status}")

            data = json.loads(response.read())
            models = data.get("data", [])  # Updated key from 'models' to 'data'

            # Log the entire response for debugging
            self.logger.debug(f"Full response from /v1/models: {data}")

            # Extract model IDs
            if isinstance(models, list):
                model_names = [model.get("id") for model in models if "id" in model]
                self.logger.debug(f"Extracted model names: {model_names}")

                if self.model not in model_names:
                    raise ValueError(f"Model '{self.model}' does not exist in Ollama service.")
            else:
                self.logger.error("Unexpected format for models data.")
                raise Exception("Unexpected format for models data.")

            self.logger.debug(f"Model '{self.model}' exists in Ollama service")
        except Exception as e:
            self.logger.error(f"Error checking model existence: {str(e)}")
            raise
        finally:
            conn.close()

    def chat_completion(self, messages, stream=False):
        headers = {"Content-Type": "application/json"}

        data = json.dumps({
            "model": self.model,
            "messages": messages,
            "stream": stream
        }).encode('utf-8')

        self.logger.debug(f"Sending chat completion request to {self.host}:{self.port}/v1/chat/completions")
        self.logger.debug(f"Request headers: {headers}")
        self.logger.debug(f"Request body: {data}")

        try:
            conn = http.client.HTTPConnection(self.host, self.port, timeout=60)
            conn.request("POST", "/v1/chat/completions", body=data, headers=headers)
            response = conn.getresponse()

            if response.status != 200:
                error_response = response.read().decode('utf-8')
                raise Exception(f"Error: {response.status}, {error_response}")

            if stream:
                return response
            else:
                response_data = response.read().decode('utf-8')
                self.logger.debug(f"Response status: {response.status}")
                self.logger.debug(f"Response body: {response_data}")
                return json.loads(response_data)
        except Exception as e:
            self.logger.error(f"Error in chat completion request: {str(e)}")
            raise
        finally:
            if not stream:
                conn.close()

    def get_info(self):
        try:
            conn = http.client.HTTPConnection(self.host, self.port, timeout=5)
            conn.request("GET", "/v1/models")
            response = conn.getresponse()
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                models = data.get('data', [])
                current_model = next((model for model in models if model.get('id') == self.model), None)
                return {
                    "api_type": "Ollama",
                    "model": self.model,
                    "status": "Running",
                    "host": self.host,
                    "port": self.port,
                    "model_details": current_model
                }
            else:
                return {
                    "api_type": "Ollama",
                    "model": self.model,
                    "status": "Not Running",
                    "host": self.host,
                    "port": self.port
                }
        except Exception as e:
            return {
                "api_type": "Ollama",
                "model": self.model,
                "status": f"Error: {str(e)}",
                "host": self.host,
                "port": self.port
            }
        finally:
            try:
                conn.close()
            except Exception:
                pass


def check_server_status():
    try:
        conn = http.client.HTTPConnection("localhost", 8080, timeout=5)
        conn.request("GET", "/v1/models")
        response = conn.getresponse()
        if response.status == 200:
            print("running")
        else:
            print("not running")
    except Exception as e:
        print("not running")
    finally:
        try:
            conn.close()
        except Exception:
            pass


def interactive_shell(client, prompt, model=None):
    print("Welcome to the interactive shell. Type 'help' for available commands or 'exit' to quit.")
    conversation_history = [
        {"role": "system", "content": prompt}
    ]

    def print_help():
        print("Available commands:")
        print("  help    - Show this help message")
        print("  clear   - Clear the conversation history")
        print("  info    - Show information about the current API and model")
        print("  exit    - Exit the interactive shell")

    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() == 'exit':
                print("Exiting interactive shell.")
                break
            elif user_input.lower() == 'help':
                print_help()
                continue
            elif user_input.lower() == 'clear':
                conversation_history = [conversation_history[0]]  # Keep only the system message
                print("Conversation history cleared.")
                continue
            elif user_input.lower() == 'info':
                info = client.get_info()
                print("API Information:")
                for key, value in info.items():
                    print(f"  {key}: {value}")
                continue

            conversation_history.append({"role": "user", "content": user_input})
            response = client.chat_completion(conversation_history, stream=True)

            print("AI: ", end="", flush=True)
            buffer = ""
            ai_response = ""
            for line in response:
                if isinstance(line, bytes):
                    line = line.decode('utf-8')
                buffer += line
                if buffer.endswith('\n'):
                    try:
                        chunks = buffer.split('\n')
                        for chunk in chunks:
                            if chunk.startswith('data: '):
                                data_str = chunk[6:]
                                if data_str == '[DONE]':
                                    print()  # New line after the response
                                    break
                                data = json.loads(data_str)
                                if 'choices' in data and len(data['choices']) > 0:
                                    delta = data['choices'][0].get('delta', {})
                                    if 'content' in delta:
                                        content = delta['content']
                                        # Clean the content before printing and appending
                                        cleaned_content = clean_content(content)
                                        ai_response += cleaned_content
                                        print(cleaned_content, end="", flush=True)
                                    if data['choices'][0].get('finish_reason') is not None:
                                        print()  # New line after the response
                                        break
                        buffer = ""
                    except json.JSONDecodeError:
                        # Incomplete JSON, keep in buffer
                        continue

            # Append the cleaned AI response to the conversation history
            conversation_history.append({"role": "assistant", "content": ai_response})

        except KeyboardInterrupt:
            print("\nExiting interactive shell.")
            break
        except Exception as e:
            print(f"An error occurred: {str(e)}")


def main():
    parser = argparse.ArgumentParser(description="API Client for Llamafile, Ollama, or OpenAI Service")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument("-p", "--prompt", help="Custom prompt for summarization", default="You are a helpful AI assistant. Respond to the user's queries concisely and accurately.")
    parser.add_argument("--service", action="store_true", help="Run llamafile as a service")
    parser.add_argument("--stop", action="store_true", help="Stop the running llamafile service")
    parser.add_argument("--status", action="store_true", help="Check if the llamafile service is running")
    parser.add_argument("-l", "--llamafile", metavar="LLAMAFILE_PATH", help="Path to the llamafile executable")
    parser.add_argument("--ollama-model", metavar="MODEL_NAME", help="Specify the Ollama model to use")
    parser.add_argument("--openai-model", metavar="MODEL_NAME", help="Specify the OpenAI model to use")
    parser.add_argument("files", nargs="*", help="Files to summarize")
    args = parser.parse_args()

    configure_logging(args.debug)
    logger = logging.getLogger(__name__)

    # Print LLAMAFILE_PATH for debugging
    logger.debug(f"LLAMAFILE_PATH environment variable: {os.environ.get('LLAMAFILE_PATH')}")

    # Determine the OpenAI model: command-line argument overrides environment variable
    openai_model = args.openai_model or os.environ.get("OPENAI_MODEL")
    openai_api_key = os.environ.get("OPENAI_API_KEY")

    # Determine the Ollama model: command-line argument overrides environment variable
    ollama_model = args.ollama_model or os.environ.get("OLLAMA_MODEL")

    try:
        if openai_api_key and openai_model:
            # OpenAI Mode
            logger.debug("Operating in OpenAI mode")
            client = OpenAIClient(api_key=openai_api_key, model=openai_model)

            # Handle service-related arguments which are not applicable in OpenAI mode
            if args.stop or args.service:
                logger.error("The '--service' and '--stop' options are not applicable in OpenAI mode.")
                print("Error: '--service' and '--stop' options are not applicable when using OpenAI API.")
                sys.exit(1)

            if args.status:
                # OpenAI does not have a status endpoint; we'll attempt a simple request
                try:
                    conn = http.client.HTTPSConnection("api.openai.com", 443, timeout=5)
                    headers = {
                        "Authorization": f"Bearer {openai_api_key}",
                        "Content-Type": "application/json"
                    }
                    test_data = json.dumps({
                        "model": openai_model,
                        "messages": [{"role": "system", "content": "Test"}],
                        "max_tokens": 1
                    })
                    conn.request("POST", "/v1/chat/completions", body=test_data, headers=headers)
                    response = conn.getresponse()
                    if response.status == 200:
                        print("running")
                    else:
                        print("not running")
                except Exception:
                    print("not running")
                finally:
                    try:
                        conn.close()
                    except Exception:
                        pass
                return

            if not args.files:
                interactive_shell(client, args.prompt, model=openai_model)
            else:
                # Read from stdin if '-' is among the files
                stdin_content = None
                if '-' in args.files:
                    if len(args.files) > 1:
                        logger.error("When using '-', no other file names should be provided.")
                        print("Error: When using '-', no other file names should be provided.")
                        sys.exit(1)
                    logger.debug("Reading content from stdin")
                    stdin_content = sys.stdin.read()

                for file in args.files:
                    if file == '-':
                        content = stdin_content
                    else:
                        with open(file, 'r') as f:
                            content = f.read()
                    messages = [{"role": "user", "content": f"{args.prompt}\n\n{content}"}]
                    response = client.chat_completion(messages, stream=False)
                    content_response = response.get("choices", [])[0].get("message", {}).get("content", "No content in response")
                    
                    # Clean the content before printing
                    cleaned_content = clean_content(content_response)
                    print(cleaned_content)
        elif ollama_model:
            # Ollama Mode
            logger.debug("Operating in Ollama mode")
            client = OllamaClient(model=ollama_model)

            # Check if Ollama service is running and model exists
            client._check_model_exists()

            if args.stop or args.service:
                logger.error("The '--service' and '--stop' options are not applicable in Ollama mode.")
                print("Error: '--service' and '--stop' options are not applicable when using Ollama model.")
                sys.exit(1)

            if args.status:
                # Check if Ollama service is running
                try:
                    conn = http.client.HTTPConnection("localhost", 11434, timeout=5)
                    conn.request("GET", "/v1/models")
                    response = conn.getresponse()
                    if response.status == 200:
                        print("running")
                    else:
                        print("not running")
                except Exception:
                    print("not running")
                finally:
                    try:
                        conn.close()
                    except Exception:
                        pass
                return

            if not args.files:
                interactive_shell(client, args.prompt, model=ollama_model)
            else:
                # Read from stdin if '-' is among the files
                stdin_content = None
                if '-' in args.files:
                    if len(args.files) > 1:
                        logger.error("When using '-', no other file names should be provided.")
                        print("Error: When using '-', no other file names should be provided.")
                        sys.exit(1)
                    logger.debug("Reading content from stdin")
                    stdin_content = sys.stdin.read()

                for file in args.files:
                    if file == '-':
                        content = stdin_content
                    else:
                        with open(file, 'r') as f:
                            content = f.read()
                    messages = [{"role": "user", "content": f"{args.prompt}\n\n{content}"}]
                    response = client.chat_completion(messages)
                    content_response = response.get("choices", [])[0].get("message", {}).get("content", "No content in response")
                    
                    # Clean the content before printing
                    cleaned_content = clean_content(content_response)
                    print(cleaned_content)
        else:
            # Llamafile Mode
            logger.debug("Operating in Llamafile mode")
            client = LlamafileClient(executable_path=args.llamafile, service_mode=args.service or args.stop)

            if args.stop:
                client.stop_llamafile()
                logger.info("Llamafile service stopped")
                return

            if args.status:
                check_server_status()
                return

            if args.service:
                client.start_llamafile(daemon=True)
                logger.info("Llamafile running as a service")
                return

            # Check if the service is running before starting a new instance
            try:
                conn = http.client.HTTPConnection("localhost", 8080, timeout=5)
                conn.request("GET", "/v1/models")
                response = conn.getresponse()
                if response.status == 200:
                    logger.info("Using running llamafile service")
                else:
                    raise Exception("Service not running")
            except Exception:
                logger.info("Starting new llamafile instance")
                client.start_llamafile()

            if not args.files:
                interactive_shell(client, args.prompt)
            else:
                # Read from stdin if '-' is among the files
                stdin_content = None
                if '-' in args.files:
                    if len(args.files) > 1:
                        logger.error("When using '-', no other file names should be provided.")
                        print("Error: When using '-', no other file names should be provided.")
                        sys.exit(1)
                    logger.debug("Reading content from stdin")
                    stdin_content = sys.stdin.read()

                for file in args.files:
                    if file == '-':
                        content = stdin_content
                    else:
                        with open(file, 'r') as f:
                            content = f.read()
                    messages = [{"role": "user", "content": f"{args.prompt}\n\n{content}"}]
                    response = client.chat_completion(messages)
                    content_response = response.get("choices", [])[0].get("message", {}).get("content", "No content in response")
                    
                    # Clean the content before printing
                    cleaned_content = clean_content(content_response)
                    print(cleaned_content)
    except FileNotFoundError as e:
        logger.error(f"Error: {str(e)}")
        print(f"Error: {str(e)}")
        sys.exit(1)  # Exit with error code 1
    except ValueError as e:
        logger.error(f"Error: {str(e)}")
        print(f"Error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.exception("An error occurred")
        print(f"An error occurred: {str(e)}")
        sys.exit(1)  # Exit with error code 1
    finally:
        if 'client' in locals():
            if isinstance(client, LlamafileClient) and not args.service and not args.stop and client.process:
                client.stop_llamafile()


if __name__ == "__main__":
    main()
