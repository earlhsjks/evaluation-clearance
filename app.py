from flask import Flask, request, jsonify, render_template
import pandas as pd
import requests
from io import StringIO
import re
from config import Config
from sqlalchemy import text
from flask_sqlalchemy import SQLAlchemy
from models.models import db, Student, Settings
from flask_socketio import SocketIO, emit  # Import SocketIO
from waitress import serve

app = Flask(__name__)

# Load configuration from config.py
app.config.from_object(Config)

# Initialize the SQLAlchemy instance after app configuration
db.init_app(app)

# Initialize Flask-SocketIO
socketio = SocketIO(app)

# Function to get the spreadsheet link from the settings table
def get_spreadsheet_link():
    setting = db.session.query(Settings).filter_by(key='spreadsheet_link').first()
    if setting:
        return setting.value
    return None  # Return None if the spreadsheet link is not found

# Function to import and refresh student data from Google Sheets
def refresh_student_data():
    try:
        # Fetch the Google Sheet using the link from the Settings table
        sheet_url = get_spreadsheet_link()
        if not sheet_url:
            print("Spreadsheet URL is not configured.")
            return

        response = requests.get(sheet_url)
        response.raise_for_status()

        # Read the spreadsheet content into a DataFrame
        html_content = StringIO(response.text)
        df = pd.read_html(html_content, header=0)[0]

        # Clean up columns and IDs
        df.columns = [str(col).strip() for col in df.columns]
        df['School ID Number'] = df['School ID Number'].astype(str).apply(lambda x: re.sub(r'\s+', '', x)).str.replace('.0', '').str.strip()

        # Clear the current student records in the database
        db.session.execute(text('TRUNCATE TABLE student'))
        db.session.commit()

        # Insert new data into the database
        for _, row in df.iterrows():
            school_id = row['School ID Number']
            name = row['Name (Ex. Juan S. Dela Cruz)']
            student = Student(school_id=school_id, name=name)
            db.session.add(student)

        db.session.commit()
        print(f"Student data refreshed from {sheet_url}")
        
        # Emit a message to notify clients of the data update
        socketio.emit('student_data_updated', {'message': 'Student data has been updated!'}, broadcast=True)

    except Exception as e:
        print(f"Error occurred while refreshing student data: {str(e)}")

# Set up APScheduler to run the refresh function every hour
# (This can also be triggered manually in other cases)
from apscheduler.schedulers.background import BackgroundScheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=refresh_student_data, trigger="interval", hours=1)  # Set the interval to 1 hour
scheduler.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/check', methods=['POST'])
def api_check():
    data = request.get_json()
    search_by = data.get('search_by')
    query = data.get('query', '').strip()

    if not query:
        return jsonify({'status': 'Empty', 'message': ''})

    try:
        # Search for student by ID or Name
        found_student = None
        if search_by == 'id':
            found_student = Student.query.filter_by(school_id=query).first()
        else:  # search by name
            found_student = Student.query.filter(Student.name.ilike(f'%{query}%')).first()

        if found_student:
            return jsonify({
                'status': 'Cleared',
                'message': f"Cleared!",
                'data': {'id': found_student.school_id, 'name': found_student.name}
            })
        else:
            return jsonify({'status': 'Not Found', 'message': 'No Evaluation yet. ❌'})

    except Exception as e:
        return jsonify({'status': 'Error', 'message': f'Error occurred: {str(e)}'})

@app.route('/api/save_response', methods=['POST'])
def save_response():
    data = request.get_json()
    student_id = data.get('student_id')
    responses = data.get('responses')

    if not student_id or not responses:
        return jsonify({'status': 'Error', 'message': 'Missing student ID or responses'})

    try:
        # Save survey responses to the database
        student = Student.query.filter_by(school_id=student_id).first()
        if not student:
            return jsonify({'status': 'Error', 'message': 'Student not found'})

        db.session.commit()

        # Emit a message to notify clients that a survey response has been saved
        socketio.emit('survey_response_saved', {'message': f'Survey response for student {student_id} has been saved!'}, broadcast=True)

        return jsonify({'status': 'Success', 'message': 'Responses saved successfully'})

    except Exception as e:
        return jsonify({'status': 'Error', 'message': f'Error occurred: {str(e)}'})
    
# Route to refresh the database
@app.route('/api/refresh', methods=['POST'])
def refresh_data():
    try:
        # Fetch the spreadsheet URL
        sheet_url = get_spreadsheet_link()
        if not sheet_url:
            return jsonify({'status': 'Error', 'message': 'Spreadsheet URL not configured'})

        # Fetch and parse the updated data from the spreadsheet
        response = requests.get(sheet_url)
        response.raise_for_status()

        # Parse the HTML content into a DataFrame
        html_content = StringIO(response.text)
        df = pd.read_html(html_content, header=0)[0]

        # Clean the data
        df.columns = [str(col).strip() for col in df.columns]
        df['School ID Number'] = df['School ID Number'].astype(str).apply(lambda x: re.sub(r'\s+', '', x)).str.replace('.0', '').str.strip()

        # Clear the existing student data and insert new data
        db.session.execute(text('TRUNCATE TABLE student'))
        db.session.commit()
        for index, row in df.iterrows():
            school_id = row['School ID Number']
            name = row['Name (Ex. Juan S. Dela Cruz)']
            student = Student(school_id=school_id, name=name)
            db.session.add(student)
        db.session.commit()

        return jsonify({'status': 'Success', 'message': 'Database refreshed successfully'})

    except Exception as e:
        return jsonify({'status': 'Error', 'message': f'Error occurred: {str(e)}'})

# SocketIO event to listen for updates on the client-side
@socketio.on('connect')
def handle_connect():
    print("Client connected")

@socketio.on('disconnect')
def handle_disconnect():
    print("Client disconnected")

# Function to update the spreadsheet link
def update_spreadsheet_link(new_link):
    setting = db.session.query(Settings).filter_by(key='spreadsheet_link').first()
    if setting:
        setting.value = new_link  # Update the existing link
    else:
        setting = Settings(key='spreadsheet_link', value=new_link)
        db.session.add(setting)  # Insert the new link

    db.session.commit()

if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=5005)
    socketio.run(app, debug=True)
