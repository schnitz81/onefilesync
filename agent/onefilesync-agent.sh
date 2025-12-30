#!/usr/bin/env bash

# variables that must be set:
# --------------------------------------------------------------------------
SERVER="127.0.0.1"
TOKEN="mylongsecrettoken"  # same as listener
SYNCFILE="$HOME/temp/testfile.txt"
# --------------------------------------------------------------------------

# variables that may be set
# --------------------------------------------------------------------------
LISTENER_PORT="48444"
LOGLEVEL=1   #  0 : error, 1 : info, 2 : debug
LOGFILE="/tmp/onefilesync-agent.log"
OSTYPE="LINUX"  # LINUX or BSD (BSD is untested)
SYNC_INTERVAL=60  # how often the file will be synced with the listener
# --------------------------------------------------------------------------


# internal vars:
listener_recent_change=1
GRACEPERIOD=5  # time after a file change that it can be synced
CHANGE_SYNC_INTERVAL=2  # sync check this often when change was recently made
DEPENDENCIES=("nc" "base64" "openssl" "gzip" "md5sum")


function log() {
	local logmsg="$1"
	local msglevel="$2"

	# determine if log message is to be printed
	if [ "$LOGLEVEL" -ge "$msglevel" ]; then
		echo "$(date +"%Y%m%d %H:%M:%S") $logmsg" | tee -a "$LOGFILE"
	fi
}


function dependencies_check() {
	# dependency check
	for dependency in "${DEPENDENCIES[@]}"; do
		if ! command -v "$dependency" &> /dev/null; then
			if [ "$dependency" != "nc" ]; then
				echo "$dependency not found."
			else  # specific info about netcat version needed if missing
				echo "netcat not found. netcat-openbsd version of netcat needed."
			fi
			exit 1
		fi
	done
}

function syncfile_exists() {
	if [ ! -f "$SYNCFILE" ]; then
		log "ERROR: Syncfile: $SYNCFILE not found." "0"
		exit 1
	fi
}

function get_current_md5(){
	syncfile_exists
	file_md5=$(md5sum "$SYNCFILE" | cut -f 1 -d ' ')
	if [ -z "$file_md5" ]; then
	  log "ERROR: md5sum for $SYNCFILE could not be fetched."; exit 1
	fi
	echo "$file_md5"
}

function syncfile_changed_recently() {
  # check if file changed the last few seconds
  local now=$(date +%s)
  if [ "$OSTYPE" == "LINUX" ]; then
    local changed_epoch=$(stat -c "%Y" "$SYNCFILE")
  elif [ "$OSTYPE" == "BSD" ]; then
    local changed_epoch=$(stat -f "%m" "$SYNCFILE")
  else
    log "ERROR: Unknown OSTYPE: $OSTYPE" "0"
    return 1
  fi
  # check if values are valid.
  if [ -z "$now" ]; then
    log "ERROR: Unable to retreive current epoch." "0"
    return 1
  elif [ -z "$changed_epoch" ]; then
    log "ERROR: Unable to retreive changed epoch of file." "0"
    return 1
  fi
  # calculate time difference to see if the file was changed within the grace period
  if [ "$((now-changed_epoch))" -lt "$GRACEPERIOD" ]; then
    true
  else
    false
  fi
}

function encrypt() {
	local unencrypted_data="$1"
	openssl aes-256-cbc -md sha3-512 -a -pbkdf2 -k "$TOKEN" -in <(echo "$unencrypted_data")
}

function decrypt() {
	local encrypted_data="$1"
	openssl aes-256-cbc -d -a -md sha3-512 -pbkdf2 -k "$TOKEN" -in <(echo "$encrypted_data")
}

function file_to_base64() {
  local file="$1"
  if [ -z "$file" ]; then
    log "ERROR: No filepath given to base64_to_file function." "0"
  fi
  base64 -w0 < "$file"
}

function base64_to_file() {
  local b64data="$1"
  local file="$2"
  # check input
  if [ -z "$b64data" ] || [ -z "$file" ]; then
    log "ERROR: Invalid input to base64_to_file function." "0"
  fi
  base64 -d <<< "$b64data" > "$file"
}

function send_to_listener() {
	local data="$1"
	if [ -z "$data" ]; then
	  log "ERROR: No input data to send_to_listener function." "0"
	fi
	response=$(echo "$data" | nc -N -w 5 "$SERVER" "$LISTENER_PORT")
	if [[ $? -ne 0 ]]; then  # check server connectivity
		log "ERROR: Connection error. No server response." "0"
	fi
	# return listener response to function call if listener returns a response
	if [ -n "$response" ]; then
	  echo -n "$response"
	fi
}

dependencies_check
syncfile_exists

while true; do

  # interval pause
  if [[ $listener_recent_change -eq 1 ]]; then
    sleep "$CHANGE_SYNC_INTERVAL"
  else
    sleep "$SYNC_INTERVAL"
  fi

  if syncfile_changed_recently; then
    while syncfile_changed_recently; do  # grace period
      log "Agent syncfile changed recently. Running grace period." "1"
      sleep "$GRACEPERIOD"
    done
  fi

  # update current_md5
  current_md5=$(get_current_md5)
  if [ -z "$current_md5" ]; then
    log "ERROR: Unable to fetch md5sum of $SYNCFILE." "0"
    exit 1
  fi

  log "Sending CMPMD5 to listener" "2"
	encrypted_response=$(send_to_listener "$(encrypt "CMPMD5 $current_md5")")

	if [ -z "$encrypted_response" ] || [[ "$encrypted_response" == *"No server response"* ]]; then
	  log "ERROR: No data received from listener." "0"
	  continue
	fi
  decrypted_response=$(decrypt "$encrypted_response")
  response_cmd=$(echo "$decrypted_response" | cut -f 1 -d ' ')

	case $response_cmd in
    AGENTSYNCED)
      log "Agent synced with listener." "2"
      listener_recent_change=0
      ;;

    LISTENERFILECHANGEDRECENTLY)
      log "Listener reported recent file change. Requesting every $CHANGE_SYNC_INTERVAL seconds." "2"
      listener_recent_change=1
      ;;

    REQAGENTTORECEIVE)
      log "Listener file changed - requesting file from listener." "1"
      log "Sending FILEREQUEST." "2"
      listener_recent_change=0
      filerequest_response="$(send_to_listener "$(encrypt "FILEREQUEST")")"
      log "Decrypting filerequest response." "2"
      decrypted_filerequest_response="$(decrypt "$filerequest_response")"

      # verify response to FILEREQUEST
      if [ "$(echo "$decrypted_filerequest_response" | cut -d ' ' -f 1)" != "LISTENERFILESEND" ]; then
        log "ERROR: LISTENERFILESEND not received. Response unexpected." "0"
      else
        log "LISTENERFILESEND received. Proceeding to decode received file." "2"
        received_md=$(echo "$decrypted_filerequest_response" | cut -d ' ' -f 2)
        log "Writing received file." "2"
        base64_to_file "$(echo "$decrypted_filerequest_response" | cut -d ' ' -f 3)" "$SYNCFILE".tmp
        log "Checking written file with received md5sum." "2"
        written_file_md5=$(md5sum "$SYNCFILE".tmp | cut -f 1 -d ' ')
        if [ "$written_file_md5" == "$received_md" ]; then
          log "Received file OK." "1"
          mv "$SYNCFILE".tmp "$SYNCFILE"
          current_md5=$(get_current_md5)
          send_to_listener "$(encrypt "AGENTRECEIVEDFILEOK")" 1>/dev/null
        else
          log "ERROR: md5sum of received file does not match received file. Not overwriting old file." "2"
          send_to_listener "$(encrypt "AGENTRECEIVEDFILEERROR")" 1>/dev/null
        fi
      fi
      ;;

    REQAGENTTOSEND)
      log "Agent file changed. Sending file to listener." "1"

      # last check for additional change before sending
      if [ "$current_md5" != "$(get_current_md5)" ]; then
        log "Additional file change detected. Reverting to grace time instead of sending file." "1"
        listener_recent_change=1
        continue
      else
        log "File unchanged since md5 comparison." "2"
        listener_recent_change=0
      fi

      log "Fetching local file to be sent." "2"
      b64file="$(file_to_base64 "$SYNCFILE")"
      # send file
      log "Sending file..." "2"
      filesend_response=$(send_to_listener "$(encrypt "FILESEND $current_md5 $b64file")")
      log "Decrypting filesend response" "2"
      decrypted_filesend_response=$(decrypt "$filesend_response")

      # evaluate response after sending file to listener
      if [ "$(echo "$decrypted_filesend_response" | cut -d ' ' -f 1)" == "LISTENERRECEIVEDFILEOK" ]; then
          log "Listener received file OK." "1"
      elif [ "$(echo "$decrypted_filesend_response" | cut -d ' ' -f 1)" == "LISTENERRECEIVEDFILEERROR" ]; then
        log "ERROR: Listener didn't receive file successfully." "0"
      else
        log "ERROR: Unknown error when sending file to listener." "0"
      fi
      ;;

    NOVALIDDATA)
      log "No valid data received." "0"
      listener_recent_change=0
      ;;

    *)
      log "Unknown error." "0"
      listener_recent_change=0
      ;;
	esac
done

