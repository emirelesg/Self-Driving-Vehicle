# 1 "/home/pi/Desktop/stm32/voltage-monitor/voltage-monitor.ino"
# 1 "/home/pi/Desktop/stm32/voltage-monitor/voltage-monitor.ino"
# 2 "/home/pi/Desktop/stm32/voltage-monitor/voltage-monitor.ino" 2

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
