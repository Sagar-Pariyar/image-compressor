import os
from flask import Flask, render_template, request, send_file, url_for, redirect, flash, jsonify
from PIL import Image, ImageDraw, ImageFont, ExifTags
from datetime import datetime
import io
import uuid
from zipfile import ZipFile
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "compression_app_secret_key"
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
app.config['COMPRESSED_FOLDER'] = os.path.join(os.getcwd(), 'compressed')

# Create folders if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['COMPRESSED_FOLDER'], exist_ok=True)

# Helper to extract EXIF date
def get_exif_date(img):
    try:
        exif = img.getexif()
        date_fields = ['DateTimeOriginal', 'DateTimeDigitized', 'DateTime']
        for tag, value in exif.items():
            decoded = ExifTags.TAGS.get(tag, tag)
            if decoded in date_fields:
                return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
        return datetime.now()
    except:
        return datetime.now()

def compress_image(image, output_path, quality=30):
    """
    Compresses the given PIL image and saves it as a JPEG.

    Parameters:
    - image (PIL.Image): The image to compress (usually already watermarked).
    - output_path (str): Where to save the compressed image.
    - quality (int): JPEG compression quality (1–95).
    """
    # Ensure image is in RGB mode for saving as JPEG
    image = image.convert("RGB")
    
    # Save with compression
    image.save(output_path, "JPEG", 
               quality=quality,
               optimize=True,
               progressive=True)

def add_watermark(img, text=None):
    """
    Add a watermark to an image with the current date and time or EXIF date if available
    
    Parameters:
    img (PIL.Image): The input image
    text (str, optional): Custom watermark text. If None, uses current date/time.
    
    Returns:
    PIL.Image: Watermarked image
    """
    # Ensure image is in RGBA mode
    img = img.convert("RGBA")
    
    # If no text provided, get from EXIF or use current date and time
    if text is None:
        try:
            exif = img.getexif()
            date_fields = ['DateTimeOriginal', 'DateTimeDigitized', 'DateTime']
            date_from_exif = None
            
            # Try to get date from EXIF
            for tag, value in exif.items():
                decoded = ExifTags.TAGS.get(tag, tag)
                if decoded in date_fields and value:
                    date_from_exif = datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
                    break
            
            # Use EXIF date or current time
            if date_from_exif:
                text = date_from_exif.strftime("%Y-%m-%d %H:%M:%S")
            else:
                text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
        except Exception as e:
            # Fallback to current date time if any error occurs
            text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Create transparent overlay
    overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Set font size relative to image width
    font_size = max(24, img.width // 30)
    
    # Try different font options
    try:
        # Try DejaVu font first (common on Linux)
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
    except:
        try:
            # Try Arial (common on Windows)
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            # Fall back to default if neither is available
            font = ImageFont.load_default()
    
    # Calculate text size and position
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Position at bottom center with margin
    x = (img.width - text_width) // 2
    y = img.height - text_height - 50
    
    # Draw semi-transparent background box
    draw.rectangle(
        [x - 10, y - 5, x + text_width + 10, y + text_height + 5],
        fill=(0, 0, 0, 128)
    )
    
    # Draw text in white
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))
    
    # Merge the overlay with the original image
    watermarked = Image.alpha_composite(img, overlay)
    
    return watermarked.convert("RGB")

def format_file_size(bytes):
    if bytes < 1024:
        return f"{bytes} bytes"
    elif bytes < 1048576:
        return f"{bytes/1024:.1f} KB"
    else:
        return f"{bytes/1048576:.1f} MB"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload-single')
def upload_single():
    return render_template('upload_single.html')

@app.route('/upload-bulk')
def upload_bulk():
    return render_template('upload_bulk.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)

    files = request.files.getlist('file')
    if not files or files[0].filename == '':
        flash('No selected files')
        return redirect(request.url)

    try:
        quality = int(request.form.get('quality', '30'))
        is_single = len(files) == 1

        if is_single:
            file = files[0]
            # Keep original filename but ensure it's safe and add a unique identifier
            original_filename = file.filename
            base_filename, ext = os.path.splitext(original_filename)
            safe_filename = secure_filename(base_filename)  # Make sure to import secure_filename from werkzeug.utils
            
            # Add a timestamp to ensure uniqueness
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            original_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{safe_filename}_{timestamp}{ext}")
            compressed_path = os.path.join(app.config['COMPRESSED_FOLDER'], f"c_{safe_filename}_{timestamp}{ext}")

            # ✅ Save raw file first to get accurate size
            file_stream = file.read()
            with open(original_path, 'wb') as f:
                f.write(file_stream)

            original_size = os.path.getsize(original_path)

            # ✅ Load image for processing
            img = Image.open(original_path)
            watermarked = add_watermark(img)
            compress_image(watermarked, compressed_path, quality=quality)

            compressed_size = os.path.getsize(compressed_path)
            reduction = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
            size_saved = original_size - compressed_size

            result = {
                'original_path': url_for('uploaded_file', filename=f"{safe_filename}_{timestamp}{ext}"),
                'compressed_path': url_for('compressed_file', filename=f"c_{safe_filename}_{timestamp}{ext}"),
                'original_size_formatted': format_file_size(original_size),
                'compressed_size_formatted': format_file_size(compressed_size),
                'original_size': format_file_size(original_size),
                'compressed_size': format_file_size(compressed_size),
                'reduction_percentage': round(reduction, 1),
                'quality_used': quality,
                'size_saved_formatted': format_file_size(size_saved),
                'download_url': url_for('download_file', filename=f"c_{safe_filename}_{timestamp}{ext}")
            }

            return render_template('result_single.html', **result)

        else:
            # Similar changes for bulk uploads
            zip_filename = f"compressed_images_{datetime.now().strftime('%Y%m%d%H%M%S')}.zip"
            zip_path = os.path.join(app.config['COMPRESSED_FOLDER'], zip_filename)

            image_infos = []
            total_original_size = 0
            total_compressed_size = 0

            with ZipFile(zip_path, 'w') as zipf:
                for file in files:
                    original_filename = file.filename
                    base_filename, ext = os.path.splitext(original_filename)
                    safe_filename = secure_filename(base_filename)
                    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

                    original_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{safe_filename}_{timestamp}{ext}")
                    compressed_path = os.path.join(app.config['COMPRESSED_FOLDER'], f"c_{safe_filename}_{timestamp}{ext}")

                    # ✅ Save raw file first
                    file_stream = file.read()
                    with open(original_path, 'wb') as f:
                        f.write(file_stream)

                    original_size = os.path.getsize(original_path)
                    total_original_size += original_size

                    img = Image.open(original_path)
                    watermarked = add_watermark(img)  # ✅ corrected this line
                    compress_image(watermarked, compressed_path, quality=quality)

                    compressed_size = os.path.getsize(compressed_path)
                    total_compressed_size += compressed_size

                    zipf.write(compressed_path, arcname=f"c_{safe_filename}{ext}")

            total_reduction = (1 - total_compressed_size / total_original_size) * 100 if total_original_size > 0 else 0
            total_saved = total_original_size - total_compressed_size

            result = {
                'image_count': len(files),
                'total_original_size_formatted': format_file_size(total_original_size),
                'total_compressed_size_formatted': format_file_size(total_compressed_size),
                'total_reduction_percentage': round(total_reduction, 1),
                'quality_used': quality,
                'total_saved_formatted': format_file_size(total_saved),
                'download_zip_url': url_for('download_zip', filename=zip_filename)
            }

            # Add this before rendering the template
            print(f"Rendering template with data: {result}")

            return render_template('result_bulk.html', **result)


    except Exception as e:
        flash(f"An error occurred: {str(e)}")
        return redirect(url_for('index'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))

@app.route('/compressed/<filename>')
def compressed_file(filename):
    return send_file(os.path.join(app.config['COMPRESSED_FOLDER'], filename))

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(
        os.path.join(app.config['COMPRESSED_FOLDER'], filename),
        as_attachment=True
    )

@app.route('/download_zip/<filename>')
def download_zip(filename):
    return send_file(
        os.path.join(app.config['COMPRESSED_FOLDER'], filename),
        as_attachment=True
    )

@app.route('/clear-and-upload')
def clear_and_upload():
    try:
        # Clear both folders
        for folder in [app.config['UPLOAD_FOLDER'], app.config['COMPRESSED_FOLDER']]:
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
        # Redirect to home page
        return redirect(url_for('index'))
    except Exception as e:
        return f"Error during cleanup: {e}", 500


@app.route('/cleanup', methods=['POST'])
def cleanup_files():
    try:
        for folder in [app.config['UPLOAD_FOLDER'], app.config['COMPRESSED_FOLDER']]:
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)