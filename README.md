# Pythonista_Silent_camera

## How to use

Clone the repository or download zip file and send it to your device

<pre>
camera(format='JPEG',
       save_to_album=True, 
       return_image=False)
</pre>

- **format**

  - supports JPEG,PNG,PIL,UIImage,CIImage
  - If you choose PIL UIImage or CIImage, **save_to_album** becomes false

- **save_to_album**

  - save photo to album when it is `True`

- **return_image**
  - You can get image using .getData() and automatically close when photo saves successfully 
## features

- Tap to focus
- No sutter sound
- Hi resorution photo
- Support triple lens camera

## Tesed devices

- iPhone 11 Pro
- iPhone XR

## Environment

- Pythonista 3.3

## Screenshot

![IMG_1004](https://user-images.githubusercontent.com/40960166/67027972-818c3e00-f145-11e9-9e7c-b822c5045b0d.png)

## ToDo

- iPad Support

## Bug

- incorrect resorutions
