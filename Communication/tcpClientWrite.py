#!/usr/bin/env python
# This script was read data from a serial port forwarded to tcp with
# socat with the following command:
# sudo socat tcp-l:1234,reuseaddr,fork file:/dev/ttyACM0,nonblock,raw,echo=0,waitlock=/var/run/ttyACM0.lock,b9600

import socket

TCP_IP = '127.0.0.1'
TCP_PORT = 1234
BUFFER_SIZE = 1024

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((TCP_IP, TCP_PORT))
data = ""
MESSAGE = "HELLO"
while True :
    s.send(MESSAGE)

    
s.close()

