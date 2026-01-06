FROM alpine
ADD onefilesync-agent.sh /
RUN apk --no-cache update \
    && apk --no-cache add bash openssl netcat-openbsd \
    && chmod +x /onefilesync-agent.sh
CMD ["/onefilesync-agent.sh"]

# build cmd
# $ docker build -t onefilesync-agent .

# run
# $ docker run --restart=unless-stopped --name onefilesync-agent -d -v /path/to/filefolder:/folder -e SERVER="127.0.0.1" -e TOKEN="mylongsecrettoken" -e SYNCFILE="/folder/myfile" -e SYNC_INTERVAL=60 onefilesync-agent


###########################################################
# # .env file / environment vars:
# # must be set:
# SERVER="127.0.0.1"
# TOKEN="mylongsecrettoken"  # same as listener
# SYNCFILE="/folder/file"
###########################################################
#
# # may be set / can be left out
# LISTENER_PORT=48444
# LOGLEVEL=1   #  0 : error, 1 : info, 2 : debug
# LOGFILE="/tmp/onefilesync-listener.log"
# OSTYPE="LINUX"   # LINUX or BSD (BSD is untested)
# SYNC_INTERVAL=10  # how often the file will be synced with the listener
###########################################################
