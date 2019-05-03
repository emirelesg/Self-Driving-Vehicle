#include <CircularBuffer.h>
#include "definitions.h"
#include <math.h>

#define BATTERY_THRESHOLD           5
#define BATTERY_WARNING_TIMEOUT     90000
#define SHUTDOWN_TIMEOUT            2000
#define CONNECTION_TIMEOUT          2000
#define BATTERY_READ_INTERVAL       1000
#define PIN_BUZZER                  PA11
#define PIN_BUTTON                  PA8
#define PIN_LED1                    PB12
#define PIN_LED2                    PB13
#define PIN_LED3                    PB14
#define PIN_LED4                    PB15
#define PIN_LMOTOR_1                PA4
#define PIN_LMOTOR_2                PA5
#define PIN_LMOTOR_ENABLE           PA6
#define PIN_RMOTOR_ENABLE           PA7
#define PIN_RMOTOR_1                PB0
#define PIN_RMOTOR_2                PB1
#define PIN_RPI_BATTERY             PA2
#define PIN_MOTOR_BATTERY           PA1
#define PIN_MOTOR_BATTERY_1C        PA0
#define STM32_VOLTAGE 3.318

const float RPI_BATTERY_FACTOR      = (STM32_VOLTAGE / 4095.0) / (47.0 / (22.0 + 47.0));
const float MOTOR_BATTERY_FACTOR    = (STM32_VOLTAGE / 4095.0) / (21.86 / (21.86 + 46.7));
const float MOTOR_BATTERY_1C_FACTOR = (STM32_VOLTAGE / 4095.0) / (46.22 / (21.63 + 46.22));
float rpiBatteryVoltage             = 0;
float motorBatteryVoltage           = 0;
float motorBatteryCell1Voltage      = 0;
float motorBatteryCell2Voltage      = 0;
int rpiBatteryCharge                = 100;
int motorBatteryCharge              = 100;
CircularBuffer<float, 10> rpiBatteryVoltageBuffer;
CircularBuffer<float, 10> motorBatteryVoltageBuffer;
CircularBuffer<float, 10> motorBatteryCell1VoltageBuffer;

char in;
String command, instruction, data1, data2;
boolean shutdownFlag, buttonFlag, connectedFlag, beepFlag;
unsigned long lastCommandTime, beepStartTime;
unsigned long lastBatteryWarningTime;
unsigned long lastButtonPressTime;
unsigned long beepDuration;
int beepRepetitions = 0;
int buttonCount = 0;

void setup() {
  Serial.begin(115200);
  pinMode(PIN_BUTTON, INPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_LED1, OUTPUT);
  pinMode(PIN_LED2, OUTPUT);
  pinMode(PIN_LED3, OUTPUT);
  pinMode(PIN_LED4, OUTPUT);
  pinMode(PIN_RPI_BATTERY, INPUT_ANALOG);
  pinMode(PIN_MOTOR_BATTERY, INPUT_ANALOG);
  pinMode(PIN_MOTOR_BATTERY_1C, INPUT_ANALOG);
  pinMode(PIN_RMOTOR_ENABLE, PWM);
  pinMode(PIN_RMOTOR_1, OUTPUT);
  pinMode(PIN_RMOTOR_2, OUTPUT);  
  pinMode(PIN_LMOTOR_1, OUTPUT);
  pinMode(PIN_LMOTOR_2, OUTPUT);
  pinMode(PIN_LMOTOR_ENABLE, PWM);
  rightMotorSpeed(0);
  leftMotorSpeed(0);
}


void leftMotorSpeed(int percentage) {
  leftMotorDirection(percentage >= 0);
  int duty = map(abs(percentage), 0, 100, 0, 65535);
  pwmWrite(PIN_LMOTOR_ENABLE, duty);
}

void rightMotorSpeed(int percentage) {
  rightMotorDirection(percentage > 0);
  int duty = map(abs(percentage), 0, 100, 0, 65535);
  pwmWrite(PIN_RMOTOR_ENABLE, duty);
}

void leftMotorDirection(boolean direc) {
  digitalWrite(PIN_LMOTOR_1, direc);
  digitalWrite(PIN_LMOTOR_2, !direc);
}

void rightMotorDirection(boolean direc) {
  digitalWrite(PIN_RMOTOR_1, direc);
  digitalWrite(PIN_RMOTOR_2, !direc);
}


float averageBuffer(CircularBuffer<float, 10> &buff) {
  float average = 0;
  for (int i = 0; i < buff.size(); i++) {
    average += buff[i];
  }
  return average / buff.size();
}

void readBatteries() {
  static unsigned long lastTime = 0;
  if (millis() - lastTime > BATTERY_READ_INTERVAL) {
    rpiBatteryVoltageBuffer.push(analogRead(PIN_RPI_BATTERY) * RPI_BATTERY_FACTOR);
    motorBatteryVoltageBuffer.push(analogRead(PIN_MOTOR_BATTERY) * MOTOR_BATTERY_FACTOR);
    motorBatteryCell1VoltageBuffer.push(analogRead(PIN_MOTOR_BATTERY_1C) * MOTOR_BATTERY_1C_FACTOR);
    rpiBatteryVoltage = averageBuffer(rpiBatteryVoltageBuffer);
    motorBatteryVoltage = averageBuffer(motorBatteryVoltageBuffer);
    motorBatteryCell1Voltage = averageBuffer(motorBatteryCell1VoltageBuffer);
    motorBatteryCell2Voltage = motorBatteryVoltage - motorBatteryCell1Voltage;  
    rpiBatteryCharge = voltageToCharge(rpiBatteryVoltage);
    motorBatteryCharge = (voltageToCharge(motorBatteryCell1Voltage) + voltageToCharge(motorBatteryCell2Voltage)) / 2;
    lastTime = millis();
  }
}

int voltageToCharge(float voltage) {
  int charge = 0;
  if (voltage >= 3.7) {
    charge = -60.7 * pow(voltage, 2) + 571.9 * voltage - 1230.9;
  } else {
    charge = 685.1 * pow(voltage, 3) - 6780.9 * pow(voltage, 2) + 22387.4 * voltage - 24655;
  }
  return constrain(charge, 0, 100);
}

void beep(unsigned long duration, int repetitions) {

  digitalWrite(PIN_BUZZER, HIGH);
  beepDuration = duration;
  beepStartTime = millis();
  beepFlag = true;
  beepRepetitions = repetitions;
  
}

void asyncBeep() {
  
  if (beepFlag && millis() - beepStartTime > beepDuration) {
    digitalWrite(PIN_BUZZER, LOW);
    beepFlag = false;
  }

  if (beepRepetitions > 0) {
    if (millis() - beepStartTime > 2 * beepDuration) {
      beep(beepDuration, beepRepetitions - 1);
    }
  }
  
  
}

void readCommands() {

  while (Serial.available()) {
    
    in = Serial.read();
    
    if (in == '\n') {
    
      command += '\0';
      instruction = command.substring(0, command.indexOf(' '));

      if (instruction.equalsIgnoreCase(F("VEL"))) {
        
        data1 = command.substring(command.indexOf(' ') + 1);
        if (data1.indexOf(' ')) {
          data2 = data1.substring(data1.indexOf(' ') + 1);  
        } else {
          data2 = data1;
        }
        leftMotorSpeed(data1.toInt());
        rightMotorSpeed(data2.toInt());
        
      } else if (instruction.equalsIgnoreCase(F("STATUS"))) {

        Serial.print(rpiBatteryVoltage);          Serial.write(',');
        Serial.print(motorBatteryVoltage);        Serial.write(',');
        Serial.print(motorBatteryCell1Voltage);   Serial.write(',');
        Serial.print(motorBatteryCell2Voltage);   Serial.write(',');
        Serial.print(rpiBatteryCharge);           Serial.write(',');
        Serial.print(motorBatteryCharge);         Serial.write(',');
        Serial.print(shutdownFlag);
        Serial.write('\n');
        
      }

      if (!connectedFlag) {
        connectedFlag = true;
        beep(75, 1);
      }
      
      command = "";
      lastCommandTime = millis();
      
    } else {
      
      command += in;
      
    }
  }
  
}

void loop() {
  readCommands();
  readBatteries();
  asyncBeep();

  buttonFlag = digitalRead(PIN_BUTTON);
  if (buttonFlag && !shutdownFlag) {
    if (millis() - lastButtonPressTime > SHUTDOWN_TIMEOUT / 4) {
      if (buttonCount >= 4) {
        beep(500, 0);
        shutdownFlag = true;
      } else {
        beep(75, 0);
      }
      lastButtonPressTime = millis();
      buttonCount++;
    }
  } else {
    buttonCount = 0;
  }
  
  if (millis() - lastCommandTime > CONNECTION_TIMEOUT && connectedFlag) {
    connectedFlag = false;
    leftMotorSpeed(0);
    rightMotorSpeed(0);
    beep(75, 1);
  }

  if (rpiBatteryCharge < BATTERY_THRESHOLD || motorBatteryCharge < BATTERY_THRESHOLD) {
    if (millis() - lastBatteryWarningTime > BATTERY_WARNING_TIMEOUT) {
      beep(150, 1);
      lastBatteryWarningTime = millis();
    }
  }
  digitalWrite(PIN_LED3, rpiBatteryCharge < BATTERY_THRESHOLD);
  digitalWrite(PIN_LED4, motorBatteryCharge < BATTERY_THRESHOLD);
  

  digitalWrite(PIN_LED1, connectedFlag);
  
}
