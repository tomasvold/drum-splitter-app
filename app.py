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

        print(f"⚙️ Creating job with workflow: {workflow}...")
        job_creation_info = client.create_job(
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
    # It's important to re-initialize the client or ensure it's available.
    # For simplicity here, we'll assume API key might need to be passed or stored securely if needed across requests.
    # However, the SDK client itself is stateless for get_job if initialized with an API key.
    # For a production app, you'd handle API key management more robustly (e.g., session, secure config).
    # For this example, we'll assume the client can be re-initialized if needed,
    # or that the API key used for job creation is implicitly available/not strictly tied to this status check call by music.ai.
    # The MusicAiClient is typically initialized with an API key that's used for all its requests.
    # We need an API key to initialize the client to check the status.
    # This is a simplification; in a real app, you'd securely manage how the API key is available for this.
    # One way is to require the API key again, or use a server-side stored key if this app has its own MusicAI account.
    # Since the user provides the API key, we'll need it.
    # This example assumes the client-side will pass it or it's configured server-side.
    # For now, let's assume we need to get it from a query param for this example,
    # or better, it should be part of a secure session or server configuration.
    
    # A more robust way would be to store the api_key used for the job creation associated with the job_id,
    # or have a global API key for the app if that's the model.
    # For this iteration, we'll just re-initialize with a placeholder.
    # THIS IS A SIMPLIFICATION AND LIKELY NEEDS THE ACTUAL API KEY.
    # The client that calls this /job_status endpoint would need to provide the API key.
    # Let's assume the client sends it as a header or query parameter for this check.
    
    api_key = request.args.get('api_key') # Or request.headers.get('X-API-Key')
    if not api_key:
        # Fallback to an environment variable if this app has its own key for status checks
        api_key = os.environ.get('MUSIC_AI_APP_API_KEY') 
    
    if not api_key:
        return jsonify({"error": "API key required to check job status"}), 400
        
    client = MusicAiClient(api_key=api_key)

    try:
        print(f"🔎 Checking status for job ID: {job_id}")
        job_info = client.get_job(job_id=job_id) # Non-blocking call
        print(f"ℹ️ Status for job {job_id}: {job_info.get('status')}")
        print(json.dumps(job_info, indent=2)) # For verbose debugging

        status = job_info.get('status')
        response_data = {"job_id": job_id, "status": status}

        if status == "SUCCEEDED":
            outputs = job_info.get("result", {}).get("outputs")
            if outputs:
                response_data["outputs"] = outputs
                response_data["message"] = "Job completed successfully with outputs."
            else:
                response_data["message"] = "Job completed successfully, but no outputs were found in the result."
                response_data["outputs"] = None # Explicitly state no outputs
        elif status == "FAILED":
            error_detail = job_info.get("result", {}).get("error", "Job failed without specific error details.")
            response_data["error_details"] = str(error_detail)
            response_data["message"] = "Job processing failed."
        
        return jsonify(response_data)

    except Exception as e:
        # This could be an SDK error if the job_id is invalid or API key is wrong for get_job
        print(f"💥 Error checking job status for {job_id}: {e}")
        traceback.print_exc()
        # Check if e has a status_code attribute (like from requests.exceptions.HTTPError)
        # or if it's a specific SDK error with more info.
        error_message = f"An error occurred while checking job status: {str(e)}"
        status_code = 500
        # if hasattr(e, 'response') and e.response is not None:
        #     status_code = e.response.status_code
        #     try:
        #         error_message = e.response.json().get('message', error_message)
        #     except ValueError: # Not JSON
        #         pass
        return jsonify({"error": error_message, "job_id": job_id}), status_code


@app.route('/results/<job_id>')
def show_results(job_id):
    # This route assumes the client has already confirmed the job is SUCCEEDED
    # and has the outputs. For simplicity, it could re-fetch or expect outputs to be passed.
    # For this version, we'll re-fetch to ensure data integrity.
    # Similar API key consideration as in /job_status
    api_key = request.args.get('api_key')
    if not api_key:
        api_key = os.environ.get('MUSIC_AI_APP_API_KEY')

    if not api_key:
        return "API Key required to view results", 400 # Or render an error template

    client = MusicAiClient(api_key=api_key)
    try:
        print(f"📊 Fetching results for job ID: {job_id} to render page.")
        job_info = client.get_job(job_id=job_id)
        status = job_info.get('status')

        if status == "SUCCEEDED":
            outputs = job_info.get("result", {}).get("outputs")
            if outputs:
                return render_template('result.html', stems=outputs, job_status=status, job_id=job_id)
            else:
                # Render result.html with a message that job succeeded but no outputs
                return render_template('result.html', stems=None, job_status="SUCCEEDED_NO_OUTPUTS", job_id=job_id, error_info="Job succeeded, but no output stems were found.")
        elif status == "FAILED":
            error_detail = job_info.get("result", {}).get("error", "Job failed.")
            return render_template('result.html', stems=None, job_status=status, job_id=job_id, error_info=str(error_detail))
        else: # Still processing or other states
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
