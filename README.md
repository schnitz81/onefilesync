# onefilesync

Minimal tool that keeps a single file two-way synced.

Works with multiple agents and non-aligned timezones.

## Requirements

### Listener
- Python 3 with standard modules (no pip installations).
- A tcp port (default 48444) needs to be reachable from the agent for the network communication.

### Agent
- netcat-openbsd
- openssl

## how-to
3 parameters need to be set:
### Agent:
- SERVER - The listener address needs to be set in the agent.
### Listener AND Agent
- TOKEN - A unique encryption token.
- SYNCFILE - Path to the file that is going to be kept in sync.

All parameters can be set in either of these ways:
- Directly in the .py/.sh file.
- Overridden with environment vars.

Listener only:
- As input arguments (run with --help for details).
- In a .env file placed in the same folder as the .py file. A minimal example included.

### Advanced settings
#### Agent
These additional parameters can also be set:
```
LISTENER_PORT="48444"
LOGLEVEL=1   #  0 : error, 1 : info, 2 : debug
LOGFILE="/tmp/onefilesync-agent.log"
OSTYPE="LINUX"  # LINUX or BSD (BSD is untested)
SYNC_INTERVAL=10   # how often the file will be synced with the listener
```
#### Listener
```
PORT = 48444
LOGLEVEL = 1   #  0 : error, 1 : info, 2 : debug
LOGFILE = "/tmp/onefilesync-listener.log"
GRACEPERIOD = 3
```

## Run as containers
The parameters can be set as environment vars. Run examples are available in the Dockerfiles respectively.

## Project goals

- Minimalism
    - 1 file agent, 1 file listener (OCI containers optional).
    - No non-standard Python modules.
    - Only netcat-openbsd needed as non-default tool on agent side.
- Low footprint
    - No webgui or third-party tools.
- Non-interfering
    - No need for SSH access or auth log pollution.
- Encrypted communication
    - All communication is encrypted with a unique token.
