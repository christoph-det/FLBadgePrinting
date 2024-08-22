import qrcode
from PIL import Image, ImageDraw, ImageFont
from time import sleep

import brother_ql
from brother_ql.raster import BrotherQLRaster
from brother_ql.backends.helpers import send

# USB or TCP
PRINTER_NAME = 'Brother QL-570'
PRINTER_IDENTIFIER = 'usb://0x04f9:0x2028'
# LABEL_FORMAT = '29x90'
LABEL_FORMAT = '62'
PRINTABLE_SIZE = (1050, 696)


def generate_qr_code(URL):
    img = qrcode.make(URL, error_correction=qrcode.constants.ERROR_CORRECT_M)
    return img


def create_label_image(first_name, surname, company, position, eventname):
   
    # qr_code = generate_qr_code('{}/qr/{}/{}'.format(nijis_url, order_id, password))

    font_face = "arial.ttf"
    
    biggest_font = ImageFont.truetype(font_face, 110)
    big_font = ImageFont.truetype(font_face, 75)
    normal_font = ImageFont.truetype(font_face, 50)
    small_font = ImageFont.truetype(font_face, 45)
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

    # TODO: add image of logo
    
    
    # if use_nijis:
    #     d.text((20, 250), "Workshops - {}".format(nijis_url), fill="black", font=jam_font)
    #    img.paste(qr_code.resize((270, 270), Image.ANTIALIAS), (720, 0))
    #    d.text((740, 250), "Scan me with your phone \n to book into workshops!", fill="black", font=qr_font)

    img.save('generated_badge.png')
    sleep(0.1)
    send_to_printer('generated_badge.png')


def send_to_printer(path):
    printer = BrotherQLRaster(PRINTER_NAME)
    print_data = brother_ql.brother_ql_create.convert(printer, [path], LABEL_FORMAT, dither=True, rotate="auto", hq=False)
    send(print_data, PRINTER_IDENTIFIER)