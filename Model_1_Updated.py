import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from textwrap import wrap
from colorthief import ColorThief
import io
import boto3
from botocore.exceptions import NoCredentialsError
import os
import requests
import json
from fastapi import FastAPI, UploadFile, File

# Set up your AWS credentials
os.environ['AWS_ACCESS_KEY_ID'] = ''
os.environ['AWS_SECRET_ACCESS_KEY'] = ''
os.environ['AWS_DEFAULT_REGION'] = ''

def get_font_name(font_path):
    return os.path.basename(font_path)

# Define the post_and_fetch_layouts function
def post_and_fetch_layouts(layouts_info):
    url = 'http://dev.api.sparkiq.ai/image-generations'
    
    for layout in layouts_info:
        try:
            response = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(layout))
            print('POST response:', response.json())
        except requests.exceptions.RequestException as e:
            print('Error:', e)
        
        try:
            get_response = requests.get(url)
            print('GET response:', get_response.json())
        except requests.exceptions.RequestException as e:
            print('Error:', e)

# Define the generate_ad_template function
def generate_ad_template(heading, desc, cta, contact, logo_bytes, product_bytes):
    # Convert bytes to file-like objects
    logo_file = io.BytesIO(logo_bytes)
    product_file = io.BytesIO(product_bytes)

    # Load the images
    logo_image = Image.open(logo_file).convert("RGBA")
    product_image = Image.open(product_file).convert("RGBA")

    def limit_title_to_four_words(title):
        words = title.split()
        return ' '.join(words[:4])

    def format_title(title, max_length=25):
        title = limit_title_to_four_words(title)
        words = title.split()
        if len(title) > max_length:
            midpoint = len(words) // 2
            line1 = ' '.join(words[:midpoint])
            line2 = ' '.join(words[midpoint:])
            return f"{line1}\n{line2}"
        return title

    def get_dominant_color(image):
        with io.BytesIO() as output:
            image.save(output, format="PNG")
            output.seek(0)
            color_thief = ColorThief(output)
            dominant_color = color_thief.get_color(quality=1)
            return '#{:02x}{:02x}{:02x}'.format(dominant_color[0], dominant_color[1], dominant_color[2])

    def get_palette(image, color_count=6):
        with io.BytesIO() as output:
            image.save(output, format="PNG")
            output.seek(0)
            color_thief = ColorThief(output)
            palette = color_thief.get_palette(color_count=color_count)
            return ['#{:02x}{:02x}{:02x}'.format(color[0], color[1], color[2]) for color in palette]

    def get_contrasting_text_color(background_color):
        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

        def rgb_to_brightness(rgb_color):
            return (rgb_color[0] * 299 + rgb_color[1] * 587 + rgb_color[2] * 114) / 1000

        if isinstance(background_color, str):
            background_rgb = hex_to_rgb(background_color)
        else:
            background_rgb = background_color

        background_brightness = rgb_to_brightness(background_rgb)

        text_colors = [
            (0, 0, 0), (255, 255, 255), (255, 69, 0), (255, 140, 0), (255, 215, 0),
            (0, 128, 128), (0, 0, 255), (75, 0, 130), (238, 130, 238), (0, 128, 0),
            (128, 0, 0), (0, 0, 128), (128, 0, 128), (0, 128, 0), (0, 255, 255),
            (255, 20, 147), (255, 105, 180), (60, 179, 113), (255, 69, 0), (255, 255, 0),
            (0, 255, 0), (0, 100, 0), (139, 69, 19), (210, 105, 30), (255, 165, 0),
            (75, 0, 130), (123, 104, 238), (106, 90, 205), (153, 50, 204), (148, 0, 211),
            (75, 0, 130), (143, 188, 143), (127, 255, 0), (255, 99, 71), (64, 224, 208),
            (0, 191, 255), (25, 25, 112), (47, 79, 79), (105, 105, 105), (112, 128, 144),
            (220, 20, 60)
        ]

        contrasting_colors = [color for color in text_colors if abs(rgb_to_brightness(color) - background_brightness) > 125]

        return random.choice(contrasting_colors)

    def get_random_contrasting_color(exclude_colors=None):
        exclude_colors = exclude_colors or []
        colors = [
            (0, 0, 0), (255, 255, 255), (255, 69, 0), (255, 140, 0), (255, 215, 0),
            (0, 128, 128), (0, 0, 255), (75, 0, 130), (238, 130, 238), (0, 128, 0),
            (128, 0, 0), (0, 0, 128), (128, 0, 128), (0, 128, 0), (0, 255, 255),
            (255, 20, 147), (255, 105, 180), (60, 179, 113), (255, 69, 0), (255, 255, 0),
            (0, 255, 0), (0, 100, 0), (139, 69, 19), (210, 105, 30), (255, 165, 0),
            (75, 0, 130), (123, 104, 238), (106, 90, 205), (153, 50, 204), (148, 0, 211),
            (75, 0, 130), (143, 188, 143), (127, 255, 0), (255, 99, 71), (64, 224, 208),
            (0, 191, 255), (25, 25, 112), (47, 79, 79), (105, 105, 105), (112, 128, 144),
            (220, 20, 60)
        ]
        colors = [color for color in colors if color not in exclude_colors]
        return random.choice(colors)

    def generate_gradient_color(color1, color2, width, height, direction='left_to_right'):
        base = Image.new('RGB', (width, height), color1)
        mask = Image.new('L', (width, height))
        top = Image.new('RGB', (width, height), color2)

        mask_data = []

        if direction == 'left_to_right':
            mask_data = [int(255 * (x / width)) for y in range(height) for x in range(width)]
        elif direction == 'top_to_bottom':
            mask_data = [int(255 * (y / height)) for y in range(height) for x in range(width)]
        elif direction == 'right_to_left':
            mask_data = [int(255 * ((width - x) / width)) for y in range(height) for x in range(width)]
        elif direction == 'bottom_to_top':
            mask_data = [int(255 * ((height - y) / height)) for y in range(height) for x in range(width)]
        elif direction == 'diagonal_tl_br':
            mask_data = [int(255 * ((x + y) / (width + height))) for y in range(height) for x in range(width)]
        elif direction == 'diagonal_bl_tr':
            mask_data = [int(255 * ((x + (height - y)) / (width + height))) for y in range(height) for x in range(width)]

        mask.putdata(mask_data)
        base.paste(top, (0, 0), mask)

        return base.filter(ImageFilter.SMOOTH)

    def get_complementary_color(color):
        return (255 - color[0], 255 - color[1], 255 - color[2])

    def sample_background_color(image, positions, area_size=10):
        colors = []
        for pos in positions:
            x, y = pos
            for i in range(-area_size // 2, area_size // 2):
                for j in range(-area_size // 2, area_size // 2):
                    try:
                        colors.append(image.getpixel((x + i, y + j)))
                    except IndexError:
                        continue
        avg_color = tuple(sum(c) // len(c) for c in zip(*colors))
        return avg_color

    def wrap_text(text, max_width, draw, font):
        lines = []
        for line in text.split('\n'):
            lines.extend(wrap(line, width=max_width, break_long_words=False))
        return lines

    def is_overlap(box1, box2):
        return not (box1[2] < box2[0] or box1[0] > box2[2] or box1[3] < box2[1] or box1[1] > box2[3])

    def adjust_font_size_based_on_space(draw, text, font_path, max_width, max_height, max_font_size=100, additional_size=0):
        min_font_size = 28
        font_size = min_font_size + additional_size

        while font_size <= max_font_size + additional_size:
            font = ImageFont.truetype(font_path, font_size)
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width, text_height = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
            if text_width <= max_width and text_height <= max_height:
                font_size += 1
            else:
                break

        return ImageFont.truetype(font_path, font_size - 1 if font_size > min_font_size else font_size)

    def draw_element(draw, key, position, size, text=None, font=None, element_type="text", image_obj=None, cta_shape="rectangle", text_color=(0, 0, 0), background_color=(255, 255, 255), mobile_icon=None):
        x = int(position[0] * width)
        y = int(position[1] * height)
        drawn_elements_info = {}

        if element_type == "text":
            max_width = int(size[0] * width) if size else width
            wrapped_text = wrap_text(text, 32, draw, font)
            max_line_width = max(draw.textbbox((0, 0), line, font=font)[2] for line in wrapped_text)
            line_height = font.getbbox('A')[3]
            gap = int(line_height * 0.4)
            total_height = (line_height + gap) * len(wrapped_text) - gap

            if key == "cta":
                padding = 30  # Increased padding
                high_res_width = max_line_width + padding * 2
                high_res_height = total_height + padding * 2

                # Increase resolution by 8x for anti-aliasing
                high_res_button = Image.new('RGBA', (high_res_width * 8, high_res_height * 8), (0, 0, 0, 0))
                high_res_draw = ImageDraw.Draw(high_res_button)

                if cta_shape == "rounded":
                    radius = 15 * 8
                    high_res_draw.rounded_rectangle(
                        [(0, 0), (high_res_width * 8, high_res_height * 8)],
                        radius=radius,
                        fill=background_color
                    )
                else:
                    high_res_draw.rectangle(
                        [(0, 0), (high_res_width * 8, high_res_height * 8)],
                        fill=background_color
                    )

                # Smooth the edges of the CTA button by downscaling
                high_res_button = high_res_button.resize((high_res_width, high_res_height), Image.LANCZOS)

                image.paste(high_res_button, (x - padding, y - padding), high_res_button)
                drawn_elements_info["cta_button"] = {"size": (high_res_width, high_res_height), "coordinates": (x, y), "color": background_color}

            if key == "desc_first_word":
                remaining_text = text.strip()

                wrapped_text = wrap_text(remaining_text, 30, draw, font)
                desc_y = y
                for i, line in enumerate(wrapped_text):
                    text_x = x - 20  # Shift the text a bit to the left
                    text_y = desc_y + i * (line_height + gap)
                    draw.text((text_x, text_y), line, text_color, font)
                drawn_elements_info[key] = {"size": (max_line_width, text_y + line_height - y), "coordinates": (x, y)}

                return (x, y, x + max_line_width, text_y + line_height), drawn_elements_info

            elif key == "contact":
                icon_size = int(line_height * 1.5)  # Adjust the size of the mobile icon
                if mobile_icon is not None:
                    mobile_icon_resized = mobile_icon.resize((icon_size, icon_size), Image.LANCZOS)
                    image.paste(mobile_icon_resized, (x, y), mobile_icon_resized)
                    x += icon_size + 5  # Add some padding after the icon

                for i, line in enumerate(wrapped_text):
                    text_x = x
                    text_y = y + i * (line_height + gap)
                    draw.text((text_x, text_y), line, fill=text_color, font=font)  # Change contact text color to highlight color
                drawn_elements_info[key] = {"size": (max_line_width, text_y + line_height - y), "coordinates": (x, y), "font_size": font.size}

                return (x - icon_size - 5, y, x + max_line_width, y + total_height), drawn_elements_info

            else:
                for i, line in enumerate(wrapped_text):
                    text_x = x
                    text_y = y + i * (line_height + gap)
                    draw.text((text_x, text_y), line, text_color, font)
                drawn_elements_info[key] = {"size": (max_line_width, text_y + line_height - y), "coordinates": (x, y)}

                return (x, y, x + max_line_width, y + total_height), drawn_elements_info

        elif element_type == "image" and image_obj:
            img = image_obj

            if "product" in key:
                x = int(position[0] * width)
                y = int(position[1] * height)
                fixed_width = 450  # Fixed width for the product image bounding box
                fixed_height = 450  # Fixed height for the product image bounding box

                img = img.crop(img.getbbox())
                img.thumbnail((fixed_width, fixed_height), Image.LANCZOS)
                image.paste(img, (x, y), img)
                drawn_elements_info[key] = {"size": (img.width, img.height), "coordinates": (x, y)}

                return (x, y, x + img.width, y + img.height), drawn_elements_info  # Bounding box is removed
            elif "logo" in key:
                logo_width = int(size[0] * width)
                logo_height = int(size[1] * height)

                img = img.crop(img.getbbox())

                # Reduce the height slightly to tighten the bounding box
                reduction_factor = 0.7
                logo_height = int(logo_height * reduction_factor)

                img.thumbnail((logo_width, logo_height), Image.LANCZOS)

                # Place the logo at the specified position
                logo_x = int(position[0] * width)
                logo_y = int(position[1] * height)

                # Draw a white rounded rectangle patch with dynamic padding
                patch_padding_top = int(logo_height * 0.1)  # 10% of the logo height
                patch_padding_side = int(logo_width * 0.1)  # 10% of the logo width
                patch_padding_bottom = int(logo_height * 0.05)  # 5% of the logo height

                if position[0] > 0.5:  # Logo on the right
                    patch_box = [
                        logo_x - patch_padding_side,
                        logo_y - patch_padding_top,
                        logo_x + logo_width + patch_padding_side * 2,
                        logo_y + logo_height + patch_padding_bottom
                    ]
                    corner_radius = 20  # Adjust this value as needed
                    draw.rounded_rectangle(patch_box, radius=corner_radius, fill=(255, 255, 255))
                else:  # Logo on the left
                    patch_box = [
                        logo_x - patch_padding_side * 2,
                        logo_y - patch_padding_top,
                        logo_x + logo_width + patch_padding_side,
                        logo_y + logo_height + patch_padding_bottom
                    ]
                    corner_radius = 20  # Adjust this value as needed
                    draw.rounded_rectangle(patch_box, radius=corner_radius, fill=(255, 255, 255))

                # Paste the logo on top of the white patch
                image.paste(img, (logo_x, logo_y), img)
                drawn_elements_info[key] = {"size": (logo_width, logo_height), "coordinates": (logo_x, logo_y)}

                return (logo_x, logo_y, logo_x + logo_width, logo_y + logo_height), drawn_elements_info

    font_path_heading = "services/Fonts/ARIALBD.TTF"
    font_path_desc = "services/Fonts/arial.ttf"
    font_path_cta = "services/Fonts/ARIALBD.TTF"
    font_path_contact = "services/Fonts/arial.ttf"
    mobile_icon_path = "services/Fonts/icon.png"  # Replace with the actual path to the mobile icon

    heading = format_title(heading)  # Ensure heading is limited to 4 words and formatted
    highlighted_heading = heading  # No need to highlight any word now
    highlight_font = ImageFont.truetype(font_path_heading, 40)  # Define the highlight font

    # Load the mobile icon
    try:
        mobile_icon = Image.open(mobile_icon_path).convert("RGBA")
    except OSError:
        print(f"Error opening mobile icon: {mobile_icon_path}")
        mobile_icon = None

    layouts = [
        {
            "logo": [(0.79, 0.0, 0.2, 0.15), logo_image, "image"],
            "heading": [(0.08, 0.76, 0.6, 0.2), heading, "text", font_path_heading],
            "desc_first_word": [(0.05, 0.37, 0.7, 0.15), desc, "text", font_path_desc],
            "cta": [(0.2, 0.2, 0.2, 0.1), cta, "text", font_path_cta],
            "contact": [(0.03, 0.05, 0.2, 0.1), contact, "text", font_path_contact],
            "product": [(0.51, 0.3, 0.47, 0.5), product_image, "image"]
        },
        {
            "logo": [(0.01, 0.0, 0.2, 0.15), logo_image, "image"],
            "heading": [(0.3, 0.06, 0.6, 0.2), heading, "text", font_path_heading],
            "desc_first_word": [(0.05, 0.32, 0.9, 0.15), desc, "text", font_path_desc],
            "cta": [(0.2, 0.75, 0.2, 0.1), cta, "text", font_path_cta],
            "contact": [(0.1, 0.92, 0.2, 0.1), contact, "text", font_path_contact],
            "product": [(0.52, 0.25, 0.5, 0.6), product_image, "image"]
        },
        {
            "logo": [(0.79, 0.0, 0.2, 0.15), logo_image, "image"],
            "heading": [(0.05, 0.06, 0.6, 0.2), heading, "text", font_path_heading],
            "desc_first_word": [(0.52, 0.38, 0.5, 0.55), desc, "text", font_path_desc],
            "cta": [(0.18, 0.85, 0.2, 0.1), cta, "text", font_path_cta],
            "contact": [(0.5, 0.85, 0.2, 0.1), contact, "text", font_path_contact],
            "product": [(0.01, 0.27, 0.5, 0.5), product_image, "image"]
        },
        {
            "logo": [(0.01, 0.0, 0.2, 0.15), logo_image, "image"],
            "heading": [(0.3, 0.06, 0.6, 0.2), heading, "text", font_path_heading],
            "desc_first_word": [(0.52, 0.38, 0.5, 0.55), desc, "text", font_path_desc],
            "cta": [(0.18, 0.85, 0.2, 0.1), cta, "text", font_path_cta],
            "contact": [(0.5, 0.85, 0.2, 0.1), contact, "text", font_path_contact],
            "product": [(0.01, 0.27, 0.5, 0.5), product_image, "image"]
        },
        {
            "logo": [(0.01, 0.0, 0.2, 0.15), logo_image, "image"],
            "heading": [(0.04, 0.75, 0.6, 0.2), heading, "text", font_path_heading],
            "desc_first_word": [(0.05, 0.32, 0.9, 0.15), desc, "text", font_path_desc],
            "cta": [(0.65, 0.18, 0.2, 0.1), cta, "text", font_path_cta],
            "contact": [(0.02, 0.18, 0.2, 0.1), contact, "text", font_path_contact],
            "product": [(0.52, 0.25, 0.5, 0.6), product_image, "image"]
        },
        {
            "logo": [(0.01, 0.0, 0.2, 0.15), logo_image, "image"],
            "heading": [(0.3, 0.02, 0.6, 0.2), heading, "text", font_path_heading],
            "desc_first_word": [(0.05, 0.37, 0.9, 0.15), desc, "text", font_path_desc],
            "cta": [(0.65, 0.85, 0.2, 0.1), cta, "text", font_path_cta],
            "contact": [(0.05, 0.87, 0.2, 0.1), contact, "text", font_path_contact],
            "product": [(0.52, 0.30, 0.5, 0.6), product_image, "image"]
        },
        {
            "logo": [(0.01, 0.0, 0.2, 0.15), logo_image, "image"],
            "heading": [(0.07, 0.15, 0.6, 0.2), heading, "text", font_path_heading],
            "desc_first_word": [(0.05, 0.42, 0.9, 0.15), desc, "text", font_path_desc],
            "cta": [(0.65, 0.85, 0.2, 0.1), cta, "text", font_path_cta],
            "contact": [(0.03, 0.87, 0.2, 0.1), contact, "text", font_path_contact],
            "product": [(0.52, 0.35, 0.5, 0.6), product_image, "image"]
        }
    ]

    grid_width = 70
    grid_height = 70

    def generate_grid(width, height):
        grid_cells = []
        for x in range(0, width, grid_width):
            for y in range(0, height, grid_height):
                grid_cells.append((x, y, x + grid_width, y + height))
        return grid_cells

    def find_empty_spaces(bounding_boxes, width, height):
        grid_cells = generate_grid(width, height)
        empty_spaces = []
        for cell in grid_cells:
            cell_empty = True
            for box in bounding_boxes:
                if is_overlap(cell, box):
                    cell_empty = False
                    break
            if cell_empty:
                empty_spaces.append(cell)
        return empty_spaces

    def draw_bounding_box(draw, box, color):
        pass

    def get_analogous_colors(color):
        r, g, b = color
        analogous_1 = ((r + 30) % 256, (g + 30) % 256, (b + 30) % 256)
        analogous_2 = ((r - 30) % 256, (g - 30) % 256, (b - 30) % 256)
        return [analogous_1, analogous_2]

    def filter_analogous_colors(color, palette):
        def is_same_color_family(color1, color2):
            return abs(color1[0] - color2[0]) <= 30 and abs(color1[1] - color2[1]) <= 30 and abs(color1[2] - color2[2]) <= 30

        filtered_colors = []
        for c in palette:
            if is_same_color_family(color, c):
                filtered_colors.append(c)

        return filtered_colors

    def adjust_and_draw_bounding_boxes(draw, bounding_boxes, expansion_factor=20, desc_expansion_factor=(75.59, 75.59)):
        adjusted_boxes = []
        for box in bounding_boxes:
            if "desc" in box[-1]:
                expansion_width, expansion_height = desc_expansion_factor
            else:
                expansion_width = expansion_height = expansion_factor

            x1, y1, x2, y2 = box[:4]
            adjusted_box = (
                max(x1 - expansion_width, 0),
                max(y1 - expansion_height, 0),
                min(x2 + expansion_width, width),
                min(y2 + expansion_height, height)
            )
            adjusted_boxes.append(adjusted_box + (box[4],))

        for box in adjusted_boxes:
            draw_bounding_box(draw, box[:4], color=(255, 255, 255, 0))

        return adjusted_boxes

    used_colors = set()

    s3_client = boto3.client('s3')
    bucket_name = "sparkiq-image-upload"

    background_urls = []
    template_urls = []

    layouts_info = []

    for i, elements in enumerate(layouts):
        width, height = 1080, 1080

        palette = get_palette(logo_image, color_count=6)

        is_single_color = len(palette) == 1
        palette_intensity_variations = []

        if is_single_color:
            base_color = Image.new('RGB', (width, height), palette[0])
            palette_intensity_variations = [base_color.point(lambda p: p * (i / 5.0)) for i in range(1, 6)]
        else:
            palette_intensity_variations = palette

        all_colors = []
        for color in palette:
            rgb_color = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
            analogous_colors = get_analogous_colors(rgb_color)
            all_colors.append(rgb_color)
            all_colors.extend(filter_analogous_colors(rgb_color, analogous_colors))

        unique_colors = list(set(all_colors))
        hex_colors = ['#{:02x}{:02x}{:02x}'.format(r, g, b) for r, g, b in unique_colors]

        while True:
            chosen_colors = random.sample(hex_colors, 2)
            if tuple(chosen_colors) not in used_colors:
                used_colors.add(tuple(chosen_colors))
                break

        print(f"Layout {i + 1} - Chosen colors: {chosen_colors}")

        directions = ['left_to_right', 'top_to_bottom', 'right_to_left', 'bottom_to_top', 'diagonal_tl_br', 'diagonal_bl_tr']
        gradient_direction = random.choice(directions)

        background = generate_gradient_color(chosen_colors[0], chosen_colors[1], width, height, direction=gradient_direction)

        background_image_path = f"background_{i + 1}.png"
        background.save(background_image_path, quality=95)

        if os.path.exists(background_image_path):
            print(f"Background image {background_image_path} saved successfully.")
        else:
            print(f"Failed to save background image {background_image_path}.")

        try:
            s3_client.upload_file(background_image_path, bucket_name, background_image_path,ExtraArgs={'ACL': 'public-read'})
            background_url = f"https://{bucket_name}.s3.amazonaws.com/{background_image_path}"
            background_urls.append(background_url)
            print(f"Background image {background_image_path} uploaded to S3 successfully.")
        except NoCredentialsError:
            print("Credentials not available for S3 upload.")

        image = Image.new("RGBA", (width, height))
        image.paste(background, (0, 0))
        draw = ImageDraw.Draw(image)
        bounding_boxes = []
        drawn_elements_info = {}

        dominant_color = get_dominant_color(image)
        highlight_color = (255, 255, 255)
        heading_color = (255, 255, 255)
        desc_color = (255, 255, 255)
        contact_color = (255, 255, 255)

        shapes = ["rounded", "rectangle"]
        random.shuffle(shapes)

        for key, value in elements.items():
            pos, text, elem_type, *font = value
            pos_x, pos_y = int(pos[0] * width), int(pos[1] * height)
            pos_w, pos_h = int(pos[2] * width), int(pos[3] * height)

            sampled_background_color = sample_background_color(image, [(pos_x + pos_w // 2, pos_y + pos_h // 2)])
            sampled_background_rgb = tuple(sampled_background_color[:3])
            complementary_color = get_complementary_color(sampled_background_rgb)

            if elem_type == "text":
                max_width = int(pos[2] * width)
                max_height = int(pos[3] * height)
                max_font_size = 150 if key == "heading" else 100
                if key == "heading":
                    additional_size = font[1] if len(font) > 1 else 0
                    adjusted_font = adjust_font_size_based_on_space(draw, text, font[0], max_width, max_height, max_font_size, additional_size)
                    text_color = (255, 255, 255)
                elif key == "desc_first_word":
                    adjusted_font = ImageFont.truetype(font[0], 40)
                    text_color = (255, 255, 255)
                elif key == "contact":
                    adjusted_font = ImageFont.truetype(font[0], 50)
                    text_color = (255, 255, 255)
                else:
                    adjusted_font = ImageFont.truetype(font[0], 40)
                    text_color = (255, 255, 255)

                wrapped_text = wrap_text(text, 30, draw, adjusted_font)[:6]
                if key == "desc_first_word":
                    box, elem_info = draw_element(draw, key, pos[:2], pos[2:], '\n'.join(wrapped_text), adjusted_font, element_type=elem_type, cta_shape=shapes[0], text_color=text_color, background_color=sampled_background_rgb)
                elif key == "cta":
                    cta_background_color = get_complementary_color(sampled_background_rgb)
                    cta_text_color = (255, 255, 255)
                    box, elem_info = draw_element(draw, key, pos[:2], pos[2:], '\n'.join(wrapped_text), adjusted_font, element_type=elem_type, cta_shape=shapes[1], text_color=cta_text_color, background_color=cta_background_color)
                elif key == "contact":
                    box, elem_info = draw_element(draw, key, pos[:2], pos[2:], '\n'.join(wrapped_text), adjusted_font, element_type=elem_type, cta_shape="rectangle", text_color=contact_color, mobile_icon=mobile_icon)
                else:
                    box, elem_info = draw_element(draw, key, pos[:2], pos[2:], '\n'.join(wrapped_text), adjusted_font, element_type=elem_type, cta_shape="rounded", text_color=text_color)
                bounding_boxes.append(box + (key,))
                drawn_elements_info.update(elem_info)
            else:
                img = text

                if key == "product":
                    pos_x = int(pos[0] * width)
                    pos_y = int(pos[1] * height)
                    fixed_width = 550
                    fixed_height = 550
                    img.thumbnail((fixed_width, fixed_height), Image.LANCZOS)
                    image.paste(img, (pos_x, pos_y), img)
                    box = (pos_x, pos_y, pos_x + img.width, pos_y + img.height)
                    drawn_elements_info[key] = {"size": (img.width, img.height), "coordinates": (pos_x, pos_y)}
                elif "logo" in key:
                    box, elem_info = draw_element(draw, key, pos[:2], pos[2:], element_type=elem_type, image_obj=img)
                    drawn_elements_info.update(elem_info)
                    bounding_boxes.append(box + (key,))

        adjusted_boxes = adjust_and_draw_bounding_boxes(draw, bounding_boxes)

        template_image_path = f"ad_template_{i + 1}.png"
        image.save(template_image_path, quality=95)

        if os.path.exists(template_image_path):
            print(f"Template image {template_image_path} saved successfully.")
        else:
            print(f"Failed to save template image {template_image_path}.")

        try:
            s3_client.upload_file(template_image_path, bucket_name, template_image_path, ExtraArgs={'ACL': 'public-read'})
            template_url = f"https://{bucket_name}.s3.amazonaws.com/{template_image_path}"
            template_urls.append(template_url)
            print(f"Template image {template_image_path} uploaded to S3 successfully.")
        except NoCredentialsError:
            print("Credentials not available for S3 upload.")

        title_font_size = adjusted_font.size if 'heading' in drawn_elements_info else None
        cta_font_size = adjusted_font.size if 'cta' in drawn_elements_info else None
        desc_font_size = adjusted_font.size if 'desc_first_word' in drawn_elements_info else None

        layout_info = {
            "id": str(i + 1),
            "bgcolor": f"{chosen_colors[0]},{chosen_colors[1]}",
            "imagelayoutsize": f"{width}x{height}",
            "logoUrl": background_url,
            "imageURL": template_url,
            "aiModel": "AI-Model-Name",
            "logoCoordinates": f"{drawn_elements_info['logo']['coordinates'][0]},{drawn_elements_info['logo']['coordinates'][1]}",
            "logoHeight": drawn_elements_info['logo']['size'][1],
            "logoWidth": drawn_elements_info['logo']['size'][0],
            "title": heading,
            "titlePosition": f"{drawn_elements_info['heading']['coordinates'][0]},{drawn_elements_info['heading']['coordinates'][1]}",
            "fontstyle": get_font_name(font_path_heading),
            "fontSize": title_font_size,
            "description": desc,
            "descriptionPosition": f"{drawn_elements_info['desc_first_word']['coordinates'][0]},{drawn_elements_info['desc_first_word']['coordinates'][1]}",
            "descriptionFontstyle": get_font_name(font_path_desc),
            "descriptionFontSize": desc_font_size,
            "ctaButtonText": cta,
            "ctaStyle": shapes[1],
            "ctaPosition": f"{drawn_elements_info['cta']['coordinates'][0]},{drawn_elements_info['cta']['coordinates'][1]}",
            "ctaFontSize": cta_font_size,
            "ctaButtonHeight": drawn_elements_info['cta_button']['size'][1],
            "ctaButtonWidth": drawn_elements_info['cta_button']['size'][0],
            "phoneNumberText": contact,
            "phoneNumberPosition": f"{drawn_elements_info['contact']['coordinates'][0]},{drawn_elements_info['contact']['coordinates'][1]}",
            "phoneNumberFontStyle": get_font_name(font_path_contact),
            "phoneNumberSize": drawn_elements_info['contact']['font_size']
        }

        layouts_info.append(layout_info)

        print(f"Layout {i + 1} - Title font size: {title_font_size}, CTA font size: {cta_font_size}, Description font size: {desc_font_size}")

        empty_spaces = find_empty_spaces(adjusted_boxes, width, height)
        print(f"Drawn elements info for layout {i + 1}: {drawn_elements_info}")
        print(f"Layout _info: {layouts_info}")
        #post_data(layouts_info)

    return layouts_info
