from objc_util import *
from ctypes import c_void_p
from PIL import Image
from PIL import ImageOps
import Gestures
import ui
import io
import os
import time
import photos
import tempfile
import coreimage
import concurrent.futures
import webbrowser
import datetime
import numbers
import math

# for test
import inspect

AVCaptureSession = ObjCClass('AVCaptureSession')
AVCaptureDevice = ObjCClass('AVCaptureDevice')
AVCaptureDeviceInput = ObjCClass('AVCaptureDeviceInput')
AVCaptureVideoDataOutput = ObjCClass('AVCaptureVideoDataOutput')
AVCaptureVideoPreviewLayer = ObjCClass('AVCaptureVideoPreviewLayer')

CMSampleBufferGetImageBuffer = c.CMSampleBufferGetImageBuffer
CMSampleBufferGetImageBuffer.argtypes = [c_void_p]
CMSampleBufferGetImageBuffer.restype = c_void_p

CVPixelBufferLockBaseAddress = c.CVPixelBufferLockBaseAddress
CVPixelBufferLockBaseAddress.argtypes = [c_void_p, c_int]
CVPixelBufferLockBaseAddress.restype = None

CVPixelBufferUnlockBaseAddress = c.CVPixelBufferUnlockBaseAddress
CVPixelBufferUnlockBaseAddress.argtypes = [c_void_p, c_int]
CVPixelBufferUnlockBaseAddress.restype = None

CIImage = ObjCClass('CIImage')
UIImage = ObjCClass('UIImage')

dispatch_get_current_queue = c.dispatch_get_current_queue
dispatch_get_current_queue.restype = c_void_p


class muon():
    def __init__(self):
        self.ciimage = None
        self.take_photo_flag = False
        self.captureFlag = False
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        self.whiteWaiter = concurrent.futures.ThreadPoolExecutor(max_workers=2)

        self._init_mainview()

        iPad = False

        if iPad == True:  # overwrite
            self.mainView.height = ui.get_screen_size()[1]/1.3
            self.mainView.width = ui.get_screen_size()[0]/1.5
            self.prez = 'sheet'

        print('init camera Settings')

        sampleBufferDelegate = create_objc_class(
            'sampleBufferDelegate',
            methods=[
                self.captureOutput_didOutputSampleBuffer_fromConnection_],
            protocols=['AVCaptureVideoDataOutputSampleBufferDelegate'])
        delegate = sampleBufferDelegate.new()

        session = AVCaptureSession.alloc().init()
        cameraTypes = ['AVCaptureDeviceTypeBuiltInTripleCamera', 'AVCaptureDeviceTypeBuiltInDualCamera',
                       'AVCaptureDeviceTypeBuiltInDualWideCamera', 'AVCaptureDeviceTypeBuiltInWideAngleCamera']

        self.cameraMaxZoom = [16, 16, 4, 4]
        defeaultZoom = [1.0, 0.5, 1.0, 0.5]
        self.typeNum = 0

        for camtype in cameraTypes:
            self.device = AVCaptureDevice.defaultDeviceWithDeviceType_mediaType_position_(
                camtype, 'vide', 0)
            _input = AVCaptureDeviceInput.deviceInputWithDevice_error_(
                self.device, None)
            if _input:
                session.addInput_(_input)
                print(camtype)
                break
            else:
                self.typeNum += 1

        else:
            print('Failed to create input')
            return

        self.device._setVideoHDREnabled_ = True
        self.device.isVideoHDREnabled = True
        self.device.isVideoStabilizationSupported = True
        self.device.isLensStabilizationSupported = True

        output = AVCaptureVideoDataOutput.alloc().init()
        queue = ObjCInstance(dispatch_get_current_queue())
        output.setSampleBufferDelegate_queue_(delegate, queue)
        output.alwaysDiscardsLateVideoFrames = True

        session.addOutput_(output)
        session.sessionPreset = 'AVCaptureSessionPreset3840x2160'

        prev_layer = AVCaptureVideoPreviewLayer.layerWithSession_(session)
        prev_layer.frame = ObjCInstance(self.mainView).bounds()
        prev_layer.setVideoGravity_('AVLayerVideoGravityResizeAspectFill')

        ObjCInstance(self.mainView).layer().addSublayer_(prev_layer)

        self._init_whitenView()
        self._init_shootbutton()
        self._init_latestPhotoView()
        self._init_savingPhotoView()
        self._init_openPhotoapp()
        self._init_closeButton()
        self._init_gestureView()
        self._init_zoomView()
        self._init_changeZoomButton()
        self._init_zoomLevelLabel()
        self._mettya_subView()

        print('Starting silent camera...')
        session.startRunning()
        self.changeZoom(defeaultZoom[self.typeNum])
        self.oldZoomScale = defeaultZoom[self.typeNum]
        self.currentZoomScale = defeaultZoom[self.typeNum]

        self.mainView.present(
            self.prez, title_bar_color='black', hide_title_bar=True)
        self.mainView.wait_modal()

        print('Stop running...')

        session.stopRunning()
        delegate.release()
        session.release()
        output.release()

    def pinchChange(self, recog):
        pinchZoomScale = recog.scale
        self.currentZoomScale = self.oldZoomScale - \
            (1-pinchZoomScale)*self.oldZoomScale

        if self.currentZoomScale <= 0.5:
            self.currentZoomScale = 0.5

        if self.currentZoomScale >= self.cameraMaxZoom[self.typeNum]:
            self.currentZoomScale = self.cameraMaxZoom[self.typeNum]

        self.changeZoom(self.currentZoomScale)

        if recog.state == 3:
            self.touch_ended()

    def changeZoom(self, scale):
        self.device.lockForConfiguration(None)
        self.device.videoZoomFactor = scale*2
        self.device.unlockForConfiguration()
        self.zoomLevelLabel.text = str('x{}'.format(round(scale, 1)))

        return scale

    def zoomAnimation(self, scale):
        t = 0
        d = scale - self.oldZoomScale
        for i in range(int(d*1000)):
            t = 0.000001 + math.exp(i/4000)/2.74/10000

            time.sleep(t)
            # print(self.oldZoomScale+i/10)
            self.changeZoom(self.oldZoomScale+i/1000)

        return scale

    def zoomAnimationB(self, scale):
        d = self.oldZoomScale - scale
        t = 0
        if d >= 1.5:
            d2 = d-1.5
            d = 1.5
            for i in range(int(d2*100)):
                t = 0.000001
                # time.sleep(t)
                self.changeZoom(self.oldZoomScale-i/100)
            self.oldZoomScale = 2.0

        i = 0

        for i in range(int(d*1000)):
            t = 0.000001 + math.exp(i/1000/1.5*4)/2.74/1000000*6
            time.sleep(t)
            self.changeZoom(self.oldZoomScale-i/1000)

        return scale

    def touch_ended(self):
        self.oldZoomScale = self.currentZoomScale

    def _openPhotoapp(self, sender):
        self.mainView.close()
        webbrowser.open('photos-redirect://')
        exit()

    def _closeButton(self, sender):
        self.mainView.close()

    def _whiteWaiter(self):
        for i in range(10):
            time.sleep(0.008)
            if i == 0:
                self.whitenView.alpha = 9.0
            else:
                self.whitenView.alpha = (9-i)/10

    def button_tapped(self, sender):
        self.whitenView.alpha = 1.0
        self.take_photo_flag = True
        # self.take_photo()
        self.executor.submit(self.take_photo)

    def chabgeZoomButton_tapped(self, sender):
        if self.oldZoomScale >= 2.0:
            if self.typeNum == 0:
                i = self.zoomAnimationB(0.5)
            else:
                i = self.zoomAnimationB(1.0)
        elif self.oldZoomScale >= 1.0:
            if self.typeNum == 0:
                i = self.zoomAnimation(2.0)
            elif self.typeNum == 1:
                i = self.zoomAnimation(2.0)
            elif self.typeNum == 2:
                i = self.zoomAnimationB(0.5)
            else:
                i = self.zoomAnimationB(1.0)
        elif self.oldZoomScale >= 0.5:
            i = self.zoomAnimation(1.0)
            self.changeZoom(1.2)
            self.changeZoom(1.0)

        self.oldZoomScale = i

    def take_photo(self):
        while True:
            if self.captureFlag == True:
                self.captureFlag = False
                break

        self.whiteWaiter.submit(self._whiteWaiter)
        self.savingPhotoView.alpha = 0.5
        self.img = coreimage.CImage()
        self.img.ci_img = self.ciimage

        self.shoot = time.time()

        #ui_img = self.img.get_uiImg()
        pilimg = self.img.get_PIL()
        delta = time.time() - self.shoot
        print('get pil time:{}'.format(delta))
        pilimg = pilimg.rotate(270, expand=True)

        delta = time.time() - self.shoot
        print('rotated time:{}'.format(delta))
        self.pilSaveAlbulm(pilimg)
        self.latestPhotoView.image = self.get_latest_photo()
        self.savingPhotoView.alpha = 0.0
        #self.stopView.image = None
        # self.img.save_album()

    def pilSaveAlbulm(self, pilImg):
        delta = time.time() - self.shoot
        print('called time:{}'.format(delta))

        today = datetime.datetime.now().strftime("%Y%m%d-%H%M")
        delta = time.time() - self.shoot
        print('get filename time:{}'.format(delta))

        temp_path = os.path.join(tempfile.gettempdir(), '{}.png'.format(today))
        delta = time.time() - self.shoot
        print('get path time:{}'.format(delta))
        # print(temp_path)

        pilImg.save(temp_path)
        delta = time.time() - self.shoot
        print('pil saved time:{}'.format(delta))

        photos.create_image_asset(temp_path)
        delta = time.time() - self.shoot
        print('album saved time:{}'.format(delta))

    def pil2ui(self, imgIn):
        with io.BytesIO() as bIO:
            imgIn.save(bIO, 'PNG')
            imgOut = ui.Image.from_data(bIO.getvalue())
        del bIO
        return imgOut

    def ci2ui(self, ci_img):
        ctx = ObjCClass('CIContext').context()
        extent = ci_img.extent()
        m = ctx.outputImageMaximumSize()
        if extent.size.width > m.width or extent.size.height > m.height:
            extent = CGRect(CGPoint(0, 0), CGSize(1024, 1024))
        cg_img = ctx.createCGImage_fromRect_(ci_img, extent)
        ui_img = UIImage.imageWithCGImage_(cg_img)
        c.CGImageRelease.argtypes = [c_void_p]
        c.CGImageRelease.restype = None
        c.CGImageRelease(cg_img)
        return ui_img

    def get_latest_photo(self):
        all_assets = photos.get_assets()
        last_asset = all_assets[-1]
        img = last_asset.get_image()

        if img.width >= img.height:
            img = img.resize((100, round(img.height/img.width*100)))
        else:
            img = img.resize((round(img.width/img.height*100), 100))

        return self.pil2ui(img)

    def captureOutput_didOutputSampleBuffer_fromConnection_(self, _self, _cmd, _output, _sample_buffer, *args):

        if self.take_photo_flag == True:
            self.take_photo_flag = False
            imagebuffer = CMSampleBufferGetImageBuffer(_sample_buffer)

            # バッファをロック
            CVPixelBufferLockBaseAddress(imagebuffer, 0)
            self.ciimage = CIImage.imageWithCVPixelBuffer_(
                ObjCInstance(imagebuffer))
            # バッファのロックを解放
            CVPixelBufferUnlockBaseAddress(imagebuffer, 0)
            self.captureFlag = True

    def _init_mainview(self):
        self.mainView = ui.View()
        self.mainView.background_color = 'black'
        self.mainView.height = ui.get_screen_size()[0]*1.78
        self.mainView.width = ui.get_screen_size()[0]
        self.mainView.name = 'Silent Camera'
        self.prez = 'fullscreen'

    def _init_whitenView(self):
        print('init whitenView')
        self.whitenView = ui.View()
        self.whitenView.height = self.mainView.height
        self.whitenView.width = self.mainView.width
        self.whitenView.background_color = 'black'
        self.whitenView.alpha = 0.0

    def _init_shootbutton(self):
        print('init shootButton')
        self.shootButton = ui.Button()
        self.shootButton.flex = 'T'
        self.shootButton.width = ui.get_screen_size()[0]*0.24
        self.shootButton.height = self.shootButton.width
        self.shootButton.center = (self.mainView.width*0.5,
                                   self.mainView.height*0.874)
        self.shootButton.action = self.button_tapped
        self.shootButton.background_image = ui.Image(
            'iow:ios7_circle_filled_256')

    def _init_latestPhotoView(self):
        print('init latestPhotoView')
        self.latestPhotoView = ui.ImageView()
        self.latestPhotoView.background_color = 'white'
        self.latestPhotoView.flex = 'T'
        self.latestPhotoView.height = 50
        self.latestPhotoView.width = self.latestPhotoView.height
        self.latestPhotoView.center = (
            self.mainView.width*0.12, self.mainView.height*0.874)
        self.latestPhotoView.image = self.get_latest_photo()

    def _init_savingPhotoView(self):
        print('init savingPhotoView')
        self.savingPhotoView = ui.ImageView()
        self.savingPhotoView.background_color = 'black'
        self.savingPhotoView.flex = 'T'
        self.savingPhotoView.height = 50
        self.savingPhotoView.width = self.savingPhotoView.height
        self.savingPhotoView.center = (
            self.mainView.width*0.12, self.mainView.height*0.874)
        self.savingPhotoView.image = ui.Image('iow:load_d_32')
        self.savingPhotoView.alpha = 0.0

    def _init_openPhotoapp(self):
        print('init openPhotoApp')
        self.openPhotoapp = ui.Button()
        self.openPhotoapp.flex = 'T'
        self.openPhotoapp.height = 50
        self.openPhotoapp.width = self.openPhotoapp.height
        self.openPhotoapp.center = (self.mainView.width*0.12,
                                    self.mainView.height*0.874)
        self.openPhotoapp.action = self._openPhotoapp

    def _init_closeButton(self):
        print('init closeButton')
        self.closeButton = ui.Button()
        self.closeButton.flex = 'RB'
        self.closeButton.center = (self.mainView.width*0.09,
                                   self.mainView.height*0.09)
        self.closeButton.image = ui.Image('iow:close_32')
        self.closeButton.height = 24
        self.closeButton.width = 24
        self.closeButton.tint_color = 'white'
        self.closeButton.action = self._closeButton

    def _init_gestureView(self):
        print('init gestureView')
        self.gestureView = ui.View()
        self.gestureView.multitouch_enabled = True
        self.gestureView.width = self.mainView.width
        self.gestureView.height = self.mainView.height
        self.gestureView.touch_ended = self.touch_ended
        Gestures.Gestures().add_pinch(self.gestureView, self.pinchChange)

    def _init_zoomView(self):
        self.zoomView = ui.View()
        self.zoomView.flex = 'T'
        self.zoomView.center = (self.mainView.width*0.88,
                                self.mainView.height*0.882)
        self.zoomView.height = 72
        self.zoomView.width = 72

    def _init_changeZoomButton(self):
        self.changeZoomButton = ui.Button()
        self.changeZoomButton.flex = 'WH'
        self.changeZoomButton.center = (self.zoomView.width*0,
                                        self.zoomView.height * 0.1)
        self.changeZoomButton.height = self.zoomView.height * 0.8
        self.changeZoomButton.width = self.zoomView.width
        self.changeZoomButton.action = self.chabgeZoomButton_tapped
        self.changeZoomButton.image = ui.Image('iow:ios7_camera_32')
        self.changeZoomButton.tint_color = 'white'

        self.zoomView.add_subview(self.changeZoomButton)

    def _init_zoomLevelLabel(self):
        self.zoomLevelLabel = ui.Label()
        self.zoomLevelLabel.flex = 'LT'
        self.zoomLevelLabel.width = self.zoomView.width
        self.zoomLevelLabel.center = (self.zoomView.width*0.82,
                                      self.zoomView.height * 0.9)
        self.zoomLevelLabel.text = 'x1.0'
        self.zoomLevelLabel.text_color = 'white'
        self.zoomView.add_subview(self.zoomLevelLabel)
        self.zoomLevelLabel.font = ('DIN Alternate', 16)

    def _mettya_subView(self):
        print('add subViews')

        self.mainView.add_subview(self.gestureView)
        self.mainView.add_subview(self.zoomView)
        self.mainView.add_subview(self.whitenView)
        self.mainView.add_subview(self.shootButton)
        self.mainView.add_subview(self.closeButton)
        self.mainView.add_subview(self.openPhotoapp)
        self.mainView.add_subview(self.latestPhotoView)
        self.mainView.add_subview(self.savingPhotoView)


cam = muon()
