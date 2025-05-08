import os
import time # Keep time in case wait_for_job_completion has configurable timeouts or for other uses
import json
# import requests # No longer needed for polling, but might be useful if you add other REST calls
from flask import Flask, request, render_template
from dotenv import load_dotenv
from musicai_sdk import MusicAiClient
# You might want to import SDK-specific errors if you want to catch them specifically
# from musicai_sdk.errors import MusicAiAPIError, MusicAiError (check SDK for actual error classes)
from werkzeug.utils import secure_filename

load_dotenv()

app = Flask(__name__)

# Ensure a temporary upload directory exists
if not os.path.exists("temp_uploads"):
    os.makedirs("temp_uploads")

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
    if not file or file.filename == '': # Also check for empty filename
        return "No file uploaded or file has no name", 400

    # Save the uploaded file temporarily
    filename = secure_filename(file.filename)
    temp_file_path = os.path.join("temp_uploads", filename)
    
    # It's good practice to ensure the directory exists right before saving
    # os.makedirs(os.path.dirname(temp_file_path), exist_ok=True) # Already done at app start globally
    file.save(temp_file_path)

    try:
        # Upload the file using the SDK
        print(f"⬆️ Uploading file: {filename} to music.ai...")
        file_url = client.upload_file(file_path=temp_file_path)
        print(f"✅ File uploaded successfully: {file_url}")

        # Create a job
        print(f"⚙️ Creating job with workflow: {workflow}...")
        # Renamed job_info from create step to avoid conflict with completed job_info
        job_creation_info = client.create_job(
            job_name=f"Drum Stem Separation - {filename}", # More descriptive job name
            workflow_id=workflow,
            params={"inputUrl": file_url}
        )
        job_id = job_creation_info['id']
        print(f"🛠️ Job created successfully with ID: {job_id}")

        # Wait for job to complete using the SDK's method
        # This is a blocking call and will handle polling internally
        print(f"⏳ Waiting for job {job_id} to complete (this may take some time)...")
        # The SDK's wait_for_job_completion handles the status checks.
        # It will raise an exception if the job fails or times out,
        # or return job details if successful.
        completed_job_info = client.wait_for_job_completion(job_id)
        
        status = completed_job_info.get('status')
        print(f"✔️ Job {job_id} finished with status: {status}")

        if status == "SUCCEEDED":
            print(f"🔍 Full completed_job_info for {job_id} (Status: {status}):")
            print(json.dumps(completed_job_info, indent=2))
            outputs = completed_job_info.get("result", {}).get("outputs")
            if outputs:
                print("✅ Job completed. Outputs:")
                print(json.dumps(outputs, indent=2))
                return render_template('result.html', stems=outputs, job_status=status)
            else:
                print("⚠️ Job SUCCEEDED but no outputs found in result.")
                return render_template('result.html', stems=None, job_status="SUCCEEDED_NO_OUTPUTS", error_info="Job succeeded but no output stems were found.")
        else: # Should typically be "FAILED" if wait_for_job_completion didn't raise an exception for failure
            error_detail = completed_job_info.get("result", {}).get("error", "Job failed without a specific error message.")
            print(f"❌ Job failed during processing. Status: {status}. Details: {error_detail}")
            return render_template('result.html', stems=None, job_status=status, error_info=str(error_detail))

    except Exception as e: # Consider catching more specific SDK errors if available
        # Example:
        # except MusicAiAPIError as sdk_api_error:
        #     print(f"💥 Music.ai API Error: {sdk_api_error}")
        #     return f"A Music.ai API error occurred: {sdk_api_error}", 500
        # except MusicAiError as sdk_error:
        #     print(f"💥 Music.ai SDK Error: {sdk_error}")
        #     return f"A Music.ai SDK error occurred: {sdk_error}", 500
        print(f"💥 An unexpected error occurred: {e}")
        # For debugging, you might want to see the traceback
        import traceback
        traceback.print_exc()
        return f"An unexpected error occurred: {str(e)}", 500

    finally:
        # Clean up the temporarily saved file
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                print(f"🗑️ Temporary file {temp_file_path} deleted.")
            except OSError as e:
                print(f"Error deleting temporary file {temp_file_path}: {e.strerror}")

if __name__ == '__main__':
    # For Render, Gunicorn (or another WSGI server) will run the app.
    # The host and port here are for local development.
    # Render will bind to the port it needs, typically via PORT env variable.
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=False) # Debug should be False for production