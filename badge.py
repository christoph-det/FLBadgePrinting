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
LEFT_MARGIN = 40
RIGHT_MARGIN = 40
TEXT_WIDTH = PRINTABLE_SIZE[0] - LEFT_MARGIN - RIGHT_MARGIN


def get_text_size(draw, text, font):
    bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=4)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def fit_font(draw, text, font_face, max_size, min_size, max_width, max_height=None):
    for size in range(max_size, min_size - 1, -1):
        font = ImageFont.truetype(font_face, size)
        width, height = get_text_size(draw, text, font)
        if width <= max_width and (max_height is None or height <= max_height):
            return font
    return ImageFont.truetype(font_face, min_size)


def wrap_text_to_width(draw, text, font, max_width, max_lines=2):
    words = []
    for word in text.split():
        if get_text_size(draw, word, font)[0] <= max_width:
            words.append(word)
            continue

        chunk = ""
        for character in word:
            candidate = chunk + character
            if chunk and get_text_size(draw, candidate, font)[0] > max_width:
                words.append(chunk)
                chunk = character
            else:
                chunk = candidate
        if chunk:
            words.append(chunk)

    if not words:
        return ""

    lines = []
    current_line = words[0]

    for word in words[1:]:
        candidate = "{} {}".format(current_line, word)
        if get_text_size(draw, candidate, font)[0] <= max_width:
            current_line = candidate
        else:
            lines.append(current_line)
            current_line = word

    lines.append(current_line)

    if len(lines) <= max_lines:
        return "\n".join(lines)

    return "\n".join(lines[:max_lines - 1] + [" ".join(lines[max_lines - 1:])])


def fit_wrapped_text(draw, text, font_face, max_size, min_size, max_width, max_height, max_lines=2):
    for size in range(max_size, min_size - 1, -1):
        font = ImageFont.truetype(font_face, size)
        wrapped_text = wrap_text_to_width(draw, text, font, max_width, max_lines)
        width, height = get_text_size(draw, wrapped_text, font)
        if width <= max_width and height <= max_height:
            return wrapped_text, font

    font = ImageFont.truetype(font_face, min_size)
    return wrap_text_to_width(draw, text, font, max_width, max_lines), font


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
    
    biggest_font = fit_font(ImageDraw.Draw(Image.new('L', PRINTABLE_SIZE)), first_name, font_face, 110, 70, TEXT_WIDTH)
    small_font = ImageFont.truetype(font_face, 38)
    img = Image.new('L', PRINTABLE_SIZE, color='white')

    d = ImageDraw.Draw(img)
    surname, surname_font = fit_wrapped_text(d, surname, font_face, 95, 48, TEXT_WIDTH, 115, max_lines=2)
    company, company_font = fit_wrapped_text(d, company, font_face, 68, 44, TEXT_WIDTH, 120, max_lines=2)
    position, position_font = fit_wrapped_text(d, position, font_face, 45, 34, TEXT_WIDTH, 100, max_lines=2)
    company_height = get_text_size(d, company, company_font)[1]
    position_y = 370 + company_height + 28

    # draw information on badge
    d.text((LEFT_MARGIN, 70), first_name, fill="black", font=biggest_font)
    d.text((LEFT_MARGIN, 170), surname, fill="black", font=surname_font, spacing=4)
    # add separator
    d.line((LEFT_MARGIN, 300, PRINTABLE_SIZE[0] - RIGHT_MARGIN, 300), fill="black", width=5)
    # company

    d.text((LEFT_MARGIN, 370), company, fill="black", font=company_font, spacing=4)
    # position
    d.text((LEFT_MARGIN, position_y), position, fill="black", font=position_font, spacing=4)
    d.text((LEFT_MARGIN, 610), eventname, fill="black", font=small_font)

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
