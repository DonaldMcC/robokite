
// Copyright (c) 2013 Nautilabs
// https://github.com/baptistelabat/robokite

// Using example in http://code.google.com/p/arduino-pinchangeint/wiki/Usage

#define NO_PORTB_PINCHANGES // PortB used for mySofwareSerial
#include <PinChangeInt.h>
#include <Wire.h>

//Parts of code taken from http://playground.arduino.cc/Main/RotaryEncoders J.Carter(of Earth)

// 'threshold' is the De-bounce Adjustment factor for the Rotary Encoder. halfSteps
volatile unsigned long threshold = 1000;

// 'halfSteps' is the counter of half-steps. The actual
// number of steps will be equal to halfSteps / 2
//
volatile long halfSteps = 0;
long halfStepsCorrection = 0;

// Working variables for the interrupt routines
//
volatile unsigned long int0time = 0;
volatile unsigned long int1time = 0;
volatile uint8_t int0signal = 0;
volatile uint8_t int1signal = 0;
volatile uint8_t int0history = 0;
volatile uint8_t int1history = 0;

uint8_t latest_interrupted_pin;
uint8_t interrupt_count[20]={0}; // 20 possible arduino pins

int pinA = 2;
int pinB = 3;
int pinReset = 4;

boolean isAbsoluteReference = false;

// These constants won't change.  They're used to give names
// to the pins used:
const int potPin = 0;  // Analog input pin that the potentiometer is attached to
const int angleOutPin = 8; // Analog output pin for angle
const int positionOutPin = 13; // Analog output pin for angle

int sensorValue = 0;        // value read from the analog in pin
int potValue = 0; // value read from potentiometer

double linearResolution = 0.005; //Resolution of the linear encoder (in meters)
double linearRange = 0.5; //Range of the sensor to normalize data (+/- linearRange/2)

double potentiometerRangeDeg= 300; 
double potentiometerMaxRange = potentiometerRangeDeg * 3.1414/180;
double potentiometerUsedRange = 3.1415;
double potentiometerDistance = 0.05;

void int0()
{
  if ( micros() - int0time < threshold )
    return;
  int0history = int0signal;
  int0signal = bitRead(PIND,pinA);
  if ( int0history==int0signal )
    return;
  int0time = micros();
  if ( int0signal == int1signal )
    halfSteps++;
  else
    halfSteps--;
}

void int1()
{
  if ( micros() - int1time < threshold )
    return;
  int1history = int1signal;
  int1signal = bitRead(PIND,pinB);
  if ( int1history==int1signal )
    return;
  int1time = micros();
}

void reset()
{
  halfStepsCorrection = halfSteps;
  isAbsoluteReference = true;
 }

void setup() {
  pinMode(pinA, INPUT);
  digitalWrite(pinA, HIGH);
  attachInterrupt(0, int0, CHANGE);
  //PCintPort::attachInterrupt(pinA, &int0, CHANGE);
  pinMode(pinB, INPUT);
  digitalWrite(pinB, HIGH);
  attachInterrupt(1, int1, CHANGE);
  //PCintPort::attachInterrupt(pinB, &int1, CHANGE);
  
  // Pin used to get absolute position
  pinMode(pinReset, INPUT);
  digitalWrite(pinReset, HIGH);
  PCintPort::attachInterrupt(pinReset, &reset, CHANGE);
  
  // Setup serial communication
  Serial.begin(115200);
  Serial.println("---------------------------------------");

Wire.begin(); // Start I2C Bus as Master
}

void loop() {
  long steps = (halfSteps / 2);
  double absolute_position_m = (halfSteps-halfStepsCorrection)*linearResolution/2;
  double relative_position_m = (halfSteps)*linearResolution/2;
  
  // read the analog in value:
  potValue = analogRead(potPin);
  double raw_angle = potValue/1024.0*potentiometerMaxRange;
  double neutralAngle = 0.8*potentiometerMaxRange;
  double angle = raw_angle - neutralAngle;
  double correction_m = angle*potentiometerDistance; 
  
  analogWrite(angleOutPin, angle/potentiometerUsedRange*256 + 128);
  analogWrite(positionOutPin, (relative_position_m + correction_m)/linearRange*256 + 128);
  
  Wire.beginTransmission(9); // transmit to device #9
  Wire.write(int((relative_position_m + correction_m)/linearRange*256 + 128));              // sends x 
  Wire.endTransmission();
  
  Serial.print((absolute_position_m/linearRange)*1024 + 512);
  Serial.print(",");
  Serial.print(correction_m/linearRange*1024 + 512);
  Serial.print(",");
  Serial.print((absolute_position_m + correction_m)/linearRange*1024 + 512);
  Serial.print(",");
  Serial.print(angle/potentiometerUsedRange*1024 + 512);
  Serial.print(",");

  delay(2);
    
  for (int thisPin = 0; thisPin < 2; thisPin++) {
    sensorValue = analogRead(thisPin);                                 
    Serial.print(sensorValue); 
    Serial.print(",");  
    delay(2);   
  }
   Serial.println("");
  // wait 2 milliseconds before the next loop
  // for the analog-to-digital converter to settle
  // after the last reading:
  delay(20);  
}















