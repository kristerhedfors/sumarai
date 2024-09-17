# summarai

**IMPORTANT NOTE: This project is primarily generated through AI assistance. Only the file `README.md.human` is human-written. All other files, including this README.md, are prompt-generated using the VSCode plugin Claude Dev and primarily the latest Anthropic Sonnet model.**

## Overview

The `summarai` project is a demonstration of rapid LLM application development using advanced dev support tools. It showcases the power of combining Visual Studio Code with the Claude Dev plugin (requires Anthropic API key and credits) to interact with local llamafile APIs, alongside various shell commands. The primary goal is to provide different types of summaries for files and content on a computer, as well as an interactive chat interface.

## Key Features

1. **Rapid LLM Application Development**: Demonstrates the ease and speed of developing LLM applications with modern tools.
2. **llamafile Showcase**: Highlights the capabilities of llamafile, an LLM packaging solution that enables:
   - Inference at competitive token rates using consumer hardware
   - Completion of meaningful tasks in isolated environments
   - Enhanced information security for sensitive applications
3. **Zero-Dependencies Philosophy**: The project adheres to the llamafile zero-dependencies approach, using only the Python standard library for all functionality.
4. **Flexible Executable Discovery**: Automatically locates the llamafile executable using a smart search algorithm.
5. **Interactive Shell**: Provides an interactive chat interface for real-time communication with the AI model.

## Technology Stack

- **IDE**: Visual Studio Code
- **AI Assistant**: Claude Dev plugin (Anthropic)
- **Local LLM**: llamafile APIs
- **Programming Language**: Python (standard library only)
- **Additional Tools**: Various shell commands for file and content manipulation

## Zero-Dependencies Approach

The `summarai` project, particularly the `summarai.py`, has been implemented using only the Python standard library. This approach aligns with the llamafile philosophy of minimizing external dependencies, resulting in:

- Improved portability across different environments
- Reduced security risks associated with third-party libraries
- Simplified deployment and maintenance

By using only built-in Python modules, we ensure that the client can run on any system with a standard Python installation, without the need for additional package management or potential compatibility issues.

## Getting Started

### Prerequisites

- Python 3.6 or higher
- llamafile executable (can be placed in PATH, current directory, or specified via LLAMAFILE environment variable)

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/summarai.git
   cd summarai
   ```

2. Ensure you have the llamafile executable. You can either:
   - Place it in your system's PATH
   - Put it in the current working directory
   - Set the LLAMAFILE environment variable to point to its location

### Usage

There are two main ways to use the summarai script:

1. **Interactive Shell Mode:**

   Run the script without any arguments to start the interactive shell:

   ```
   python summarai.py
   ```

   This will launch an interactive chat interface where you can communicate with the AI model in real-time. Available commands in the interactive shell:
   - `help`: Show available commands
   - `clear`: Clear the conversation history
   - `exit`: Exit the interactive shell

2. **File Summarization Mode:**

   To summarize one or more files:

   ```
   python summarai.py file1.txt file2.txt
   ```

   You can also specify a custom prompt for summarization:

   ```
   python summarai.py --prompt "Provide a detailed analysis of:" file.txt
   ```

Additional options:

- `--debug`: Enable debug output
- `--service`: Run llamafile as a service
- `--stop`: Stop the running llamafile service
- `--status`: Check if the llamafile service is running

If you want to specify a custom path for the llamafile executable:

```
python summarai.py --executable /path/to/llamafile [other options]
```

## Llamafile Executable Search Order

The `summarai` project uses a smart search algorithm to locate the llamafile executable. The search order is as follows:

1. User-specified path (if provided via the --executable argument)
2. System PATH
3. Current working directory
4. LLAMAFILE environment variable

This flexible approach ensures that the script can find the llamafile executable in various setups without requiring manual configuration in most cases.

## Use Cases

The `summarai` project is particularly useful for:

1. Developers looking to understand LLM application development workflows with minimal dependencies
2. Organizations requiring secure, isolated LLM solutions
3. Researchers exploring efficient LLM deployment on consumer hardware
4. Projects needing a lightweight, portable LLM client implementation
5. Users who want to interact with an AI model through a simple command-line interface

## Future Development

This project serves as a starting point for further exploration and development in the field of LLM applications, emphasizing minimal dependencies and standard library usage. We welcome contributions and ideas to expand its capabilities and use cases while maintaining the zero-dependencies philosophy.

## License

(TODO: Add license information)

## Contact

(TODO: Add contact information or contribution guidelines)

---

*Note: This README was generated and updated using the summarai project itself, showcasing its capabilities in action.*