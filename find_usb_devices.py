import usb.core

def find_usb_devices():
    devices = usb.core.find(find_all=True)
    return devices

if __name__ == '__main__':
    print(find_usb_devices())

