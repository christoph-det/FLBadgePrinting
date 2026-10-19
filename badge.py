import terminal_colors
import qrcode
from PIL import Image, ImageDraw, ImageFont
from time import sleep
import logging

# brother_ql still imports its own deprecated module internally; hide that warning
logging.getLogger('brother_ql.devicedependent').setLevel(logging.ERROR)

import brother_ql
from brother_ql.raster import BrotherQLRaster
from brother_ql.backends.helpers import send

import usb.core

import os
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
LEFT_MARGIN = 60
RIGHT_MARGIN = 60
TEXT_WIDTH = PRINTABLE_SIZE[0] - LEFT_MARGIN - RIGHT_MARGIN

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(BASE_DIR, "fonts")
FONT_DISPLAY_REGULAR = os.path.join(FONT_DIR, "InterDisplay-Regular.ttf")
FONT_DISPLAY_SEMIBOLD = os.path.join(FONT_DIR, "InterDisplay-SemiBold.ttf")
FONT_DISPLAY_BOLD = os.path.join(FONT_DIR, "InterDisplay-Bold.ttf")
FONT_REGULAR = os.path.join(FONT_DIR, "Inter-Regular.ttf")
FONT_MEDIUM = os.path.join(FONT_DIR, "Inter-Medium.ttf")


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

    if len(lines) == 2:
        lines = balance_two_lines(draw, words, font)

    if len(lines) <= max_lines:
        return "\n".join(lines)

    return "\n".join(lines[:max_lines - 1] + [" ".join(lines[max_lines - 1:])])


def balance_two_lines(draw, words, font):
    best_lines, best_width = None, None
    for split in range(1, len(words)):
        lines = [" ".join(words[:split]), " ".join(words[split:])]
        width = max(get_text_size(draw, line, font)[0] for line in lines)
        if best_width is None or width < best_width:
            best_lines, best_width = lines, width
    return best_lines


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


def line_height(font):
    ascent, descent = font.getmetrics()
    return ascent + descent


def text_block_height(text, font, line_spacing):
    if not text:
        return 0
    lines = text.split("\n")
    return len(lines) * line_height(font) + (len(lines) - 1) * line_spacing


def draw_centered_block(draw, y, text, font, line_spacing):
    for line in text.split("\n"):
        draw.text((PRINTABLE_SIZE[0] // 2, y), line, fill="black", font=font, anchor="ma")
        y += line_height(font) + line_spacing
    return y - line_spacing


def draw_tracked_text(draw, y, text, font, tracking):
    widths = [draw.textlength(character, font=font) for character in text]
    total_width = sum(widths) + tracking * (len(text) - 1)
    x = (PRINTABLE_SIZE[0] - total_width) / 2
    for character, width in zip(text, widths):
        draw.text((x, y), character, fill="black", font=font)
        x += width + tracking
    return total_width


def render_label_image(first_name, surname, company, position, eventname):
    first_name = unicodedata.normalize('NFC', first_name or "").strip()
    surname = unicodedata.normalize('NFC', surname or "").strip()
    company = unicodedata.normalize('NFC', company or "").strip()
    position = unicodedata.normalize('NFC', position or "").strip()
    eventname = unicodedata.normalize('NFC', eventname or "").strip()

    img = Image.new('L', PRINTABLE_SIZE, color='white')
    d = ImageDraw.Draw(img)
    center_x = PRINTABLE_SIZE[0] // 2

    # no logo: the label is stuck onto an A6 card that already carries it
    top_margin = 24
    bottom_margin = 22

    # footer: event name, tracked uppercase
    footer_font = ImageFont.truetype(FONT_MEDIUM, 25)
    footer_text = eventname.upper()
    footer_y = PRINTABLE_SIZE[1] - bottom_margin - line_height(footer_font)
    footer_width = 0
    while footer_text:
        footer_width = sum(d.textlength(c, font=footer_font) for c in footer_text) + 5 * (len(footer_text) - 1)
        if footer_width <= TEXT_WIDTH:
            break
        footer_font = ImageFont.truetype(FONT_MEDIUM, footer_font.size - 1)
        footer_y = PRINTABLE_SIZE[1] - bottom_margin - line_height(footer_font)
    if footer_text:
        draw_tracked_text(d, footer_y, footer_text, footer_font, 5)

    # content: first name, surname (dominant), divider, company, position
    content_top = top_margin
    content_bottom = footer_y if footer_text else PRINTABLE_SIZE[1] - bottom_margin
    min_padding = 20
    name_gap = 4
    divider_height = 4

    def block_height(block):
        kind, text, font, _ = block
        return divider_height if kind == "divider" else text_block_height(text, font, 2)

    # shrink everything step by step until the content fits between header and footer
    for scale in [1.0, 0.94, 0.88, 0.82, 0.76, 0.7, 0.64, 0.58]:
        first_name_text, first_name_font = fit_wrapped_text(d, first_name, FONT_DISPLAY_REGULAR, round(72 * scale), 34, TEXT_WIDTH, 90, max_lines=1)
        surname_text, surname_font = fit_wrapped_text(d, surname, FONT_DISPLAY_BOLD, round(130 * scale), 44, TEXT_WIDTH, 300, max_lines=2)
        company_text, company_font = fit_wrapped_text(d, company, FONT_DISPLAY_SEMIBOLD, round(86 * scale), 32, TEXT_WIDTH, 215, max_lines=2)
        position_text, position_font = fit_wrapped_text(d, position, FONT_REGULAR, round(50 * scale), 28, TEXT_WIDTH, 130, max_lines=2)

        divider_gap = round(34 * scale)
        info_gap = round(10 * scale)
        blocks = [
            ("text", first_name_text, first_name_font, 0),
            ("text", surname_text, surname_font, name_gap),
        ]
        if company_text or position_text:
            blocks.append(("divider", None, None, divider_gap))
            blocks.append(("text", company_text, company_font, divider_gap))
            blocks.append(("text", position_text, position_font, info_gap if company_text else divider_gap))

        blocks = [block for block in blocks if block[0] == "divider" or block[1]]
        content_height = sum(block_height(block) for block in blocks) + sum(block[3] for block in blocks[1:])
        if content_height <= content_bottom - content_top - 2 * min_padding:
            break

    y = content_top + (content_bottom - content_top - content_height) // 2

    for index, block in enumerate(blocks):
        kind, text, font, gap = block
        if index > 0:
            y += gap
        if kind == "divider":
            d.line((center_x - 45, y + divider_height // 2, center_x + 45, y + divider_height // 2), fill="black", width=divider_height)
            y += divider_height
        else:
            y = draw_centered_block(d, y, text, font, 2)

    # pure black and white for crisp thermal printing
    img = img.point(lambda value: 0 if value < 160 else 255, mode='1')
    return img.rotate(90, expand=True)


def create_label_image(first_name, surname, company, position, eventname):
    img = render_label_image(first_name, surname, company, position, eventname)
    img.save('generated_badge.png')
    sleep(0.1)
    send_to_printer('generated_badge.png')


def send_to_printer(path):
    printer = BrotherQLRaster(PRINTER_NAME)
    print_data = brother_ql.brother_ql_create.convert(printer, [path], LABEL_FORMAT, dither=False, hq=True)
    send(print_data, PRINTER_IDENTIFIER)
