package main

import (
	"bufio"
	"bytes"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"io/ioutil"
	"log"
	"net/http"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"strings"
	"syscall"
	"time"
)

var debugEnabled bool

func debug(format string, v ...interface{}) {
	if debugEnabled {
		log.Printf(format, v...)
	}
}

type LlamafileClient struct {
	executablePath string
	apiKey         string
	host           string
	port           int
	cmd            *exec.Cmd
}

type Message struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type ChatCompletionResponse struct {
	Choices []struct {
		Message struct {
			Content string `json:"content"`
		} `json:"message"`
	} `json:"choices"`
}

func NewLlamafileClient(executablePath string) (*LlamafileClient, error) {
	path, err := findExecutable(executablePath)
	if err != nil {
		return nil, err
	}
	apiKeyBytes := make([]byte, 16)
	_, err = rand.Read(apiKeyBytes)
	if err != nil {
		return nil, err
	}
	apiKey := hex.EncodeToString(apiKeyBytes)
	client := &LlamafileClient{
		executablePath: path,
		apiKey:         apiKey,
		host:           "localhost",
		port:           8080,
	}
	return client, nil
}

func findExecutable(executablePath string) (string, error) {
	if executablePath != "" {
		if _, err := os.Stat(executablePath); err == nil {
			return executablePath, nil
		}
		return "", fmt.Errorf("Specified executable path %s not found.", executablePath)
	}

	// Search in PATH
	pathExecutable, err := exec.LookPath("llamafile")
	if err == nil {
		return pathExecutable, nil
	}

	// Search in current directory
	currentDirExecutable := filepath.Join(".", "llamafile")
	if _, err := os.Stat(currentDirExecutable); err == nil {
		return currentDirExecutable, nil
	}

	// Search in LLAMAFILE environment variable
	envExecutable := os.Getenv("LLAMAFILE")
	if envExecutable != "" {
		if _, err := os.Stat(envExecutable); err == nil {
			return envExecutable, nil
		}
	}

	return "", fmt.Errorf("Llamafile executable not found.")
}

func (client *LlamafileClient) StartLlamafile(daemon bool) error {
	cmdStr := fmt.Sprintf("%s --api-key %s", client.executablePath, client.apiKey)
	debug("Starting llamafile with command: %s", cmdStr)
	if daemon {
		cmd := exec.Command("/bin/sh", "-c", cmdStr)
		cmd.SysProcAttr = &syscall.SysProcAttr{
			Setpgid: true,
		}
		err := cmd.Start()
		if err != nil {
			return err
		}
		client.cmd = cmd
		debug("Daemon process started")
	} else {
		cmd := exec.Command("/bin/sh", "-c", cmdStr)
		stderr, err := cmd.StderrPipe()
		if err != nil {
			return err
		}
		stdout, err := cmd.StdoutPipe()
		if err != nil {
			return err
		}
		err = cmd.Start()
		if err != nil {
			return err
		}
		client.cmd = cmd

		// Handle termination signals
		c := make(chan os.Signal, 1)
		signal.Notify(c, os.Interrupt, syscall.SIGTERM)
		go func() {
			<-c
			client.StopLlamafile()
			os.Exit(1)
		}()

		// Discard or handle stdout and stderr as needed
		go func() {
			io.Copy(ioutil.Discard, stdout)
		}()
		go func() {
			io.Copy(ioutil.Discard, stderr)
		}()

		debug("Waiting for llamafile to start...")
		err = client.waitForServer()
		if err != nil {
			return err
		}
		debug("Llamafile started successfully")
	}
	return nil
}

func (client *LlamafileClient) waitForServer() error {
	timeout := 60 * time.Second
	checkInterval := 1 * time.Second
	startTime := time.Now()
	for time.Since(startTime) < timeout {
		resp, err := http.Get(fmt.Sprintf("http://%s:%d/v1/models", client.host, client.port))
		if err == nil && resp.StatusCode == http.StatusOK {
			resp.Body.Close()
			debug("Server is ready")
			return nil
		}
		if client.cmd.ProcessState != nil && client.cmd.ProcessState.Exited() {
			log.Printf("Llamafile process exited unexpectedly.")
			return fmt.Errorf("Llamafile failed to start")
		}
		time.Sleep(checkInterval)
	}
	return fmt.Errorf("Server did not become ready within the timeout period")
}

func (client *LlamafileClient) StopLlamafile() error {
	if client.cmd != nil && client.cmd.Process != nil {
		debug("Stopping llamafile process")
		err := client.cmd.Process.Signal(syscall.SIGTERM)
		if err != nil {
			return err
		}
		done := make(chan error)
		go func() { done <- client.cmd.Wait() }()
		select {
		case <-time.After(10 * time.Second):
			log.Println("Llamafile process did not terminate, forcing kill")
			err := client.cmd.Process.Kill()
			if err != nil {
				return err
			}
		case err := <-done:
			if err != nil {
				return err
			}
		}
		debug("Llamafile process stopped")
	}
	return nil
}

func (client *LlamafileClient) ChatCompletion(messages []Message, model string, stream bool) (*ChatCompletionResponse, io.ReadCloser, error) {
	url := fmt.Sprintf("http://%s:%d/v1/chat/completions", client.host, client.port)
	data := map[string]interface{}{
		"model":    model,
		"messages": messages,
		"stream":   stream,
	}
	jsonData, err := json.Marshal(data)
	if err != nil {
		return nil, nil, err
	}

	req, err := http.NewRequest("POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, nil, err
	}
	req.Header.Set("Content-Type", "application/json")
	if client.apiKey != "" {
		req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", client.apiKey))
	}

	debug("Sending chat completion request to %s", url)
	debug("Request headers: %v", req.Header)
	debug("Request body: %s", string(jsonData))

	clientHttp := &http.Client{}
	resp, err := clientHttp.Do(req)
	if err != nil {
		return nil, nil, err
	}

	if resp.StatusCode != http.StatusOK {
		bodyBytes, _ := ioutil.ReadAll(resp.Body)
		resp.Body.Close()
		return nil, nil, fmt.Errorf("Error: %d, %s", resp.StatusCode, string(bodyBytes))
	}

	if stream {
		return nil, resp.Body, nil
	} else {
		defer resp.Body.Close()
		var response ChatCompletionResponse
		err = json.NewDecoder(resp.Body).Decode(&response)
		if err != nil {
			return nil, nil, err
		}
		return &response, nil, nil
	}
}

func checkServerStatus() {
	resp, err := http.Get("http://localhost:8080/v1/models")
	if err != nil || resp.StatusCode != http.StatusOK {
		fmt.Println("not running")
	} else {
		fmt.Println("running")
	}
	if resp != nil {
		resp.Body.Close()
	}
}

func interactiveShell(client *LlamafileClient) {
	fmt.Println("Welcome to the interactive shell. Type 'help' for available commands or 'exit' to quit.")
	conversationHistory := []Message{
		{"system", "You are a helpful AI assistant. Respond to the user's queries concisely and accurately."},
	}

	printHelp := func() {
		fmt.Println("Available commands:")
		fmt.Println("  help    - Show this help message")
		fmt.Println("  clear   - Clear the conversation history")
		fmt.Println("  exit    - Exit the interactive shell")
	}

	reader := bufio.NewReader(os.Stdin)
	for {
		fmt.Print("You: ")
		userInput, err := reader.ReadString('\n')
		if err != nil {
			fmt.Println("Error reading input:", err)
			continue
		}
		userInput = strings.TrimSpace(userInput)
		if strings.ToLower(userInput) == "exit" {
			fmt.Println("Exiting interactive shell.")
			break
		} else if strings.ToLower(userInput) == "help" {
			printHelp()
			continue
		} else if strings.ToLower(userInput) == "clear" {
			conversationHistory = conversationHistory[:1] // Keep only the system message
			fmt.Println("Conversation history cleared.")
			continue
		}

		conversationHistory = append(conversationHistory, Message{"user", userInput})
		_, body, err := client.ChatCompletion(conversationHistory, "local-model", true)
		if err != nil {
			fmt.Println("An error occurred:", err)
			continue
		}
		fmt.Print("AI: ")
		aiResponse := ""
		buffer := ""
		reader := bufio.NewReader(body)
		for {
			line, err := reader.ReadString('\n')
			if err != nil {
				if err == io.EOF {
					break
				}
				fmt.Println("Error reading response:", err)
				break
			}
			buffer += line
			if strings.HasSuffix(buffer, "\n") {
				chunks := strings.Split(buffer, "\n")
				for _, chunk := range chunks {
					if strings.HasPrefix(chunk, "data: ") {
						dataStr := strings.TrimPrefix(chunk, "data: ")
						var data map[string]interface{}
						err := json.Unmarshal([]byte(dataStr), &data)
						if err != nil {
							// Incomplete JSON, skip
							continue
						}
						choices, ok := data["choices"].([]interface{})
						if !ok || len(choices) == 0 {
							continue
						}
						choice := choices[0].(map[string]interface{})
						delta, ok := choice["delta"].(map[string]interface{})
						if !ok {
							continue
						}
						if content, ok := delta["content"].(string); ok {
							aiResponse += content
							fmt.Print(content)
						}
						if finishReason, ok := choice["finish_reason"]; ok && finishReason != nil {
							fmt.Println()
							break
						}
					}
				}
				buffer = ""
			}
		}
		conversationHistory = append(conversationHistory, Message{"assistant", aiResponse})
	}
}

func main() {
	debugFlag := flag.Bool("debug", false, "Enable debug output")
	prompt := flag.String("prompt", "Summarize the following content:", "Custom prompt for summarization")
	service := flag.Bool("service", false, "Run llamafile as a service")
	stop := flag.Bool("stop", false, "Stop the running llamafile service")
	status := flag.Bool("status", false, "Check if the llamafile service is running")
	executablePath := flag.String("executable", "", "Path to the llamafile executable")
	flag.Parse()

	files := flag.Args()
	debugEnabled = *debugFlag

	if debugEnabled {
		log.SetFlags(log.LstdFlags | log.Lshortfile)
	} else {
		log.SetFlags(0)
		log.SetOutput(ioutil.Discard)
	}

	client, err := NewLlamafileClient(*executablePath)
	if err != nil {
		log.Fatalf("Error initializing LlamafileClient: %v", err)
	}

	if *stop {
		err := client.StopLlamafile()
		if err != nil {
			log.Fatalf("Error stopping llamafile service: %v", err)
		}
		log.Println("Llamafile service stopped")
		return
	}

	if *status {
		checkServerStatus()
		return
	}

	if *service {
		err := client.StartLlamafile(true)
		if err != nil {
			log.Fatalf("Error starting llamafile as service: %v", err)
		}
		log.Println("Llamafile running as a service")
		return
	}

	if len(files) == 0 {
		err := client.StartLlamafile(false)
		if err != nil {
			log.Fatalf("Error starting llamafile: %v", err)
		}
		defer client.StopLlamafile()
		interactiveShell(client)
	} else {
		err := client.StartLlamafile(false)
		if err != nil {
			log.Fatalf("Error starting llamafile: %v", err)
		}
		defer client.StopLlamafile()
		for _, file := range files {
			content, err := ioutil.ReadFile(file)
			if err != nil {
				log.Printf("Error reading file %s: %v", file, err)
				continue
			}
			messages := []Message{
				{"user", fmt.Sprintf("%s\n\n%s", *prompt, string(content))},
			}
			response, _, err := client.ChatCompletion(messages, "local-model", false)
			if err != nil {
				log.Printf("Error getting chat completion: %v", err)
				continue
			}
			if len(response.Choices) > 0 {
				contentResponse := response.Choices[0].Message.Content
				fmt.Println(contentResponse)
			} else {
				fmt.Println("No content in response")
			}
		}
	}
}
