<img width="1300" alt="Colored Pig (1)" src="https://github.com/user-attachments/assets/609466bf-f338-47e1-be4e-a97e6ce42e5c" />

# Pig Docs

Pig is an API to launch and automate Windows apps. Plug this SDK into your AI Agent apps to give them a computer!

---

> **Warning**: This API and associated infrastructure are currently in alpha and will likely undergo changes.

## Table of Contents

- [Pig Docs](#pig-docs)
  - [Table of Contents](#table-of-contents)
  - [Installation](#installation)
  - [Quick Start Guide](#quick-start-guide)
    - [Authentication](#authentication)
    - [Basic Usage](#basic-usage)
    - [Resuming an Existing Session](#resuming-an-existing-session)
    - [Resource Management](#resource-management)
  - [Command Line Interface](#command-line-interface)
  - [API Reference](#api-reference)
    - [VM Class](#vm-class)
      - [Constructor](#constructor)
      - [Methods](#methods)
    - [Connection Class](#connection-class)
      - [Mouse Operations](#mouse-operations)
      - [Keyboard Operations](#keyboard-operations)
      - [Screen Operations](#screen-operations)
      - [Scripting](#scripting)
      - [Control Management](#control-management)
  - [Advanced Usage](#advanced-usage)
    - [Async](#async)
    - [Custom Image Configuration](#custom-image-configuration)
    - [Temporary VM Sessions](#temporary-vm-sessions)
  - [Configuration](#configuration)

## Installation

Install the package using pip:

```bash
pip install pig-python
```

This installation includes both the Python SDK and the `pig` command-line interface.

## Quick Start Guide

### Authentication

Set up your API key before using the SDK:

```bash
export PIG_SECRET_KEY=your_api_key
```

[Apply Here](https://pig.dev/alpha) to get your API key.

### Basic Usage

Here's a simple example to launch and interact with a VM:

```python
from pig import VM

# Create and connect to a new VM
vm = VM()
print("Starting VM...")
conn = vm.connect()  # Initial boot takes a few minutes

# Interact with the VM
conn.mouse_move(100, 100)  
conn.left_click(100, 100)  
conn.type("Hello, World!")
```

### Resuming an Existing Session

To reconnect to an existing VM:

```python
vm = VM(id="VM-ABCDEFG-ABCDEFG-ABCDEFG")
conn = vm.connect()
conn.type("Hello Again!")
```

> Hint: if you don't know the VM ID, you can use the `pig ls` CLI command to list all VMs.

### Resource Management

Always clean up your VMs when finished:

```python
# Option 1: Stop VM (persists to disk)
vm.stop()

# Option 2: Terminate VM (deletes the disk)
vm.terminate()
```

For automated scripts, use the context manager pattern:

```python
with VM().session() as conn:
    conn.mouse_move(100, 100)
    conn.left_click(100, 100)
    # VM automatically stops when the block exits
```
The context manager ensures your VMs stop.

> **Warning**: During the alpha period, VMs left running without activity may be manually stopped by the Pig team. But please be a good citizen and clean up after yourself.

## Command Line Interface

The `pig` CLI provides convenient VM management commands:

```bash
# List all VMs
pig ls

# Output format:
ID                          Status    Created
--------------------------  --------  ----------------
VM-6F25BH9-VHENR80-05CRX4Z  Running   2025-01-16 06:47
VM-6F228MS-Q0EEQR0-02JT39X  Running   2025-01-15 23:45
```

Available Commands:
- `pig ls`: List all VMs
- `pig create`: Create a new VM
- `pig start <vm_id>`: Start a specific VM
- `pig stop <vm_id>`: Stop a specific VM
- `pig terminate <vm_id>`: Terminate and delete a VM
- `pig img ls`: List available VM images
- `pig img snapshot --vm <vm_id> --tag <tag>`: Snapshot an existing VM into a new image. Destroys the parent VM.

## API Reference

### VM Class
The VM class is your interface for managing VMs, the cloud machines that run the Windows OS.

#### Constructor

```python
VM(
    id: Optional[str] = None,           # Optionally attach to existing VM.
                                        # If none, new VM will be created.

    image: Optional[Union[Windows, str]] = None, # OS image configuration
    temporary: bool = False,            # If True, terminates VM after session
    api_key: Optional[str] = None,      # API key (alternative to env var)
    log_level: str = "INFO",            # Log level for any informational messages
)
```

#### Methods

- `create() -> str`: Creates a new VM and returns its ID
- `connect() -> Connection`: Connects to the VM, creating if necessary
- `session() -> VMSession`: Creates a managed VM session
- `start()`: Starts the VM
- `stop()`: Stops the VM
- `terminate()`: Terminates and deletes the VM

> **Tip:** During development and exploration, prefer using the imperative API (`vm.start(), vm.stop()`) so you can watch the VM and experiment. Use the context manager (`vm.session()`) once you're ready to automate tasks.

### Connection Class

The connection class is your interface for interracting with a running VM. This is what you'll expose as Tools to your agent.

A Connection has the following methods:

#### Mouse Operations
- `cursor_position() -> Tuple[int, int]`: Get current cursor position
- `mouse_move(x: int, y: int)`: Move cursor to coordinates
- `left_click(x: Optional[int], y: Optional[int])`: Left click at current location, or at specified coordinates
- `left_click_drag(x: int, y: int)`: Click and drag from current location to target coordinates
- `double_click(x: Optional[int], y: Optional[int])`: Double click at current location, or at specified coordinates
- `right_click(x: Optional[int], y: Optional[int])`: Right click at current location, or at specified coordinates

#### Keyboard Operations
- `type(text: str)`: Type text into VM. Maps to keystrokes, executed with a short delay between each character.
- `key(combo: str)`: Send key combination (e.g., 'ctrl+c', 'alt+Tab'). Supports multiple key strokes separated by space (e.g., 'shift-h i ctrl+a ctrl+c')

#### Screen Operations
- `screenshot() -> bytes`: Capture screenshot (BMP format)
- `width -> int`: Get VM width (1024)
- `height -> int`: Get VM height (768)

#### Scripting
- `cmd(command: str, close_after: bool = False)`: Sends a workflow to the VM to open a cmd terminal and input a command. Close_after to close the terminal after running the script. Otherwise the terminal window will remain open.
- `powershell(command: str, close_after: bool = False)`: Sends a workflow to the VM to open a powershell terminal and input a command. Close_after to close the window after running the script. Otherwise the powershell window will remain open.

#### Control Management
- `yield_control()`: Transfer control to human operator. This makes all future interactions error until a button is clicked in the UI to grant control back to the agent.
- `await_control()`: Wait for control to be returned to the agent.

## Advanced Usage

### Async
All methods on VM and Connection can be made async by adding `.aio()` to the method call.

For example:
```python
from pig import VM
async def main():

    vm = VM()
    await vm.create.aio()

    async with vm.session.aio() as conn:
        await conn.left_click.aio(x=100, y=100)
        await conn.type.aio("Hello, World!")
```

### Custom Image Configuration

You can create custom VM images to use.
1. Connect to a machine from your desired base image.
2. Install your desired applications and configuration.
3. Use the below CLI command to snapshot the VM into a new image

```bash
# Snapshot VM into image
pig img snapshot --vm YOUR_VM_ID -t YOUR_CHOSEN_NAME

# View your images
pig img ls
```

Future VMs may then be created from these images 

via CLI:
```bash
pig create -i IMAGE_ID
```

or via the SDK:
```python
vm = VM(image="IMAGE_ID")
vm.create()
```


### Temporary VM Sessions

```python
vm = VM(temporary=True)
with vm.session() as conn:
    # VM terminates after block exit, rather than stopping.
    # This deletes the VM disk, making it no longer usable.
```

## Configuration

Environment Variables:
- `PIG_SECRET_KEY`: API authentication key
