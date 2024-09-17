package main

import (
	"fmt"
	"io/ioutil"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

var (
	execCommand = exec.Command
	httpGet     = http.Get
)

func TestFindExecutable(t *testing.T) {
	// Save the original PATH and LLAMAFILE env vars
	origPath := os.Getenv("PATH")
	origLlamafile := os.Getenv("LLAMAFILE")
	defer func() {
		os.Setenv("PATH", origPath)
		os.Setenv("LLAMAFILE", origLlamafile)
	}()

	// Test case 1: Executable not found
	os.Setenv("PATH", "/test/path")
	os.Setenv("LLAMAFILE", "")
	_, err := findExecutable()
	if err == nil {
		t.Error("Expected error when executable not found, got nil")
	}

	// Test case 2: Executable in current directory
	currentDir, _ := os.Getwd()
	dummyFile := filepath.Join(currentDir, "llamafile")
	os.Create(dummyFile)
	defer os.Remove(dummyFile)

	fmt.Printf("Debug: Current Directory=%s, LLAMAFILE=%s\n", currentDir, os.Getenv("LLAMAFILE"))
	path, err := findExecutable()
	if err != nil {
		t.Errorf("Unexpected error: %v", err)
	}
	if path != dummyFile {
		t.Errorf("Expected %s, got %s", dummyFile, path)
	}

	// Test case 3: Executable in LLAMAFILE env var
	customPath := filepath.Join(currentDir, "llamafile")
	os.Setenv("LLAMAFILE", customPath)
	fmt.Printf("Debug: Custom Path=%s, Exists=%t\n", customPath, exists(customPath))
	path, err = findExecutable()
	if err != nil {
		t.Errorf("Unexpected error: %v", err)
	}
	if path != customPath {
		t.Errorf("Expected %s, got %s", customPath, path)
	}
}

func exists(filePath string) bool {
	info, err := os.Stat(filePath)
	return err == nil && !info.IsDir()
}

func TestGenerateAPIKey(t *testing.T) {
	key1 := generateAPIKey()
	key2 := generateAPIKey()

	if len(key1) != 32 {
		t.Errorf("Expected API key length of 32, got %d", len(key1))
	}
	if key1 == key2 {
		t.Error("Generated API keys should be unique")
	}
}

func TestNewLlamafileClient(t *testing.T) {
	// Create a temporary llamafile executable for testing
	tempDir, err := os.MkdirTemp("", "llamafile_test")
	if err != nil {
		t.Fatalf("Failed to create temp directory: %v", err)
	}
	defer os.RemoveAll(tempDir)

	tempExecutable := filepath.Join(tempDir, "llamafile")
	if err := os.WriteFile(tempExecutable, []byte("#!/bin/sh\necho 'Mock Llamafile'"), 0755); err != nil {
		t.Fatalf("Failed to create temp executable: %v", err)
	}

	// Set the LLAMAFILE environment variable to the temp executable
	os.Setenv("LLAMAFILE", tempExecutable)
	defer os.Unsetenv("LLAMAFILE")

	client, err := NewLlamafileClient("", "", "localhost", 8080)
	if err != nil {
		t.Fatalf("Unexpected error: %v", err)
	}

	fmt.Printf("Debug: LLAMAFILE=%s, ExecutablePath=%s, Exists=%t\n", os.Getenv("LLAMAFILE"), client.ExecutablePath, exists(client.ExecutablePath))

	if client == nil {
		t.Fatal("Expected non-nil client")
	}

	if client.Host != "localhost" {
		t.Errorf("Expected host to be localhost, got %s", client.Host)
	}
	if client.Port != 8080 {
		t.Errorf("Expected port to be 8080, got %d", client.Port)
	}
	if client.APIKey == "" {
		t.Error("API key should not be empty")
	}
	if client.ExecutablePath != tempExecutable {
		t.Errorf("Expected ExecutablePath to be %s, got %s", tempExecutable, client.ExecutablePath)
	}
}

func TestConfigureLogging(t *testing.T) {
	configureLogging(true)
	if logger == nil {
		t.Error("Logger should not be nil when debug is enabled")
	}

	configureLogging(false)
	if logger == nil {
		t.Error("Logger should not be nil when debug is disabled")
	}
}

func TestStartLlamafile(t *testing.T) {
	// Mock LlamafileClient for testing
	client := &LlamafileClient{
		ExecutablePath: "/path/to/mock",
		APIKey:         "mockapikey",
		Host:           "localhost",
		Port:           8080,
	}

	// Mock exec.Command to prevent starting a real process
	oldExecCommand := execCommand
	execCommand = func(name string, arg ...string) *exec.Cmd {
		cmd := exec.Command(name, arg...)
		cmd.Stdout = ioutil.Discard
		cmd.Stderr = ioutil.Discard
		return cmd
	}
	defer func() { execCommand = oldExecCommand }()

	err := client.StartLlamafile(false)
	if err == nil {
		t.Error("Expected error when starting llamafile with mock path")
	}
}

func TestCheckServerStatus(t *testing.T) {
	// Mock http.Get to control the response
	oldHttpGet := httpGet
	httpGet = func(url string) (*http.Response, error) {
		if url == "http://localhost:8080/v1/models" {
			return &http.Response{
				StatusCode: http.StatusOK,
				Body:       ioutil.NopCloser(strings.NewReader("OK")),
			}, nil
		}
		return nil, fmt.Errorf("error")
	}
	defer func() { httpGet = oldHttpGet }()

	checkServerStatus() // Expect "running"
}

func TestInteractiveShell(t *testing.T) {
	// Mock LlamafileClient for testing
	client := &LlamafileClient{
		ExecutablePath: "/path/to/mock",
		APIKey:         "mockapikey",
		Host:           "localhost",
		Port:           8080,
	}

	// Mock user input for testing
	oldStdin := os.Stdin
	defer func() { os.Stdin = oldStdin }()
	mockInput := "help\nexit\n"
	r, w, _ := os.Pipe()
	os.Stdin = r
	w.WriteString(mockInput)
	w.Close()

	oldStdout := os.Stdout
	oldStderr := os.Stderr
	defer func() {
		os.Stdout = oldStdout
		os.Stderr = oldStderr
	}()
	// Ensure it triggers expected functions without errors
	interactiveShell(client)
}

func TestMainFunction(t *testing.T) {
	// Ensure LLAMAFILE environment variable is accurately set
	llamafilePath := filepath.Join("..", "golang", "llamafile")
	os.Setenv("LLAMAFILE", llamafilePath)

	// Print the absolute path for verification
	absPath, err := filepath.Abs(llamafilePath)
	if err != nil {
		t.Fatalf("Failed to get absolute path: %v", err)
	}
	fmt.Printf("LLAMAFILE environment set to: %s (absolute path: %s)\n", llamafilePath, absPath)

	// Manually verify the existence of the file
	_, err = os.Stat(llamafilePath)
	if os.IsNotExist(err) {
		t.Fatalf("LLAMAFILE executable not found at %s", llamafilePath)
	}

	// Save and restore the original arguments
	origArgs := os.Args
	defer func() { os.Args = origArgs }()
	defer os.Unsetenv("LLAMAFILE")

	// Check server status as a test
	os.Args = []string{"sumarai", "--status"}
	main() // Expect checkServerStatus to run correctly

	// Stop Llamafile as a test
	os.Args = []string{"sumarai", "--stop"}
	main() // Expect StopLlamafile to execute without error
}
