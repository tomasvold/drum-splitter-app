import os
import json
from flask import Flask, request, render_template, jsonify # Added jsonify
from dotenv import load_dotenv
from musicai_sdk import MusicAiClient
from werkzeug.utils import secure_filename
import traceback # For detailed error logging

load_dotenv()

app = Flask(__name__)

# Ensure a temporary upload directory exists
TEMP_UPLOAD_DIR = "temp_uploads"
if not os.path.exists(TEMP_UPLOAD_DIR):
    os.makedirs(TEMP_UPLOAD_DIR)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file_and_create_job():
    # Use your private credentials from Render Environment Variables
    api_key = os.environ.get('MUSIC_AI_API_KEY')
    workflow = os.environ.get('MUSIC_AI_WORKFLOW_SLUG')

    if not api_key or not workflow:
        return jsonify({"error": "Server configuration error: Missing API credentials"}), 500

    client = MusicAiClient(api_key=api_key)
    file = request.files.get('audio')
    if not file or file.filename == '':
        return jsonify({"error": "No file uploaded"}), 400

    filename = secure_filename(file.filename)
    temp_file_path = os.path.join(TEMP_UPLOAD_DIR, filename)
    
    try:
        file.save(temp_file_path)
        print(f"⬆️ Uploading file: {filename}...")
        file_url = client.upload_file(file_path=temp_file_path)

        job_creation_info = client.add_job(
            job_name=f"Drum Stem Separation - {filename}",
            workflow_slug=workflow,
            params={"inputUrl": file_url}
        )
        job_id = job_creation_info.get('id')
        
        if not job_id:
            return jsonify({"error": "Failed to create job", "details": job_creation_info}), 500
            
        return jsonify({"job_id": job_id, "message": "Job created successfully."})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@app.route('/job_status/<job_id>', methods=['GET'])
def get_job_status(job_id):
    # Always use your server-side key
    api_key = os.environ.get('MUSIC_AI_API_KEY')
    client = MusicAiClient(api_key=api_key)

    try:
        job_info = client.get_job(job_id=job_id) 
        status = job_info.get('status')
        response_data = {"job_id": job_id, "status": status}

        if status == "SUCCEEDED":
            outputs = job_info.get("result") 
            if outputs and isinstance(outputs, dict) and len(outputs) > 0:
                response_data["outputs"] = outputs
            else:
                response_data["outputs"] = None 
        elif status == "FAILED":
            error_detail = job_info.get("result", {}).get("error", "Job failed.")
            response_data["error_details"] = str(error_detail)
        
        return jsonify(response_data)
    except Exception as e:
        return jsonify({"error": str(e), "job_id": job_id}), 500

@app.route('/results/<job_id>')
def show_results(job_id):
    # Always use your server-side key
    api_key = os.environ.get('MUSIC_AI_API_KEY')
    client = MusicAiClient(api_key=api_key)
    
    try:
        job_info = client.get_job(job_id=job_id)
        status = job_info.get('status')

        if status == "SUCCEEDED":
            outputs = job_info.get("result")
            return render_template('result.html', stems=outputs, job_status=status, job_id=job_id)
        elif status == "FAILED":
            error_detail = job_info.get("result", {}).get("error", "Job failed.")
            return render_template('result.html', stems=None, job_status=status, job_id=job_id, error_info=str(error_detail))
        else: 
            return render_template('result.html', stems=None, job_status=status, job_id=job_id)
    except Exception as e:
        return render_template('result.html', stems=None, job_status="ERROR_FETCHING_RESULTS", error_info=str(e))
