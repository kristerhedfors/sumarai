import pytest
import subprocess
import os

@pytest.fixture
def llamafile_service():
    # Setup: Start the llamafile service
    start_result = subprocess.run(["python3", "summarai.py", "--service"], capture_output=True, text=True)
    print(f"Service start stdout: {start_result.stdout}")
    print(f"Service start stderr: {start_result.stderr}")
    yield
    # Teardown: Stop the llamafile service
    stop_result = subprocess.run(["python3", "summarai.py", "--stop"], capture_output=True, text=True)
    print(f"Service stop stdout: {stop_result.stdout}")
    print(f"Service stop stderr: {stop_result.stderr}")


def test_start_llamafile_service(llamafile_service):
    # Check the service status through some means, here assuming a status check command is available
    result = subprocess.run(["python3", "summarai.py", "--status"], capture_output=True, text=True)
    print(f"Status check stdout: {result.stdout}")
    print(f"Status check stderr: {result.stderr}")
    assert "running" in result.stdout.lower() or "running" in result.stderr.lower()


def test_stop_llamafile_service():
    # Start the service first
    start_result = subprocess.run(["python3", "summarai.py", "--service"], capture_output=True, text=True)
    print(f"Service start stdout: {start_result.stdout}")
    print(f"Service start stderr: {start_result.stderr}")
    # Stop the service
    result = subprocess.run(["python3", "summarai.py", "--stop"], capture_output=True, text=True)
    print(f"Service stop stdout: {result.stdout}")
    print(f"Service stop stderr: {result.stderr}")
    # Assuming the stdout contains the information about the stop status
    assert "stopped" in result.stdout.lower() or "stopped" in result.stderr.lower()
