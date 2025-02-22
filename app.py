from flask import Flask, jsonify, Response, render_template, send_file
import cv2
from paddleocr import PaddleOCR
import numpy as np
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import threading
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os
from io import BytesIO

app = Flask(__name__)

ocr = PaddleOCR()

area = [(5, 150), (3, 4750), (1000, 4750), (950, 150)]  
camera = None  # Global variable to hold the camera object
camera_lock = threading.Lock()  # Lock to handle concurrent access to camera

# Flag to control camera feed
camera_active = False

# Conversion of mm to points (1 mm = 2.83465 points)
ticket_width = 80 * 2.83465  # 80mm to points
ticket_height = 150 * 2.83465  # 150mm to points

def extract_text_in_polygon(image, area):
    mask = np.zeros(image.shape[:2], dtype=np.uint8)
    polygon = np.array([area], dtype=np.int32)
    cv2.fillPoly(mask, polygon, 255)

    masked_image = cv2.bitwise_and(image, image, mask=mask)

    results = ocr.ocr(masked_image, rec=True)
    detected_texts = []

    if results and results[0]:
        for result in results[0]:
            text, confidence = result[1]
            detected_texts.append((text, confidence))

    return detected_texts

def manage_numberplate_db(numberplate):
    """Connect to MySQL database and insert the detected number plate."""
    
    host = "127.0.0.1"
    user = "root"
    password = ""
    database = "numberplate"
    port = 3306
    
    connection = None
    try:
        connection = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            port=port
        )
        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database}")
            connection.database = database

            create_table_query = """
            CREATE TABLE IF NOT EXISTS numberplate (
                id INT AUTO_INCREMENT PRIMARY KEY,
                numberplate TEXT NOT NULL,
                entry_date DATE,
                entry_time TIME
            )
            """
            cursor.execute(create_table_query)
            connection.commit()

            insert_data_query = """
            INSERT INTO numberplate (numberplate, entry_date, entry_time)
            VALUES (%s, %s, %s)
            """
            current_date = datetime.now().date()
            current_time = datetime.now().time()
            data = (numberplate, current_date, current_time)
            cursor.execute(insert_data_query, data)
            connection.commit()

            print(f"Data for {numberplate} inserted successfully!")

    except Error as e:
        print(f"Error: '{e}'")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

def get_last_numberplate():
    """Fetch the last inserted number plate from the database."""
    
    host = "127.0.0.1"
    user = "root"
    password = ""
    database = "numberplate"
    port = 3306
    
    connection = None
    last_numberplate = None
    try:
        connection = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            port=port,
            database=database
        )
        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute("SELECT numberplate, entry_date, entry_time FROM numberplate ORDER BY id DESC LIMIT 1")
            result = cursor.fetchone()
            if result:
                last_numberplate = {
                    'numberplate': result[0],
                    'date': result[1],
                    'time': result[2]
                }
    except Error as e:
        print(f"Error: '{e}'")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

    return last_numberplate

def generate_pdf_ticket(ticket_data):
    """Generate a PDF ticket with custom size of 80mm x 150mm."""
    buffer = BytesIO()

    # Create a PDF document with custom size (80mm x 150mm)
    c = canvas.Canvas(buffer, pagesize=(ticket_width, ticket_height))

    # Add border around the ticket
    border_margin = 10
    border_width = ticket_width - 2 * border_margin
    border_height = ticket_height - 2 * border_margin
    c.setStrokeColorRGB(0.1, 0.2, 0.5)  # Set the border color
    c.setLineWidth(3)  # Set the border thickness
    c.rect(border_margin, border_margin, border_width, border_height)  # Draw rectangle for border

    # Ticket Title - Centered
    c.setFont("Helvetica-Bold", 16)
    title = "PARKING TICKET"
    title_width = c.stringWidth(title, "Helvetica-Bold", 16)  # Get width of title string
    title_x = (ticket_width - title_width) / 2  # Calculate the X position to center the title
    c.drawString(title_x, ticket_height - 40, title)  # Draw title at calculated position


    # Numberplate Information
    c.setFont("Helvetica", 12)
    c.drawString(border_margin + 10, ticket_height - 70, f"Vehicle Number: {ticket_data['numberplate']}")
    c.drawString(border_margin + 10, ticket_height - 90, f"Date: {ticket_data['date']}")
    c.drawString(border_margin + 10, ticket_height - 110, f"Time: {ticket_data['time']}")

    # Price Information
    c.setFont("Helvetica-Bold", 12)
    c.drawString(border_margin + 10, ticket_height - 130, "Price: LKR. 100/-")  # Moved price text up

    # Adding the quotes in 3 languages at the bottom
    c.setFont("Helvetica", 10)
    y_position = 30  # Start position for the quotes from the bottom

    # Adding the quotes in 3 languages at the bottom (centered)
    c.setFont("Helvetica", 10)
    y_position = 30  # Start position for the quotes from the bottom

    # English quote
    english_quote = "Keep it safe until you leave this place."
    english_width = c.stringWidth(english_quote, "Helvetica", 10)
    english_x = (ticket_width - english_width) / 2
    c.drawString(english_x, y_position, english_quote)
    
    # Developer signature at the bottom - centered, italicized
    developer_text = "Developed by Kavishka Rathnayake"
    c.setFont("Helvetica-Oblique", 10)  # Italic font
    developer_width = c.stringWidth(developer_text, "Helvetica-Oblique", 10)
    developer_x = (ticket_width - developer_width) / 2
    c.drawString(developer_x, border_margin + 10, developer_text)  # Just above the bottom


   
    # Save the PDF to the buffer
    c.showPage()
    c.save()

    # Move buffer position to the beginning of the file
    buffer.seek(0)
    return buffer

def generate_frames():
    global camera_active, camera
    with camera_lock:
        if not camera_active:
            return
        camera = cv2.VideoCapture(0)
        if not camera.isOpened():
            print("Error: Camera not accessible.")
            return

    while camera_active:
        success, frame = camera.read()
        if not success:
            break

        detected_texts = extract_text_in_polygon(frame, area)

        # If detected texts are found, save them to the database
        if detected_texts:
            for text, confidence in detected_texts:
                print(f"Detected Text: {text} (Confidence: {confidence:.2f})")
                try:
                    manage_numberplate_db(text)  # Insert the number plate into the database
                except Exception as e:
                    print(f"Error updating database: {e}")

        cv2.polylines(frame, [np.array(area, np.int32)], isClosed=True, color=(255, 0, 0), thickness=2)

        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue

        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    with camera_lock:
        if camera is not None:
            camera.release()
            camera = None

@app.route('/video_feed')
def video_feed():
    global camera_active
    if not camera_active:
        camera_active = True
        threading.Thread(target=generate_frames).start()
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/stop_camera', methods=['POST'])
def stop_camera():
    global camera_active
    camera_active = False

    # Retrieve the last number plate data
    last_numberplate = get_last_numberplate()
    
    if last_numberplate:
        # Generate PDF for the ticket
        ticket_pdf = generate_pdf_ticket(last_numberplate)

        # Send the generated PDF as a downloadable file
        return send_file(ticket_pdf, as_attachment=True, download_name="ticket.pdf", mimetype="application/pdf")
    else:
        return jsonify({"message": "Camera feed stopped, but no number plate detected."})

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)