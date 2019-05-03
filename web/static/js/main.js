// ------------------------------------------------------------------
// General Functions
// ------------------------------------------------------------------

/**
 * Get the rgba string from variables.
 * @param {number} r Red color from 0 - 255.
 * @param {number} g Green color from 0 - 255.
 * @param {number} b Blue color from 0 - 255.
 * @param {number} a Alpha channel from 0 - 1.
 * @returns {string} rgba color.
 */
function rgba(r, g, b, a) {
    
    return `rgba(${r}, ${g}, ${b}, ${a})`;

}

/**
 * Constrain a value to be within the range min <= val <= max.
 * @param {number} val value to constrain.
 * @param {number} min minimum acceptable value.
 * @param {number} max maximum acceptable value.
 * @returns {number} the constrained value.s
 */
function clamp(val, min, max) {
    
    if (val < min) return min;
    if (val > max) return max;
    return val;

}
/**
 * Converts a byte array to a base 64 jpeg image string.
 * @param {byteArray} rawBytes Raw byte array of a Base64 Jpeg image.
 * @returns {string} the base64 image.
 */
function byteArrayToImage(rawBytes) {

    // Initialize the output string by writing the base64 header.
    let binary = 'data:image/jpg;base64,';

    // Convert the byte to an array.
    let bytes = new Uint8Array(rawBytes);

    // Read every byte and convert it to string.
    const length = bytes.byteLength
    for (let i = 0; i < length; i++) {
        binary += String.fromCharCode(bytes[i]);
    }

    // Send image.
    return binary;
}

/**
 * Calculate a color that represents the charge on a lithium battery 18650.
 * The color is a linear interpolation between red and green. The threshold values
 * are defined inside of the function.
 * @param {number} voltage voltage at which the color will be calculated.
 * @param {number} cells amount of cells the battery has.
 */
function getChargeColor(voltage, cells) {

    // Take the amount of cells into account.
    const minVoltage = settings.MIN_CELL_VOLTAGE * cells;
    const maxVoltage = settings.MAX_CELL_VOLTAGE * cells;

    // Calculate the percentage of charge. This is not a good indicator of charge since it is lineal.
    // However it is only used as a visual representation of the remaining charge.
    const raw = (voltage - minVoltage) / (maxVoltage - minVoltage);

    // Constrain the percentage to be within 0 and 1 and scale by 255.
    const percentage = Math.ceil(255 * clamp(raw, 0, 1));

    // Calculate a color proprotional to the remaining charge.
    return rgba(255 - percentage, percentage, 0, 0.3);

}

/**
 * Returns an rgba color depening on the speed. If the speed is positive
 * the color is green, if its negative the color is red. The intensity of the
 * color varies with the speed.
 * @param {number} speed speed for which the color will be calculated.
 * @returns {string} rgba color.
 */
function getSpeedColor(speed) {

    if (speed > 0) {
        return rgba(0, 100 + 1.5 * speed, 0, 0.3);
    }
    return rgba(100 - 1.5 * speed, 0, 0, 0.3);

}

// ------------------------------------------------------------------
// Label Class
// ------------------------------------------------------------------
class Label {
    constructor(label, displayLabel, color) {
        this.width = 50;
        this.height = 40;
        this.position = {x: 0, y: 0};
        this.label = label || '';
        this.value = '';
        this.displayLabel = displayLabel || false;
        this.color = color || 'rgba(255, 0, 0, 0.3)';
    } 
    setPosition(x, y) {
        this.position.x = x;
        this.position.y = y;
    }
    draw() {
        
        // Set the width and height of the label depending on the text width.
        this.width = ctx.measureText(this.value).width + 30;

        // Translate to the position of the box.
        ctx.save();
        ctx.translate(this.position.x, this.position.y);

        // Draw the box centered around the desired position.
        ctx.beginPath();
        ctx.fillStyle = this.color;
        ctx.rect(-this.width / 2, -this.height / 2, this.width, this.height);
        ctx.fill();
        ctx.closePath();

        // Draw the label centered on the box.
        ctx.beginPath();
        ctx.textAlign = 'center';
        ctx.fillStyle = 'rgba(255, 255, 255, 0.6)';
        ctx.textBaseline = 'middle';
        ctx.fillText(this.value, 0, 0);
        if (this.displayLabel) {
            ctx.textAlign = 'left';
            ctx.textBaseline = 'bottom';
            ctx.fillText(this.label, -this.width / 2, -this.height/2 - 3);
        }
        ctx.closePath();

        // Restore the translation made.
        ctx.restore();

    }
}

// ------------------------------------------------------------------
// Button Class
// ------------------------------------------------------------------
class Button {
    constructor(label, callback, color) {
        this.width = 0;
        this.height = 0;
        this.position = {x: 0, y: 0};
        this.callback = callback;
        this.label = label || '';
        this.labelObj = new Label(label);
        this.isOver = false;
        this.clickStarted = false;
        this.color = color || [127, 0, 255];
    }
    setPosition(x, y) {
        this.position.x = x;
        this.position.y = y;
        this.labelObj.setPosition(this.position.x, this.position.y);
    }
    isMouseOver() {
        const checkX  = (mouse.x > this.position.x - this.labelObj.width / 2 && mouse.x < this.position.x + this.labelObj.width / 2);
        const checkY = (mouse.y > this.position.y - this.labelObj.height / 2 && mouse.y < this.position.y + this.labelObj.height / 2);
        this.isOver = checkX && checkY;
        if (this.isOver && !mouse.isDown && this.clickStarted) {
            this.clickStarted = false;
            this.callback();
        }
        return this.isOver;
    }
    click() {
        if (!this.clickStarted) {
            this.clickStarted = true;
        }
    }
    draw() {
        this.labelObj.value = this.label;
        this.labelObj.color = rgba(this.color[0], this.color[1], this.color[2], this.isOver ? 0.5 : 0.3);
        this.labelObj.draw();
        this.width = this.labelObj.width;
        this.height = this.labelObj.height;
    }
}

// ------------------------------------------------------------------
// Joystick Class
// ------------------------------------------------------------------

class Joystick {
    constructor() {
        this.x = 0;
        this.y = 0;
        this.leftSpeed = 0;
        this.rightSpeed = 0;
        this.angle = 0;
        this.mag = 0;
        this.position = {x: 0, y: 0};
        this.innerRadius = 40;
        this.outsideRadius = 100;
        this.isDragging = false;
        this.isOver = false;
        this.opacity = 0;
        this.hideMode = true;
    }
    isMouseOver() {
        this.isOver = (mouse.x - (this.x + this.position.x)) ** 2 + (mouse.y - (this.y + this.position.y)) ** 2 < this.innerRadius ** 2;
        return this.isOver || this.isDragging;
    }
    setPosition(x, y) {
        this.position.x = x;
        this.position.y = y;
    }
    move() {

        const newX = mouse.x - this.position.x;
        const newY = mouse.y - this.position.y;

        if (Math.sqrt(newX ** 2 + newY ** 2) < this.outsideRadius) {
            this.x = newX;
            this.y = newY;
            this.angle = Math.atan2(this.y, this.x);
            this.mag = Math.sqrt(this.x ** 2 + this.y ** 2);
        } else {
            this.angle = Math.atan2(newY, newX);
            this.mag = this.outsideRadius;
            this.x = this.mag * Math.cos(this.angle);
            this.y = this.mag * Math.sin(this.angle);
        }
    }
    draw() {
        if (!this.isDragging ) {
            if (this.mag > 3) {
                this.mag -= 10;
                if (this.mag < 3) this.mag = 0;
                this.x = this.mag * Math.cos(this.angle);
                this.y = this.mag * Math.sin(this.angle);
            }
        }

        this.calculateSpeed();


        if (this.hideMode) {
            if (this.isDragging) {
                if (this.opacity < 0.3) {
                    this.opacity += 0.02;
                }
            } else if (this.opacity > 0) {
                this.opacity -= 0.02;
            }
        } else {
            this.opacity = this.isDragging ? 0.5 : 0.25;
        }

        ctx.save();
        ctx.translate(this.position.x, this.position.y);

        ctx.fillStyle = rgba(0, 255, 255, this.opacity);
        ctx.beginPath();
        ctx.arc(0, 0, this.outsideRadius, 0, Math.PI * 2);
        ctx.fill();
        ctx.closePath()

        ctx.beginPath();
        ctx.arc(this.x, this.y, this.innerRadius, 0, Math.PI * 2);
        ctx.fill();
        ctx.closePath();
        
        ctx.restore();
        

    }
    calculateSpeed() {

        // Normalize the x and y position to [-1, 1].
        let normX = this.x / this.outsideRadius;
        let normY = this.y / this.outsideRadius;
        
        // Rotate plane by 45 degrees.
        let r = Math.sqrt(normX ** 2 + normY ** 2);
        let a = Math.atan2(normY, normX) + Math.PI / 4;

        // Calculate coordinates back.
        let rawLeftSpeeed = r * Math.cos(a) * Math.sqrt(2);
        let rawRightSpeed = r * Math.sin(a) * Math.sqrt(2);

        // Make sure that values are within [-maxManualSpeed, maxManualSpeed].
        this.leftSpeed = Math.round(clamp(rawLeftSpeeed, -1, 1) * settings.maxManualSpeed);
        this.rightSpeed = Math.round(clamp(rawRightSpeed, -1, 1) * -settings.maxManualSpeed);

    }
    resize() {
        if (!this.hideMode) {
            this.position.x = settings.width / 2;
            this.position.y = settings.height / 2;
        }
    }
}

// ------------------------------------------------------------------
// Mouse Class
// ------------------------------------------------------------------

class Mouse {
    constructor() {
        this.x = 0;
        this.y = 0;
        this.px = 0;
        this.py = 0;
        this.dx = 0;
        this.dy = 0;
        this.isDown = false;
        this.overSomething = false;
        this.isTouch = this.isTouchDevice();
    }
    setPosition(x, y) {
        this.px = this.x;
        this.py = this.y;
        this.x = x;
        this.y = y;
        this.dx = this.x - this.px;
        this.dy = this.y - this.py;
    }
    mouseUp(e) {
        this.isDown = false;
        this.mouseMove(e);
    }
    mouseDown(e) {
        this.isDown = true;
        this.mouseMove(e);
    }
    touchStart(e) {
        mouse.isDown = true;
        this.mouseMove(e.changedTouches[0]);
    }
    touchEnd(e) {
        mouse.isDown = false;
        this.mouseMove(e.changedTouches[0]);
    }
    touchMove(e) {
        this.mouseMove(e.changedTouches[0]);
    }
    isTouchDevice() {
        // https://stackoverflow.com/questions/4817029/whats-the-best-way-to-detect-a-touch-screen-device-using-javascript
        return (('ontouchstart' in window) || window.DocumentTouch && document instanceof DocumentTouch);
    }

    /**
     * Handles mouse events. Gets the current mouse coordinates and updates the different
     * objects.
     * @param {event} e mouse event.
     */
    mouseMove(e) {

        // Gets the coordinates of the event. Assumes that the canvas is full screen.
        let x = e.clientX;
        let y = e.clientY;

        // Stop any events.
        if (e.cancellable) e.preventDefault();

        // Store the new position and calculate changes in position.
        this.setPosition(x, y);

        // Update the cursor. Check if the mouse is over any draggable object.
        this.overSomething = joystick.isMouseOver() || startButton.isMouseOver() || shutdownButton.isMouseOver();
        canvas.style.cursor = this.overSomething ? 'pointer' : 'default';

        // Start button click.
        if (this.isDown && startButton.isOver) startButton.click();

        // Shutdown button click.
        if (this.isDown && shutdownButton.isOver) shutdownButton.click();

        // Joystick drag start.
        if (this.isDown && joystick.isOver) {
            joystick.isDragging = true;
        }

        // Hide mode of joystick. Clicks anywhere on the screen but the mouse isn't over
        // another object. Move the position of the joystick to the mouse.
        if (this.isDown && !this.overSomething && !joystick.isDragging && joystick.hideMode) {
            joystick.setPosition(mouse.x, mouse.y);
        } 

        // Joystick drag while mouse is down.
        if (joystick.isDragging) {
            joystick.isDragging = mouse.isDown;
            joystick.move();
        }

        settings.isMouseDown = this.isDown;

    }
}

// ------------------------------------------------------------------
// Settings Class
// ------------------------------------------------------------------

class Settings {
    constructor() {

        // General Folder
        this.width = 0;
        this.height = 0;
        this.isMouseDown = false;
        this.maxManualSpeed = 100;

        // OpenCV Folder
        // This settings must match the names on the CameraSettings
        // class. Otherwise they can't be updated.
        // Sets the default value for these settings.
        this.camera = {
            enabled: true,
            display: 'raw',
            blurKernelSize: 3,
            blurIterations: 3,
            cannyLowThreshold: 10,
            cannyHighThreshold: 40,
            houghRho: 1,
            houghThreshold: 20,
            houghMinLineLength: 5,
            houghMaxLineGap: 60,
            roiY0: 160,
            roiY1: 230,
            roiBottom: 480,
            roiTop: 315,
            absMinLineAngle: 10,
            laneMinY: 165,
            laneMaxY: 245,
            drawAllLines: false
        };

        // Hidden
        this.serverTime = -1;
        this.rpiBatteryVoltage = -1;
        this.motorBatteryVoltage = -1;
        this.isConnected = false;
        this.binaryImage = undefined;
        this.image = new Image();

        // Constants
        this.FONT = '16px Sans';
        this.MIN_CELL_VOLTAGE = 3.2;
        this.MAX_CELL_VOLTAGE = 4.1;
        this.SPEED_BAR_WIDTH = 15;
        this.SPEED_BAR_SEPARATION = 15;
    } 
    reset() {
        this.rpiBatteryVoltage = -1;
        this.motorBatteryVoltage = -1;
        this.isConnected = false;
        this.startAuto = false;
    }
}

// ------------------------------------------------------------------
// Variables
// ------------------------------------------------------------------

// Global Objects.
let canvas = undefined;                                         // Canvas html object.
let ctx = undefined;                                            // Context of the canvas.
let gui = undefined;                                            // dat.GUI object.
let guiFolders = [];
let settings = new Settings();                                  // Settings object used by the dat.GUI object.
let mouse = new Mouse();                                        // Mouse object. Stores the position and handles callbacks.
let joystick = new Joystick();                                  // Joystick for speed control.
let connectedLabel = new Label('Server', true);                              // Label for displaying if the app is connected to the server.
let rpiBatteryLabel = new Label('RPi', true);                                // Label for displaying the remaining battery capacity.
let motorBatteryLabel = new Label('Motor', true);                               // Label for displaying the remianing motor battery capacity.
let startButton = new Button('Start Auto', startClicked, [0, 255, 0]);            // Button for opencv start.
let shutdownButton = new Button('Shutdown', shutdownClicked, [255, 0, 0]);   // Button for stoping the server.
const socket = io.connect('http://10.0.0.2:8000');              // Socket to the server.


// ------------------------------------------------------------------
// Init
// ------------------------------------------------------------------

/**
 * Shorthand for document.onLoad function. This function runs when the document
 * is loaded. Creates the new GUI object and initializes the canvas and the
 * animation process.
 */
$(() => {
    
    // Configure settings.
    gui = new dat.GUI();

    // Folder 1: General settings.
    let f1 = gui.addFolder('General');
    guiFolders.push(f1);
    f1.add(settings, 'width');
    f1.add(settings, 'height');
    f1.add(settings, 'isMouseDown');
    f1.add(settings, 'isConnected');
    f1.add(settings, 'rpiBatteryVoltage');
    f1.add(settings, 'motorBatteryVoltage');
    f1.add(settings, 'maxManualSpeed', 0, 100, 1);
    // f1.open();
    
    // Folder 2: OpenCV settings.
    let f2 = gui.addFolder('Camera');
    guiFolders.push(f2);
    f2.add(settings.camera, 'enabled');
    f2.add(settings.camera, 'display', [
        'raw', 
        'undistorted', 
        'gray', 
        'blur', 
        'edges', 
        'maskedEdges',
        'houghLines'
    ]);
    f2.add(settings.camera, 'blurKernelSize', [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21]);
    f2.add(settings.camera, 'blurIterations', 1, 5, 1);
    f2.add(settings.camera, 'cannyLowThreshold', 1, 200, 1);
    f2.add(settings.camera, 'cannyHighThreshold', 1, 200, 1);
    f2.add(settings.camera, 'houghRho', 1, 200, 1);
    f2.add(settings.camera, 'houghThreshold', 1, 200, 1);
    f2.add(settings.camera, 'houghMinLineLength', 1, 100, 1);
    f2.add(settings.camera, 'houghMaxLineGap', 1, 100, 1);
    f2.add(settings.camera, 'roiY0', 1, 320, 1)
    f2.add(settings.camera, 'roiY1', 1, 320, 1);
    f2.add(settings.camera, 'roiBottom', 1, 480, 1);
    f2.add(settings.camera, 'roiTop', 1, 480, 1);
    f2.add(settings.camera, 'absMinLineAngle', 0, 45, 1);
    f2.add(settings.camera, 'laneMinY', 0, 320, 1);
    f2.add(settings.camera, 'laneMaxY', 0, 320, 1);
    f2.add(settings.camera, 'drawAllLines');
    f2.open();
    
    // Get the canvas objects.
	canvas = document.getElementById('control');
	ctx = canvas.getContext('2d');
    
    // Set all listeners.
    bindListeners();
    
    // Start the animation sequence.
    draw();

});


/**
 * Binds all the event listeners for this application. These include the
 * mouse and resize callbacks.
 */
function bindListeners() {

    // Set callbacks.
    if (!mouse.isTouch) {
        canvas.addEventListener('mouseup', (e) => { mouse.mouseUp(e); }, false);
        canvas.addEventListener('mousedown', (e) => { mouse.mouseDown(e); }, false);
        canvas.addEventListener('mousemove', (e) => { mouse.mouseMove(e) }, false);
    }
    canvas.addEventListener('touchmove', (e) => { mouse.touchMove(e); }, false);
	canvas.addEventListener('touchstart', (e) => { mouse.touchStart(e); }, false);
	canvas.addEventListener('touchend', (e) => { mouse.touchEnd(e); }, false);
    window.addEventListener('resize', resize, false);

    // Force resize event.
    resize();

}

/**
 * Callback function for the resize events.
 * Makes sure that the canvas fills up the screen. The pixelratio must be taken into
 * account. This produces crisper displays on HDPI displays.
 */
function resize() {

    // Get the dimensions of the webpage.
    settings.width = document.body.clientWidth;
    settings.height = document.body.clientHeight;
    
    // Get the pixel ratio and set the dimensions of the canvas.
	const pixelRatio = window.devicePixelRatio;
	canvas.width = Math.floor(settings.width * pixelRatio);
    canvas.height = Math.floor(settings.height * pixelRatio);
    
    // Set the style dimensions of the canvas to match the browser's dimensions.
	canvas.style.width = `${settings.width}px`;
    canvas.style.height = `${settings.height}px`;
    
    // Scale the canvas to the desired pixel ration.
    ctx.scale(pixelRatio, pixelRatio);
    
    // Call other object's resize functions.
    joystick.resize();

}

// ------------------------------------------------------------------
// Draw loop
// ------------------------------------------------------------------

/**
 * Draws the left and right speed bars.
 */
function drawSpeedBars() {

    let w = settings.SPEED_BAR_WIDTH;       // Width of the bars in pixels.
    let x = settings.SPEED_BAR_SEPARATION;  // Sepeartion between bars from the start -x position.

    // Sets the center position for the bars.
    ctx.save();
    ctx.translate(75, settings.height / 2);

    // Draw the background of the bars.
    ctx.beginPath();
    ctx.fillStyle = 'rgba(255, 255, 255, 0.15)';
    ctx.rect(-x - w/2, -100, w, 200);
    ctx.rect(x - w/2, -100, w, 200);
    ctx.fill();
    ctx.closePath();

    // Draw the text labels for the bars.
    ctx.beginPath();
    ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
    ctx.textAlign = 'center';
    ctx.fillText('L', -x, -110)
    ctx.fillText('R', x, -110)
    ctx.closePath();

    // Draws the left speed bar.
    ctx.beginPath();
    ctx.fillStyle = getSpeedColor(joystick.leftSpeed);
    ctx.rect(-x - w / 2, 0, w, -joystick.leftSpeed);
    ctx.fill();
    ctx.closePath();

    // Draws the right speed bar.
    ctx.beginPath();
    ctx.fillStyle = getSpeedColor(joystick.rightSpeed);
    ctx.rect(x - w / 2, 0, w, -joystick.rightSpeed);
    ctx.fill();
    ctx.closePath();

    // Restores back the transofrmation done.
    ctx.restore();

}

/**
 * Draws all labels and buttons to the canvas. The position, color and label of each element
 * is calculated here.
 */
function drawLabels() {

    // Update the connection label.
    connectedLabel.value = settings.isConnected ? 'Connected' : 'Disconnected';
    connectedLabel.color = settings.isConnected ? 'rgba(0, 255, 0, 0.3)' : 'rgba(255, 0, 0, 0.3)';
    
    // Change the style of the button.
    startButton.label = settings.camera.enabled ? 'Stop Auto' : 'Start Auto';
    startButton.color = settings.camera.enabled ? [255, 0, 0] : [0, 255, 0];

    // Rasperrby Pi battery label.
    // Make sure that the status has the property.
    if (settings.isConnected) {
        rpiBatteryLabel.value = `${settings.rpiBatteryVoltage} V`;
        rpiBatteryLabel.color = getChargeColor(settings.rpiBatteryVoltage, 1);
    } else {
        rpiBatteryLabel.value = '-';
        rpiBatteryLabel.color = 'rgba(255, 255, 255, 0.15)';
    }
    
    // Motor battery label.
    // Make sure that the status has the property.
    if (settings.isConnected) {
        motorBatteryLabel.value = `${settings.motorBatteryVoltage} V`;
        motorBatteryLabel.color = getChargeColor(settings.motorBatteryVoltage, 2);
    } else {
        motorBatteryLabel.value = '-';
        motorBatteryLabel.color = 'rgba(255, 255, 255, 0.15)';
    }
    
    // Set the position of the elements.
    connectedLabel.setPosition(connectedLabel.width / 2 + 40, settings.height / 2 - 200);
    rpiBatteryLabel.setPosition(connectedLabel.width + rpiBatteryLabel.width / 2 + 60, connectedLabel.position.y);
    motorBatteryLabel.setPosition(connectedLabel.width + rpiBatteryLabel.width + 80 + motorBatteryLabel.width / 2, connectedLabel.position.y);
    startButton.setPosition(startButton.width / 2 + 40, settings.height / 2 + 200);
    shutdownButton.setPosition(settings.width - shutdownButton.width / 2 - 40, settings.height / 2 + 200);

    // Draw the buttons and labels to the canvas.
    connectedLabel.draw();
    rpiBatteryLabel.draw();
    motorBatteryLabel.draw();
    shutdownButton.draw();
    startButton.draw();

}
 
/**
 * Draws the last received image from the server into the canvas.
 * The image is centered around width / 2 and height / 2.
 */
function drawImage() {

    // If the server is connected and has received a valid image.
    if (settings.isConnected && settings.binaryImage != undefined) {

        // Display dimensions
        let scale = 1;
        let frameWidth = 480 * scale;
        let frameHeight = 320 * scale;

        // Display image by setting the source of the Image obect to the received image.
        settings.image.src = settings.binaryImage;
        ctx.drawImage(settings.image, settings.width / 2 - frameWidth / 2, settings.height / 2 - frameHeight / 2, frameWidth, frameHeight);

    }
     
}

/**
 * This function runs at 60fps. Draws the main components and sends the speed to the server.
 * By sending such message, a status message is received in response.
 */
function draw() {

    // Sends a status message to the server. This message starts the communication cycle.
    if (settings.isConnected) {

        // Convert the blurKernelSize to an int.
        let cameraSettings = settings.camera;
        cameraSettings.blurKernelSize = parseInt(cameraSettings.blurKernelSize)
        
        // Send status to the server.
        socket.emit('message', {
            'leftSpeed': joystick.leftSpeed,
            'rightSpeed': joystick.rightSpeed,
            'camera': cameraSettings
        });    
    }

    // Clear the whole canvas.
    ctx.clearRect(0, 0, settings.width, settings.height);

    // Set font for all objects in the canvas.
    ctx.font = settings.FONT;
    
    // Draw elements to the canvas.
    drawImage();        // Draws the received image to the canvas.
    joystick.draw();    // Draws the joystick if needed.
    drawSpeedBars();    // Draws the speed bars.
    drawLabels();       // Draws labels and buttons.
    
    // Iterate over all folders in the gui in order to update them.
    for (let i = 0; i < guiFolders.length; i++) {

        // If any of the folders is opened then update the controls inside of it.
        if (!guiFolders[i].closed) {
            for (let j in guiFolders[i].__controllers) {
                guiFolders[i].__controllers[j].updateDisplay();
            }
        }
    }

    // Request the next animation frame.
    requestAnimationFrame(draw);

}

// ------------------------------------------------------------------
// Sockets
// ------------------------------------------------------------------

/**
 * Callback function for when the connection to the server is established.
 */
socket.on('connect', () => {
    settings.isConnected = true;
})

/**
 * Callback function for when the connection to the server is lost.
 */
socket.on('disconnect', () => {
    settings.reset()
});

/**
 * Callback function for the 'status' message.
 * This message is sent from the server.
 */
socket.on('status', (data) => {
    if (data) {

        // Copy the received data to the status.
        settings.rpiBatteryVoltage = data['rpiBatteryVoltage']
        settings.motorBatteryVoltage = data['motorBatteryVoltage']
        settings.serverTime = data['time'];
        rawImage = data['image']

        // Check if image data was received.
        if (rawImage && rawImage != -1) {
            settings.binaryImage = byteArrayToImage(rawImage);
        }

    }
});

// ------------------------------------------------------------------
// Buttons
// ------------------------------------------------------------------

/**
 * Callback function for when the start button is pressed.
 * By calling this function the control algorithm on the Camera is enabled or disabled.
 */
function startClicked() {

    if (settings.isConnected) {

        // Change the settings object.
        settings.camera.enabled = !settings.camera.startAuto;

    }
    
}

/**
 * Callback function for when the shutdown button is pressed.
 */
function shutdownClicked() {

    // Confirm that the user wants to shutdown the system.
    if (settings.isConnected && window.confirm('Are you sure?')) {
        socket.emit('shutdown', true);
    }

}