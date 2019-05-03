#!/usr/bin/python3
# -*- coding: utf-8 -*-

from queue import Queue
import threading
import struct
import serial
import time
from os import getpid

class Car(threading.Thread):
    """
        Car class used as an interface between the STM32 micro and the
        RPI. The STM32 controls the motors and reports on the voltage 
        of the RPI.
    """

    def __init__(self, serialPort, baudRate, debug=False):
        threading.Thread.__init__(self)
        self.debug = debug
        self.serialPort = serialPort
        self.baudRate = baudRate
        self.daemon = True
        self.stop = threading.Event()
        self.requestStatus = threading.Event()
        self.messageQ = Queue()
        self.commandQ = Queue()
        self.buffer = ''

        print(getpid(), 'Creating Car...')

    def run(self):
        """
            Main run function. Monitors the commandQ for available commands
            and sends them to the car. If the command requests data,
            then it waits for it and sends it back.
        """

        print(getpid(), 'Starting Car...')

        # While the stop signal is not set continue running:
        while not self.stop.isSet():

            # Open the serial interface with the 'with' version
            # In case of an error, the with part will close
            # the connection to the serial port automatically.
            try:
                with serial.Serial(port=self.serialPort, baudrate=self.baudRate, timeout=1) as controller:

                    # Send all available commands to the car.
                    while not self.commandQ.empty() and not self.requestStatus.isSet():

                        # Get a command from the q and make sure it ends with a
                        # new line character.
                        rawCommand = self.commandQ.get()
                        if not rawCommand.endswith('\n'):
                            rawCommand += '\n'

                        # Sends the comamnd to the car in ascii format.
                        controller.write(rawCommand.encode('ascii', errors='ignore'))

                        # Signal task completion.
                        self.commandQ.task_done()

                    # Check if the status flag is set.
                    if (self.requestStatus.isSet()):
                        
                        # Clear flag.
                        self.requestStatus.clear()

                        # Send request command to controller.
                        controller.write('STATUS\n'.encode('ascii', errors='ignore'))

                        # Read, process, and send back data.
                        rawData = controller.readline()
                        data = self.processStatus(rawData)
                        self.messageQ.put(data)

                        # Display if debug is active.
                        if (self.debug):
                            print('\nSTATUS: ', data)

                    # Wait a small time to avoid hanging the cpu.
                    time.sleep(0.01)

            # If for some reason the port can't be opened, catch error and stop thread.
            except serial.serialutil.SerialException:
                print('serial port cant be opened')
                break
        
        print(getpid(), 'Killing Car...')

    def processStatus(self, data):
        """
            Process the raw data obtained from the status command.
            rpiBatteryVoltage
            motorBatteryVoltage,
            motorBatteryCell1Voltage,
            motorBatteryCell2Voltage
            shutdownFlag
        """

        # Parse input data
        data = data.decode('ascii', errors='ignore')
        data = data.strip().split(',')
        processed = {}

        # Read individual values from parsed data.
        # Make sure that the length matches the data excepted.
        if (len(data) == 7):
            try:
                processed['rpiBatteryVoltage'] = float(data[0])
                processed['motorBatteryVoltage'] = float(data[1])
                processed['motorBatteryCell1Voltage'] = float(data[2])
                processed['motorBatterycell2Voltage'] = float(data[3])
                processed['rpiBatteryCharge'] = int(data[4])
                processed['motorBatteryCharge'] = int(data[5])
                processed['shutdownFlag'] = data[6] == '1'
            except:
                pass

        return processed

# If the module is run in standalone mode.
if __name__ == '__main__':

    """
        Small test for simulating sending commands to the car.
        Speed commands at 60Hz.
        Status command at 1Hz.
    """
    car = Car('/dev/ttyAMA0', 115200, debug=True)
    car.start()
    while True:
        try:
            for i in range(60):
                car.commandQ.put('VEL 0 0')
                time.sleep(1/60)
            car.requestStatus.set()
        except KeyboardInterrupt:
            break;