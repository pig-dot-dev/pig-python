# Pig Docs

Pig is an API to launch and automate Windows apps. Plug this SDK into your AI Agent apps to give them a computer!

---

> **Warning**: This API and associated infrastructure are currently in alpha and will likely undergo changes.


## Getting Started

### Step 1: Install the Python SDK

```bash
pip install pig-python
```

### Step 2: Start Piglet

The Piglet is a process that runs on your Windows machine to drive the automations. 

Follow [this guide](https://github.com/pig-dot-dev/piglet/) to download it, and start it with the command:

```bash
# Start the Piglet server (exposes localhost:3000)
piglet start
```

### Step 3: Call It Locally

The SDK can be used from the same Windows machine to send automations to Piglet.

```python
from pig import Client
client = Client()

# Select your local machine
machine = client.machines.local()

# Start a connection and send a workflow
with machine.connect() as conn:
    conn.key("super")                     # Press Windows key
    conn.type("hello world!")             # Type text
```

### Step 4: Call It Over The Internet (Using Pig)

Your Piglet can be controlled over the internet by subscribing it as a machine in Pig's API.
> [Get your API key here](https://pig.dev/alpha)

```bash
# Start Piglet pointing to Pig's control server
piglet join --secret SK-YOUR_API_KEY
```

This will register your Piglet as a machine in Pig's API.

Now, from any computer, you can send automations to your connected Piglet.

Use the pig CLI to see your connected machines:
```bash
# List available machines
pig ls
```
```
ID                         state    Created
-------------------------  -------  ----------------
M-6HNGAXR-NT0B3VA-P33Q0R2  RUNNING  2025-02-10 23:31
```

And send an automation to it by specifying the machine ID.
```python
from pig import Client
client = Client()

# Select your remote machine
machine = client.machines.get("M-6HNGAXR-NT0B3VA-P33Q0R2")

# Start a connection and send a workflow
with machine.connect() as conn:
    conn.key("super")                     # Press Windows key
    conn.type("hello world!")             # Type text
```

## API Reference

### Machine Management

```python
# Get your local machine
machine = client.machines.local()

# Get a remote machine by ID
machine = client.machines.get("M-ABCD123")
```

### Connection APIs

```python
# All operations should use the context manager pattern
with machine.connect() as conn:
    # Keyboard
    conn.type("Hello World")              # Type text
    conn.key("super")                     # Press Windows key
    conn.key("ctrl+c ctrl+v")             # Key combinations
    
    # Mouse
    conn.mouse_move(x=100, y=100)         # Move cursor
    conn.left_click()                     # Click at current position
    conn.left_click(x=100, y=100)         # Move and click
    conn.right_click(x=100, y=100)        # Right click
    conn.double_click(x=100, y=100)       # Double click
    conn.left_click_drag(x=200, y=200)    # Click and drag
    
    # Screen
    image = conn.screenshot()             # Take screenshot
    x, y = conn.cursor_position()         # Get cursor position
    w, h = conn.dimensions()              # Get machine dimensions
    
    # Control
    conn.yield_control()                  # Give control to human
    conn.await_control()                  # Wait for control back
```

### CLI Reference

```bash
# List all machines
pig ls

# Example output:
ID                         state    Created
-------------------------  -------  ----------------
M-6HNGAXR-NT0B3VA-P33Q0R2  RUNNING  2025-02-10 23:31
