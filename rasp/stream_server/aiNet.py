import tensorflow as tf # Default graph is initialized when the library is imported
import os
from PIL import Image
import numpy as np
import cv2
import sys
from tensorflow.lite.python import interpreter as interpreter_wrapper
import time

IMAGE_MEAN = 0.0
IMAGE_STD = 255.0

class AINet(object):
  def __init__(self, model_dir):
    self.interpreter = interpreter_wrapper.Interpreter(model_path=model_dir)
    self.interpreter.allocate_tensors()

    self.input_details = self.interpreter.get_input_details()
    self.output_details = self.interpreter.get_output_details()

    print(self.input_details)
    print(self.output_details)

  def predict(self, img, quantized = True):
    print(img.shape)
    resized_image = cv2.resize(img, (32, 32), cv2.INTER_AREA)

    if quantized == False:
      resized_image = resized_image.astype('float32')
      mean_image = np.full((32, 32), IMAGE_MEAN, dtype='float32')
      resized_image = (resized_image - mean_image)/IMAGE_STD

    resized_image = resized_image[np.newaxis, ...]

    start_time = time.time()
    self.interpreter.set_tensor(self.input_details[0]['index'], resized_image)
    self.interpreter.invoke()

    output_data0 = self.interpreter.get_tensor(self.output_details[0]['index'])
    output_data0 = np.squeeze(output_data0)
    output_data0 = output_data0.astype(np.float)

    out = np.amax(output_data0)
    idex = np.where(output_data0 == out)

    return idex[0][0],out/255

def testAI():

  img = cv2.imread('./test_images/image1.jpg')
  image_org = img
  net = AINet("./pretrained_model/model_best_quantized.tflite")
  idex,out = net.predict(img)

  print('{}:{}%'.format(idex,out))

if __name__ == '__main__':
  testAI()