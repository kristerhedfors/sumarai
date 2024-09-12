# summarai

## Overview

The `summarai` project is a demonstration of rapid LLM application development using advanced dev support tools. It showcases the power of combining Visual Studio Code with the Claude Dev plugin (requires Anthropic API key and credits) to interact with local llamafile APIs, alongside various shell commands. The primary goal is to provide different types of summaries for files and content on a computer.

## Key Features

1. **Rapid LLM Application Development**: Demonstrates the ease and speed of developing LLM applications with modern tools.
2. **llamafile Showcase**: Highlights the capabilities of llamafile, an LLM packaging solution that enables:
   - Inference at competitive token rates using consumer hardware
   - Completion of meaningful tasks in isolated environments
   - Enhanced information security for sensitive applications
3. **Zero-Dependencies Philosophy**: The project adheres to the llamafile zero-dependencies approach, using only the Python standard library for all functionality.
4. **Flexible Executable Discovery**: Automatically locates the llamafile executable using a smart search algorithm.

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

Run the script with a message:

```
python summarai.py --message "Your message here"
```

If you want to specify a custom path for the llamafile executable:

```
python summarai.py --executable /path/to/llamafile --message "Your message here"
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

## Future Development

This project serves as a starting point for further exploration and development in the field of LLM applications, emphasizing minimal dependencies and standard library usage. We welcome contributions and ideas to expand its capabilities and use cases while maintaining the zero-dependencies philosophy.

## License

(TODO: Add license information)

## Contact

(TODO: Add contact information or contribution guidelines)

---

*Note: This README was generated and updated using the summarai project itself, showcasing its capabilities in action.*