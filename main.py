from objc_util import *
from ctypes import c_void_p
from PIL import Image
from PIL import ImageOps
import ui
import io
import os
import time
import photos
import tempfile
import coreimage
import concurrent.futures
import webbrowser

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

        self.mainView = ui.View()
        self.mainView.background_color = 'black'
        self.mainView.height = ui.get_screen_size()[0]*1.78
        self.mainView.width = ui.get_screen_size()[0]
        self.mainView.name = 'Silent Camera'

        # if iPad == True: #overwrite
        #self.height = ui.get_screen_size()[1]/1.3
        #self.width = ui.get_screen_size()[0]/1.5

        sampleBufferDelegate = create_objc_class(
            'sampleBufferDelegate',
            methods=[
                self.captureOutput_didOutputSampleBuffer_fromConnection_],
            protocols=['AVCaptureVideoDataOutputSampleBufferDelegate'])
        delegate = sampleBufferDelegate.new()

        session = AVCaptureSession.alloc().init()
        device = AVCaptureDevice.defaultDeviceWithMediaType_('vide')
        _input = AVCaptureDeviceInput.deviceInputWithDevice_error_(
            device, None)
        if _input:
            session.addInput_(_input)
        else:
            print('Failed to create input')
            return

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

        self.whitenView = ui.View()
        self.whitenView.height = self.mainView.height
        self.whitenView.width = self.mainView.width
        self.whitenView.background_color = 'white'
        self.whitenView.alpha = 0.0

        button = ui.Button()
        button.flex = 'T'
        button.width = ui.get_screen_size()[0]*0.24
        button.height = button.width
        button.center = (self.mainView.width*0.5, self.mainView.height*0.85)
        button.action = self.button_tapped
        button.background_image = ui.Image('iow:ios7_circle_filled_256')
        # button.alpha=0.8

        self.latestPhotoView = ui.ImageView()
        self.latestPhotoView.background_color = 'white'
        self.latestPhotoView.flex = 'T'
        self.latestPhotoView.height = 50
        self.latestPhotoView.width = self.latestPhotoView.height
        self.latestPhotoView.center = (
            self.mainView.width*0.12, self.mainView.height*0.85)
        self.latestPhotoView.image = self.get_latest_photo()

        self.savingPhotoView = ui.ImageView()
        self.savingPhotoView.background_color = 'black'
        self.savingPhotoView.flex = 'T'
        self.savingPhotoView.height = 50
        self.savingPhotoView.width = self.savingPhotoView.height
        self.savingPhotoView.center = (
            self.mainView.width*0.12, self.mainView.height*0.85)
        self.savingPhotoView.image = ui.Image('iow:load_d_32')
        self.savingPhotoView.alpha = 0.0

        openPhotoapp = ui.Button()
        openPhotoapp.flex = 'T'
        openPhotoapp.height = 50
        openPhotoapp.width = openPhotoapp.height
        openPhotoapp.center = (self.mainView.width*0.12,
                               self.mainView.height*0.85)
        openPhotoapp.action = self._openPhotoapp

        self.mainView.add_subview(self.whitenView)
        self.mainView.add_subview(button)
        self.mainView.add_subview(self.latestPhotoView)
        self.mainView.add_subview(self.savingPhotoView)
        self.mainView.add_subview(openPhotoapp)

        session.startRunning()

        self.mainView.present('fullscreen', title_bar_color='black')
        self.mainView.wait_modal()

        session.stopRunning()
        delegate.release()
        session.release()
        output.release()

    def _openPhotoapp(self, sender):
        self.mainView.close()
        webbrowser.open('photos-redirect://')
        exit()

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

    def take_photo(self):
        while True:
            if self.captureFlag == True:
                self.captureFlag = False
                break

        self.whiteWaiter.submit(self._whiteWaiter)
        self.savingPhotoView.alpha = 0.5
        self.img = coreimage.CImage()
        self.img.ci_img = self.ciimage

        #ui_img = self.img.get_uiImg()
        pilimg = self.img.get_PIL()
        pilimg = pilimg.rotate(270, expand=True)
        self.pilSaveAlbulm(pilimg)
        self.latestPhotoView.image = self.get_latest_photo()
        self.savingPhotoView.alpha = 0.0
        #self.stopView.image = None
        # self.img.save_album()

    def pilSaveAlbulm(self, pilImg):
        #temp_path = os.path.join(tempfile.gettempdir(), 'temp.png')
        pilImg.save('temp.png')
        photos.create_image_asset('temp.png')

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


cam = muon()
