from PIL import Image, ImageDraw, ImageFont
import os

def generate_ico():
    # 256x256 is the standard high-resolution icon size for Windows
    size = (256, 256)
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    dc = ImageDraw.Draw(img)
    
    # Coordinates and padding
    width, height = size
    pad = 8
    
    # 1. Draw dark blue/slate circle background (shield look)
    dc.ellipse([pad, pad, width - pad, height - pad], fill=(15, 23, 42, 255), outline=(249, 115, 22, 255), width=8)
    
    # 2. Draw orange traffic warning triangle inside
    tri_pad = 28
    pt1 = (width / 2, tri_pad)
    pt2 = (tri_pad, height - tri_pad - 10)
    pt3 = (width - tri_pad, height - tri_pad - 10)
    
    # Draw glowing outline for triangle
    dc.polygon([pt1, pt2, pt3], fill=(249, 115, 22, 255))
    
    # Draw inner dark triangle to make a warning border look
    inner_pad = 12
    pt1_in = (width / 2, tri_pad + inner_pad * 1.5)
    pt2_in = (tri_pad + inner_pad * 1.3, height - tri_pad - 10 - inner_pad)
    pt3_in = (width - tri_pad - inner_pad * 1.3, height - tri_pad - 10 - inner_pad)
    dc.polygon([pt1_in, pt2_in, pt3_in], fill=(15, 23, 42, 255))
    
    # 3. Draw bold text "AIT" in the middle
    # We will use drawing text paths or a default bold layout
    # To be safe without relying on font file paths, we draw custom lines or try default fonts
    try:
        # Try to use a standard system font
        font = ImageFont.truetype("arial.ttf", 64)
    except IOError:
        font = ImageFont.load_default()
        
    # Draw "AIT" in white, centered
    text = "AIT"
    # Get text bounding box for exact centering
    bbox = dc.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Render centered text
    x = (width - text_width) / 2
    y = (height - text_height) / 2 + 10 # slightly down to align with triangle center
    dc.text((x, y), text, fill=(255, 255, 255, 255), font=font)
    
    # Save as .ico containing multiple sizes for Windows (essential for high-quality scaling)
    icon_path = "app_icon.ico"
    img.save(
        icon_path, 
        format="ICO", 
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    )
    print(f"Icon generated successfully: {os.path.abspath(icon_path)}")

if __name__ == "__main__":
    generate_ico()
