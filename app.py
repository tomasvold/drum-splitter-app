import os
import time
from flask import Flask, request, render_template, jsonify
from dotenv import load_dotenv
from musicai_sdk import MusicAiClient

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
    temp_file_path = os.path.join("temp_uploads", file.filename)
    os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)
    file.save(temp_file_path)

    try:
        # Upload the file using the SDK
        file_url = client.upload_file(file_path=temp_file_path)
        print(f"Uploaded file URL: {file_url}")

        # Create a job
        job_info = client.create_job(
            job_name="Drum Stem Separation",
            workflow_id=workflow,
            params={"inputUrl": file_url}
        )
        job_id = job_info['id']
        print(f"Job created with ID: {job_id}")

        # Wait for job completion
        result = client.wait_for_job_completion(job_id)
        print("Job completed successfully.")

        # ✅ Render the result page with stems
        return render_template('result.html', stems=result['result'])

    except Exception as e:
        print(f"Error: {e}")
        return f"An error occurred: {e}", 500

    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

if __name__ == '__main__':
    app.run(debug=True)
