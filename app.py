from flask import Flask, render_template, jsonify, request, Response, send_file
import threading
import queue
import os
from datetime import datetime

from scraper import run_scraper, load_data, has_data, get_topics
from pdf_gen import generate_pdf

app = Flask(__name__)

progress_queue = queue.Queue()
scrape_status = {"running": False, "done": False, "error": None}


# ── ROUTES ───────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/topics")
def topics():
    """Returns the full list of available topics"""
    return jsonify({"topics": get_topics()})


@app.route("/api/status")
def status():
    return jsonify({
        "has_data": has_data(),
        "running": scrape_status["running"],
        "done": scrape_status["done"],
        "error": scrape_status["error"],
    })


@app.route("/api/scrape", methods=["POST"])
def start_scrape():
    """Starts scraping for the selected topics"""
    if scrape_status["running"]:
        return jsonify({"error": "Scraper is already running!"}), 400

    body = request.get_json(silent=True) or {}
    selected = body.get("topics", [])

    if not selected:
        return jsonify({"error": "No topics selected!"}), 400

    scrape_status["running"] = True
    scrape_status["done"] = False
    scrape_status["error"] = None

    def do_scrape():
        try:
            def progress(msg):
                progress_queue.put(msg)

            run_scraper(selected, progress_callback=progress)
            scrape_status["done"] = True

        except Exception as e:
            scrape_status["error"] = str(e)
        finally:
            scrape_status["running"] = False
            progress_queue.put("__DONE__")

    thread = threading.Thread(target=do_scrape, daemon=True)
    thread.start()

    return jsonify({"started": True})


@app.route("/api/progress")
def progress_stream():
    """Streams live progress to the browser"""
    def generate():
        while True:
            try:
                msg = progress_queue.get(timeout=30)
                if msg == "__DONE__":
                    yield f"data: __DONE__\n\n"
                    break
                yield f"data: {msg}\n\n"
            except queue.Empty:
                yield f"data: ping\n\n"

    return Response(generate(), mimetype="text/event-stream")


@app.route("/api/data")
def get_data():
    """Returns all scraped data"""
    data = load_data()
    if not data:
        return jsonify({"results": {}, "selected_topics": []})
    return jsonify(data)


@app.route("/api/generate-pdf", methods=["POST"])
def generate_pdf_route():
    """Generates and downloads the PDF"""
    data = load_data()
    if not data:
        return jsonify({"error": "No data yet. Please scrape first!"}), 400

    body = request.get_json(silent=True) or {}
    student_name = body.get("student_name", "Anonymous")
    selected_topics = body.get("topics", list(data.get("results", {}).keys()))

    filename = f"GFG_Learning_Module_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    try:
        path = generate_pdf(
            data=data,
            selected_topics=selected_topics,
            student_name=student_name,
            filename=filename
        )
        return send_file(path, as_attachment=True, download_name=filename, mimetype="application/pdf")
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── RUN ──────────────────────────────────────────────────────

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    os.makedirs("templates", exist_ok=True)
    print("Server running at http://localhost:5050")
    app.run(debug=False, port=5050)