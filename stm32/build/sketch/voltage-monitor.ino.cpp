#include <Arduino.h>
#line 1 "/home/pi/Desktop/stm32/voltage-monitor/voltage-monitor.ino"
#line 1 "/home/pi/Desktop/stm32/voltage-monitor/voltage-monitor.ino"
#include "definitions.h"

#line 3 "/home/pi/Desktop/stm32/voltage-monitor/voltage-monitor.ino"
void setup();
#line 10 "/home/pi/Desktop/stm32/voltage-monitor/voltage-monitor.ino"
void loop();
#line 3 "/home/pi/Desktop/stm32/voltage-monitor/voltage-monitor.ino"
void setup() {

    Serial.begin(115200);
    pinMode(PB12, OUTPUT);
    
}

void loop() {

    
while (Serial.available()) {
      Serial.write(Serial.read());
	Serial.write('\n');
    }

}

