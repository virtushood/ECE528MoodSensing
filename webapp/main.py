#!/usr/bin/env python
# -*- coding: utf-8 -*-


# Note: the download folder in send_from_directory may change depending on the
# server. E.g., on PythonAnywhere, you need to change it to
# '../' + app.config['DL_FOLDER'] in the history and dl functions

# todo: check comments, remove unused functions, remove unused imports
# Imports the Google Cloud client library
from google.cloud import storage
from google.oauth2 import service_account
import json
from flask import (Flask, render_template, request, redirect, flash,
                   make_response, send_from_directory, send_file)
from datetime import datetime
from werkzeug.utils import secure_filename
import os
import sys
from uuid import uuid4 as makeUniqueName  # To generate unique id for comps

from twilio.rest import Client

account_sid = os.environ['TWILIO_ACCOUNT_SID']
auth_token = os.environ['TWILIO_AUTH_TOKEN']
twilio_phone = os.environ['TWILIO_PHONE_NUMBER']

twilio_client = Client(account_sid, auth_token)

# static_path is the deprecated form of static_url_path
app = Flask(import_name=__name__, static_url_path='/static',
            static_folder='static', template_folder='templates')

# Config details @ http://flask.pocoo.org/docs/0.12/config/
# app.config['DEBUG'] = True  # Debug
# app.config['EXPLAIN_TEMPLATE_LOADING'] = True  # Debug
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 365 * 24 * 60 * 60
app.config['UPLOAD_FOLDER'] = 'uploads/'  # Sets the upload folder
app.config['DL_FOLDER'] = 'comps/'  # Sets the download folder
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']

# pie chart data
labels = ['Anger', 'Sorrow', 'Joy', 'Surprise']
values = [0, 0, 0, 0]
colors = ["#F7464A", "#bdbdbd", "#ffff00", "#4cc4fc"]


def get_pie_chart_data():
    global values
    values = [0, 0, 0, 0]
    client = storage.Client()
    
    img_bucket = client.get_bucket('ece528imagestorage2')
    json_bucket = client.get_bucket('ece528jsonstorage2')

    images = {}
    emotions_keys = ['angerLikelihood', 'sorrowLikelihood', 'joyLikelihood', 'surpriseLikelihood']
    emotions = ['Anger', 'Sorrow', 'Joy', 'Surprise']


    for img_blob in img_bucket.list_blobs():
        try:
            json_blob = json_bucket.get_blob(img_blob.name + '/output-1-to-1.json')
            json_url = ''
            json_str = ''
            if json_blob:
                json_url = json_blob.public_url
                json_str = json_blob.download_as_string()
                json_obj = json.loads(json_str)
                
                for i, emotion_key in enumerate(emotions_keys):
                    if json_obj['responses'][0]['faceAnnotations'][0][emotion_key] in ['VERY_LIKELY', 'LIKELY', 'POSSIBLE']:
                        values[i] += 1
        except:
            pass

def make_img_table():
    ''' Generates a list of the components data for the /view page. '''
    # connect to gcp

    client = storage.Client()

    # Retrieve an existing bucket
    # https://console.cloud.google.com/storage/browser/[bucket-id]/
    img_bucket = client.get_bucket('ece528imagestorage2')
    json_bucket = client.get_bucket('ece528jsonstorage2')

    images = {}
    emotions_keys = ['angerLikelihood', 'sorrowLikelihood', 'joyLikelihood', 'surpriseLikelihood']
    emotions = ['Anger', 'Sorrow', 'Joy', 'Surprise']


    for img_blob in img_bucket.list_blobs():
        json_blob = json_bucket.get_blob(img_blob.name + '/output-1-to-1.json')
        json_url = ''
        json_str = ''
        if json_blob:
            try:
                json_url = json_blob.public_url
                json_str = json_blob.download_as_string()
                json_obj = json.loads(json_str)
                emotion_strs = []
                for emotion_key, emotion in zip(emotions_keys, emotions):
                    emotion_strs.append(f"{emotion}={json_obj['responses'][0]['faceAnnotations'][0][emotion_key]}")
            except:
                pass
        images[img_blob.name] = [img_blob.public_url, json_url, img_blob.time_created, emotion_strs]
    return images



def AddToDb(photo):
    ''' Adds the uploaded file to the gcloud database. '''
    client = storage.Client()

    # Retrieve an existing bucket
    # https://console.cloud.google.com/storage/browser/[bucket-id]/
    img_bucket = client.get_bucket('ece528imagestorage2')
    blub = img_bucket.blob(str(makeUniqueName()))
    blub.upload_from_string(photo.read(), content_type=photo.content_type)

    message = twilio_client.messages \
                .create(
                     body="new picture has been uploaded",
                     from_=twilio_phone,
                     to='+12483036485'
                 )

    #print(message.sid)
    


# PAGE 1
@app.route('/', methods=['GET'])
def home():
    '''Renders the home page.'''
    get_pie_chart_data()
    return render_template('1_home.html', title='ECE 528 Mood Sense',
                           year=datetime.now().year, set=zip(values, labels, colors), max=12)




# PAGE 3
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    '''Handles file upload for database uploads'''
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file:
            AddToDb(file)
            flash(f'{file} uploaded successfully.')
    return render_template('3_uploaddb.html', title='Upload',
                           year=datetime.now().year)


# PAGE 4
@app.route('/view', methods=['GET'])
def view():
    '''Renders the database contents table page.'''

    return render_template('4_viewdb.html', title='Database',
                           content=make_img_table(), year=datetime.now().year)


# PAGE 5
@app.route('/history', methods=['GET', 'POST'])
def history():
    ''' Creates and returns the history page '''
    if request.method == 'POST':
        if 'submit' in request.form:
            count = request.form['records']
            summary = Summary(int(count))
            response = make_response(summary)
            response.headers['Content-Disposition'] = 'attachment; '\
                                                      'filename=summary.csv'
            return response
        elif 'delete' in request.form:
            compid = request.form['delete']
            delete(compid)
    return render_template('5_history.html', title='History',
                           comps=reversed(CDC), year=datetime.now().year)


# PAGE 6
@app.route('/download', methods=['GET', 'POST'])
def download():
    ''' Displays a waiting message '''
    return render_template('6_offlinedl.html', title='Download',
                           year=datetime.now().year)


@app.route('/favicon.ico')
def favicon():
    ''' Returns the favicon icon when requested in the old way (IE era). '''
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.jpg', mimetype='image/jpeg')

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
