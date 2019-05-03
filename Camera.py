#!/usr/bin/python3
# -*- coding: utf-8 -*-

from imutils.video.pivideostream import PiVideoStream
import imutils
import multiprocessing
import numpy as np
import cv2
import time
import datetime
import base64
from os import getpid
from io import BytesIO

class CameraSettings():

    def __init__(self):

        # Images
        self.raw = None
        self.undistorted = None
        self.gray = None
        self.blur = None
        self.edges = None
        self.maskedEdges = None
        self.houghLines = None

        self.rawHoughLines = []

        # Settings received from the web application.
        self.enabled = True
        self.display = 'raw'
        self.blurKernelSize = 5
        self.blurIterations = 1
        self.cannyLowThreshold = 10
        self.cannyHighThreshold = 40
        self.houghRho = 1
        self.houghTheta = np.pi / 180
        self.houghThreshold = 20
        self.houghMinLineLength = 5
        self.houghMaxLineGap = 60
        self.roiBottom = 300
        self.roiTop = 200
        self.roiY0 = 100
        self.roiY1 = 200
        self.absMinLineAngle = 15

        # Camera settings
        self.frameDimensions = (480, 320)
        self.frameRate = 24
        
        # Camera calibration
        # Scale the calibration matrix to the desired frame dimensions.
        self.calibrationResolution = (1280, 720)                            # Resolution at which the camera Matrix is provided.
        kx = self.frameDimensions[0] / self.calibrationResolution[0]        # Calculate the change in the -x axis.
        ky = self.frameDimensions[1] / self.calibrationResolution[1]        # Calculate the change in the -y axis.
        cameraMatrix = np.array([                                           # Raw camera calibration matrix.
            [1.00612323e+03, 0.00000000e+00, 6.31540281e+02],
            [0.00000000e+00, 1.00551440e+03, 3.48207362e+02],
            [0.00000000e+00, 0.00000000e+00, 1.00000000e+00]
        ])
        self.cameraMatrix = np.multiply(cameraMatrix, [                     # Adjust the camera calibration matrix.
            [kx, 1, kx],
            [1, ky, ky],
            [1, 1, 1]
        ])
        self.distortionCoefficients = np.array([[0.18541226, -0.32660915, 0.00088513, -0.00038131, -0.02052374]])
        self.newCameraMatrix, self.roi = cv2.getOptimalNewCameraMatrix(self.cameraMatrix, self.distortionCoefficients, self.frameDimensions, 1, self.frameDimensions)
        self.rectifyMapX, self.rectifyMapY = cv2.initUndistortRectifyMap(self.cameraMatrix, self.distortionCoefficients, None, self.newCameraMatrix, self.frameDimensions, 5)

        # Lane detection
        self.lanes = {
            'right': [],
            'left': []
        }
        self.laneMinY = 50
        self.laneMaxY = 300
        self.drawAllLines = False

class Camera():

    def __init__(self, debug=False):
        self.debug = debug
        self.commandQ = multiprocessing.Queue()
        self.imageQ = multiprocessing.Queue()
        self.stop = multiprocessing.Event()
        self.sendFrames = multiprocessing.Event()
        self.process = multiprocessing.Process(target=self.run, args=())
        self.process.daemon = True
        self.settings = CameraSettings()

        print(getpid(), 'Creating Camera...')

    def processCommands(self):

        while not self.commandQ.empty():

            # Read commands from the queue.
            data = self.commandQ.get()

            # Extract the keys received from the dictionary
            for key in data.keys():

                # If the key exists in the settigns object, then replace
                # its value.
                if key in self.settings.__dict__.keys():
                    self.settings.__dict__[key] = data[key]

    def run(self):

        def processFrame(image):

            # Undistort the raw image.
            # Instead of using cv2.undistort, use cv2.remap. It is faster.
            self.settings.undistorted = cv2.remap(image, self.settings.rectifyMapX, self.settings.rectifyMapY, cv2.INTER_LINEAR)

            # Convert image to gray scale.
            self.settings.gray = cv2.cvtColor(self.settings.undistorted, cv2.COLOR_BGR2GRAY)

            # Blur image so that the Canny edge detector doesn't find useless edges.
            # The blur can be done in several iterations.
            # Make sure that the blur kernel size is also larger than 1.
            self.settings.blur = self.settings.gray
            if (self.settings.blurKernelSize > 1):
                for i in range(self.settings.blurIterations):
                    self.settings.blur = cv2.GaussianBlur(self.settings.blur, ((self.settings.blurKernelSize, self.settings.blurKernelSize)), sigmaX=0, sigmaY=0)
            
            # Detect edges unsing a Canny edge detector.
            self.settings.edges = cv2.Canny(self.settings.blur, self.settings.cannyLowThreshold, self.settings.cannyHighThreshold, apertureSize=3)
    
            # Create a region of iterest using the obtained values.
            mask = np.zeros_like(self.settings.edges)
            w = self.settings.frameDimensions[0]
            x0 = (w - self.settings.roiTop) / 2
            x1 = (w - self.settings.roiBottom) / 2 
            vertices = np.array([[
                (x0, self.settings.roiY0),              # Bottom left
                (x1, self.settings.roiY1),              # Top left
                (w - x1, self.settings.roiY1),          # Top right
                (w - x0, self.settings.roiY0)           # Bottom right
            ]], dtype=np.int32)
            cv2.fillPoly(mask, vertices, 255)
            self.settings.maskedEdges = cv2.bitwise_and(self.settings.edges, mask)

            # Detect lines.
            self.rawHoughLines = cv2.HoughLinesP(
                self.settings.maskedEdges, 
                rho = self.settings.houghRho, 
                theta = self.settings.houghTheta, 
                threshold = self.settings.houghThreshold, 
                lines = np.array([]), 
                minLineLength = self.settings.houghMinLineLength, 
                maxLineGap = self.settings.houghMaxLineGap
            )
        
        def processLines():

            # Empty arrays for storing line coordinates (sets of points (x, y)).
            rightLines = {
                'x': [],
                'y': []
            }
            leftLines = {
                'x': [],
                'y': []
            }

            # Create a copy of the gray scale image but in rgb
            self.settings.houghLines = cv2.cvtColor(self.settings.gray, cv2.COLOR_GRAY2BGR)

            # Make sure that some lines were found.
            if type(self.rawHoughLines) == type(np.array([])):

                # Iterate through all lines found.
                for line in self.rawHoughLines:
                    for x1, y1, x2, y2 in line:

                        # Calculate the direction of the line found.
                        direction = np.rad2deg(np.arctan2(y2 - y1, x2 - x1))

                        # Make sure that the angle of the line has a minimum angle.
                        if (np.abs(direction) > self.settings.absMinLineAngle):
                            
                            # Lines that have a positive angle correspond to the right line.
                            if (direction > 0):

                                rightLines['x'].extend([x1, x2])
                                rightLines['y'].extend([y1, y2])

                                # Draw right lines with a red color.
                                if self.settings.drawAllLines:
                                    cv2.line(self.settings.houghLines, (x1, y1), (x2, y2), (0, 0, 255))

                            # Lines with a negative angle correspond to the left lane.
                            else:

                                leftLines['x'].extend([x1, x2])
                                leftLines['y'].extend([y1, y2])

                                # Draw left lines with a blue color.
                                if self.settings.drawAllLines:
                                    cv2.line(self.settings.houghLines, (x1, y1), (x2, y2), (255, 0, 0))
            
            # Make sure points on the left side were found.
            if len(leftLines['x']) > 0 and len(leftLines['y']) > 0:
                
                # Using the points found, find a 1st order polynomial that best fits the data.
                polyLeft = np.poly1d(np.polyfit(leftLines['y'], leftLines['x'], deg=1))
                
                # Evaluate the function found for the desired lane lengths.
                self.settings.lanes['left'] = [
                    int(polyLeft(self.settings.laneMinY)),
                    self.settings.laneMinY,
                    int(polyLeft(self.settings.laneMaxY)),
                    self.settings.laneMaxY
                ]
            
            # Make sure points on the right side were found.
            if len(rightLines['x']) > 0 and len(rightLines['y']) > 0:
                
                # Using the points found, find a 1st order polynomial that best fits the data.
                polyRight = np.poly1d(np.polyfit(rightLines['y'], rightLines['x'], deg=1))
                
                # Evaluate the function found for the desired lane lengths.
                self.settings.lanes['right'] = [
                    int(polyRight(self.settings.laneMinY)), 
                    self.settings.laneMinY, 
                    int(polyRight(self.settings.laneMaxY)), 
                    self.settings.laneMaxY
                ]

            # Only draw the main lanes if the drawAllLines option is turned off.
            if not self.settings.drawAllLines:

                # Draw the left lane on the image.
                if len(self.settings.lanes['left']):
                    cv2.line(self.settings.houghLines, (self.settings.lanes['left'][0], self.settings.lanes['left'][1]), (self.settings.lanes['left'][2], self.settings.lanes['left'][3]), (255, 0, 0), 2)
                
                # Draw the right lane on the image.
                if len(self.settings.lanes['right']):
                    cv2.line(self.settings.houghLines, (self.settings.lanes['right'][0], self.settings.lanes['right'][1]), (self.settings.lanes['right'][2], self.settings.lanes['right'][3]), (0, 0, 255), 2)


        print(getpid(), 'Starting Camera...')

        # Open the picamera with a 'with' instruction. This makes sure
        # that if something happends the camera object will be closed automatically.
        try:
            
            # Setup threaded camera object.
            stream = PiVideoStream(resolution=self.settings.frameDimensions, framerate=self.settings.frameRate).start()
            
            # Wait for the camera to warm-up.
            time.sleep(2)

            # Get the current start time.
            startTime = cv2.getTickCount()

            # Process frames while the stop flag is not set.
            while not self.stop.is_set():

                # Calculate change in time between frames and fps.
                deltaTime = (cv2.getTickCount() - startTime) / cv2.getTickFrequency()
                fps = 1 / deltaTime

                # Update the start time.
                startTime = cv2.getTickCount()

                # Retrieve the frame from imutils stream.
                self.settings.raw = stream.read()

                # Process image.
                if self.settings.enabled:
                    processFrame(self.settings.raw)
                    processLines()
                
                # If the parent process has requested a new frame, place it on the queue
                # By doing this, the parent process makes sure that no more than the required
                # frames are placed in the queue. If for some reason the parent slows down
                # no more frames will be placed in the queue until this flag is set by the parent.
                if self.sendFrames.is_set():

                    # Select which frame to send back to the server.
                    toSend = None
                    if self.settings.display in self.settings.__dict__.keys():
                        toSend = self.settings.__dict__[self.settings.display]
                    else:
                        toSend = self.settings.raw

                    # Append the cycle time to the frame that will be sent.
                    cv2.putText(toSend, 'Cycle: %.2ffps' % (fps), (10, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

                    # Send frame.
                    self.imageQ.put(toSend)

                    # Clear flag since an element has been placed into the queue.
                    self.sendFrames.clear()

                # Read commands from the queue and update the current settings.
                self.processCommands()

            # Close the camera stream.
            stream.stop()

        except KeyboardInterrupt:
            pass
        
        except Exception:
            raise

        # Close the process completely.
        print(getpid(), 'Killing Camera...')
        self.sendFrames.clear()
        while not self.imageQ.empty():
            self.imageQ.get()

    def start(self):
        self.process.start()

    @staticmethod
    def encodeImage(image, quality=50):
        retval, buffer = cv2.imencode('.jpg', image, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        binaryImage =  base64.b64encode(buffer)
        return binaryImage

if __name__ == "__main__":

    """
        Small test for the camera class.
    """

    # Start the camera in debug mode.
    cam = Camera(debug=True)
    cam.start()

    # Create a opencv window.
    cv2.namedWindow('main', cv2.WINDOW_AUTOSIZE)

    # Select frame to display.
    cam.commandQ.put({
        'enabled': True,
        'display': 'undistorted'
    })

    while True:
    
        # Request frames from the camera.
        cam.sendFrames.set()

        # Read the latest frame from the queue.
        latestFrame = None
        while not cam.imageQ.empty():
            latestFrame = cam.imageQ.get()

        # Display latest frame if any. 
        if latestFrame is not None:
            cv2.imshow('main', latestFrame)

        # Wait at about 24fps
        key = cv2.waitKey(int(1000/24)) & 0xFF

        # Quit gracefully.
        if (key == ord('q')):
            
            cam.stop.set()
            break

        # Write the binary image to a file.
        elif (key == ord('w')):

            # Open file and write encoded data.
            with open('out.txt', 'wb') as fh:
                fh.write(Camera.encodeImage(latestFrame))
            print('wrote image')
    
    print('exited main')
    cv2.destroyAllWindows()
       
    