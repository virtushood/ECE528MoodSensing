#ECE528 Mood Sensing Project
#Created by Garrett Parks
import cv2, time
from google.cloud import storage
from google.oauth2 import service_account
from uuid import uuid4 as makeUniqueName
import json
import os


def AddToDb(filename):
    ''' Adds the uploaded file to the gcloud database. '''
    f = open('ece528moodsensing-49d85b0a130d.json', 'r')
    gcp_credentials_string = f.read()
    f.close()
    gcp_json_credentials_dict = json.loads(gcp_credentials_string)
    credentials = service_account.Credentials.from_service_account_info(gcp_json_credentials_dict)
    client = storage.Client(project=gcp_json_credentials_dict['project_id'], credentials=credentials)

    img_bucket = client.get_bucket('ece528imagestorage')
    blub = img_bucket.blob(str(makeUniqueName()))
    blub.upload_from_filename(filename)

# Assigning our background image to None
background_init = None

video = cv2.VideoCapture(0)
 
 
# While loop set to cycle every 2 seconds to avoid spam capture.
while True:

    check, frame = video.read()
 
    motion_detected = 0
 
    #gray-scale the captured image
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    #grayscale image is put through GaussianBlur filter to help detection.
    gray = cv2.GaussianBlur(gray, (21, 21), 0)
 
    #initialize background with first image detected
    if background_init is None:
        background_init = gray
        continue
 
    image_diff = cv2.absdiff(background_init, gray)
 
    # If change in between static background and
    # current frame is greater than 30 it will show white color(255)
    image_threshold = cv2.threshold(image_diff, 30, 255, cv2.THRESH_BINARY)[1]

    image_threshold = cv2.dilate(image_threshold, None, iterations = 2)

    cnts,_ = cv2.findContours(image_threshold.copy(),
                       cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
 
    for contour in cnts:
        if cv2.contourArea(contour) < 10000:
            continue
        motion_detected = 1

    if motion_detected == 1:
        cv2.imshow("Color Frame", frame)
        print("Motion Detected. Sending image to cloud.")
        
        cv2.imwrite("image_diff.jpg", frame)
        AddToDb("image_diff.jpg")


    key = cv2.waitKey(1)
    # if q entered whole process will stop
    if key == ord('q'):
        break
    time.sleep(2)
 
video.release()
cv2.destroyAllWindows()