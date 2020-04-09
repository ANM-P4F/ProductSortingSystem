#include <Servo.h>
#include <AFMotor.h>
#include <ArduinoSTL.h> //install arduinoSTL

#define DEBUG

// Declare the Servo pin 
int servoPinHorizon = 9;
int servoPinVertical = 10;
// Create a servo object 
Servo servoHorizon ;
Servo servoVertical;

AF_DCMotor motor(1);

int dcMotorPWMVal = 360;

int inputPinInspect = A0;
int inputPinSort = A1;
int inputPinInspectState = HIGH;
int inputPinInspectStatePre = HIGH;
int inputPinSortState = HIGH;
int inputPinSortStatePre = HIGH;
int productType = 0;
int systemState = 0;
bool doSort = false;

std::vector<int> vProductType;

enum STATE {
  STATE_STOP = 0,
  STATE_RUN,
  STATE_PAUSE,
  STATE_DETECTED,
  STATE_TEST
};

void setup() {
  // put your setup code here, to run once:
  Serial.begin(9600);
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(inputPinInspect, INPUT);
  pinMode(inputPinSort, INPUT);

  servoHorizon.attach(servoPinHorizon);
  servoVertical.attach(servoPinVertical);
  servoHorizon.write(45);
  servoVertical.write(0);

}

void loop() {
  if (Serial.available()) {
    String data = Serial.readString();
    if(data.indexOf("OFF")!=-1){
      systemState = STATE_STOP;
      vProductType.clear();
      servoHorizon.write(45);
    }else if(data.indexOf("RUN")!=-1){
      systemState = STATE_RUN;
      dcMotorPWMVal = getValue(data, ':', 1).toInt();
      motor.setSpeed(dcMotorPWMVal);
    }else if(data.indexOf("TEST")!=-1){
      systemState = STATE_TEST;
      int testServo = getValue(data, ':', 1).toInt();
      Serial.print("write servo ");
      Serial.println(testServo);
      servoHorizon.write(testServo);
    }else if(data.indexOf("Detected")!=-1){
      productType = getValue(data, ':', 1).toInt();
      vProductType.push_back(productType);
      systemState = STATE_DETECTED;
    }
  }

  inputPinInspectState = digitalRead(inputPinInspect);
  if(systemState==STATE_RUN){
    if(inputPinInspectState==LOW&&inputPinInspectStatePre==HIGH){
      systemState=STATE_PAUSE;
    }else{
      motor.run(FORWARD);
    }
  }else if(systemState==STATE_PAUSE){
      motor.run(RELEASE);
      Serial.println("STATE_PAUSE");
      systemState = STATE_STOP;
  }else if(systemState==STATE_STOP){
      motor.run(RELEASE);
  }else if(systemState==STATE_TEST){

  }else if(systemState==STATE_DETECTED){
      Serial.println("STATE_DETECTED");
      systemState = STATE_STOP;
  }
  inputPinInspectStatePre = inputPinInspectState;

  controlServos();

  delay(10);
}

void controlServos(){

  inputPinSortState = digitalRead(inputPinSort);
  if(inputPinSortStatePre==HIGH&&inputPinSortState==LOW){
    doSort = true;
  }
  inputPinSortStatePre = inputPinSortState;

  if(doSort){
    // Serial.print("do sort ");
    doSort = false;
    if(vProductType.size()>0){
      productType = vProductType[0];
      vProductType.erase(vProductType.begin());
      Serial.println(productType);
    }
    switch (productType)
    {
      case 0:
        servoHorizon.write(45);
        break;
      case 1:
        servoHorizon.write(0);
        break;
      case 2:
        servoHorizon.write(90);
        break;
      default:
        break;
    }
  }
}

String getValue(String data, char separator, int index)
{
    int found = 0;
    int strIndex[] = { 0, -1 };
    int maxIndex = data.length() - 1;

    for (int i = 0; i <= maxIndex && found <= index; i++) {
        if (data.charAt(i) == separator || i == maxIndex) {
            found++;
            strIndex[0] = strIndex[1] + 1;
            strIndex[1] = (i == maxIndex) ? i+1 : i;
        }
    }
    return found > index ? data.substring(strIndex[0], strIndex[1]) : "";
}