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


def configure_logging(debug_enabled):
    level = logging.DEBUG if debug_enabled else logging.INFO
    logging.basicConfig(level=level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class LlamafileClient:
    def __init__(self, executable_path=None, api_key=None, host="localhost", port=8080):
        self.logger = logging.getLogger(__name__)
        self.executable_path = self._find_executable(executable_path)
        self.api_key = api_key if api_key else secrets.token_hex(16)
        self.host = host
        self.port = port
        self.process = None

    def _find_executable(self, executable_path):
        self.logger.debug("Starting search for llamafile executable")
        self.logger.debug(f"LLAMAFILE_PATH environment variable: {os.environ.get('LLAMAFILE_PATH')}")
        
        if executable_path:
            self.logger.debug(f"Checking specified executable path: {executable_path}")
            if os.path.isfile(executable_path):
                self.logger.debug(f"Using specified executable path: {executable_path}")
                return executable_path
            self.logger.warning(f"Specified executable path {executable_path} not found.")

        # Search in PATH
        self.logger.debug("Searching for llamafile in PATH")
        path_executable = shutil.which('llamafile')
        if path_executable:
            self.logger.debug(f"Found llamafile in PATH: {path_executable}")
            return path_executable
        self.logger.debug("llamafile not found in PATH")

        # Search in LLAMAFILE_PATH environment variable
        env_executable = os.environ.get('LLAMAFILE_PATH')
        if env_executable:
            self.logger.debug(f"Checking LLAMAFILE_PATH: {env_executable}")
            if os.path.isfile(env_executable):
                self.logger.debug(f"Using llamafile from LLAMAFILE_PATH: {env_executable}")
                return env_executable
            else:
                self.logger.warning(f"LLAMAFILE_PATH set but file not found: {env_executable}")
        else:
            self.logger.debug("LLAMAFILE_PATH environment variable not set")

        # Search in current directory
        current_dir = os.getcwd()
        self.logger.debug(f"Searching for llamafile in current directory: {current_dir}")
        current_dir_executable = os.path.join(current_dir, 'llamafile')
        if os.path.isfile(current_dir_executable):
            self.logger.debug(f"Using llamafile from current directory: {current_dir_executable}")
            return current_dir_executable
        self.logger.debug("llamafile not found in current directory")

        self.logger.error("Llamafile executable not found in PATH, current directory, or LLAMAFILE_PATH environment variable.")
        raise FileNotFoundError("Llamafile executable not found.")

    def start_llamafile(self, daemon=False):
        cmd = f"{self.executable_path} --api-key {self.api_key}"
        self.logger.debug(f"Starting llamafile with command: {cmd}")
        try:
            if daemon:
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

        self.process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        self.logger.debug("Daemon process started")

    def _wait_for_server(self, timeout=60, check_interval=1):
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                conn = http.client.HTTPConnection(self.host, self.port)
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

            if self.process.poll() is not None:
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

    def chat_completion(self, messages, model="local-model", stream=False):
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        data = json.dumps({
            "model": model,
            "messages": messages,
            "stream": stream
        }).encode('utf-8')

        self.logger.debug(f"Sending chat completion request to {self.host}:{self.port}/v1/chat/completions")
        self.logger.debug(f"Request headers: {headers}")
        self.logger.debug(f"Request body: {data}")

        try:
            conn = http.client.HTTPConnection(self.host, self.port)
            conn.request("POST", "/v1/chat/completions", body=data, headers=headers)
            response = conn.getresponse()

            if response.status != 200:
                raise Exception(f"Error: {response.status}, {response.read().decode('utf-8')}")

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


def check_server_status():
    try:
        conn = http.client.HTTPConnection("localhost", 8080)
        conn.request("GET", "/v1/models")
        response = conn.getresponse()
        if response.status == 200:
            print("running")
        else:
            print("not running")
    except Exception as e:
        print("not running")


def interactive_shell(client, prompt):
    print("Welcome to the interactive shell. Type 'help' for available commands or 'exit' to quit.")
    conversation_history = [
        {"role": "system", "content": prompt}
    ]

    def print_help():
        print("Available commands:")
        print("  help    - Show this help message")
        print("  clear   - Clear the conversation history")
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

            conversation_history.append({"role": "user", "content": user_input})
            response = client.chat_completion(conversation_history, stream=True)

            print("AI: ", end="", flush=True)
            buffer = ""
            ai_response = ""
            for line in response:
                buffer += line.decode('utf-8')
                if buffer.endswith('\n'):
                    try:
                        chunks = buffer.split('\n')
                        for chunk in chunks:
                            if chunk.startswith('data: '):
                                data = json.loads(chunk[6:])
                                if 'choices' in data and len(data['choices']) > 0:
                                    delta = data['choices'][0].get('delta', {})
                                    if 'content' in delta:
                                        content = delta['content']
                                        ai_response += content
                                        print(content, end="", flush=True)
                                    if data['choices'][0].get('finish_reason') is not None:
                                        print()  # New line after the response
                                        break
                        buffer = ""
                    except json.JSONDecodeError:
                        # Incomplete JSON, keep in buffer
                        continue

            conversation_history.append({"role": "assistant", "content": ai_response})

        except KeyboardInterrupt:
            print("\nExiting interactive shell.")
            break
        except Exception as e:
            print(f"An error occurred: {str(e)}")


def main():
    parser = argparse.ArgumentParser(description="Llamafile API Client")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument("-p", "--prompt", help="Custom prompt for summarization", default="You are a helpful AI assistant. Respond to the user's queries concisely and accurately.")
    parser.add_argument("--service", action="store_true", help="Run llamafile as a service")
    parser.add_argument("--stop", action="store_true", help="Stop the running llamafile service")
    parser.add_argument("--status", action="store_true", help="Check if the llamafile service is running")
    parser.add_argument("-l", "--llamafile", metavar="LLAMAFILE_PATH", help="Path to the llamafile executable")
    parser.add_argument("files", nargs="*", help="Files to summarize")
    args = parser.parse_args()

    configure_logging(args.debug)
    logger = logging.getLogger(__name__)

    # Print LLAMAFILE_PATH for debugging
    logger.debug(f"LLAMAFILE_PATH environment variable: {os.environ.get('LLAMAFILE_PATH')}")

    try:
        client = LlamafileClient(executable_path=args.llamafile)

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

        if not args.files:
            client.start_llamafile()
            interactive_shell(client, args.prompt)
        else:
            client.start_llamafile()

            for file in args.files:
                with open(file, 'r') as f:
                    content = f.read()
                messages = [{"role": "user", "content": f"{args.prompt}\n\n{content}"}]
                response = client.chat_completion(messages)
                content_response = response.get("choices", [])[0].get("message", {}).get("content", "No content in response")
                print(content_response)
    except FileNotFoundError as e:
        logger.error(f"Error: {str(e)}")
        print(f"Error: {str(e)}")
    except Exception as e:
        logger.exception("An error occurred")
    finally:
        if 'client' in locals() and not args.service:
            client.stop_llamafile()

if __name__ == "__main__":
    main()
