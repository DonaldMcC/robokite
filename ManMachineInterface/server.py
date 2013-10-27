#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# Copyright (c) 2013 Nautilabs
#
# Licensed under the MIT License,
# https://github.com/baptistelabat/robokite
# Authors: Baptiste LABAT
#
# Used http://www.linuxforu.com/2012/04/getting-started-with-html5-websockets/
 
import tornado.web
import tornado.websocket
import tornado.ioloop
import datetime
import os
import sys
import serial
import numpy as np
import time
import threading
import json
sys.path.append('..')
sys.path.append('../ObjectTracking')
import simpleTrack

global ser # Serial communication
global alpha # Pulse Width Modulation between -1 and 1
alpha = 0
global serialPending
serialPending = ''
global serialHistory
serialHistory = ''
mostRecentLine = ''
clients = [] # Stores the web client which are connected.
global kite

kite = simpleTrack.Kite()
cv_thread = threading.Thread(None, simpleTrack.Kite.track, None, (kite,))
try:
  cv_thread.start()
  print "Kite sensors properly initialised"
except:
  print "No kite sensors"

def computeXORChecksum(chksumdata):
	# Inspired from http://doschman.blogspot.fr/2013/01/calculating-nmea-sentence-checksums.html
    # Initializing XOR counter
    csum = 0
    
    # For each char in chksumdata, XOR against the previous 
    # XOR char.  The final XOR of the last char will be the
    # checksum  
    for c in chksumdata:
        # Makes XOR value of counter with the next char in line
        # and stores the new XOR value in csum
        csum ^= ord(c)
    h = hex(csum)    
    return h[2:] # Get hex data without 0x prefix
    
def openSerial():
  global ser
  
  # Loop over varying serial port till you find one (assume you have only one device connected)
  locations = ['/dev/ttyACM0','/dev/ttyACM1','/dev/ttyACM2','/dev/ttyACM3','/dev/ttyACM4','/dev/ttyACM5','/dev/ttyUSB0','/dev/ttyUSB1','/dev/ttyUSB2','/dev/ttyUSB3','/dev/ttyS0','/dev/ttyS1','/dev/ttyS2','/dev/ttyS3']
  for device in locations:
    try:
      print "Trying...",device
      ser = serial.Serial(device, baudrate=19200, timeout=1)
      print "Connected on ", device
      break
    except:
      print "Failed to connect on ", device
      
  time.sleep(1.5) # Arduino is reset when opening port so wait before communicating
  # An alternative would be to listen to a message from the arduino saying it is ready
  ser.write('i1') # i to start serial control, 1 is the minimum expecting message frequency (in house protocol)

def updateSerial():
    global alpha
    global ser
	
    try:
		# Send an in house proprietary message
		# 0: stands for open-source (by contradiction to P, which stands for proprietary!)
		# R: stands for robokite, the name of the project
		# PWM: stands for Pulse Width Modulation, the way the motor is controlled.
		msg = "ORPWM" + "," + str(alpha)
		msg = "$" + msg + "*" + computeXORChecksum(msg) + chr(13).encode('ascii')
		print "Send " + msg
		ser.write(msg)
    except Exception, e:
        print("Serial exception: " + str(e))
        
def updateFeedback():
    global alpha
    global ser
    global kite
	
    try:
		# Send an in house proprietary message
		# 0: stands for open-source (by contradiction to P, which stands for proprietary!)
		# R: stands for robokite, the name of the project
		# POS: stands for POSition
		msg = "ORPOS"+","+str(np.round(np.rad2deg(kite.orientation), 1))+","+str(np.round(np.rad2deg(kite.elevation), 1))+","+str(np.round(np.rad2deg(kite.bearing),1))
		msg = "$" + msg + "*" + computeXORChecksum(msg) + chr(13).encode('ascii')
		print "Send " + msg
		ser.write(msg)
    except Exception, e:
        print("Serial exception: " + str(e))
        

def checkSerial():
    global ser
    global serialPending
    
    try:
        s = ser.readline()
        print "Received from arduino: " + s
    except Exception, e:
        print("Error reading from serial port" + str(e))
        return
    
    if len(s):
        serialPending += s
        parseSerial()
    

#called whenever there is new input to check

def parseSerial():
    global serialHistory
    
    split = serialPending.split("\r\n")
    if len( split ) > 1:
        for line in split[0:-1]:
            
            #do some stuff with the line, if necessary
            #example:
            mostRecentLine = line
            #print "Received " + mostRecentLine
            # in this example, status will show the most recent line
            #serialHistory += line

        pending = split[-1]
 
class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("ui.html")
 
class WebSocketHandler(tornado.websocket.WebSocketHandler):
    def on_message(self, message):
        global ser
        global alpha
        
        self.write_message(u"Status OK " + message)
        print "received message from MMI: " + message
        msg = json.loads(message)
        if msg.get('id')=='pwm1':       
          alpha = float(msg.get('value'))/100.0
          msg = "ORPWM" + "," + str(alpha)
          msg = "$" + msg + "*" + computeXORChecksum(msg) + chr(13).encode('ascii')
          try:
            ser.write(msg)
            print "send " + msg
          except:
            print "time out exception"
        
    def open(self):
      global alpha
      
      openSerial()
      alpha = 0
      clients.append(self)
      self.write_message(u"Connected")
      print "Open web client connection"
      
    def on_close(self):
      clients.remove(self)
      print "Close web client connection"

handlers = [
    (r"/", MainHandler),
    (r"/websocket", WebSocketHandler),
]
settings = dict(
            static_path = os.path.join(os.path.dirname(__file__), "static"),
)
application = tornado.web.Application(handlers, **settings)

def timer():
    for c in clients:
        c.write_message(datetime.datetime.utcnow().strftime("%Y%m%d_%Hh%Mm_%Ss"))

if __name__ == "__main__":
    openSerial()
    application.listen(8080)
    mainLoop = tornado.ioloop.IOLoop.instance()
    scheduler = tornado.ioloop.PeriodicCallback(checkSerial, 10, io_loop = mainLoop)
    scheduler2 = tornado.ioloop.PeriodicCallback(updateSerial, 100, io_loop = mainLoop)
    schedulerFeedback = tornado.ioloop.PeriodicCallback(updateFeedback, 100, io_loop = mainLoop)
    scheduler.start()
    scheduler2.start()
    #schedulerFeedback.start()
    mainLoop.start()
    

