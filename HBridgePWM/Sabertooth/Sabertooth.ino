
// Copyright (c) 2013 Nautilabs. All rights reserved.
// http://code.google.com/p/robokite/source/checkout

// This file used SoftwareSerial example (Copyright (c) 2012 Dimension Engineering LLC) for Sabertooth http://www.dimensionengineering.com/software/SabertoothSimplifiedArduinoLibrary/html/index.html
// See license.txt in the Sabertooth arduino library for license details.
// It is as well derived from HBridgePWM.ino from robokite project
// http://code.google.com/p/robokite/source/browse/HBridgePWM/HBridgePWM.ino

#include <SoftwareSerial.h>
#include <SabertoothSimplified.h>

SoftwareSerial SWSerial(NOT_A_PIN, 11); // RX on no pin (unused), TX on pin 11 (to S1).
SabertoothSimplified ST(SWSerial); // Use SWSerial as the serial port.

const int analogInPin = A0;  // Analog input pin that the potentiometer is attached to

int sensorValue = 0;        // Value read from the potentiometer
int initialSensorValue = 0;
double alphaSigned = 0;
String inputString = "";         // A string to hold incoming data
boolean stringComplete = false;  // Whether the string is complete
boolean isSerialControl = false; 
boolean isManualControl = false;
// Read the analog in value
// The range was reduced 
double sensorValueMin = 200;//0
double sensorValueMax = 800;//1023
double deadBand = 0.1; // Use to ensure zero speed. Should not be zero
double serialFrequency = 0;
long lastSerialInputTime = 0;

void setup()
{
  // Initialize software serial communication with Sabertooth 
  SWSerial.begin(9600);
  // Initialize serial communications at 9600 bps:
  Serial.begin(9600); 
}

void serialEvent() {
  while (Serial.available()) {
    // Get the new byte:
    char inChar = (char)Serial.read();
    // Add it to the inputString:
    inputString += inChar;
    // If the incoming character is a newline, set a flag
    // so the main loop can do something about it:
    if (inChar == '\n') {
      stringComplete = true;
    }
  }
  if (inputString[0] == 'i')
  {
    isSerialControl = true;
    initialSensorValue = analogRead(analogInPin);
    if (inputString.substring(1)=="")
    {
      serialFrequency = 0;
    }
    else
    { 
      serialFrequency = StrToFloat(inputString.substring(1));
    } 
  }
  else
  {
   if (inputString == "o")
   {
     isSerialControl = false;
   }
   else
   {
     // To reject incorrect value due to 0. badly read
     if ((StrToFloat(inputString)>=-1) & (StrToFloat(inputString)<=1))
     {
       alphaSigned = StrToFloat(inputString);
       lastSerialInputTime = millis();
       Serial.println(alphaSigned);
     }
   }
  }
  Serial.println(inputString);
  inputString="";
}

void loop()
{
  int power;
  sensorValue = analogRead(analogInPin);
  setMode();
  computeAlphaSigned();
  
  power = alphaSigned*127;
  ST.motor(1, power);
  delay(20);
}

void setMode()
{  
  // If the analog value is changed, it means that the user wants to take control with the joystick
  // so fallback to joystick control
  if (fabs(initialSensorValue-sensorValue) > 10)
  {
    isSerialControl = false;
  }
	
  // Fallback to manual control if the analog voltage is close to zero (probably unplugged)
  // Place after hardware limit if possible
  // This avoids to go to full speed if one cable in the potentiometer is unplugged
  // Warning: if the midle cable of the potentiometer is unplugged, the signal is free, and the fault can not be detected
  // \todo invert polarity to be able to detect floating pin.
  isManualControl = (sensorValue < 5)|(sensorValue >1023-5);
}

float StrToFloat(String str){
  char carray[str.length() + 1]; // Determine the size of the array
  str.toCharArray(carray, sizeof(carray)); // Put str into an array
  return atof(carray);
}

void computeAlphaSigned()
{
  if (serialFrequency != 0)
  { // Fallbacks to zero as we received no message in the expected time (twice the time)
    if ((millis()-lastSerialInputTime) > 2*1/serialFrequency*1000)
    {
      alphaSigned = 0;
    }
  }
    // If not in Serial control overwrite the value 
  if (false == isSerialControl)
  {
    // Compute the value corresponding to the deadband
    double sensorDeadBandMax = sensorValueMin + (deadBand/2.0+0.5)*(sensorValueMax - sensorValueMin);
    double sensorDeadBandMin = sensorValueMin + (-deadBand/2.0+0.5)*(sensorValueMax - sensorValueMin);
    if (sensorValue < sensorDeadBandMin) //strictly to avoid alphaSigned equals zero
    {
      alphaSigned = (sensorValue-sensorValueMin)/(sensorDeadBandMax - sensorValueMin)-1;
    } 
    else
    {
      if (sensorValue > sensorDeadBandMax)
      {
        alphaSigned = (sensorValue-sensorDeadBandMax)/(sensorValueMax - sensorDeadBandMax);
      }
      else
      {
        alphaSigned = 0;
      }
    }
  }
  Serial.println(sensorValue);
  alphaSigned = min(1, max(-1, alphaSigned));
}
