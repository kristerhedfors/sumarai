# sumarai

**IMPORTANT NOTE: This project is primarily generated through AI assistance. Only the file `README.md.human` is human-written. All other files, including this README.md, are prompt-generated using the VSCode plugin Claude Dev and primarily the latest Anthropic Sonnet model.**

## Overview

The `sumarai` project is a demonstration of rapid LLM application development using a strict no-code workflow. It showcases the power of combining Visual Studio Code with the Claude Dev plugin (requires Anthropic API key and credits) to create a functional application through natural language prompting alone. The primary goal is to provide different types of summaries for files and content on a computer, as well as an interactive chat interface, all without writing a single line of code manually.

## Development Approach

This project employs a unique development methodology:

1. **No-Code Workflow**: The entire application is developed without manually writing any code. Instead, all code is generated through natural language prompts.

2. **Conversational Prompting**: The development process mimics a conversation with a skilled developer colleague. By describing features, requirements, and necessary changes in natural language, the AI assistant (Claude Dev) generates and modifies the codebase accordingly.

3. **Rapid Iteration**: This approach allows for quick iterations and adjustments, as changes can be requested and implemented through simple conversational prompts.

4. **AI-Driven Problem Solving**: Complex programming challenges are solved by leveraging the AI's vast knowledge of programming patterns, best practices, and problem-solving techniques.

This methodology demonstrates the potential of AI-assisted development in dramatically reducing the time and technical expertise required to create functional applications.

## Key Features

1. **Rapid LLM Application Development**: Demonstrates the ease and speed of developing LLM applications with AI assistance.
2. **llamafile Integration**: Highlights the capabilities of llamafile, an LLM packaging solution that enables:
   - Inference at competitive token rates using consumer hardware
   - Completion of meaningful tasks in isolated environments
   - Enhanced information security for sensitive applications
3. **Ollama Integration**: Supports using Ollama models as an alternative to llamafile.
4. **Zero-Dependencies Philosophy**: The project adheres to using only the standard Python library for all functionality.
5. **Flexible Executable Discovery**: Automatically locates the llamafile executable using a smart search algorithm.
6. **Interactive Shell**: Provides an interactive chat interface for real-time communication with the AI model.
7. **File Summarization**: Ability to summarize content from multiple files.
8. **Custom Prompts**: Allows users to specify custom prompts for summarization tasks.
9. **Service Mode**: Option to run llamafile as a background service.
10. **Debugging Support**: Includes a debug mode for detailed logging.
11. **API Information**: Ability to display current API and model information in the interactive shell.

## Technology Stack

- **IDE**: Visual Studio Code
- **AI Assistant**: Claude Dev plugin (Anthropic)
- **Local LLM**: llamafile APIs or Ollama
- **Programming Language**: Python (standard library only)
- **Additional Tools**: Various shell commands for file and content manipulation

## Zero-Dependencies Approach

The `sumarai` project has been implemented using only the standard library of Python. This approach aligns with the llamafile philosophy of minimizing external dependencies, resulting in:

- Improved portability across different environments
- Reduced security risks associated with third-party libraries
- Simplified deployment and maintenance

By using only built-in modules, we ensure that the client can run on any system with a standard Python installation, without the need for additional package management or potential compatibility issues.

## Getting Started

### Prerequisites

- Python 3.6 or higher
- llamafile executable (can be placed in PATH, current directory, or specified via LLAMAFILE_PATH environment variable)
- Alternatively, Ollama installed and running (if using Ollama mode)

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/sumarai.git
   cd sumarai
   ```

2. If using llamafile, download and set up the llamafile:
   ```
   wget https://huggingface.co/Mozilla/Meta-Llama-3.1-8B-Instruct-llamafile/resolve/main/Meta-Llama-3.1-8B-Instruct.Q6_K.llamafile
   mv Meta-Llama-3.1-8B-Instruct.Q6_K.llamafile llamafile
   chmod +x llamafile
   ```

3. Ensure you have the llamafile executable. You can either:
   - Place it in your system's PATH
   - Keep it in the current working directory
   - Set the LLAMAFILE_PATH environment variable to point to its location

4. If using Ollama, ensure it's installed and running on your system.

### Usage

There are two main ways to use the sumarai application:

1. **Interactive Shell Mode:**

   Run the script without any arguments to start the interactive shell:

   ```
   python sumarai.py
   ```

   This will launch an interactive chat interface where you can communicate with the AI model in real-time. Available commands in the interactive shell:
   - `help`: Show available commands
   - `clear`: Clear the conversation history
   - `info`: Display information about the current API and model
   - `exit`: Exit the interactive shell

2. **File Summarization Mode:**

   To summarize one or more files:

   ```
   python sumarai.py file1.txt file2.txt
   ```

   You can also specify a custom prompt for summarization:

   ```
   python sumarai.py --prompt "Provide a detailed analysis of:" file.txt
   ```

Additional options:

- `--debug`: Enable debug output
- `--service`: Run llamafile as a service (llamafile mode only)
- `--stop`: Stop the running llamafile service (llamafile mode only)
- `--status`: Check if the llamafile service is running (llamafile mode only)
- `--llamafile LLAMAFILE_PATH`: Specify the path to the llamafile executable
- `--ollama-model MODEL_NAME`: Specify the Ollama model to use (Ollama mode)

To use Ollama instead of llamafile, specify the Ollama model:

```
python sumarai.py --ollama-model MODEL_NAME [other options]
```

You can also set the OLLAMA_MODEL environment variable to specify the Ollama model.

## Llamafile Executable Search Order

When using llamafile mode, the `sumarai` project uses a smart search algorithm to locate the llamafile executable. The search order is as follows:

1. User-specified path (if provided via the --llamafile argument)
2. System PATH
3. Current working directory
4. LLAMAFILE_PATH environment variable

This flexible approach ensures that the script can find the llamafile executable in various setups without requiring manual configuration in most cases.

## Use Cases

The `sumarai` project is particularly useful for:

1. Developers exploring AI-assisted, no-code application development workflows
2. Organizations seeking to rapidly prototype and develop applications with minimal manual coding
3. Researchers studying the capabilities and limitations of AI-driven software development
4. Projects requiring secure, isolated LLM solutions with minimal dependencies
5. Users who want to interact with an AI model through a simple command-line interface
6. Developers interested in comparing local LLM solutions (llamafile vs Ollama)

## Running Tests

The `sumarai` project uses pytest for testing. To run the tests, follow these steps:

1. Ensure you have pytest installed. If not, you can install it using pip:
   ```
   pip install pytest
   ```

2. Navigate to the project root directory:
   ```
   cd /path/to/sumarai
   ```

3. Run the tests using pytest:
   ```
   pytest
   ```

   This command will discover and run all test files in the project.

4. For more verbose output, you can use:
   ```
   pytest -v
   ```

5. To run a specific test file, you can specify the file path:
   ```
   pytest test/test_sumarai_pytest.py
   ```

6. To run a specific test function, you can use the following format:
   ```
   pytest test/test_sumarai_pytest.py::test_function_name
   ```

Please note that some tests may require a running llamafile process. These tests are marked with `@pytest.mark.skip(reason="This test requires a running llamafile process")` and will be skipped by default. To run these tests, ensure you have a llamafile process running and remove the skip decorator.

## Future Development

This project serves as a starting point for further exploration and development in the field of AI-assisted, no-code LLM applications. We welcome contributions and ideas to expand its capabilities and use cases while maintaining the zero-dependencies philosophy and the no-code development approach. Some potential areas for future development include:

1. Enhancing the interactive shell with more features
2. Improving error handling and edge case management
3. Developing a graphical user interface (GUI) version of the application
4. Extending the summarization capabilities to handle more file formats and larger datasets
5. Integrating with other local LLM solutions
6. Implementing more advanced NLP tasks beyond summarization

## License

(TODO: Add license information)

## Contact

(TODO: Add contact information or contribution guidelines)

---

*Note: This README was generated and updated using the sumarai project itself, showcasing its capabilities in action.*