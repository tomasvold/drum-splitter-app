import os
import time
import json
import requests
from flask import Flask, request, render_template
from dotenv import load_dotenv
from musicai_sdk import MusicAiClient
from werkzeug.utils import secure_filename

load_dotenv()

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    # Get user-provided credentials
    api_key = request.form.get('api_key')
    workflow = request.form.get('workflow')

    if not api_key or not workflow:
        return "Missing API key or workflow", 400

    client = MusicAiClient(api_key=api_key)

    file = request.files.get('audio')
    if not file:
        return "No file uploaded", 400

    # Save the uploaded file temporarily
    filename = secure_filename(file.filename)
    temp_file_path = os.path.join("temp_uploads", filename)
    os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)
    file.save(temp_file_path)

    try:
        # Upload the file using the SDK
        file_url = client.upload_file(file_path=temp_file_path)
        print(f"✅ Uploaded file: {file_url}")

        # Create a job
        job_info = client.create_job(
            job_name="Drum Stem Separation",
            workflow_id=workflow,
            params={"inputUrl": file_url}
        )
        job_id = job_info['id']
        print(f"🛠️ Job created with ID: {job_id}")

        # Poll the job manually via REST API
        headers = {"Authorization": f"Bearer {api_key}"}
        status = "QUEUED"
        while status not in ["SUCCEEDED", "FAILED"]:
            time.sleep(2)
            response = requests.get(
                f"https://api.music.ai/api/job/{job_id}",
                headers=headers
            )
            if response.status_code != 200:
                print("Failed to poll job status:", response.text)
                return f"Polling error: {response.text}", 500
            job_data = response.json()
            status = job_data.get("status", "UNKNOWN")
            print(f"⏳ Job status: {status}")

        if status == "SUCCEEDED":
            outputs = job_data.get("result", {}).get("outputs")
            print("✅ Job completed. Outputs:")
            print(json.dumps(outputs, indent=2))
            return render_template('result.html', stems=outputs, job_status=status)
        else:
            print("❌ Job failed during processing.")
            return render_template('result.html', stems=None, job_status=status)

    except Exception as e:
        print(f"💥 Error: {e}")
        return f"An error occurred: {e}", 500

    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

if __name__ == '__main__':
    app.run(debug=True)
