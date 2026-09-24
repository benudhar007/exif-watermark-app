import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import piexif
import io
import datetime

st.set_page_config(page_title="GPS Image Stamper", layout="centered")

st.title("📸 GPS Image Stamper")
st.write("Add a NoteCam-style GPS overlay and EXIF metadata to your image.")

uploaded_file = st.file_uploader("Upload an Image", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    
    st.subheader("1. Configuration")
    
    col1, col2 = st.columns(2)
    with col1:
        date_input = st.date_input("Date", datetime.date.today())
        time_input = st.time_input("Time", datetime.datetime.now().time())
        latitude = st.number_input("Latitude (Decimal Degrees)", format="%.6f", value=20.549127)
        longitude = st.number_input("Longitude (Decimal Degrees)", format="%.6f", value=86.284726)
    with col2:
        elevation = st.text_input("Elevation", "5.36±7.06 m")
        accuracy = st.text_input("Accuracy", "4.78 m")
        note_text = st.text_input("Note", "after work, Baba sanatan pitha high school campus")
        
    if st.button("Process Image", type="primary"):
        with st.spinner("Processing..."):
            date_time_str = f"{date_input.strftime('%Y:%m:%d')} {time_input.strftime('%H:%M:%S')}"
            display_time_str = f"{date_input.strftime('%d-%m-%Y')} {time_input.strftime('%H:%M')}"
            
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
                
            txt_layer = Image.new("RGBA", image.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(txt_layer)
            
            font_size = max(12, int(image.size[1] * 0.025))
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", size=font_size)
            except IOError:
                try:
                    font = ImageFont.truetype("arial.ttf", size=font_size)
                except IOError:
                    font = ImageFont.load_default()
            
            # Prepare text block
            lines = [
                f"Latitude: {latitude:.6f}",
                f"Longitude: {longitude:.6f}",
                f"Elevation: {elevation}",
                f"Accuracy: {accuracy}",
                f"Time: {display_time_str}",
                f"Note: {note_text}"
            ]
            
            # Calculate box dimensions
            padding = int(font_size * 0.5)
            line_spacing = int(font_size * 0.2)
            
            max_width = 0
            total_height = padding
            for line in lines:
                try:
                    bbox = draw.textbbox((0, 0), line, font=font)
                    w = bbox[2] - bbox[0]
                    h = bbox[3] - bbox[1]
                except AttributeError:
                    w, h = draw.textsize(line, font=font)
                max_width = max(max_width, w)
                total_height += h + line_spacing
                
            box_width = max_width + (padding * 2)
            box_height = total_height + padding
            
            # Position at bottom left
            x_offset = int(image.size[0] * 0.02)
            y_offset = image.size[1] - box_height - int(image.size[1] * 0.02)
            
            # Draw semi-transparent background box
            draw.rectangle(
                [x_offset, y_offset, x_offset + box_width, y_offset + box_height],
                fill=(230, 230, 230, 180) # Light gray, semi-transparent
            )
            
            # Draw text
            current_y = y_offset + padding
            for line in lines:
                draw.text((x_offset + padding, current_y), line, font=font, fill=(0, 0, 0, 255))
                try:
                    h = draw.textbbox((0, 0), line, font=font)[3] - draw.textbbox((0, 0), line, font=font)[1]
                except AttributeError:
                    h = draw.textsize(line, font=font)[1]
                current_y += h + line_spacing
                
            # Draw "Powered by NoteCam" in bottom right
            logo_text = "Powered by NoteCam"
            try:
                bbox = draw.textbbox((0, 0), logo_text, font=font)
                logo_w = bbox[2] - bbox[0]
                logo_h = bbox[3] - bbox[1]
            except AttributeError:
                logo_w, logo_h = draw.textsize(logo_text, font=font)
                
            logo_x = image.size[0] - logo_w - int(image.size[0] * 0.02)
            logo_y = image.size[1] - logo_h - int(image.size[1] * 0.02)
            draw.text((logo_x, logo_y), logo_text, font=font, fill=(255, 69, 0, 255)) # Orange/Red
            
            watermarked = Image.alpha_composite(image, txt_layer)
            watermarked = watermarked.convert("RGB")
            
            # --- Add EXIF data ---
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
            
            img_byte_arr = io.BytesIO()
            watermarked.save(img_byte_arr, format='JPEG', exif=exif_bytes)
            img_byte_arr.seek(0)
            
            st.success("Image processed successfully!")
            
            st.subheader("2. Result")
            st.image(watermarked, caption="Preview of GPS Stamped Image")
            
            st.download_button(
                label="⬇️ Download Image",
                data=img_byte_arr,
                file_name="gps_stamped_image.jpg",
                mime="image/jpeg"
            )
