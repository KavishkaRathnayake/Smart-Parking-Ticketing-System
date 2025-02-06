import cv2
from paddleocr import PaddleOCR
import numpy as np
from server import manage_numberplate_db  # Import the function for database updates
import time

# Initialize PaddleOCR
ocr = PaddleOCR()

# polygonal area 

area = [(5, 400 - 100), (3, 5000 - 100), (1000, 5000 - 100), (950, 400 - 100)]  


# Function to perform OCR on an image and return all detected text within the polygonal area
def extract_text_in_polygon(image, area):
    # Create a mask of the polygonal area
    mask = np.zeros(image.shape[:2], dtype=np.uint8)
    polygon = np.array([area], dtype=np.int32)
    cv2.fillPoly(mask, polygon, 255)  # Fill the polygon with white (255) on black background (0)

    # Apply the mask to the image
    masked_image = cv2.bitwise_and(image, image, mask=mask)

    # Perform OCR on the masked image
    results = ocr.ocr(masked_image, rec=True)  # rec=True enables text recognition
    detected_texts = []

    # Process OCR results
    if results and results[0]:
        for result in results[0]:
            text = result[1][0]  # Extract recognized text
            confidence = result[1][1]  # Confidence score
            detected_texts.append((text, confidence))

    return detected_texts

# Access Raspberry Pi Camera
camera = cv2.VideoCapture(1)  # Use 0 for the default camera
if not camera.isOpened():
    print("Error: Could not open the camera.")
    exit()

# Start the timer
start_time = time.time()

try:
    while True:
        # Capture frame-by-frame
        ret, frame = camera.read()
        if not ret:
            print("Error: Failed to capture image.")
            break

        # Extract all text within the polygonal area
        detected_texts = extract_text_in_polygon(frame, area)

        # Display results and update the database
        if detected_texts:
            print("Detected Texts within Polygonal Area:")
            for idx, (text, confidence) in enumerate(detected_texts, start=1):
                print(f"{idx}. {text} (Confidence: {confidence:.2f})")

                # Update text in the database using manage_numberplate_db
                try:
                    manage_numberplate_db(text)  # Assuming this function saves text to the DB
                    print(f"Updated database with text: {text}")
                except Exception as e:
                    print(f"Error updating database: {e}")
        else:
            print("No numberplate detected in the polygonal area.")

        # Draw the polygon on the frame
        cv2.polylines(frame, [np.array(area, np.int32)], isClosed=True, color=(255, 0, 0), thickness=2)  # Draw the polygon
        cv2.imshow("Raspberry Pi Camera Feed", frame)

        # Check if 'q' is pressed or if 10 seconds have elapsed
        elapsed_time = time.time() - start_time
        if cv2.waitKey(1) & 0xFF == ord('q') or elapsed_time >= 15:
            print("Closing camera feed after 10 seconds.")
            break

finally:
    # Release the camera and close all windows
    camera.release()
    cv2.destroyAllWindows()
