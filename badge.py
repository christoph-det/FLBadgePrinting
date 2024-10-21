import terminal_colors
import qrcode
from PIL import Image, ImageDraw, ImageFont
from time import sleep

import brother_ql
from brother_ql.raster import BrotherQLRaster
from brother_ql.backends.helpers import send

import usb.core

import unicodedata


printer_found = usb.core.find(idVendor=0x4F9)

if printer_found:
    printer_vendor = hex(printer_found.idVendor)
    printer_product = hex(printer_found.idProduct)
    PRINTER_IDENTIFIER = f"usb://{printer_vendor}:{printer_product}"
    print(PRINTER_IDENTIFIER)
else:
    print(terminal_colors.RED + "Error: No printer connected. Limited functionality." + terminal_colors.RESET)



# USB or TCP
PRINTER_NAME = 'QL-810W'
# Can be found 
# PRINTER_IDENTIFIER = 'usb://04f9:209c'
# LABEL_FORMAT = '29x90'
LABEL_FORMAT = '62'
#PRINTABLE_SIZE = (1050, 696)
PRINTABLE_SIZE = (1050, 696)


def generate_qr_code(URL):
    img = qrcode.make(URL, error_correction=qrcode.constants.ERROR_CORRECT_M)
    return img


def create_label_image(first_name, surname, company, position, eventname):
   
    first_name = unicodedata.normalize('NFC', first_name)
    surname = unicodedata.normalize('NFC', surname)
    company = unicodedata.normalize('NFC', company)
    position = unicodedata.normalize('NFC', position)
    eventname = unicodedata.normalize('NFC', eventname)


    future_law_logo = Image.open('future_law_logo.jpg')
    font_face = "arial.ttf"
    
    biggest_font = ImageFont.truetype(font_face, 110)
    big_font = ImageFont.truetype(font_face, 75)
    normal_font = ImageFont.truetype(font_face, 45)
    small_font = ImageFont.truetype(font_face, 38)
    img = Image.new('L', PRINTABLE_SIZE, color='white')

    d = ImageDraw.Draw(img)

    # draw information on badge
    d.text((40, 70), first_name, fill="black", font=biggest_font)
    d.text((40, 190), surname, fill="black", font=big_font)
    # add separator
    d.line((40, 300, 1010, 300), fill="black", width=5)
    # company
    d.text((40, 370), company, fill="black", font=normal_font)
    # position
    d.text((40, 440), position, fill="black", font=normal_font)
    d.text((40, 610), eventname, fill="black", font=small_font)

    # add logo

    # if "legal tech" in eventname.lower():
    #    img.paste(future_law_logo.resize((300, 53), Image.LANCZOS), (720, 600))
    
    # QR Code
    # qr_code = generate_qr_code('https:future-law.eu')
    # img.paste(qr_code.resize((270, 270), Image.ANTIALIAS), (720, 0))

    img = img.rotate(90, expand=True)

    img.save('generated_badge.png')
    sleep(0.1)
    send_to_printer('generated_badge.png')


def send_to_printer(path):
    printer = BrotherQLRaster(PRINTER_NAME)
    print_data = brother_ql.brother_ql_create.convert(printer, [path], LABEL_FORMAT, dither=True, hq=False)
    send(print_data, PRINTER_IDENTIFIER)