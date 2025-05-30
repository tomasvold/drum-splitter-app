import os
import json
from flask import Flask, request, render_template, jsonify
from dotenv import load_dotenv

import musicai_sdk  # <--- First, import the package itself
from musicai_sdk import MusicAiClient # <--- Then, you can import specific classes/functions from it
# Now that 'musicai_sdk' is imported as a module, you can access its __version__
print(f"MUSICAI_SDK_VERSION: {musicai_sdk.__version__}")

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
    # Get user-provided credentials
    api_key = request.form.get('api_key')
    workflow = request.form.get('workflow')

    if not api_key or not workflow:
        return jsonify({"error": "Missing API key or workflow"}), 400

    client = MusicAiClient(api_key=api_key)

    file = request.files.get('audio')
    if not file or file.filename == '':
        return jsonify({"error": "No file uploaded or file has no name"}), 400

    filename = secure_filename(file.filename)
    temp_file_path = os.path.join(TEMP_UPLOAD_DIR, filename)
    
    try:
        file.save(temp_file_path)

        print(f"⬆️ Uploading file: {filename} to music.ai...")
        file_url = client.upload_file(file_path=temp_file_path)
        print(f"✅ File uploaded successfully: {file_url}")

        job_creation_info = client.jobs.create(  # not client.create_job
        job_name=f"Drum Stem Separation - {filename}",
        workflow_id=workflow,
        params={"inputUrl": file_url}
        )
        job_id = job_creation_info.get('id')
        if not job_id:
            print(f"❌ Failed to create job. Response: {job_creation_info}")
            return jsonify({"error": "Failed to create job with music.ai", "details": job_creation_info}), 500
            
        print(f"🛠️ Job created successfully with ID: {job_id}")
        return jsonify({"job_id": job_id, "message": "File uploaded and job created. Polling for status."})

    except Exception as e:
        print(f"💥 An unexpected error occurred during upload/job creation: {e}")
        traceback.print_exc()
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500
    finally:
        # Clean up the temporarily saved file after job creation attempt
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                print(f"🗑️ Temporary file {temp_file_path} deleted after job creation attempt.")
            except OSError as e_os:
                print(f"Error deleting temporary file {temp_file_path}: {e_os.strerror}")

@app.route('/job_status/<job_id>', methods=['GET'])
def get_job_status(job_id):
    api_key = request.args.get('api_key') 
    if not api_key:
        api_key = os.environ.get('MUSIC_AI_APP_API_KEY') 
    
    if not api_key:
        return jsonify({"error": "API key required to check job status"}), 400
        
    client = MusicAiClient(api_key=api_key)

    try:
        print(f"🔎 Checking status for job ID: {job_id}")
        job_info = client.get_job(job_id=job_id) 
        print(f"ℹ️ Status for job {job_id}: {job_info.get('status')}")
        
        # This is where we log the full JSON if needed for debugging
        # print(json.dumps(job_info, indent=2)) 

        status = job_info.get('status')
        response_data = {"job_id": job_id, "status": status}

        if status == "SUCCEEDED":
            # CORRECTED LINE: Get the 'result' object directly
            outputs = job_info.get("result") 
            
            # Log the full job_info when SUCCEEDED to confirm structure
            print(f"🔍 Full job_info for SUCCEEDED job {job_id} in /job_status:")
            print(json.dumps(job_info, indent=2))

            if outputs and isinstance(outputs, dict) and len(outputs) > 0: # Check if outputs is a non-empty dictionary
                response_data["outputs"] = outputs
                response_data["message"] = "Job completed successfully with outputs."
            else:
                response_data["message"] = "Job completed successfully, but no output stems were found in the result field."
                response_data["outputs"] = None 
        elif status == "FAILED":
            error_detail = job_info.get("result", {}).get("error", "Job failed without specific error details.")
            response_data["error_details"] = str(error_detail)
            response_data["message"] = "Job processing failed."
        
        return jsonify(response_data)

    except Exception as e:
        print(f"💥 Error checking job status for {job_id}: {e}")
        traceback.print_exc()
        error_message = f"An error occurred while checking job status: {str(e)}"
        status_code = 500
        return jsonify({"error": error_message, "job_id": job_id}), status_code


@app.route('/results/<job_id>')
def show_results(job_id):
    api_key = request.args.get('api_key')
    if not api_key:
        api_key = os.environ.get('MUSIC_AI_APP_API_KEY')

    if not api_key:
        return render_template('result.html', stems=None, job_status="ERROR_FETCHING_RESULTS", job_id=job_id, error_info="API Key required to view results")


    client = MusicAiClient(api_key=api_key)
    try:
        print(f"📊 Fetching results for job ID: {job_id} to render page.")
        job_info = client.get_job(job_id=job_id)
        status = job_info.get('status')

        # Log the full job_info when fetching for results page
        print(f"🔍 Full job_info for results page {job_id} (Status: {status}):")
        print(json.dumps(job_info, indent=2))

        if status == "SUCCEEDED":
            # CORRECTED LINE: Get the 'result' object directly
            outputs = job_info.get("result")
            
            if outputs and isinstance(outputs, dict) and len(outputs) > 0: # Check if outputs is a non-empty dictionary
                return render_template('result.html', stems=outputs, job_status=status, job_id=job_id, error_info=None)
            else:
                return render_template('result.html', stems=None, job_status="SUCCEEDED_NO_OUTPUTS", job_id=job_id, error_info="Job succeeded, but no output stems were found in the result field. The workflow might not have generated any for this input.")
        elif status == "FAILED":
            error_detail = job_info.get("result", {}).get("error", "Job failed.")
            return render_template('result.html', stems=None, job_status=status, job_id=job_id, error_info=str(error_detail))
        else: 
            return render_template('result.html', stems=None, job_status=status, job_id=job_id, error_info="Job is not yet complete or in an unknown state.")

    except Exception as e:
        print(f"💥 Error fetching job details for results page (job {job_id}): {e}")
        traceback.print_exc()
        return render_template('result.html', stems=None, job_status="ERROR_FETCHING_RESULTS", job_id=job_id, error_info=str(e))


if __name__ == '__main__':
    app_port = int(os.environ.get('PORT', 8080))
    app_debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    print(f"🚀 Starting Flask app on 0.0.0.0:{app_port} with debug={app_debug}")
    app.run(host='0.0.0.0', port=app_port, debug=app_debug)
