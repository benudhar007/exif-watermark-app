import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import piexif
import io

st.set_page_config(page_title="GPS & Watermark Image Editor", layout="centered")

st.title("📸 Add GPS, Timestamp & Watermark to Images")
st.write("Upload an image, set the GPS location, timestamp, and watermark. The output file will have all standard EXIF tags set perfectly!")

uploaded_file = st.file_uploader("Upload an Image", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # Try to load the original EXIF to populate defaults if available, otherwise just handle the image
    image = Image.open(uploaded_file)
    
    st.subheader("1. Configuration")
    
    col1, col2 = st.columns(2)
    with col1:
        date_input = st.date_input("Date")
        time_input = st.time_input("Time")
    with col2:
        latitude = st.number_input("GPS Latitude (Decimal Degrees)", format="%.6f", value=20.0)
        longitude = st.number_input("GPS Longitude (Decimal Degrees)", format="%.6f", value=86.0)
        
    watermark_text = st.text_input("Watermark Text", "CONTRACTOR PROOF")
    
    if st.button("Process Image", type="primary"):
        with st.spinner("Processing..."):
            # Combine date and time
            date_time_str = f"{date_input.strftime('%Y:%m:%d')} {time_input.strftime('%H:%M:%S')}"
            
            # Ensure image is in RGBA for watermarking
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
                
            # --- 1. Add Watermark ---
            txt_layer = Image.new("RGBA", image.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(txt_layer)
            
            # Determine a dynamic font size based on image width
            font_size = int(image.size[0] * 0.08)
            
            try:
                # Try a standard macOS font
                font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", size=font_size)
            except IOError:
                try:
                    # Try a standard Windows/Linux font
                    font = ImageFont.truetype("arial.ttf", size=font_size)
                except IOError:
                    font = ImageFont.load_default()
            
            # Calculate text size and position (Center)
            try:
                text_bbox = draw.textbbox((0, 0), watermark_text, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
            except AttributeError:
                # Fallback for older Pillow versions
                text_width, text_height = draw.textsize(watermark_text, font=font)
            
            x = image.size[0] // 2 - text_width // 2
            y = image.size[1] // 2 - text_height // 2
            
            # Draw translucent text (white with alpha 100/255)
            # Add a slight black outline for visibility on light backgrounds
            outline_color = (0, 0, 0, 100)
            draw.text((x-2, y-2), watermark_text, font=font, fill=outline_color)
            draw.text((x+2, y-2), watermark_text, font=font, fill=outline_color)
            draw.text((x-2, y+2), watermark_text, font=font, fill=outline_color)
            draw.text((x+2, y+2), watermark_text, font=font, fill=outline_color)
            
            draw.text((x, y), watermark_text, font=font, fill=(255, 255, 255, 120))
            
            # Combine watermark
            watermarked = Image.alpha_composite(image, txt_layer)
            watermarked = watermarked.convert("RGB") # Must convert to RGB for JPEG format
            
            # --- 2. Add EXIF data ---
            def decimal_to_dms(value):
                degrees = int(value)
                minutes = int((value - degrees) * 60)
                seconds = int((value - degrees - minutes/60) * 360000)
                return ((degrees, 1), (minutes, 1), (seconds, 10000))
                
            gps_lat_dms = decimal_to_dms(abs(latitude))
            gps_lon_dms = decimal_to_dms(abs(longitude))
            
            exif_dict = {
                "0th": {
                    piexif.ImageIFD.DateTime: date_time_str.encode(),
                },
                "Exif": {
                    piexif.ExifIFD.DateTimeOriginal: date_time_str.encode(),
                    piexif.ExifIFD.DateTimeDigitized: date_time_str.encode(),
                },
                "GPS": {
                    piexif.GPSIFD.GPSLatitudeRef: b'N' if latitude >= 0 else b'S',
                    piexif.GPSIFD.GPSLatitude: gps_lat_dms,
                    piexif.GPSIFD.GPSLongitudeRef: b'E' if longitude >= 0 else b'W',
                    piexif.GPSIFD.GPSLongitude: gps_lon_dms,
                },
            }
            
            exif_bytes = piexif.dump(exif_dict)
            
            # Save to buffer
            img_byte_arr = io.BytesIO()
            watermarked.save(img_byte_arr, format='JPEG', exif=exif_bytes)
            img_byte_arr.seek(0)
            
            st.success("Image processed successfully!")
            
            st.subheader("2. Result")
            st.image(watermarked, caption="Preview of Watermarked Image")
            
            st.download_button(
                label="⬇️ Download Image with EXIF & Watermark",
                data=img_byte_arr,
                file_name="processed_image_with_exif.jpg",
                mime="image/jpeg"
            )
