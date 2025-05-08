from flask import Flask, request, jsonify, render_template 
import pandas as pd
import requests
from io import StringIO
import re
from config import Config
from flask_sqlalchemy import SQLAlchemy
from models.models import db, Student, Settings
from flask_socketio import SocketIO, emit
from waitress import serve

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
socketio = SocketIO(app)

# Function to get the spreadsheet link from the settings table
def get_spreadsheet_link():
    setting = db.session.query(Settings).filter_by(key='spreadsheet_link').first()
    return setting.value if setting else None

# Function to import and refresh student data from Google Sheets
def refresh_student_data():
    try:
        sheet_url = get_spreadsheet_link()
        if not sheet_url:
            print("Spreadsheet URL is not configured.")
            return {'status': 'Error', 'message': 'Spreadsheet URL not configured'}

        response = requests.get(sheet_url)
        response.raise_for_status()

        html_content = StringIO(response.text)
        df = pd.read_html(html_content, header=0)[0]

        df.columns = [str(col).strip() for col in df.columns]
        df['School ID Number'] = df['School ID Number'].astype(str).apply(
            lambda x: re.sub(r'\s+', '', x)
        ).str.replace('.0', '').str.strip()

        # Use raw SQL to TRUNCATE (reset auto-increment)
        db.session.execute('TRUNCATE TABLE student RESTART IDENTITY CASCADE;')

        # Insert new data
        for _, row in df.iterrows():
            school_id = row['School ID Number']
            name = row['Name (Ex. Juan S. Dela Cruz)']
            student = Student(school_id=school_id, name=name)
            db.session.add(student)

        db.session.commit()
        db.session.remove()

        print(f"Student data refreshed from {sheet_url}")

        # Notify clients via SocketIO
        socketio.emit('student_data_updated', {'message': 'Student data has been updated!'}, broadcast=True)

        return {'status': 'Success', 'message': 'Database refreshed successfully'}

    except Exception as e:
        print(f"Error occurred while refreshing student data: {str(e)}")
        return {'status': 'Error', 'message': f'Error: {str(e)}'}

# APScheduler to auto-refresh every hour
from apscheduler.schedulers.background import BackgroundScheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=refresh_student_data, trigger="interval", hours=1)
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
        found_student = None
        if search_by == 'id':
            found_student = Student.query.filter_by(school_id=query).first()
        else:
            found_student = Student.query.filter(Student.name.ilike(f'%{query}%')).first()

        if found_student:
            return jsonify({
                'status': 'Cleared',
                'message': 'Cleared!',
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
        student = Student.query.filter_by(school_id=student_id).first()
        if not student:
            return jsonify({'status': 'Error', 'message': 'Student not found'})

        db.session.commit()

        socketio.emit('survey_response_saved', {
            'message': f'Survey response for student {student_id} has been saved!'
        }, broadcast=True)

        return jsonify({'status': 'Success', 'message': 'Responses saved successfully'})

    except Exception as e:
        return jsonify({'status': 'Error', 'message': f'Error occurred: {str(e)}'})

@app.route('/api/refresh', methods=['POST'])
def refresh_data():
    result = refresh_student_data()
    return jsonify(result)

@socketio.on('connect')
def handle_connect():
    print("Client connected")

@socketio.on('disconnect')
def handle_disconnect():
    print("Client disconnected")

def update_spreadsheet_link(new_link):
    setting = db.session.query(Settings).filter_by(key='spreadsheet_link').first()
    if setting:
        setting.value = new_link
    else:
        setting = Settings(key='spreadsheet_link', value=new_link)
        db.session.add(setting)
    db.session.commit()

if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=5005)
    socketio.run(app, debug=True)
