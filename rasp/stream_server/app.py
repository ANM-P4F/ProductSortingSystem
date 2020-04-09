#!/usr/bin/env python
from importlib import import_module
import os
from flask import Flask, render_template, Response, jsonify
import camera_opencv
import aiNet
import cv2
import serial
from flask import request
import numpy as np
import time
import socket
import argparse
import sys

print ('Number of arguments:', len(sys.argv), 'arguments.')
print ('Argument List:', str(sys.argv))

parser = argparse.ArgumentParser(description='product soring system')
parser.add_argument('-p', '--portname', type=str, help='port name', default='/dev/ttyACM0')
parser.add_argument('-s', '--saveimg', type=int, help='save imgs', default=0)
myparser = parser.parse_args()


# # import camera driver
# if os.environ.get('CAMERA'):
#     Camera = import_module('camera_' + os.environ['CAMERA']).Camera
# else:
#     from camera import Camera

Camera = camera_opencv.Camera
net = aiNet.AINet("./pretrained_model/model_best_quantized.tflite")

# Raspberry Pi camera module (requires picamera package)
# from camera_pi import Camera

# configure the serial connections (the parameters differs on the device you are connecting to)
SERIAL = serial.Serial(
    port = myparser.portname,          #your arduino UART-USB name, check it on arduino-ide
    baudrate = 9600,
)

SERIAL.isOpen()

DETECTION_THRESHOLD = 500

CLASS_NAME = {
  0 : ("BATMAN LOGO",0),
  1 : ("P4F LOGO",0),
  2 : ("SUPERMAN LOGO",0)
}

serverPWM = 360

conveyorState = 0

thresh = 190
maxValue = 255 

# Create a UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
server_address = ('192.168.1.255', 1102)

def whiteBalance(img):
    result = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    avg_a = np.average(result[:, :, 1])
    avg_b = np.average(result[:, :, 2])
    result[:, :, 1] = result[:, :, 1] - ((avg_a - 128) * (result[:, :, 0] / 255.0) * 1.1)
    result[:, :, 2] = result[:, :, 2] - ((avg_b - 128) * (result[:, :, 0] / 255.0) * 1.1)
    result = cv2.cvtColor(result, cv2.COLOR_LAB2BGR)
    return result

def cropROI(img):
  # Convert the image to gray-scale
  gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

  # Basic threshold example
  th, bina = cv2.threshold(gray, thresh, maxValue, cv2.THRESH_BINARY)

  _, contours, hierarchy = cv2.findContours(bina, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

  print('*******************************')
  cnt = 0
  longest = 0
  contours_ = []
  max_x = []
  max_y = []
  min_x = []
  min_y = []
  pts = []
  for contour in contours:
    if(len(contour)>100):
      contours_.append(contour)
      contour = np.reshape(contour, [contour.shape[0],2])
      xmax, ymax = contour.max(axis=0)
      xmin, ymin = contour.min(axis=0)
      max_x.append(xmax)
      max_y.append(ymax)
      min_x.append(xmin)
      min_y.append(ymin)
  max_x = max(max_x)
  max_y = max(max_y)
  min_x = min(min_x)
  min_y = min(min_y)

  # print("min x {} max x {}".format(min_x, max_x))
  # print("min y {} max y {}".format(min_y, max_y))

  crop = img[ min_y:max_y, min_x:max_x].copy()

  return crop

app = Flask(__name__)

@app.route('/')
def index():
    """Video streaming home page."""
    return render_template('index.html')

def gen(camera):
    """Video streaming generator function."""
    result = ''
    frame = camera.get_frame()
    productBoxes = []
    productBoxes.append(((0, frame.shape[0]-50),(frame.shape[1]/3-2, frame.shape[0]-2)))
    productBoxes.append(((frame.shape[1]/3-2, frame.shape[0]-50),(frame.shape[1]/3*2-2, frame.shape[0]-2)))
    productBoxes.append(((frame.shape[1]/3*2-2, frame.shape[0]-50),(frame.shape[1]/3*3-2, frame.shape[0]-2)))

    while True:
        outSerial = ''
        frame = camera.get_frame()

        frame = whiteBalance(frame)

        while SERIAL.inWaiting() > 0:
            outSerial = SERIAL.readline().decode("utf-8")
        
        if outSerial != '':
            outSerial = outSerial.replace('\r\n','')
            print("Arduino=>pi: {}".format(outSerial))
            if outSerial == "STATE_PAUSE" :
              time.sleep(0.5)
              frame = camera.get_frame()
              cv2.imwrite('imgs/img_.jpg',frame)
              crop = cropROI(frame)
              if myparser.saveimg == 1:
                ts = time.time()
                ts = int(ts)
                # cv2.imwrite('imgs/img_'+str(ts)+'.jpg',frame)
                cv2.imwrite('imgs/crop_'+str(ts)+'.jpg',crop)
                print('saved {}'.format('imgs/img_'+str(ts)+'.jpg'))
                print('saved {}'.format('imgs/crop_'+str(ts)+'.jpg'))
              start_time = time.time()
              classNo, certainty = net.predict(crop)
              exe_time = time.time()-start_time
              certainty = round(certainty*100, 2)
              result = 'Detected:{}({}%) in {} s'.format(CLASS_NAME[int(classNo)][0], certainty, exe_time)
              SERIAL.write(('Detected:{}\r\n'.format(classNo)).encode())
              CLASS_NAME[int(classNo)] = (CLASS_NAME[int(classNo)][0], CLASS_NAME[int(classNo)][1] + 1)
              print(result)
            elif outSerial == "STATE_DETECTED":
              SERIAL.write(('RUN:'+str(serverPWM)).encode())
              sock.sendto(b'START', server_address)
        frame = cv2.resize(frame, (640,480))
        frame = cv2.putText(frame, result, (10,30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
        cnt = 0
        for productBox in productBoxes:
          frame = cv2.rectangle(frame, 
                                (int(productBox[0][0]), int(productBox[0][1])),
                                (int(productBox[1][0]), int(productBox[1][1])),
                                (0,255,0), 
                                2)
          frame = cv2.putText(frame, CLASS_NAME[cnt][0] + ': {}'.format(CLASS_NAME[cnt][1]), (int(productBox[0][0])+5,int((productBox[0][1]+productBox[1][1])/2)), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)
          cnt = cnt+1

        frame = cv2.imencode('.jpg', frame)[1].tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(gen(Camera()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/OFF')
def OFF():
    global conveyorState
    print("html request OFF")
    SERIAL.write('OFF'.encode())
    sock.sendto(b'STOP', server_address)
    conveyorState = 0
    resp = jsonify(success=True)
    return resp

@app.route('/RUN')
def RUN():
    global conveyorState
    print("html request RUN "+str(serverPWM))
    SERIAL.write(('RUN:'+str(serverPWM)).encode())
    sock.sendto(b'START', server_address)
    conveyorState = 1
    resp = jsonify(success=True)
    return resp

@app.route('/PWM')
def PWM():
    global serverPWM
    print("html update PWM {}".format(request.args['val']))
    serverPWM = int(request.args['val'])
    if conveyorState == 1:
      SERIAL.write(('RUN:'+str(serverPWM)).encode())
    resp = jsonify(success=True)
    return resp

if __name__ == '__main__':
    app.run(host='0.0.0.0', threaded=True)
