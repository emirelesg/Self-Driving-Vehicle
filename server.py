#!/usr/bin/python3
# -*- coding: utf-8 -*-

from flask_socketio import SocketIO, disconnect
from flask import Flask, render_template
from Camera import Camera
from os import getpid
from Car import Car
import time
import subprocess
import sys

latestStatus        = {
    'time': -1,
    'rpiBatteryVoltage': -1,
    'motorBatteryVoltage': -1,
    'image': -1
}
lastStatusSendTime  = 0         # Stores the last time a status request was sent.
statusRequested     = False     # Flag for signaling if a status request is in progress, but no answer has been yet received.
car = None
camera = None
cameraSettings = None

app = Flask(__name__, static_url_path='', static_folder='web/static', template_folder='web/templates')
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SECRET_KEY'] = 'FOODBABE'

socketio = SocketIO(app)

def initCar():
    """
        Makes sure that a connection to the car is established.
        If the thread dies for some reason, the thread will be
        started up again.
    """

    global car
    
    # Init car if it doens't exist.
    if car is None:
        car = Car('/dev/ttyAMA0', 115200, debug=False)
        car.start()
    
    # If car is dead start it again.
    elif not car.isAlive():
        car = None
        initCar()

def initCamera():
    """
        Makes sure that a connection to the camera process is established.
    """

    global camera

    # Init camera if it doesn't exist.
    if camera is None:
        camera = Camera(debug=True)
        try:
            camera.start()
        except AssertionError:
            handleShutdown(True)
            
    
    # If camera is dead start it again.
    elif not camera.process.is_alive():
        try:
            camera.start()
        except AssertionError:
            handleShutdown(True)


@app.route('/')
def index():
    """
        When a new connection occurs, send the main index file.
    """
    
    # Make sure that the car object is created/alive.
    global car
    initCar()
    initCamera()

    return render_template('index.html')

@socketio.on('disconnected')
def handleDisconnected():
    """ When a user disconnects, reset camera flags for sending frames. """

    global camera

    # Make sure that the camera exists.
    if camera is not None:

        # Clear flag to request frames.
        camera.startPipeline.clear()
        camera.sendFrames.clear()

        # Empty camera queue for safety.
        while not camera.imageQ.empty():
            camera.imageQ.get()

@socketio.on('shutdown')
def handleShutdown(state):
    """
        Closes any connections to clients, the car controller and the camera.
    """
    
    global car, camera

    # Close any socket connections.
    disconnect()

    print(getpid(), 'Initializing shutdown...')

    # Stop the connection to the car controller.
    if car is not None:
        car.stop.set()

    # Stop the connection to the camera.
    if camera is not None:
        camera.stop.set()

    # Wait for camera to be dead.
    waitTime = 0
    print(getpid(), 'Waiting for Camera to die...')
    while camera.process.is_alive() or waitTime < 5:
        time.sleep(1)
        waitTime += 1
    print(getpid(), 'Camera dead')
    
    try:
        # Stop socket io and catch the SystemExit event caused by it.
        socketio.stop()
    except SystemExit:
        # Kill the current process that is running the python server.
        print(getpid(), 'Exited from flask-socketio...')
        subprocess.run(['kill', '%d' % getpid()])

@socketio.on('message')
def handleMessage(message):
    """
        Handle messages received from the web interface.
        The rate at which the messages are received set the
        speed of the system.
        This function also handles the communication with the car and the camera.
    """

    # Make sure that the car object is created/alive.
    global car, camera, latestStatus
    initCar()
    initCamera()

    def comServerToCar():
        """
            Sends data from the server -> car.
        """

        # Send commanded speed to the car.        
        command = 'VEL %d %d' % (message['leftSpeed'], message['rightSpeed'])
        car.commandQ.put(command)

    def comCarToServer():
        """
            Receives data from the car -> server.
        """

        global statusRequested, lastStatusSendTime
        
        # If the status data has already been requested. Check if the data
        # is in the queue.
        if (statusRequested):

            # Check queue for messages.
            while not car.messageQ.empty():
                
                # Get the latest status
                status = car.messageQ.get()
                if status:
                    
                    # Check if the shutdown flag is set.
                    if status['shutdownFlag']:
                        subprocess.run(['sudo', 'shutdown', '-h', 'now'])

                    # Update the latest status flags with the data received from the car.
                    latestStatus['rpiBatteryVoltage'] = status['rpiBatteryVoltage']
                    latestStatus['motorBatteryVoltage'] = status['motorBatteryVoltage']

                    # Reset flag
                    statusRequested = False

        # If more than a second has passed since the last time data
        # was requested, then request data.
        elif (time.time() - lastStatusSendTime > 1):

            # Sets flag for signaling a status request.
            car.requestStatus.set()
            statusRequested = True
            lastStatusSendTime = time.time()

    def comCameraToServer():
        """
            Receives data from the camera -> server.
        """
        
        # Request a new frame from the camera.
        camera.sendFrames.set()

        # Get the latest frame from the queue. Drop any other frames in the queue.
        latestImage = None
        while not camera.imageQ.empty():
            latestImage = camera.imageQ.get()
        
        # Check if an image was received on this cycle. If an image was received convert it and
        # set it to the status. If no image was received then avoid sending the past image to save
        # bandwidth and send a -1.
        if latestImage is not None:
            latestStatus['image'] = Camera.encodeImage(latestImage, quality=20)
        else:
            latestStatus['image'] = -1
    
    def comServerToCamera():
        """
            Sends data from the server -> camera.
        """
        
        # Pass to the camera the received message from the server.
        camera.commandQ.put(message['camera'])

    def comServerToClient():
        """
            Sends data from the server -> client.
            The data is the latestStatus data, and it is updated by the other functions
            in order to send the latest data.
        """
        
        # Update the time on the status data.
        latestStatus['time'] = time.time()

        # Send data back.
        socketio.emit('status', latestStatus)

    # Handle communications with the car. Make sure that it has been enabled.
    if car is not None:
        comServerToCar()
        comCarToServer()

    # Handle communications with the camera. Make sure that it has been enabled.
    if camera is not None:
        comCameraToServer()
        comServerToCamera()

    # Send data back to the client.
    comServerToClient()

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8000, debug=False)