#include <Servo.h>
#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <WiFiUdp.h>

#define HAND 14
#define ARM 12
#define FINGERL 13
#define FINGERR 15
#define INPUT_BOX 16

enum STATE{
  STATE_START = 0,
  STATE_HAND0,
  STATE_ARM0,
  STATE_FINGER0,
  STATE_ARM1,
  STATE_HAND1,
  STATE_FINGER1,
  STATE_STOP
};

Servo servoMotorHand;
Servo servoMotorArm;
Servo servoMotorFingerL;
Servo servoMotorFingerR;

unsigned long previousMillis = 0;
const long interval = 1000;
int ledState = LOW;

int dir = 1;

const char* ssid = "your ssid";
const char* password = "your password";

//Creating UDP Listener Object. 
WiFiUDP UDPServer;
unsigned int UDPPort = 1102;

byte packetBuffer[8];

int reqState = STATE_STOP;
int myState = STATE_STOP;

int angle = 0;

const int FINGER_ANGLE_R = 30;
const int FINGER_ANGLE_L = 30;
const int ARM_ANGLE = 90;
const int HAND_ANGLE = 90;

void setup() { 
  servoMotorHand.attach(HAND);
  servoMotorHand.write(0);

  servoMotorArm.attach(ARM);
  servoMotorArm.write(ARM_ANGLE);

  servoMotorFingerL.attach(FINGERL);
  servoMotorFingerL.write(0);

  servoMotorFingerR.attach(FINGERR);
  servoMotorFingerR.write(FINGER_ANGLE_R);

  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(INPUT_BOX, INPUT);

  WiFi.begin(ssid, password);
  Serial.begin(9600);
  Serial.println("");

  // Wait for connection
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.print("Connected to ");
  Serial.println(ssid);
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());

  UDPServer.begin(UDPPort); 

}

void loop() { 
  unsigned long currentMillis = millis();
  if (currentMillis - previousMillis >= interval) {
    previousMillis = currentMillis;
    if (ledState == LOW)
      ledState = HIGH;  // Note that this switches the LED *off*
    else
      ledState = LOW;   // Note that this switches the LED *on*
    digitalWrite(LED_BUILTIN, ledState);
    // angle += dir*5;
    // if(angle >= 90){
    //   dir = -1;
    // }else if(angle <= 0){
    //   dir = 1;
    // }
    // Serial.print(angle);
    // servoMotorHand.write(angle);
    // servoMotorArm.write(angle);
  }
  processPostData();
  actuatorControl();
  delay(10);
}

void actuatorControl(){
  if(myState==STATE_START){
    myState = STATE_HAND0;
  }else if(myState==STATE_HAND0){
    servoMotorHand.write(HAND_ANGLE);
    delay(500);
    myState = STATE_ARM0;
  }else if(myState==STATE_ARM0){
    if(angle <= ARM_ANGLE){
      angle += 5;
      servoMotorArm.write(ARM_ANGLE-angle);
      delay(50);
    }else{
      angle = 0;
      myState = STATE_HAND1;
    }
  }else if(myState==STATE_HAND1){
    servoMotorHand.write(0);
    delay(500);
    myState = STATE_FINGER0;
  }else if(myState==STATE_FINGER0){
    if(digitalRead(INPUT_BOX)==LOW){
      servoMotorFingerL.write(FINGER_ANGLE_L);
      servoMotorFingerR.write(0);
      delay(800);
      myState = STATE_ARM1;
    }
  }else if(myState==STATE_ARM1){
    if(angle <= ARM_ANGLE){
      angle += 5;
      servoMotorArm.write(angle);
      delay(50);
    }else{
      angle = 0;
      myState = STATE_FINGER1;
      delay(500);
    }
  }else if(myState==STATE_FINGER1){
    servoMotorFingerL.write(FINGER_ANGLE_L*2/3);
    servoMotorFingerR.write(FINGER_ANGLE_R/3);
    delay(100);
    servoMotorFingerL.write(FINGER_ANGLE_L/3);
    servoMotorFingerR.write(FINGER_ANGLE_R*2/3);
    delay(100);
    servoMotorFingerL.write(FINGER_ANGLE_L/4);
    servoMotorFingerR.write(FINGER_ANGLE_R*3/4);
    myState = STATE_STOP;
  }else if(myState==STATE_STOP){
    if(reqState==STATE_START){
      myState=STATE_START;
      reqState=STATE_STOP;
    }
    servoMotorHand.attach(HAND);
    servoMotorHand.write(0);

    servoMotorArm.attach(ARM);
    servoMotorArm.write(ARM_ANGLE);

    servoMotorFingerL.attach(FINGERL);
    servoMotorFingerL.write(0);

    servoMotorFingerR.attach(FINGERR);
    servoMotorFingerR.write(FINGER_ANGLE_R);
  }
  if(myState!=STATE_STOP){
    Serial.println(myState);
    Serial.println(digitalRead(INPUT_BOX));
  }
}

void processPostData(){
  int cb = UDPServer.parsePacket();
  if (cb) {
    for(int i=0; i < sizeof(packetBuffer); i++){
      packetBuffer[i] = 0;
    }
    UDPServer.read(packetBuffer, sizeof(packetBuffer));
    String data = String((const char*)packetBuffer);
    Serial.println(data);
    if(data.equals("START")){
      reqState = STATE_START;
    }else if(data.equals("STOP")){
      myState = STATE_STOP;
    }
  }
}
