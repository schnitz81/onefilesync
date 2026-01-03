# onefilesync

Minimal tool that keeps a single file two-way synced.

## Requirements

### Listener
Python 3 with standard modules (no pip installations).
A tcp port (default 48444) needs to be reachable from the agent for the network communication.
A Dockerfile / Docker image is available as an option. 

### Agent
netcat-openbsd

## how-to
3 parameters need to be set:
### Agent:
- SERVER - The listener address needs to be set in the agent.
### Listener AND Agent
- TOKEN - A unique encryption token.
- SYNCFILE - Path to the file that is going to be kept in sync.

The listener parameters can be set in either of three ways:
- Directly in the .py file.
- As environment vars.
- In a .env file in the same folder as the .py file. A minimal example included.

### Advanced settings
#### Agent
These extra parameters can be changed in the agent.
```
LISTENER_PORT="48444"
LOGLEVEL=1   #  0 : error, 1 : info, 2 : debug
LOGFILE="/tmp/onefilesync-agent.log"
OSTYPE="LINUX"  # LINUX or BSD (BSD is untested)
SYNC_INTERVAL=60  # How often
```
#### Listener
Just like the two previous parameters, these can be set as environment vars or in the optional .env file.  
```
PORT = 48444
LOGLEVEL = 1   #  0 : error, 1 : info, 2 : debug
LOGFILE = "/tmp/onefilesync-listener.log"
GRACEPERIOD = 5
```

## Project goals

- Minimalism
    - 1 file agent, 1 file listener (OCI container optional).
    - No non-standard Python modules.
    - Only netcat-openbsd needed as non-default tool on agent side.
- Low footprint
    - No webgui or third-party tools.
- Non-interfering
    - No need for SSH access or auth log pollution.
- Encrypted communication
    - All communication is encrypted with a unique token.