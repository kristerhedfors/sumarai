package main

import (
	"os"
	"testing"
)

func TestFindExecutable(t *testing.T) {
	// Save the original PATH and LLAMAFILE env vars
	origPath := os.Getenv("PATH")
	origLlamafile := os.Getenv("LLAMAFILE")
	defer func() {
		os.Setenv("PATH", origPath)
		os.Setenv("LLAMAFILE", origLlamafile)
	}()

	// Test case 1: Executable in PATH
	os.Setenv("PATH", "/test/path")
	os.Setenv("LLAMAFILE", "")
	_, err := findExecutable()
	if err == nil {
		t.Error("Expected error when executable not found, got nil")
	}

	// Test case 2: Executable in current directory
	currentDir, _ := os.Getwd()
	dummyFile := currentDir + "/llamafile"
	os.Create(dummyFile)
	defer os.Remove(dummyFile)

	path, err := findExecutable()
	if err != nil {
		t.Errorf("Unexpected error: %v", err)
	}
	if path != dummyFile {
		t.Errorf("Expected %s, got %s", dummyFile, path)
	}

	// Test case 3: Executable in LLAMAFILE env var
	os.Setenv("LLAMAFILE", "/custom/path/llamafile")
	path, err = findExecutable()
	if err != nil {
		t.Errorf("Unexpected error: %v", err)
	}
	if path != "/custom/path/llamafile" {
		t.Errorf("Expected /custom/path/llamafile, got %s", path)
	}
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
	client, err := NewLlamafileClient("", "", "localhost", 8080)
	if err != nil {
		t.Errorf("Unexpected error: %v", err)
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
}

// Add more tests as needed for other functions