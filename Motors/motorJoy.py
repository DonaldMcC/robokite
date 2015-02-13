#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# Copyright (c) 2013 Nautilabs
#
# Licensed under the MIT License,
# https://github.com/baptistelabat/robokite
# Authors: Baptiste LABAT
#
# This script receives order from a USB joystick and send them to an arduino board
# using NMEA messages for robustness
# Press first button to switch to manual order
# Press second button to switch to open loop control
# Press third button to switch to closed loop control
# Press fourth button to switch to fully automatic control
# Use forward/backward motion to control one axis
# Use left/right motion to control other axis
# Use cross to trim joystick (independant for each mode)
# Use reset button to reset trim
#
# Warning: the joystick has to be in neutral position when plugged,
# otherwise it might be badly initialized
#
# Supports automatic reconnection of joystick and serial connection
# Tested on ubuntu 14.04

import time
import serial
import numpy as np
import pygame
from pygame.locals import *
from scipy.interpolate import interp1d
import os
try:
  from pymavlink import mavutil
  isMavlinkInstalled = True
except:
  isMavlinkInstalled = False

global msg1, msg2, mfb, power1, power2, mode, add_deadband

# Define a linear interpolation function to create a deadband
xi = [-1000, -127, -80, 80, 127, 1000]
yi = [-127, -127, 0, 0, 127, 127]
add_deadband = interp1d(xi, yi, kind='linear')

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
    return h[2:].zfill(2)# Get hex data without 0x prefix
    
def NMEA(message_type, value, talker_id= "OR"):
  msg = talker_id + message_type +","+ str(value)
  msg = "$"+ msg +"*"+ computeXORChecksum(msg) + str(chr(13).encode('ascii')) + str(chr(10).encode('ascii'))
  return msg

# Parameters for the serial connection
locations = ['/dev/ttyACM0','/dev/ttyACM1','/dev/ttyACM2','/dev/ttyACM3','/dev/ttyACM4','/dev/ttyACM5','/dev/ttyUSB0','/dev/ttyUSB1','/dev/ttyUSB2','/dev/ttyUSB3','/dev/ttyS0','/dev/ttyS1','/dev/ttyS2','/dev/ttyS3','COM1','COM2','COM3']
baudrate = 57600

ORDER_SAMPLE_TIME = 0.05 #seconds Sample time to send order without overwhelming arduino

MANUAL    = 0 # Control lines are released to enable manual control
JOY_OL    = 1 # Joystick controls voltage applied to motors (open loop control)
JOY_CL    = 2 # Joystick controls kite bar position in closed loop
AUTO      = 3 # Kite roll is stabilised thanks to IMU measurements, joystick controls the kite roll angle
mode = JOY_OL

joy_OL_offset_forward = 0
joy_OL_offset_right   = 0
joy_CL_offset_forward = 0
joy_CL_offset_right   = 0
auto_offset_forward   = 0
auto_offset_right     = 0

def resetOrder():
  global msg1, msg2, mfb, power1, power2, mode
  # Define the NMEA message in use
  if mode==JOY_OL:
    msg1 = NMEA("PW1", 0, "OR") # Order to first motor
    msg2 = NMEA("PW2", 0, "OR") # Order to second motor
  elif mode==JOY_CL:
    msg1 = NMEA("SP1", 0, "OR") # Order to first motor
    msg2 = NMEA("SP2", 0, "OR") # Order to second motor
  elif mode==AUTO:
    msg1 = NMEA("PW1", 0, "OR") # Order to first motor
    msg2 = NMEA("PW2", 0, "OR") # Order to second motor
  mfb  = NMEA("FBR", 0, "OR") # Feedback request
  power1 = 0
  power2 = 0

# Use pygame for the joystick

JOY_RECONNECT_TIME = 2 #seconds. Time to reconnect if no joystick motion

# Definition of gamepad button in use
FORWARD_BACKWARD_BUTTON = 2
LEFT_RIGHT_BUTTON = 3
RESET_OFFSET_BUTTON = 8

pygame.init()

# Read mavlink messages
if isMavlinkInstalled:
  try:
    master = mavutil.mavlink_connection('/dev/ttyUSB1', baud=57600, source_system=255) # 255 is ground station
  except:
    isMavlinkInstalled = False
    print("Mavlink connection failed")
rollspeed = 0
roll = 0

# This loop is here for robustness in case of deconnection
while True:
    for device in locations:
      try:
        print("Trying...", device)
        resetOrder()
        
        # First open with  baudrate zero and close to enable reconnection after deconnection
		# Thanks to Rémi Moncel for this trick http://robokite.blogspot.fr/2014/11/reconnexion-automatique-du-port-serie.html#comment-form
        ser = serial.Serial(device, baudrate=0, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=2, xonxoff=0, rtscts=0, interCharTimeout=None)   
        ser.close()
        # Note that by default arduino is restarting on serial connection
        ser = serial.Serial(device, baudrate=baudrate, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=2, xonxoff=0, rtscts=0, interCharTimeout=None)   
        print("Connected on ", device)
        break
      except:
        print("Failed to connect on ", device)
    # Wait so that arduino is fully awoken
    time.sleep(1.5)
        
    # Reset the timer    
    t0 = time.time()
    last_event_time = 0


    # This is the main program loop
    while True:

      # Deals with joystick deconnection and reconnection      
      if time.time()-last_event_time > JOY_RECONNECT_TIME:
         print("No joystick event for x seconds, trying reconnection")
         last_event_time = time.time()
         resetOrder()
         pygame.quit()
         pygame.init()
         pygame.joystick.init()
         actual_nb_joysticks = pygame.joystick.get_count()
         print("Number of joystick: ", actual_nb_joysticks)
         if actual_nb_joysticks > 0:
            my_joystick = pygame.joystick.Joystick(0)
            my_joystick.init()
            nb_joysticks = actual_nb_joysticks
            print("Joystick reinit")
      
      # Deals with gamepad events 
      for event in pygame.event.get():

        last_event_time = time.time()
        # Button events
        if event.type == JOYBUTTONDOWN:
            if event.button == MANUAL:
                mode = MANUAL
                print("MANUAL")
            elif event.button == JOY_OL:
                mode = JOY_OL
                print("JOY_OL: JOYSTICK OPEN LOOP")
            elif event.button == JOY_CL:
                mode = JOY_CL
                print("JOY_CL: JOYSTICK to BAR POSITION CLOSE LOOP")
            elif event.button == AUTO:
                mode = AUTO
                print("AUTO: JOYSTICK to KITE ROLL CLOSE LOOP")
            elif event.button == RESET_OFFSET_BUTTON:
                if mode == JOY_OL:
                  joy_OL_offset_forward = 0
                  joy_OL_offset_right   = 0
                elif mode == JOY_CL:
                  joy_CL_offset_forward = 0
                  joy_CL_offset_right   = 0
                elif mode == AUTO:
                  auto_offset_forward   = 0
                  auto_offset_right   = 0                  
        # Joystick events  
        if event.type == JOYAXISMOTION:
          if event.axis == FORWARD_BACKWARD_BUTTON:
            #print("power control ", event.value)
            power1 = event.value*127
          elif event.axis == LEFT_RIGHT_BUTTON :
            #print("direction control ", event.value)
            power2 = add_deadband(event.value*127)
            
        # Trim events
        if event.type == JOYHATMOTION:
            if mode == JOY_OL:
              joy_OL_offset_forward -= event.value[1]
              joy_OL_offset_right   += event.value[0]
            elif mode == JOY_CL:
              joy_CL_offset_forward -= event.value[1]
              joy_CL_offset_right   += event.value[0]
            elif mode == AUTO:
              auto_offset_forward   -= event.value[1]
              auto_offset_right     += event.value[0]
        
        # Create messages to be sent   
        if mode == JOY_OL:
            msg1 = NMEA("PW1", int(power1 + joy_OL_offset_right),   "OR")
            msg2 = NMEA("PW2", int(power2 + joy_OL_offset_forward), "OR")
        elif mode == JOY_CL:
            msg1 = NMEA("SP1", int(power1 + joy_CL_offset_right),   "OR")
            msg2 = NMEA("SP2", int(power2 + joy_CL_offset_forward), "OR")
        elif mode == AUTO:
            msg1 = NMEA("PW1", int(power1 + auto_offset_right + roll*180/np.pi), "OR")
            msg2 = NMEA("PW2", int(power2 + auto_offset_forward),   "OR")  # \todo: add regulation based on line tension?
        elif mode == MANUAL:
            msg1 = NMEA("PW1", 0, "OR")
            msg2 = NMEA("PW2", 0, "OR")     
            
      # Mavlink messages
      if isMavlinkInstalled:  
        msg = master.recv_match(type='ATTITUDE', blocking=False)
        if msg!=None:
          rollspeed = msg.rollspeed
          roll = msg.roll
          if mode == AUTO:
            msg1 = NMEA("PW1",  int(power1 + auto_offset_right + roll*180/np.pi), "OR")
    
      # Send messages 
      if time.time()-t0 > ORDER_SAMPLE_TIME:
        try:
            ser.write(msg1.encode())
            #print(msg1)
            ser.write(msg2.encode())
            #print(msg2)
            ser.write(mfb.encode())
            #print(mfb)
            t0 = time.time()
        except:
            print("break")
            ser.close()
            break

      try: # The ressource can be temporarily unavailable
        if ser.inWaiting() > 0:
            line = ser.readline()
            print("Received from arduino: ", line)
      except Exception as e:
        ser.close()
        print("Error reading from serial port" + str(e))
      
ser.close()
print("Closing")
