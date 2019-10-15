from objc_util import *
import inspect

inspectClass = ObjCClass('AVCaptureVideoDataOutput')

for x in dir(inspectClass):
  print (x)
