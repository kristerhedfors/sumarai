#!/bin/bash

# ============================
# invoke_ai.sh
# ============================
# This script invokes ai.py in various ways using the '-' argument to read from stdin,
# combined with customized prompts using --prompt. It measures and compares
# the execution times when running llamafile as a service and when not running as a service.
# Each test case is executed multiple times to improve time resolution.

# ----------------------------
# Configuration
# ----------------------------

# Path to ai.py (modify if necessary)
AI="./sumarai.py"

# Number of iterations per test case
NUM_ITERATIONS=5

# Check if ai.py is executable
if [[ ! -x "$AI" ]]; then
    echo "Error: $AI is not found or not executable."
    exit 1
fi

# Define test cases
declare -a TEST_CASES=(
    "--prompt 'Custom Prompt 1: Summarize the following text.' sample1.txt"
    "--prompt 'Custom Prompt 2: Analyze the sentiment of the text.' sample2.txt"
    "--prompt 'Custom Prompt 3: Extract key points from the text.' -"
    "--prompt 'Custom Prompt 4: Translate the text to Spanish.' -"
)

# Define input data for stdin tests
STDIN_INPUT_1="This is the first sample input for stdin. It contains information that needs to be summarized."
STDIN_INPUT_2="This is the second sample input for stdin. It contains data that requires sentiment analysis."

# Temporary files for stdin inputs
STDIN_FILE_1="stdin_input1.txt"
STDIN_FILE_2="stdin_input2.txt"

# Create temporary stdin input files
echo "$STDIN_INPUT_1" > "$STDIN_FILE_1"
echo "$STDIN_INPUT_2" > "$STDIN_FILE_2"

# Define variables to store timing results using parallel arrays
declare -a WITH_SERVICE_AVG_TIMES
declare -a WITH_SERVICE_MIN_TIMES
declare -a WITH_SERVICE_MAX_TIMES
declare -a WITHOUT_SERVICE_AVG_TIMES
declare -a WITHOUT_SERVICE_MIN_TIMES
declare -a WITHOUT_SERVICE_MAX_TIMES

# ----------------------------
# Helper Functions
# ----------------------------

# Function to start llamafile as a service
start_service() {
    echo "Starting llamafile as a service..."
    "$AI" --service &
    SERVICE_PID=$!
    # Wait for the service to start
    sleep 5
    # Check if service is running
    SERVICE_STATUS=$("$AI" --status)
    echo "Service status after starting: '$SERVICE_STATUS'"
    if [[ "$SERVICE_STATUS" != "running" ]]; then
        echo "Error: Failed to start llamafile service."
        kill "$SERVICE_PID" 2>/dev/null
        exit 1
    fi
    echo "llamafile service started with PID $SERVICE_PID."
}

# Function to stop llamafile service
stop_service() {
    echo "Stopping llamafile service..."
    "$AI" --stop
    # Wait for the service to stop
    sleep 2
    SERVICE_STATUS=$("$AI" --status)
    echo "Service status after stopping: '$SERVICE_STATUS'"
    if [[ "$SERVICE_STATUS" == "running" ]]; then
        echo "Error: Failed to stop llamafile service."
        exit 1
    fi
    echo "llamafile service stopped."
}

# Function to run a single test case multiple times
# Arguments:
#   1. Test case string
#   2. Mode: "with_service" or "without_service"
run_test() {
    local TEST="$1"
    local MODE="$2"
    local INPUT_FILE=""
    local ITER
    local ELAPSED
    local TOTAL_TIME=0
    local MIN_TIME=""
    local MAX_TIME=""

    # Determine how to handle stdin
    if [[ "$TEST" == *" -" ]]; then
        # Identify which stdin file to use based on the prompt
        if [[ "$TEST" == *"Custom_Prompt_3"* ]]; then
            INPUT_FILE="$STDIN_FILE_1"
        elif [[ "$TEST" == *"Custom_Prompt_4"* ]]; then
            INPUT_FILE="$STDIN_FILE_2"
        fi
    fi

    # Execute the test case NUM_ITERATIONS times
    for (( ITER=1; ITER<=NUM_ITERATIONS; ITER++ )); do
        # Start timing
        START_TIME=$(date +%s.%N)
        
        if [[ "$INPUT_FILE" == "-" ]]; then
            # Provide input via stdin
            if [[ "$TEST" == *"Custom_Prompt_3"* ]]; then
                echo "$STDIN_INPUT_1" | "$AI" $TEST > /dev/null 2>&1
            elif [[ "$TEST" == *"Custom_Prompt_4"* ]]; then
                echo "$STDIN_INPUT_2" | "$AI" $TEST > /dev/null 2>&1
            fi
        else
            # Provide input via file
            "$AI" $TEST > /dev/null 2>&1
        fi

        # End timing
        END_TIME=$(date +%s.%N)
        # Calculate elapsed time
        ELAPSED=$(echo "$END_TIME - $START_TIME" | bc)
        
        # Ensure elapsed time has leading zero if necessary
        if [[ "$ELAPSED" == .* ]]; then
            ELAPSED="0$ELAPSED"
        fi

        # Accumulate total time
        TOTAL_TIME=$(echo "$TOTAL_TIME + $ELAPSED" | bc)
        
        # Determine min and max times
        if [[ -z "$MIN_TIME" ]] || (( $(echo "$ELAPSED < $MIN_TIME" | bc -l) )); then
            MIN_TIME="$ELAPSED"
        fi
        if [[ -z "$MAX_TIME" ]] || (( $(echo "$ELAPSED > $MAX_TIME" | bc -l) )); then
            MAX_TIME="$ELAPSED"
        fi
    done

    # Calculate average time
    AVG_TIME=$(echo "scale=6; $TOTAL_TIME / $NUM_ITERATIONS" | bc)
    
    # Store the results in the appropriate arrays
    if [[ "$MODE" == "with_service" ]]; then
        WITH_SERVICE_AVG_TIMES+=("$AVG_TIME")
        WITH_SERVICE_MIN_TIMES+=("$MIN_TIME")
        WITH_SERVICE_MAX_TIMES+=("$MAX_TIME")
    else
        WITHOUT_SERVICE_AVG_TIMES+=("$AVG_TIME")
        WITHOUT_SERVICE_MIN_TIMES+=("$MIN_TIME")
        WITHOUT_SERVICE_MAX_TIMES+=("$MAX_TIME")
    fi
}

# Function to run all test cases in a given mode
# Arguments:
#   1. Mode: "with_service" or "without_service"
run_all_tests() {
    local MODE="$1"
    echo "Running tests in mode: $MODE"
    for TEST in "${TEST_CASES[@]}"; do
        run_test "$TEST" "$MODE"
    done
}

# Function to display the timing results
display_results() {
    echo "=========================================="
    echo "           Timing Results"
    echo "=========================================="
    printf "%-80s %-20s %-20s %-20s %-20s %-20s %-20s %-20s\n" "Test Case" "With Service Avg(s)" "With Service Min(s)" "With Service Max(s)" "Without Service Avg(s)" "Without Service Min(s)" "Without Service Max(s)" "Difference(s)"
    printf "%-80s %-20s %-20s %-20s %-20s %-20s %-20s %-20s\n" "---------" "--------------------" "--------------------" "--------------------" "-----------------------" "-----------------------" "-----------------------" "--------------------"
    
    local NUM_TESTS=${#TEST_CASES[@]}
    for (( i=0; i<NUM_TESTS; i++ )); do
        local TEST="${TEST_CASES[$i]}"
        # Extract original test case description
        ORIGINAL_TEST="${TEST#--prompt '}"
        ORIGINAL_TEST="${ORIGINAL_TEST%'}"
        ORIGINAL_TEST="${ORIGINAL_TEST//_/ }"
        
        local WITH_AVG="${WITH_SERVICE_AVG_TIMES[$i]}"
        local WITH_MIN="${WITH_SERVICE_MIN_TIMES[$i]}"
        local WITH_MAX="${WITH_SERVICE_MAX_TIMES[$i]}"
        local WITHOUT_AVG="${WITHOUT_SERVICE_AVG_TIMES[$i]}"
        local WITHOUT_MIN="${WITHOUT_SERVICE_MIN_TIMES[$i]}"
        local WITHOUT_MAX="${WITHOUT_SERVICE_MAX_TIMES[$i]}"
        
        # Calculate the difference (avg)
        DIFF=$(echo "scale=6; $WITHOUT_AVG - $WITH_AVG" | bc)
        
        # Ensure DIFF has leading zero if necessary
        if [[ "$DIFF" == .* ]]; then
            DIFF="0$DIFF"
        fi

        # Format the output
        printf "%-80s %-20s %-20s %-20s %-20s %-20s %-20s %-20s\n" "$TEST" "$WITH_AVG" "$WITH_MIN" "$WITH_MAX" "$WITHOUT_AVG" "$WITHOUT_MIN" "$WITHOUT_MAX" "$DIFF"
    done
    echo "=========================================="
}

# ----------------------------
# Main Script Execution
# ----------------------------

echo "===== Starting ai.py Invocation Tests ====="

# Start llamafile as a service
start_service

# Run all tests with llamafile service running
run_all_tests "with_service"

# Stop the service
stop_service

# Run all tests without llamafile service running
run_all_tests "without_service"

# Display the results
display_results

# Clean up temporary stdin input files
rm -f "$STDIN_FILE_1" "$STDIN_FILE_2"

echo "===== Tests Completed ====="
