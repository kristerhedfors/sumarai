// sumarai.go
package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io/ioutil"
	"net"
	"net/http"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"regexp"
	"runtime"
	"strconv"
	"strings"
	"syscall"
	"time"
)

const (
	llamafileDir  = ".llamafile"
	pidFileName   = "llamafile.pid"
	apiKeyFile    = "api_key"
	defaultHost   = "localhost"
	defaultPort   = 8080
	defaultPrompt = "You are a helpful AI assistant. Respond to the user's queries concisely and accurately."
)

type LlamafileClient struct {
	executablePath string
	apiKey         string
	host           string
	port           int
	process        *os.Process
	serviceMode    bool
}

type Message struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type ChatCompletionRequest struct {
	Model    string    `json:"model"`
	Messages []Message `json:"messages"`
	Stream   bool      `json:"stream"`
}

type ChatCompletionResponse struct {
	Choices []struct {
		Delta struct {
			Content string `json:"content"`
		} `json:"delta"`
		FinishReason string `json:"finish_reason"`
	} `json:"choices"`
}

func CleanContent(content string) string {
	tagsToRemove := []string{
		`<\|eot_id\|>`,
		// Add more tags here as needed
	}

	for _, tag := range tagsToRemove {
		re := regexp.MustCompile(tag)
		content = re.ReplaceAllString(content, "")
	}
	return content
}

func ConfigureLogging(debugEnabled bool) {
	if debugEnabled {
		// Enable detailed logging if needed
	}
}

func NewLlamafileClient(executablePath string, serviceMode bool) (*LlamafileClient, error) {
	execPath, err := findExecutable(executablePath)
	if err != nil {
		return nil, err
	}

	apiKey := ""
	apiKeyFilePath := filepath.Join(os.Getenv("HOME"), llamafileDir, apiKeyFile)
	if data, err := ioutil.ReadFile(apiKeyFilePath); err == nil {
		apiKey = strings.TrimSpace(string(data))
	} else {
		apiKey = generateAPIKey()
	}

	return &LlamafileClient{
		executablePath: execPath,
		apiKey:         apiKey,
		host:           defaultHost,
		port:           defaultPort,
		serviceMode:    serviceMode,
	}, nil
}

func generateAPIKey() string {
	return fmt.Sprintf("%x", time.Now().UnixNano())
}

func findExecutable(executablePath string) (string, error) {
	if executablePath != "" {
		absPath, err := filepath.Abs(executablePath)
		if err != nil {
			return "", err
		}
		if fileExistsAndExecutable(absPath) {
			return absPath, nil
		}
		return "", fmt.Errorf("specified executable path %s not found or not executable", absPath)
	}

	// Check LLAMAFILE environment variable
	if envPath := os.Getenv("LLAMAFILE"); envPath != "" {
		absPath, err := filepath.Abs(envPath)
		if err == nil && fileExistsAndExecutable(absPath) {
			return absPath, nil
		}
	}

	// Check LLAMAFILE_PATH environment variable
	if envPath := os.Getenv("LLAMAFILE_PATH"); envPath != "" {
		absPath, err := filepath.Abs(envPath)
		if err == nil && fileExistsAndExecutable(absPath) {
			return absPath, nil
		}
	}

	// Check current directory
	currentDir, err := os.Getwd()
	if err == nil {
		currentDirExecutable := filepath.Join(currentDir, "llamafile")
		if fileExistsAndExecutable(currentDirExecutable) {
			return currentDirExecutable, nil
		}
	}

	// Check system PATH
	if pathExecutable, err := exec.LookPath("llamafile"); err == nil {
		return pathExecutable, nil
	}

	return "", errors.New("llamafile executable not found in PATH, current directory, or environment variables")
}

func fileExistsAndExecutable(path string) bool {
	info, err := os.Stat(path)
	if err != nil {
		return false
	}
	mode := info.Mode()
	return mode.IsRegular() && mode&0111 != 0
}

func (client *LlamafileClient) StartLlamafile(daemon bool) error {
	if client.executablePath == "" {
		return errors.New("llamafile executable not found")
	}

	if client.serviceMode && daemon {
		return client.startDaemon()
	}

	cmd, err := client.buildCommand()
	if err != nil {
		return err
	}

	// Set process attributes conditionally
	if runtime.GOOS != "windows" {
		// Unix-like systems
		cmd.SysProcAttr = &syscall.SysProcAttr{
			Setsid: true,
		}
	} else {
		// Windows systems
		// Avoid setting SysProcAttr fields that are not defined on Unix-like systems
		cmd.SysProcAttr = &syscall.SysProcAttr{}
	}

	if err := cmd.Start(); err != nil {
		return err
	}

	client.process = cmd.Process

	// Wait for server to be ready
	return client.waitForServer()
}

func (client *LlamafileClient) buildCommand() (*exec.Cmd, error) {
	apiKeyArg := fmt.Sprintf("--api-key %s", client.apiKey)
	var cmd *exec.Cmd

	if runtime.GOOS == "windows" {
		// Use cmd.exe on Windows
		cmdLine := fmt.Sprintf("%s %s", client.executablePath, apiKeyArg)
		cmd = exec.Command("cmd", "/C", cmdLine)
	} else {
		// Use sh on Unix-like systems
		cmdLine := fmt.Sprintf("%s %s", client.executablePath, apiKeyArg)
		cmd = exec.Command("sh", "-c", cmdLine)
	}

	// Redirect output if needed
	return cmd, nil
}

func (client *LlamafileClient) startDaemon() error {
	homeDir, err := os.UserHomeDir()
	if err != nil {
		return err
	}

	llamaDir := filepath.Join(homeDir, llamafileDir)
	if _, err := os.Stat(llamaDir); os.IsNotExist(err) {
		if err := os.MkdirAll(llamaDir, 0755); err != nil {
			return err
		}
	}

	cmd, err := client.buildCommand()
	if err != nil {
		return err
	}

	// Set process attributes conditionally
	if runtime.GOOS != "windows" {
		// Unix-like systems
		cmd.SysProcAttr = &syscall.SysProcAttr{
			Setsid: true,
		}
	} else {
		// Windows systems
		// Avoid setting SysProcAttr fields that are not defined on Unix-like systems
		cmd.SysProcAttr = &syscall.SysProcAttr{}
	}

	// Start the process
	if err := cmd.Start(); err != nil {
		return err
	}

	// Write pid file
	pidFilePath := filepath.Join(llamaDir, pidFileName)
	err = ioutil.WriteFile(pidFilePath, []byte(fmt.Sprintf("%d", cmd.Process.Pid)), 0644)
	if err != nil {
		return err
	}

	// Write API key file
	apiKeyFilePath := filepath.Join(llamaDir, apiKeyFile)
	err = ioutil.WriteFile(apiKeyFilePath, []byte(client.apiKey), 0600)
	if err != nil {
		return err
	}

	return nil
}

func (client *LlamafileClient) waitForServer() error {
	timeout := time.After(60 * time.Second)
	tick := time.Tick(1 * time.Second)

	for {
		select {
		case <-timeout:
			return errors.New("server did not become ready within the timeout period")
		case <-tick:
			conn, err := net.DialTimeout("tcp", fmt.Sprintf("%s:%d", client.host, client.port), 1*time.Second)
			if err == nil {
				conn.Close()
				return nil
			}
		}
	}
}

func (client *LlamafileClient) StopLlamafile() error {
	if client.process != nil {
		if err := client.process.Kill(); err != nil {
			return err
		}
		_, err := client.process.Wait()
		return err
	}

	homeDir, err := os.UserHomeDir()
	if err != nil {
		return err
	}

	pidFilePath := filepath.Join(homeDir, llamafileDir, pidFileName)
	data, err := ioutil.ReadFile(pidFilePath)
	if err != nil {
		return errors.New("PID file not found")
	}

	pidStr := strings.TrimSpace(string(data))
	pidInt, err := strconv.Atoi(pidStr)
	if err != nil {
		return fmt.Errorf("invalid PID in PID file: %v", err)
	}

	process, err := os.FindProcess(pidInt)
	if err != nil {
		return fmt.Errorf("process with PID %d not found: %v", pidInt, err)
	}

	if err := process.Kill(); err != nil {
		return fmt.Errorf("failed to kill process with PID %d: %v", pidInt, err)
	}

	fmt.Printf("Killed process with PID %d\n", pidInt)

	// Remove PID file
	if err := os.Remove(pidFilePath); err != nil {
		return fmt.Errorf("failed to remove PID file: %v", err)
	}

	return nil
}

func (client *LlamafileClient) ChatCompletion(messages []Message, stream bool) (*http.Response, error) {
	url := fmt.Sprintf("http://%s:%d/v1/chat/completions", client.host, client.port)
	requestBody := ChatCompletionRequest{
		Model:    "local-model",
		Messages: messages,
		Stream:   stream,
	}

	jsonData, err := json.Marshal(requestBody)
	if err != nil {
		return nil, err
	}

	req, err := http.NewRequest("POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, err
	}

	if client.apiKey != "" {
		req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", client.apiKey))
	}
	req.Header.Set("Content-Type", "application/json")

	clientHTTP := &http.Client{}
	resp, err := clientHTTP.Do(req)
	if err != nil {
		return nil, err
	}

	if resp.StatusCode != 200 {
		bodyBytes, _ := ioutil.ReadAll(resp.Body)
		return nil, fmt.Errorf("error: %d, %s", resp.StatusCode, string(bodyBytes))
	}

	return resp, nil
}

func CheckServerStatus() {
	conn, err := net.DialTimeout("tcp", fmt.Sprintf("%s:%d", defaultHost, defaultPort), 1*time.Second)
	if err == nil {
		fmt.Println("running")
		conn.Close()
	} else {
		fmt.Println("not running")
	}
}

func InteractiveShell(client *LlamafileClient, prompt string) {
	fmt.Println("Welcome to the interactive shell. Type 'help' for available commands or 'exit' to quit.")
	conversationHistory := []Message{
		{Role: "system", Content: prompt},
	}

	scanner := bufio.NewScanner(os.Stdin)

	for {
		fmt.Print("You: ")
		if !scanner.Scan() {
			break
		}
		userInput := strings.TrimSpace(scanner.Text())

		if strings.ToLower(userInput) == "exit" {
			fmt.Println("Exiting interactive shell.")
			break
		} else if strings.ToLower(userInput) == "help" {
			printHelp()
			continue
		} else if strings.ToLower(userInput) == "clear" {
			conversationHistory = conversationHistory[:1]
			fmt.Println("Conversation history cleared.")
			continue
		}

		conversationHistory = append(conversationHistory, Message{Role: "user", Content: userInput})
		resp, err := client.ChatCompletion(conversationHistory, true)
		if err != nil {
			fmt.Printf("An error occurred: %s\n", err.Error())
			continue
		}

		defer resp.Body.Close()
		reader := bufio.NewReader(resp.Body)
		fmt.Print("AI: ")
		var aiResponse string

		for {
			line, err := reader.ReadString('\n')
			if err != nil {
				break
			}

			if strings.HasPrefix(line, "data: ") {
				data := strings.TrimPrefix(line, "data: ")
				if data == "[DONE]\n" {
					break
				}

				var response ChatCompletionResponse
				if err := json.Unmarshal([]byte(data), &response); err != nil {
					continue
				}

				for _, choice := range response.Choices {
					content := choice.Delta.Content
					cleanedContent := CleanContent(content)
					aiResponse += cleanedContent
					fmt.Print(cleanedContent)
				}
			}
		}

		// Add a newline after the AI's response
		fmt.Println()

		conversationHistory = append(conversationHistory, Message{Role: "assistant", Content: aiResponse})
	}
}

func printHelp() {
	fmt.Println("Available commands:")
	fmt.Println("  help    - Show this help message")
	fmt.Println("  clear   - Clear the conversation history")
	fmt.Println("  exit    - Exit the interactive shell")
}

func main() {
	debug := flag.Bool("debug", false, "Enable debug output")
	prompt := flag.String("prompt", defaultPrompt, "Custom prompt for summarization")
	service := flag.Bool("service", false, "Run llamafile as a service")
	stop := flag.Bool("stop", false, "Stop the running llamafile service")
	status := flag.Bool("status", false, "Check if the llamafile service is running")
	llamafile := flag.String("llamafile", "", "Path to the llamafile executable")

	flag.Parse()
	files := flag.Args()

	ConfigureLogging(*debug)

	client, err := NewLlamafileClient(*llamafile, *service || *stop)
	if err != nil {
		fmt.Printf("Error: %s\n", err.Error())
		os.Exit(1)
	}

	if *stop {
		if err := client.StopLlamafile(); err != nil {
			fmt.Printf("Error stopping llamafile: %s\n", err.Error())
			os.Exit(1)
		}
		fmt.Println("Llamafile service stopped")
		return
	}

	if *status {
		CheckServerStatus()
		return
	}

	if *service {
		if err := client.StartLlamafile(true); err != nil {
			fmt.Printf("Error starting llamafile as a service: %s\n", err.Error())
			os.Exit(1)
		}
		fmt.Println("Llamafile running as a service")
		return
	}

	// Handle graceful shutdown
	c := make(chan os.Signal, 1)
	signal.Notify(c, os.Interrupt)
	defer signal.Stop(c)
	go func() {
		<-c
		if err := client.StopLlamafile(); err != nil {
			fmt.Printf("Error stopping llamafile: %s\n", err.Error())
		}
		os.Exit(1)
	}()

	// Start llamafile if not running
	conn, err := net.DialTimeout("tcp", fmt.Sprintf("%s:%d", client.host, client.port), 1*time.Second)
	if err != nil {
		if err := client.StartLlamafile(false); err != nil {
			fmt.Printf("Error starting llamafile: %s\n", err.Error())
			os.Exit(1)
		}
	} else {
		conn.Close()
		fmt.Println("Using running llamafile service")
	}

	if len(files) == 0 {
		InteractiveShell(client, *prompt)
	} else {
		for _, file := range files {
			content, err := ioutil.ReadFile(file)
			if err != nil {
				fmt.Printf("Error reading file %s: %s\n", file, err.Error())
				continue
			}
			messageContent := fmt.Sprintf("%s\n\n%s", *prompt, string(content))
			messages := []Message{
				{Role: "user", Content: messageContent},
			}
			resp, err := client.ChatCompletion(messages, false)
			if err != nil {
				fmt.Printf("An error occurred: %s\n", err.Error())
				continue
			}
			defer resp.Body.Close()
			bodyBytes, err := ioutil.ReadAll(resp.Body)
			if err != nil {
				fmt.Printf("An error occurred: %s\n", err.Error())
				continue
			}
			var response map[string]interface{}
			if err := json.Unmarshal(bodyBytes, &response); err != nil {
				fmt.Printf("Error parsing response: %s\n", err.Error())
				continue
			}
			choices, ok := response["choices"].([]interface{})
			if ok && len(choices) > 0 {
				choice := choices[0].(map[string]interface{})
				message, ok := choice["message"].(map[string]interface{})
				if ok {
					content, _ := message["content"].(string)
					cleanedContent := CleanContent(content)
					fmt.Println(cleanedContent)
				}
			}
		}
	}

	if err := client.StopLlamafile(); err != nil {
		fmt.Printf("Error stopping llamafile: %s\n", err.Error())
	}
}
