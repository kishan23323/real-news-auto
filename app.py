"""
Local Review UI — run this on your PC to review videos before posting.

    pip install flask
    python app.py

Then open: http://localhost:5000

Features:
- See all generated videos with thumbnail preview
- Watch the video in browser
- Delete if not happy
- Click "Post to YouTube (Unlisted)" when ready
"""
import os, json
from flask import Flask, render_template_string, send_file, jsonify, request, redirect

app = Flask(__name__)
VIDEO_DIR = "daily_videos"

HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>Real News — Video Review</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: #0f0f0f; color: #fff; font-family: Arial, sans-serif; }
    header { background: #cc1414; padding: 18px 30px; display: flex; align-items: center; gap: 16px; }
    header h1 { font-size: 26px; font-weight: bold; letter-spacing: 1px; }
    header span { background: #fff; color: #cc1414; font-size: 12px; font-weight: bold;
                  padding: 3px 10px; border-radius: 4px; }
    .container { max-width: 1100px; margin: 30px auto; padding: 0 20px; }
    .empty { text-align: center; padding: 80px; color: #666; font-size: 18px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(480px, 1fr)); gap: 28px; }
    .card { background: #1a1a1a; border-radius: 12px; overflow: hidden; border: 1px solid #2a2a2a; }
    .card:hover { border-color: #cc1414; }
    .thumb { position: relative; cursor: pointer; }
    .thumb img { width: 100%; display: block; }
    .thumb .play { position: absolute; top: 50%; left: 50%; transform: translate(-50%,-50%);
                   font-size: 52px; opacity: 0.85; pointer-events: none; }
    .no-thumb { width: 100%; height: 200px; background: #222; display: flex;
                align-items: center; justify-content: center; color: #555; font-size: 14px; }
    .info { padding: 16px; }
    .info h3 { font-size: 15px; color: #eee; margin-bottom: 6px; line-height: 1.4; }
    .info .meta { font-size: 12px; color: #666; margin-bottom: 14px; }
    .actions { display: flex; gap: 10px; }
    .btn { padding: 10px 18px; border: none; border-radius: 6px; font-size: 14px;
           font-weight: bold; cursor: pointer; flex: 1; text-align: center; }
    .btn-preview { background: #333; color: #fff; }
    .btn-preview:hover { background: #444; }
    .btn-post { background: #cc1414; color: #fff; }
    .btn-post:hover { background: #ee2020; }
    .btn-post:disabled { background: #555; cursor: not-allowed; }
    .btn-delete { background: #1a1a1a; color: #cc1414; border: 1px solid #cc1414; flex: 0.4; }
    .btn-delete:hover { background: #cc1414; color: #fff; }
    /* Modal */
    .modal { display:none; position:fixed; top:0;left:0;width:100%;height:100%;
             background:rgba(0,0,0,0.92); z-index:999; align-items:center; justify-content:center; }
    .modal.open { display:flex; }
    .modal-inner { max-width:900px; width:95%; }
    .modal-inner video { width:100%; border-radius:8px; }
    .modal-close { float:right; background:#cc1414; color:#fff; border:none;
                   padding:8px 18px; border-radius:6px; cursor:pointer; margin-bottom:10px; font-size:14px; }
    .status { margin-top:10px; padding:10px 14px; border-radius:6px; font-size:13px; display:none; }
    .status.ok  { background:#1a3a1a; color:#4caf50; display:block; }
    .status.err { background:#3a1a1a; color:#f44336; display:block; }
  </style>
</head>
<body>
<header>
  <h1>REAL NEWS</h1>
  <span>VIDEO REVIEW PANEL</span>
</header>
<div class="container">
  {% if not videos %}
  <div class="empty">
    No videos found in <code>daily_videos/</code><br><br>
    Run the pipeline first to generate videos.
  </div>
  {% else %}
  <p style="color:#888;margin-bottom:20px;">{{ videos|length }} video(s) ready for review</p>
  <div class="grid">
    {% for v in videos %}
    <div class="card" id="card-{{ loop.index0 }}">
      <div class="thumb" onclick="openPreview('{{ v.video }}')">
        {% if v.thumb %}
        <img src="/thumb/{{ v.thumb }}" alt="thumbnail">
        {% else %}
        <div class="no-thumb">No thumbnail</div>
        {% endif %}
        <div class="play">&#9654;</div>
      </div>
      <div class="info">
        <h3>{{ v.name }}</h3>
        <div class="meta">{{ v.size }}</div>
        <div class="actions">
          <button class="btn btn-preview" onclick="openPreview('{{ v.video }}')">Preview</button>
          <button class="btn btn-post" id="post-{{ loop.index0 }}"
                  onclick="postVideo('{{ v.video }}', {{ loop.index0 }})">
            Post Unlisted
          </button>
          <button class="btn btn-delete" onclick="deleteVideo('{{ v.video }}', {{ loop.index0 }})">Delete</button>
        </div>
        <div class="status" id="status-{{ loop.index0 }}"></div>
      </div>
    </div>
    {% endfor %}
  </div>
  {% endif %}
</div>

<!-- Video preview modal -->
<div class="modal" id="modal">
  <div class="modal-inner">
    <button class="modal-close" onclick="closePreview()">Close X</button>
    <video id="modal-video" controls></video>
  </div>
</div>

<script>
function openPreview(filename) {
  document.getElementById("modal-video").src = "/video/" + filename;
  document.getElementById("modal").classList.add("open");
}
function closePreview() {
  const v = document.getElementById("modal-video");
  v.pause(); v.src = "";
  document.getElementById("modal").classList.remove("open");
}
function setStatus(idx, msg, ok) {
  const el = document.getElementById("status-" + idx);
  el.textContent = msg;
  el.className = "status " + (ok ? "ok" : "err");
}
function postVideo(filename, idx) {
  const btn = document.getElementById("post-" + idx);
  btn.disabled = true;
  btn.textContent = "Uploading...";
  setStatus(idx, "Uploading to YouTube as Unlisted — please wait...", true);
  fetch("/post", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({video: filename})
  })
  .then(r => r.json())
  .then(data => {
    if (data.ok) {
      btn.textContent = "Posted!";
      setStatus(idx, "Uploaded! youtube.com/watch?v=" + data.video_id, true);
    } else {
      btn.disabled = false;
      btn.textContent = "Post Unlisted";
      setStatus(idx, "Error: " + data.error, false);
    }
  });
}
function deleteVideo(filename, idx) {
  if (!confirm("Delete this video?")) return;
  fetch("/delete", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({video: filename})
  })
  .then(r => r.json())
  .then(data => {
    if (data.ok) {
      document.getElementById("card-" + idx).remove();
    }
  });
}
</script>
</body>
</html>
"""


def get_videos():
    if not os.path.exists(VIDEO_DIR):
        return []
    videos = []
    for f in sorted(os.listdir(VIDEO_DIR), reverse=True):
        if not f.endswith(".mp4"):
            continue
        video_path = f
        # find matching thumbnail
        thumb_name = f.replace(".mp4", ".jpg").replace("video_", "thumb_")
        thumb_path = thumb_name if os.path.exists(os.path.join(VIDEO_DIR, thumb_name)) else None
        size_bytes = os.path.getsize(os.path.join(VIDEO_DIR, f))
        size_mb = f"{size_bytes / 1024 / 1024:.1f} MB"
        videos.append({"video": video_path, "thumb": thumb_path, "name": f, "size": size_mb})
    return videos


@app.route("/")
def index():
    return render_template_string(HTML, videos=get_videos())


@app.route("/video/<path:filename>")
def serve_video(filename):
    return send_file(os.path.join(VIDEO_DIR, filename), mimetype="video/mp4")


@app.route("/thumb/<path:filename>")
def serve_thumb(filename):
    return send_file(os.path.join(VIDEO_DIR, filename), mimetype="image/jpeg")


@app.route("/post", methods=["POST"])
def post_video():
    data     = request.get_json()
    filename = data.get("video")
    if not filename:
        return jsonify(ok=False, error="No filename")
    video_path = os.path.join(VIDEO_DIR, filename)
    thumb_name = filename.replace(".mp4", ".jpg").replace("video_", "thumb_")
    thumb_path = os.path.join(VIDEO_DIR, thumb_name)

    try:
        from upload_youtube import upload_video
        # extract title from filename: video_2026-07-01_My_Title.mp4
        parts = filename.replace(".mp4","").split("_", 2)
        title = parts[2].replace("_"," ") if len(parts) > 2 else filename
        video_id = upload_video(
            video_path, title=title,
            thumbnail_path=thumb_path if os.path.exists(thumb_path) else None,
            privacy="unlisted"
        )
        return jsonify(ok=True, video_id=video_id)
    except Exception as e:
        return jsonify(ok=False, error=str(e))


@app.route("/delete", methods=["POST"])
def delete_video():
    data     = request.get_json()
    filename = data.get("video")
    try:
        os.remove(os.path.join(VIDEO_DIR, filename))
        thumb = filename.replace(".mp4",".jpg").replace("video_","thumb_")
        if os.path.exists(os.path.join(VIDEO_DIR, thumb)):
            os.remove(os.path.join(VIDEO_DIR, thumb))
        return jsonify(ok=True)
    except Exception as e:
        return jsonify(ok=False, error=str(e))


if __name__ == "__main__":
    print("\n Real News Review Panel")
    print(" Open in browser: http://localhost:5000\n")
    app.run(debug=False, port=5000)
