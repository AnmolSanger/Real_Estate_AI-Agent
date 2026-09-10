import uuid
import threading

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, request, jsonify
from crewai import Crew
from agents import property_researcher, property_analyst
from tasks import create_research_task, create_analysis_task

app = Flask(__name__)

jobs = {}


def run_crew(job_id, location, property_type):
    jobs[job_id]["status"] = "running"
    try:
        research_task = create_research_task(location, property_type)
        analysis_task = create_analysis_task(location, property_type, research_task)

        crew = Crew(
            agents=[property_researcher, property_analyst],
            tasks=[research_task, analysis_task],
            verbose=True,
        )

        result = crew.kickoff()
        jobs[job_id]["status"] = "done"
        jobs[job_id]["result"] = str(result)
    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    location = data.get("location", "").strip()
    property_type = data.get("property_type", "").strip()

    if not location or not property_type:
        return jsonify({"error": "Both location and property type are required."}), 400

    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "starting", "location": location, "property_type": property_type}

    thread = threading.Thread(target=run_crew, args=(job_id, location, property_type))
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/status/<job_id>")
def status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
