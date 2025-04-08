# Image Compression App

A Flask web application that compresses images and adds date/time watermarks.

## Features

- **Single Image Compression**: Upload and compress individual images
- **Bulk Image Compression**: Upload multiple images and download them as a compressed ZIP file
- **Automatic Watermarking**: Adds a date/time watermark based on EXIF data or current time
- **Customizable Compression Quality**: Set your desired compression level

## Demo

The application is live at: (https://image-compressor-t82d.onrender.com)

## Technologies Used

- **Backend**: Flask (Python)
- **Image Processing**: Pillow (PIL)
- **Frontend**: HTML, CSS, JavaScript
- **Deployment**: Render

## Local Development

### Prerequisites

- Python 3.8+
- pip

### Installation

1. Clone this repository
```bash
git clone https://github.com/yourusername/image-compression-app.git
cd image-compression-app
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Run the application
```bash
python app.py
```

4. Open your browser and navigate to `http://localhost:5000`

## Deployment

This application is configured for deployment on Render.

### Deployment Requirements

- `requirements.txt`: Lists all Python dependencies
- `gunicorn_config.py`: Configuration for the Gunicorn WSGI server
- `Procfile`: Instructions for Render on how to run the application

## Project Structure

```
├── app.py                 # Main Flask application
├── gunicorn_config.py     # Gunicorn configuration for deployment
├── requirements.txt       # Python dependencies
├── Procfile               # Deployment instructions
├── compressed/            # Storage for compressed images
├── uploads/               # Storage for original uploaded images
├── static/                # Static assets (CSS)
└── templates/             # HTML templates
    ├── index.html         # Homepage
    ├── upload_single.html # Single upload page
    ├── upload_bulk.html   # Bulk upload page
    ├── result_single.html # Single image result page
    └── result_bulk.html   # Bulk compression result page
```

## How It Works

1. **Upload**: Users upload one or more images through the web interface
2. **Processing**: 
   - The app extracts EXIF data to get the original date/time
   - Adds a semi-transparent watermark with the date/time
   - Compresses the image using the specified quality level
3. **Result**: Displays compression statistics and download links

## Limitations

- Free tier on Render uses ephemeral storage; uploaded files are not permanently stored
- Large images may cause memory issues on limited hosting plans

## Author
Sagar Pariyar
