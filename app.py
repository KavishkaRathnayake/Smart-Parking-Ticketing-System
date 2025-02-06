from flask import Flask, jsonify, Response, render_template, send_file
import cv2
from paddleocr import PaddleOCR
import numpy as np
import mysql.connector
from mysql.connector import Error
import threading
import time
from PIL import Image, ImageDraw, ImageFont
import os

app = Flask(__name__)

ocr = PaddleOCR()

# Polygon area for number plate detection
area = [(5, 150), (3, 4750), (1000, 4750), (950, 150)]  
camera = None  
camera_lock = threading.Lock()  
camera_active = False  

# Database Configuration
DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "",
    "database": "numberplate",
    "port": 3306
}

TICKET_PATH = "static/ticket.png"

def stop_camera_after_delay(delay):
    """Stops the camera after a given delay (in seconds)."""
    time.sleep(delay)
    global camera_active
    camera_active = False
    print("Camera feed stopped automatically.")

def get_latest_ticket():
    """Fetch the latest detected number plate."""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM numberplate ORDER BY id DESC LIMIT 1")
        ticket = cursor.fetchone()
        cursor.close()
        connection.close()
        return ticket
    except Exception as e:
        print("Database error:", e)
        return None

def generate_ticket_image(ticket_data):
    """Generate a ticket PNG including the latest number plate data."""
    if not ticket_data:
        return None

    ticket_id = ticket_data['id']
    numberplate = ticket_data['numberplate']
    entry_date = ticket_data['entry_date']
    entry_time = ticket_data['entry_time']

    # Ticket Content
    ticket_text = f"Ticket ID: {ticket_id}\nPlate: {numberplate}\nDate: {entry_date}\nTime: {entry_time}"

    # Create Image
    img = Image.new("RGB", (300, 200), "white")
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except:
        font = ImageFont.load_default()

    draw.text((20, 50), ticket_text, fill="black", font=font)

    # Ensure static directory exists
    if not os.path.exists("static"):
        os.makedirs("static")

    # Save Image
    img.save(TICKET_PATH)

    # Verify the file exists after saving
    if os.path.exists(TICKET_PATH):
        print(f"Ticket saved successfully: {TICKET_PATH}")
    else:
        print("Error: Ticket image was not saved!")

    return TICKET_PATH

def extract_text_in_polygon(image, area):
    """Extract number plate text from the given polygon area."""
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
    """Insert detected plate into the database."""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS numberplate (
                id INT AUTO_INCREMENT PRIMARY KEY,
                numberplate TEXT NOT NULL,
                entry_date DATE,
                entry_time TIME
            )
        """)
        connection.commit()

        insert_data_query = """
        INSERT INTO numberplate (numberplate, entry_date, entry_time)
        VALUES (%s, CURDATE(), CURTIME())
        """
        cursor.execute(insert_data_query, (numberplate,))
        connection.commit()
        cursor.close()
        connection.close()
    except Error as e:
        print(f"Database error: {e}")

def generate_frames():
    """Generate live camera feed with OCR detection."""
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
        if detected_texts:
            for text, confidence in detected_texts:
                print(f"Detected Text: {text} (Confidence: {confidence:.2f})")
                manage_numberplate_db(text)

        cv2.polylines(frame, [np.array(area, np.int32)], isClosed=True, color=(255, 0, 0), thickness=2)

        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

    with camera_lock:
        if camera is not None:
            camera.release()
            camera = None

@app.route('/video_feed')
def video_feed():
    """Start live camera feed and automatically stop after 10 seconds."""
    global camera_active
    if not camera_active:
        camera_active = True
        threading.Thread(target=generate_frames).start()
        threading.Thread(target=stop_camera_after_delay, args=(10,)).start()
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/generate_ticket', methods=['GET'])
def generate_ticket():
    """Fetch the latest ticket data and create a PNG ticket."""
    ticket = get_latest_ticket()
    if not ticket:
        return jsonify({"error": "No ticket found"}), 404

    image_path = generate_ticket_image(ticket)
    return jsonify({"ticket_image_url": f"/{image_path}"})

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
