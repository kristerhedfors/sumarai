package main

import (
	"bufio"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"io/ioutil"
	"log"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

var logger *log.Logger

func configureLogging(debugEnabled bool) {
	logLevel := "INFO"
	if debugEnabled {
		logLevel = "DEBUG"
	}
	logger = log.New(os.Stdout, fmt.Sprintf("%s: ", logLevel), log.Ldate|log.Ltime|log.Lshortfile)
}

type LlamafileClient struct {
	ExecutablePath string
	APIKey         string
	Host           string
	Port           int
	process        *os.Process
}

func findExecutable() (string, error) {
	// Search in LLAMAFILE environment variable first
	envExecutable := os.Getenv("LLAMAFILE")
	fmt.Printf("Debug: Checking LLAMAFILE environment variable: %s\n", envExecutable)
	if envExecutable != "" {
		if _, err := os.Stat(envExecutable); err == nil {
			return envExecutable, nil
		}
	}

	// Search in PATH
	pathExecutable, err := exec.LookPath("llamafile")
	fmt.Printf("Debug: Checking PATH for llamafile executable: %s\n", pathExecutable)
	if err == nil {
		return pathExecutable, nil
	}

	// Search in current directory
	currentDir, err := os.Getwd()
	if err != nil {
		return "", fmt.Errorf("error getting current directory: %v", err)
	}
	currentDirExecutable := filepath.Join(currentDir, "llamafile")
	fmt.Printf("Debug: Checking current directory for llamafile executable: %s\n", currentDirExecutable)
	if _, err := os.Stat(currentDirExecutable); err == nil {
		return currentDirExecutable, nil
	}

	return "", fmt.Errorf("llamafile executable not found in LLAMAFILE environment variable, PATH, or current directory")
}

func NewLlamafileClient(executablePath string, apiKey string, host string, port int) (*LlamafileClient, error) {
	fmt.Printf("Debug: Creating LlamafileClient with ExecutablePath: %s\n", executablePath)
	var err error
	if executablePath == "" {
		executablePath, err = findExecutable()
		if err != nil {
			return nil, fmt.Errorf("failed to find llamafile executable: %v", err)
		}
	}

	if apiKey == "" {
		apiKey = generateAPIKey()
	}

	return &LlamafileClient{
		ExecutablePath: executablePath,
		APIKey:         apiKey,
		Host:           host,
		Port:           port,
	}, nil
}

func generateAPIKey() string {
	b := make([]byte, 16)
	_, err := rand.Read(b)
	if err != nil {
		logger.Fatalf("Error generating API key: %v", err)
	}
	return hex.EncodeToString(b)
}

func (c *LlamafileClient) StartLlamafile(daemon bool) error {
	cmd := exec.Command(c.ExecutablePath, "--api-key", c.APIKey)
	logger.Printf("Starting llamafile with command: %s", cmd.String())

	if daemon {
		return c.startDaemon(cmd)
	}

	var err error
	c.process, err = cmd.Process, cmd.Start()
	if err != nil {
		return fmt.Errorf("Error starting llamafile: %v", err)
	}

	logger.Println("Waiting for llamafile to start...")
	err = c.waitForServer()
	if err != nil {
		return err
	}
	logger.Println("Llamafile started successfully")
	return nil
}

func (c *LlamafileClient) startDaemon(cmd *exec.Cmd) error {
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	return cmd.Start()
}

func (c *LlamafileClient) waitForServer() error {
	timeout := time.After(60 * time.Second)
	tick := time.Tick(1 * time.Second)
	for {
		select {
		case <-timeout:
			return fmt.Errorf("Server did not become ready within the timeout period")
		case <-tick:
			resp, err := http.Get(fmt.Sprintf("http://%s:%d/v1/models", c.Host, c.Port))
			if err == nil && resp.StatusCode == http.StatusOK {
				resp.Body.Close()
				return nil
			}
		}
	}
}

func (c *LlamafileClient) StopLlamafile() error {
	if c.process == nil {
		return nil
	}
	logger.Println("Stopping llamafile process")
	err := c.process.Signal(os.Interrupt)
	if err != nil {
		return fmt.Errorf("Error stopping llamafile: %v", err)
	}
	_, err = c.process.Wait()
	if err != nil {
		return fmt.Errorf("Error waiting for llamafile to stop: %v", err)
	}
	logger.Println("Llamafile process stopped")
	return nil
}

func (c *LlamafileClient) ChatCompletion(messages []map[string]string, model string, stream bool) (io.ReadCloser, error) {
	url := fmt.Sprintf("http://%s:%d/v1/chat/completions", c.Host, c.Port)
	data := map[string]interface{}{
		"model":    model,
		"messages": messages,
		"stream":   stream,
	}
	jsonData, err := json.Marshal(data)
	if err != nil {
		return nil, fmt.Errorf("Error marshaling request data: %v", err)
	}

	req, err := http.NewRequest("POST", url, strings.NewReader(string(jsonData)))
	if err != nil {
		return nil, fmt.Errorf("Error creating request: %v", err)
	}

	req.Header.Set("Content-Type", "application/json")
	if c.APIKey != "" {
		req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", c.APIKey))
	}

	logger.Printf("Sending chat completion request to %s", url)
	logger.Printf("Request headers: %v", req.Header)
	logger.Printf("Request body: %s", jsonData)

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("Error in chat completion request: %v", err)
	}

	if resp.StatusCode != http.StatusOK {
		body, _ := ioutil.ReadAll(resp.Body)
		resp.Body.Close()
		return nil, fmt.Errorf("Error: %d, %s", resp.StatusCode, string(body))
	}

	return resp.Body, nil
}

func checkServerStatus() {
	resp, err := http.Get("http://localhost:8080/v1/models")
	if err != nil {
		fmt.Println("not running")
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusOK {
		fmt.Println("running")
	} else {
		fmt.Println("not running")
	}
}

func interactiveShell(client *LlamafileClient) {
	fmt.Println("Welcome to the interactive shell. Type 'help' for available commands or 'exit' to quit.")
	conversationHistory := []map[string]string{
		{"role": "system", "content": "You are a helpful AI assistant. Respond to the user's queries concisely and accurately."},
	}

	scanner := bufio.NewScanner(os.Stdin)
	for {
		fmt.Print("You: ")
		if !scanner.Scan() {
			break
		}
		userInput := strings.TrimSpace(scanner.Text())

		switch strings.ToLower(userInput) {
		case "exit":
			fmt.Println("Exiting interactive shell.")
			return
		case "help":
			fmt.Println("Available commands:")
			fmt.Println("  help    - Show this help message")
			fmt.Println("  clear   - Clear the conversation history")
			fmt.Println("  exit    - Exit the interactive shell")
			continue
		case "clear":
			conversationHistory = []map[string]string{conversationHistory[0]}
			fmt.Println("Conversation history cleared.")
			continue
		}

		conversationHistory = append(conversationHistory, map[string]string{"role": "user", "content": userInput})
		response, err := client.ChatCompletion(conversationHistory, "local-model", true)
		if err != nil {
			fmt.Printf("Error: %v\n", err)
			continue
		}

		fmt.Print("AI: ")
		scanner := bufio.NewScanner(response)
		scanner.Split(bufio.ScanLines)
		var aiResponse strings.Builder
		for scanner.Scan() {
			line := scanner.Text()
			if strings.HasPrefix(line, "data: ") {
				var data map[string]interface{}
				err := json.Unmarshal([]byte(line[6:]), &data)
				if err != nil {
					continue
				}
				if choices, ok := data["choices"].([]interface{}); ok && len(choices) > 0 {
					if choice, ok := choices[0].(map[string]interface{}); ok {
						if delta, ok := choice["delta"].(map[string]interface{}); ok {
							if content, ok := delta["content"].(string); ok {
								fmt.Print(content)
								aiResponse.WriteString(content)
							}
						}
						if finishReason, ok := choice["finish_reason"].(string); ok && finishReason != "" {
							fmt.Println()
							break
						}
					}
				}
			}
		}
		conversationHistory = append(conversationHistory, map[string]string{"role": "assistant", "content": aiResponse.String()})
		response.Close()
	}
}

func main() {
	var debugEnabled bool
	var prompt string
	var runAsService bool
	var stop bool
	var checkStatus bool
	var files []string

	for i := 1; i < len(os.Args); i++ {
		arg := os.Args[i]
		switch arg {
		case "--debug":
			debugEnabled = true
		case "-p", "--prompt":
			if i+1 < len(os.Args) {
				i++
				prompt = os.Args[i]
			}
		case "--service":
			runAsService = true
		case "--stop":
			stop = true
		case "--status":
			checkStatus = true
		default:
			files = append(files, arg)
		}
	}

	if prompt == "" {
		prompt = "Summarize the following content:"
	}

	configureLogging(debugEnabled)

	if !runAsService && !stop && !checkStatus && len(files) == 0 {
		client, err := NewLlamafileClient("", "", "localhost", 8080)
		if err != nil {
			logger.Fatalf("Error creating LlamafileClient: %v", err)
		}

		defer client.StopLlamafile()
		err = client.StartLlamafile(false)
		if err != nil {
			logger.Fatalf("Error starting Llamafile: %v", err)
		}
		interactiveShell(client)
		return
	}

	client, err := NewLlamafileClient("", "", "localhost", 8080)
	if err != nil {
		logger.Fatalf("Error creating LlamafileClient: %v", err)
	}

	if stop {
		err = client.StopLlamafile()
		if err != nil {
			logger.Fatalf("Error stopping Llamafile service: %v", err)
		}
		logger.Println("Llamafile service stopped")
		return
	}

	if checkStatus {
		checkServerStatus()
		return
	}

	if runAsService {
		err = client.StartLlamafile(true)
		if err != nil {
			logger.Fatalf("Error starting Llamafile service: %v", err)
		}
		logger.Println("Llamafile running as a service")
		return
	}

	for _, file := range files {
		content, err := ioutil.ReadFile(file)
		if err != nil {
			logger.Printf("Error reading file %s: %v", file, err)
			continue
		}
		messages := []map[string]string{
			{"role": "user", "content": fmt.Sprintf("%s\n\n%s", prompt, string(content))},
		}
		response, err := client.ChatCompletion(messages, "local-model", false)
		if err != nil {
			logger.Printf("Error in chat completion for file %s: %v", file, err)
			continue
		}
		defer response.Close()
		body, err := ioutil.ReadAll(response)
		if err != nil {
			logger.Printf("Error reading response for file %s: %v", file, err)
			continue
		}
		var result map[string]interface{}
		err = json.Unmarshal(body, &result)
		if err != nil {
			logger.Printf("Error parsing response for file %s: %v", file, err)
			continue
		}
		if choices, ok := result["choices"].([]interface{}); ok && len(choices) > 0 {
			if choice, ok := choices[0].(map[string]interface{}); ok {
				if message, ok := choice["message"].(map[string]interface{}); ok {
					if content, ok := message["content"].(string); ok {
						fmt.Println(content)
					}
				}
			}
		}
	}
}
