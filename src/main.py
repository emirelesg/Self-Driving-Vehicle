#!/usr/bin/python3
# -*- coding: utf-8 -*-

from imutils.video.pivideostream import PiVideoStream
from processor import ImageProcessor
from tracker import Tracker
from car import Car
import numpy as np
import time
import cv2

# Define the average positions for the left and right lanes.
averageLeft = np.poly1d(np.array([-3.45, 778.36]))
averageRight = np.poly1d(np.array([3.66, -328.14]))

# Initialize the communications with the car via serial.
car = Car('/dev/ttyAMA0', 115200)
car.start()
command = ''

# Initalize the camera processor, defines the frame rate and frame size.
processor = ImageProcessor((480, 320), 20)

# Open the threaded version of the PiCamera class.
cv2.namedWindow('main', cv2.WINDOW_AUTOSIZE)
camera = PiVideoStream(resolution=processor.frameDimensions, framerate=processor.frameRate).start()
time.sleep(2)

# Create a Kalman Filter for the left and right lanes.
rightTracker = Tracker()
leftTracker = Tracker()

def writeCarStatus(frame, status):
    """
        Takes the status received from the car class and displays it on a frame.
    """

    if status:
        cv2.putText(frame, 'RPi: %.2f v' % (status['rpiBatteryVoltage']), (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)
        cv2.putText(frame, 'Motor: %.2f v' % (status['motorBatteryVoltage']), (10, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)
    return frame

def main():

    global command, camera, processor
    
    statusRequestTime = time.time()
    latestCarStatus = None
    enableControl = False
    enableMotors = False

    pid = 0
    sumError = 0
    averageError = 0
    prevError = 0
    dt = 1.0 / 20

    while True:

        # 1. Reads frame from the camera.
        frame = camera.read()

        # 2. Processes the frame to extract the lanes.
        out = processor.process(frame)
        
        # 3. Passes the found lanes to the Kalman Filter.
        left = leftTracker.add(processor.left.poly)
        right = rightTracker.add(processor.right.poly)

        # 4. Draws the unfiltered lanes.
        # processor.drawPoly(out, processor.left.poly, (0, 100, 200))
        # processor.drawPoly(out, processor.right.poly, (200, 100, 0))

        # 4. Draws the output of the Kalman Filter.
        processor.drawPoly(out, left, (0, 50, 255))
        processor.drawPoly(out, right, (255, 50, 0))

        # 4. Draws the average position for the lanes.
        processor.drawPoly(out, averageLeft, (255, 255, 255))
        processor.drawPoly(out, averageRight, (255, 255, 255))

        # Once the control is enabled via the C key.
        if enableControl:

            # Calculates the error on both lanes.
            y0 = processor.roiY[0] * processor.h
            leftError = averageLeft(y0) - left(y0)
            rightError = averageRight(y0) - right(y0)
            averageError = (leftError + rightError) / 2

            # Displays the error on the frame.
            cv2.putText(out, '%.2f' % (leftError), (int(averageLeft(y0)), int(y0) + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)
            cv2.putText(out, '%.2f' % (rightError), (int(averageRight(y0)), int(y0) + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)

            # Define PID constants.
            kp = 0.05
            ki = 0.05
            kd = 0.01
            
            # 5. Calculate the PID terms. 
            prevError = averageError
            sumError += averageError * ki * dt
            if sumError > 50:
                sumError = 50
            elif sumError < -50:
                sumError = -50
            p = kp * averageError
            i = sumError
            d = (averageError - prevError) * kd / dt

            # Add P, I, and D terms to get the PID control. Since the vehicle must only steer slightly, the vehicle has
            # a base speed.
            pid = p + i + d
            baseSpeed = 50
            velLeft = int(baseSpeed - pid)
            velRight = int(baseSpeed + pid)

            # Constrains the speed to be within 0 and 100%.
            if velLeft < 0:
                velLeft = 0
            elif velLeft > 100:
                velLeft = 100
            if velRight < 0:
                velRight = 0
            elif velRight > 100:
                velRight = 100

            # If motors are enabled via the M key, sends the calculated speed to the car.
            if enableMotors:
                command = 'VEL %d %d \t PID %.1f P %.1f I %.1f D %.1f' % (velLeft, velRight, pid, p, i ,d)
                print(command)

        # Draw the current status of the vehicle on the frame.
        out2 = writeCarStatus(out, latestCarStatus)

        # Display the output image.
        cv2.imshow('main', out2)

        # Reads any key press and process them.
        # w - Move forward.
        # s - Move backward.
        # d - Move right.
        # a - Move left.
        # Space - Stop.
        # q - Quit.
        # k - Print coefficients of the unfiltered lanes.
        # c - Enable PID calculations.
        # m - Enable motors to be controlled by the PID control loop.
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('k'):
            print('Left: ', processor.left.poly.coeffs)
            print('Right: ', processor.right.poly.coeffs)
        elif key == ord('w'):
            command = 'VEL 50 50'
        elif key == ord('s'):
            command = 'VEL -50 -50'
        elif key == ord('a'):
            command = 'VEL 0 50'
        elif key == ord('d'):
            command = 'VEL 50 0'
        elif key == ord(' '):
            command = 'VEL 0 0'
        elif key == ord('c'):
            enableControl = not enableControl
            if enableControl:
                print('CONTROL ON')
            else:
                print('CONTROL OFF')
            enableMotors = False
        elif key == ord('m'):
            enableMotors = not enableMotors
            if enableMotors:
                print('MOTORS ON')
            else:
                print('MOTORS OFF')
                command = 'VEL 0 0'

        # Sends a command to the vehicle.
        car.commandQ.put(command)

        # Request every second the status from the vehicle's batteries.
        if time.time() - statusRequestTime > 1.0:
            car.requestStatus.set()
            statusRequestTime = time.time()
        
        # Read the status from the car.
        while not car.messageQ.empty():
            latestCarStatus = car.messageQ.get()

    # Close communications with the camera and car.
    # Close allw windows.
    car.stop.set()
    camera.stop()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()