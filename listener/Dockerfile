FROM python:3-alpine
LABEL name="onefilesync-listener"
LABEL maintainer="schnitz81"
LABEL description="Listener for onefilesync - minimal tool that keeps a single file two-way synced."
LABEL url="https://github.com/schnitz81/onefilesync"
RUN apk --no-cache update && apk add --no-cache openssl
COPY onefilesync-listener.py /
ENTRYPOINT ["python","-u","onefilesync-listener.py"]

# build example
# $ docker build -t onefilesync-listener .
# run example
# docker run -d --name onefilesync-listener -p 48444:48444 -v /path/to/file.txt:/file.txt -e SYNCFILE="/file.txt" -e TOKEN="mylongsecrettoken" onefilesync-listener


###########################################################
# # .env file / environment vars:
# # must be set:
# TOKEN = "mylongsecrettoken"  # same as agent
# SYNCFILE = "/home/user/temp/testfile.txt"
###########################################################
#
# # may be set / can be left out
# PORT = 48444
# LOGLEVEL = 1   #  0 : error, 1 : info, 2 : debug
# LOGFILE = "/tmp/onefilesync-listener.log"
# GRACEPERIOD = 3
###########################################################