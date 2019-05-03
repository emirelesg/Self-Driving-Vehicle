FILENAME = voltage-monitor.ino

BUILD_DIR = build
CACHE_DIR = cache

HARDWARE = -hardware /opt/arduino-1.8.9/hardware -hardware /home/pi/.arduino15/packages -hardware /home/pi/Arduino/hardware
TOOLS = -tools /opt/arduino-1.8.9/tools-builder -tools /opt/arduino-1.8.9/hardware/tools/avr -tools /home/pi/.arduino15/packages
LIBRARIES = -built-in-libraries /opt/arduino-1.8.9/libraries -libraries /home/pi/Arduino/libraries

all: upload

upload: compile
	/home/pi/Arduino/hardware/Arduino_STM32-master/tools/linux/serial_upload ttyAMA0 {upload.altID} {upload.usbID} $(BUILD_DIR)/$(FILENAME).bin
	screen /dev/ttyAMA0 115200
	
compile: build | cache
	/opt/arduino-1.8.9/arduino-builder -compile $(HARDWARE) $(TOOLS) $(LIBRARIES) -fqbn=Arduino_STM32-master:STM32F1:genericSTM32F103C:device_variant=STM32F103C8,upload_method=serialMethod,cpu_speed=speed_72mhz,opt=osstd -vid-pid=0000_0000 -ide-version=10809 -build-path $(BUILD_DIR) -warnings=none -build-cache $(CACHE_DIR) -prefs=build.warn_data_percentage=75 $(FILENAME)

cache:
	mkdir -p $@

build:
	mkdir -p $@
