import pytest
import subprocess
import os
import stat
import time
import signal

SUMARAI_SCRIPT = "sumarai.py"
LLAMAFILE_DIR = os.path.join(os.path.expanduser("~"), ".llamafile")
PID_FILE = os.path.join(LLAMAFILE_DIR, "llamafile.pid")
API_KEY_FILE = os.path.join(LLAMAFILE_DIR, "api_key")


@pytest.fixture
def llamafile_service():
    # Setup: Start the llamafile service
    start_result = subprocess.run(
        ["python3", SUMARAI_SCRIPT, "--service"], capture_output=True, text=True
    )
    print(f"Service start stdout: {start_result.stdout}")
    print(f"Service start stderr: {start_result.stderr}")

    # Ensure no error during start
    assert start_result.returncode == 0, "Failed to start the llamafile service"
    
    # Wait a little longer to ensure the service starts properly
    time.sleep(10)  # Increase sleep time if necessary

    yield

    # Teardown: Stop the llamafile service
    stop_result = subprocess.run(
        ["python3", SUMARAI_SCRIPT, "--stop"], capture_output=True, text=True
    )
    print(f"Service stop stdout: {stop_result.stdout}")
    print(f"Service stop stderr: {stop_result.stderr}")

    # Ensure the PID file and API key file are removed
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)
    if os.path.exists(API_KEY_FILE):
        os.remove(API_KEY_FILE)



def test_start_llamafile_service(llamafile_service):
    # Check that the PID file and API key file are created
    assert os.path.exists(PID_FILE), "PID file was not created"
    assert os.path.exists(API_KEY_FILE), "API key file was not created"

    # Check the permissions of the API key file
    api_key_file_mode = stat.S_IMODE(os.lstat(API_KEY_FILE).st_mode)
    assert api_key_file_mode == 0o600, "API key file does not have mode 0600"

    # Check the service status
    result = subprocess.run(
        ["python3", SUMARAI_SCRIPT, "--status"], capture_output=True, text=True
    )
    print(f"Status check stdout: {result.stdout}")
    print(f"Status check stderr: {result.stderr}")
    assert "running" in result.stdout.lower() or "running" in result.stderr.lower()

    # Verify that the process is running
    with open(PID_FILE, 'r') as f:
        pid = int(f.read())
    try:
        os.kill(pid, 0)  # Check if process exists
    except ProcessLookupError:
        pytest.fail(f"Process with PID {pid} is not running")


def test_stop_llamafile_service():
    # Start the service
    start_result = subprocess.run(
        ["python3", SUMARAI_SCRIPT, "--service"], capture_output=True, text=True
    )
    print(f"Service start stdout: {start_result.stdout}")
    print(f"Service start stderr: {start_result.stderr}")

    # Wait a moment to ensure the service starts
    time.sleep(5)

    # Stop the service
    stop_result = subprocess.run(
        ["python3", SUMARAI_SCRIPT, "--stop"], capture_output=True, text=True
    )
    print(f"Service stop stdout: {stop_result.stdout}")
    print(f"Service stop stderr: {stop_result.stderr}")

    # Wait for the service to fully stop
    time.sleep(5)

    # Check that the PID file and API key file are removed
    assert not os.path.exists(PID_FILE), "PID file was not removed after stopping service"
    assert not os.path.exists(API_KEY_FILE), "API key file was not removed after stopping service"

    # Check the service status
    result = subprocess.run(
        ["python3", SUMARAI_SCRIPT, "--status"], capture_output=True, text=True
    )
    print(f"Status check stdout: {result.stdout}")
    print(f"Status check stderr: {result.stderr}")
    assert "not running" in result.stdout.lower() or "not running" in result.stderr.lower()

    # Verify that the process is not running
    # If PID file existed, we can check the PID; otherwise, assume process is stopped
    if os.path.exists(PID_FILE):
        with open(PID_FILE, 'r') as f:
            pid = int(f.read())
        try:
            os.kill(pid, 0)
            pytest.fail(f"Process with PID {pid} is still running")
        except ProcessLookupError:
            pass  # Process is not running

    # Cleanup
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)
    if os.path.exists(API_KEY_FILE):
        os.remove(API_KEY_FILE)


def test_files_not_created_without_service():
    # Ensure that PID and API key files do not exist
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)
    if os.path.exists(API_KEY_FILE):
        os.remove(API_KEY_FILE)

    # Run sumarai.py without --service
    run_result = subprocess.run(
        ["python3", SUMARAI_SCRIPT], input="exit\n", text=True, capture_output=True
    )
    print(f"Run stdout: {run_result.stdout}")
    print(f"Run stderr: {run_result.stderr}")

    # Check that PID and API key files are not created
    assert not os.path.exists(PID_FILE), "PID file should not be created without --service"
    assert not os.path.exists(API_KEY_FILE), "API key file should not be created without --service"
