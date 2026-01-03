import socket
import datetime
import subprocess
import base64
import hashlib
import os
import sys
import time
from pathlib import Path


# variables that must be set
# (can be overridden by environment variables or .env file)
###########################################################
TOKEN = "mylongsecrettoken"  # same as agent
SYNCFILE = "/home/user/testfile.txt"
###########################################################

# variables that can be set if needed
# (can be overridden by environment variables or .env file)
###########################################################
PORT = 48444
LOGLEVEL = 1   #  0 : error, 1 : info, 2 : debug
LOGFILE = "/tmp/onefilesync-listener.log"
GRACEPERIOD = 3
###########################################################


def set_env_vars():
    global PORT
    global TOKEN
    global SYNCFILE
    global LOGLEVEL
    global LOGFILE
    global GRACEPERIOD

    # .env file parsing
    env_file = Path(__file__).parent / ".env"
    envvars = {}
    if env_file.exists():
        with env_file.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                envvar, value = line.split("=", 1)
                envvar = envvar.strip()
                value = value.strip()
                envvars[envvar] = value

        # set env values available in .env file
        for envvar, value in envvars.items():
            os.environ[envvar] = value

    # environment variables
    if 'PORT' in os.environ:
        PORT = int(os.environ['PORT'])
    if 'TOKEN' in os.environ:
        TOKEN = os.environ['TOKEN']
    if 'SYNCFILE' in os.environ:
        SYNCFILE = os.environ['SYNCFILE']
    if 'LOGLEVEL' in os.environ:
        LOGLEVEL = int(os.environ['LOGLEVEL'])
    if 'LOGFILE' in os.environ:
        LOGFILE = os.environ['LOGFILE']
    if 'GRACEPERIOD' in os.environ:
        GRACEPERIOD = int(os.environ['GRACEPERIOD'])


def log(msg, msglevel):
    if LOGLEVEL >= msglevel:
        print(f"{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} {msg}")
        if LOGFILE:
            with open(LOGFILE, "a") as f:
                f.write(msg + '\n')



def file_exists(filepath):
    if os.path.exists(filepath):
        return True
    else:
        return False


def rename_file(old_filepath, new_filepath):
    try:
        os.rename(old_filepath, new_filepath)
        return True
    except Exception as rename_e:
        log("Error: Unable to rename file:", 0)
        log(rename_e, 0)
        return False


def decrypt(data):
    try:
        # decrypt data with TOKEN
        command = [
            'openssl', 'aes-256-cbc', '-d',
            '-md', 'sha3-512',
            '-a', '-pbkdf2',
            '-k', TOKEN
        ]
        # Use Popen to execute OpenSSL with piped input
        with subprocess.Popen(command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True) as proc:

            # Pass data to stdin
            openssl_output, openssl_error = proc.communicate(input=data)
            openssl_output = openssl_output.replace('\n', '')

            # Check for errors
            if proc.returncode != 0:
                # handling invalid received data
                if 'error reading input file' in openssl_error:
                    log(f"Invalid data received: {data}", 0)
                else:
                    log(openssl_error, 0)
        return openssl_output
    except UnicodeDecodeError as decode_e:
        log("Decoding error. Is the token same in listener and agent?", 0)
    except Exception as openssl_e:
        log(openssl_e, 0)


def encrypt(data):
    try:
        # encrypt data with TOKEN
        command = [
            'openssl', 'aes-256-cbc',
            '-md', 'sha3-512',
            '-a', '-pbkdf2',
            '-k', TOKEN
        ]
        # Use Popen to execute OpenSSL with piped input
        with subprocess.Popen(command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True) as proc:

            # Pass data to stdin
            openssl_output, openssl_error = proc.communicate(input=data)

            # Check for errors
            if proc.returncode != 0:
                log(openssl_error, 0)

        return openssl_output
    except Exception as openssl_e:
        log(openssl_e, 0)


def sync_file_changed_recently():
    try:
        epoch_now = int(time.time())
        if 'linux' in sys.platform.lower():
            filechanged_output = subprocess.run(f'''
                    stat -c "%Y" "{SYNCFILE}"
                ''',
                shell=True, check=True,
                executable='/bin/sh',
                capture_output=True,
                text=True
            )
            filechanged_epoch = int(filechanged_output.stdout.rstrip())
        elif 'bsd' in sys.platform.lower():
            filechanged_output = subprocess.run(f'''
                    stat -f "%m" "{SYNCFILE}"
                ''',
                shell=True, check=True,
                executable='/bin/sh',
                capture_output=True,
                text=True
            )
            filechanged_epoch = int(filechanged_output.stdout.rstrip())
        else:
            log("ERROR: Unrecognized OS.", 0)
            exit(1)
        if epoch_now - filechanged_epoch < GRACEPERIOD:
            return True
        else:
            return False
    except Exception as changetimeread_e:
        log(changetimeread_e, 0)


def get_md5(file):
    try:
        h = hashlib.md5()
        with open(file, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception as hashsum_e:
        log(hashsum_e, 0)


def file_to_base64(filepath):
    try:
        with open(filepath, "rb") as f:
            b64str = base64.b64encode(f.read()).decode('utf-8')
        return b64str
    except Exception as filetob64_e:
        log(filetob64_e, 0)


def base64_to_file(b64str, filepath):
    try:
        b64decoded = base64.b64decode(b64str)
        with open(filepath, 'wb') as f:
            f.write(b64decoded)
    except Exception as b64tofile_e:
        log(b64tofile_e, 0)


def process(data, addr):

    # decrypt received data
    decrypted_data = decrypt(data.decode("utf-8"))
    if decrypted_data is None:
        log("No valid data decrypted.", 0)
        return "NOVALIDDATA"

    log('Decrypted data:', 2)
    log(decrypted_data, 2)

    # get received command
    command = decrypted_data.split(' ')[0].rstrip()

    # sync check
    if command == 'REQMD5':
        log(f"command received from {addr}: REQMD5", 2)
        #received_md5 = decrypted_data.split(' ')[1].rstrip()
        current_md5 = get_md5(SYNCFILE)

        if current_md5 is None:
            log("Unable to get md5sum for local syncfile.", 0)
            exit(1)
        elif sync_file_changed_recently():
            log("Listener file changed recently - LISTENERFILECHANGEDRECENTLY", 2)
            return "LISTENERFILECHANGEDRECENTLY"
        else:
            log(f"returning LISTENERCURRENTMD5 {current_md5}" ,2)
            return f"LISTENERCURRENTMD5 {current_md5}"

    # agent is sending file
    elif command == 'FILESEND':
        log(f"Agent {addr} file changed. Receiving file from agent.", 1)
        received_md5 = decrypted_data.split(' ')[1]
        log(f"received_md5: {received_md5}", 2)
        received_file = decrypted_data.split(' ')[2]
        log("Saving received file.", 2)
        base64_to_file(received_file, f'{SYNCFILE}.tmp')

        # verify received file and overwrite old file if valid
        log("Checking received file against received md5sum.", 2)
        if get_md5(f'{SYNCFILE}.tmp') == received_md5:
            log("md5sum on received file is valid. Overwriting local file with received file." ,2)

            if rename_file(f'{SYNCFILE}.tmp', SYNCFILE):
                log("Received file OK.", 1)
                return "LISTENERRECEIVEDFILEOK"
        else:
            log(f"ERROR: md5sum on received file from {addr} is invalid. Not overwriting current local file.", 0)
            return "LISTENERRECEIVEDFILEERROR"

    # agent is expecting to receive file
    elif command == 'FILEREQUEST':
        log(f"Listener file changed - agent {addr} requesting file.", 1)
        log(f"Sending md5sum and file to agent {addr}.", 2)
        current_md5 = get_md5(SYNCFILE)
        b64file = file_to_base64(SYNCFILE)
        return f"LISTENERFILESEND {current_md5} {b64file}"

    # agent received file successfully
    elif command == 'AGENTRECEIVEDFILEOK':
        log(f"Agent {addr} received file OK.", 1)

    # agent received file error
    elif command == 'AGENTRECEIVEDFILEERROR':
        log(f"ERROR: Agent {addr} failed to receive file.", 0)

    elif command == '' or command is None:
        log(f"No valid data when processing request from {addr}.", 0)
        log("Returning NOVALIDDATA", 2)
        return "NOVALIDDATA"

    # Should never happen
    else:
        log("Error: Unknown command.", 0)


def tcp_listen_and_reply():

    # create a socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # bind the socket with server and port number
    s.bind(('0.0.0.0', PORT))

    # maximum connections allowed to the socket
    s.listen(1)

    while True:
        connsock, addr = s.accept()

        # display client address
        log(f"{datetime.datetime.now()} -------------------------------------------", 2)
        log(f"Connection from: {str(addr)}", 2)

        try:
            total_size = 1024 * 1024 * 500  # max 500 MB
            received_data = bytearray()
            bytes_received = 0
            while bytes_received < total_size:
                chunk = connsock.recv(32768)
                if not chunk:
                    break  # connection closed from agent
                received_data.extend(chunk)
                bytes_received += len(chunk)
            data = bytes(received_data)

        except ConnectionResetError as conn_error:
            log(f"Connection reset error: {conn_error}", 0)
            # disconnect the server
            connsock.close()
            continue

        # generate response
        returnmsg = encrypt(process(data, addr))
        log(f"returnmsg to parse: {returnmsg}", 2)

        try:
            connsock.send(returnmsg.encode('utf-8'))
            log("Responded.", 2)
        except Exception as send_e:
            log("Response send error:", 0)
            log(send_e, 0)
        # disconnect the server
        connsock.close()


def main():
    set_env_vars()
    if not file_exists(SYNCFILE):
        log(f"{SYNCFILE} not found. Please check your path and try again.", 0)
        exit(1)
    tcp_listen_and_reply()


if __name__ == '__main__':
    main()