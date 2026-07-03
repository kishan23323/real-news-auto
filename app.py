"""
Real News Studio — Desktop-style web app

Run:  python app.py
Open: http://localhost:5000
"""
import os, json, threading, time, uuid, queue
from flask import Flask, render_template_string, send_file, jsonify, request, Response

app    = Flask(__name__)
DOWNLOADS = os.path.join(os.path.expanduser("~"), "Downloads", "daily_videos")
os.makedirs(DOWNLOADS, exist_ok=True)

# track generation progress per job
_jobs = {}   # job_id -> {status, progress, message, video, thumb, title, lang, error, approval_event, approved_sentences}

# ─────────────────────────────────────────────────────────────────────────────
HTML = r"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Real News Studio</title>
  <style>
    :root {
      --red: #cc1414; --dark: #0f0f0f; --card: #181818;
      --border: #2a2a2a; --text: #e0e0e0; --sub: #888;
      --gold: #FFD700; --green: #4caf50;
    }
    * { box-sizing: border-box; margin:0; padding:0; }
    body { background:var(--dark); color:var(--text); font-family:Arial,sans-serif;
           height:100vh; display:flex; flex-direction:column; overflow:hidden; }

    /* ── Top bar ─────────────────────────────────────────────── */
    .topbar { background:linear-gradient(90deg,#900,var(--red));
              padding:12px 24px; display:flex; align-items:center;
              gap:14px; flex-shrink:0; box-shadow:0 2px 12px rgba(0,0,0,0.5); }
    .topbar h1 { font-size:20px; font-weight:900; letter-spacing:2px; }
    .topbar .badge { background:#fff; color:var(--red); font-size:10px;
                     font-weight:bold; padding:2px 8px; border-radius:3px; }
    .topbar .spacer { flex:1; }
    .topbar .folder { font-size:11px; color:rgba(255,255,255,0.6); cursor:pointer; }

    /* ── Layout ──────────────────────────────────────────────── */
    .body { display:flex; flex:1; overflow:hidden; }

    /* ── Sidebar ─────────────────────────────────────────────── */
    .sidebar { width:230px; background:#111; border-right:1px solid var(--border);
               display:flex; flex-direction:column; flex-shrink:0; overflow-y:auto; }
    .sidebar-section { padding:14px 16px 6px; font-size:10px; color:#555;
                       text-transform:uppercase; letter-spacing:1px; }
    .nav-item { padding:10px 18px; cursor:pointer; font-size:13px; color:#aaa;
                display:flex; align-items:center; gap:10px; transition:all 0.15s; }
    .nav-item:hover  { background:#1a1a1a; color:#fff; }
    .nav-item.active { background:#1a1a1a; color:var(--red);
                       border-left:3px solid var(--red); }
    .nav-item .ico { font-size:16px; width:20px; text-align:center; }

    .video-list { flex:1; overflow-y:auto; padding:8px; }
    .vitem { padding:8px 10px; border-radius:6px; cursor:pointer; margin-bottom:4px;
             font-size:12px; color:#aaa; display:flex; align-items:center; gap:8px;
             border:1px solid transparent; transition:all 0.15s; }
    .vitem:hover  { background:#1e1e1e; color:#fff; border-color:var(--border); }
    .vitem.active { background:#1e1e1e; color:#fff; border-color:var(--red); }
    .vitem .dot   { width:8px; height:8px; border-radius:50%; flex-shrink:0; }

    /* ── Main area ───────────────────────────────────────────── */
    .main { flex:1; display:flex; flex-direction:column; overflow:hidden; }

    /* ── Panels (tabs) ───────────────────────────────────────── */
    .panel { display:none; flex:1; overflow:auto; padding:24px; }
    .panel.active { display:flex; flex-direction:column; gap:20px; }

    /* ── Generate panel ──────────────────────────────────────── */
    .gen-card { background:var(--card); border:1px solid var(--border);
                border-radius:12px; padding:28px 32px; max-width:700px; margin:auto; width:100%; }
    .gen-card h2 { font-size:20px; margin-bottom:6px; }
    .gen-card p  { font-size:13px; color:var(--sub); margin-bottom:24px; }
    .field { margin-bottom:16px; }
    .field label { font-size:12px; color:var(--sub); display:block; margin-bottom:6px; }
    .field input, .field select {
      width:100%; padding:11px 14px; background:#111; border:1px solid var(--border);
      border-radius:7px; color:#fff; font-size:14px; outline:none;
    }
    .field input:focus, .field select:focus { border-color:var(--red); }
    .row { display:flex; gap:12px; }
    .row .field { flex:1; }
    .btn-gen { width:100%; padding:14px; background:var(--red); color:#fff;
               border:none; border-radius:8px; font-size:16px; font-weight:bold;
               cursor:pointer; margin-top:8px; transition:background 0.2s; }
    .btn-gen:hover:not(:disabled) { background:#ee2020; }
    .btn-gen:disabled { background:#444; cursor:not-allowed; }

    /* progress */
    .progress-wrap { margin-top:20px; display:none; }
    .progress-wrap.show { display:block; }
    .progress-steps { display:flex; gap:0; margin-bottom:16px; }
    .step { flex:1; text-align:center; padding:8px 4px; font-size:11px; color:#555;
            border-bottom:2px solid var(--border); transition:all 0.3s; }
    .step.active { color:var(--red); border-color:var(--red); }
    .step.done   { color:var(--green); border-color:var(--green); }
    .progress-bar-bg { background:#222; border-radius:4px; height:6px; overflow:hidden; }
    .progress-bar    { height:100%; background:var(--red); border-radius:4px;
                       transition:width 0.4s ease; width:0%; }
    .progress-msg    { font-size:12px; color:var(--sub); margin-top:8px; min-height:20px; }
    .progress-log    { background:#111; border-radius:6px; padding:12px;
                       font-size:11px; color:#666; font-family:monospace;
                       height:90px; overflow-y:auto; margin-top:8px; }

    /* approval panel */
    .approval-panel { background:#0d1a0d; border:1px solid #2a6a2a;
                      border-radius:10px; padding:20px; margin-top:18px; display:none; }
    .approval-panel.show { display:block; }
    .approval-panel h3 { font-size:15px; color:#4caf50; margin-bottom:4px; }
    .approval-panel p  { font-size:12px; color:#888; margin-bottom:14px; }
    .approval-panel .lang-badge { display:inline-block; background:#1a3a1a;
                                   color:#4caf50; font-size:11px; padding:2px 10px;
                                   border-radius:10px; margin-bottom:14px; }
    .approval-toolbar { display:flex; gap:8px; margin-bottom:12px; }
    .btn-toolbar { padding:8px 14px; background:#111; color:#4caf50;
                   border:1px solid #2a6a2a; border-radius:6px; font-size:12px;
                   font-weight:bold; cursor:pointer; transition:all 0.15s; }
    .btn-toolbar:hover { background:#1a3a1a; }
    .btn-toolbar.copied { background:#4caf50; color:#0d1a0d; border-color:#4caf50; }
    .bulk-textarea { width:100%; min-height:260px; max-height:340px;
                      background:#111; border:1px solid #2a6a2a; border-radius:6px;
                      color:#ddd; font-size:13px; padding:12px; outline:none;
                      font-family:Arial,sans-serif; line-height:1.6; resize:vertical;
                      margin-bottom:10px; display:none; }
    .bulk-textarea.show { display:block; }
    .bulk-hint { font-size:11px; color:#666; margin:-4px 0 10px; display:none; }
    .bulk-hint.show { display:block; }
    .sentence-list { display:flex; flex-direction:column; gap:6px;
                     max-height:340px; overflow-y:auto; margin-bottom:14px; }
    .sentence-list.hide { display:none; }
    .sentence-row  { display:flex; align-items:flex-start; gap:8px; }
    .sentence-num  { font-size:11px; color:#555; padding-top:8px;
                     min-width:26px; text-align:right; flex-shrink:0; }
    .sentence-input {
      flex:1; background:#111; border:1px solid #2a2a2a; border-radius:6px;
      color:#ddd; font-size:13px; padding:7px 10px; outline:none;
      font-family:Arial,sans-serif; resize:vertical; min-height:36px;
      line-height:1.5;
    }
    .sentence-input:focus { border-color:#4caf50; }
    .sentence-del { background:transparent; border:none; color:#555;
                    cursor:pointer; font-size:16px; padding:6px; flex-shrink:0; }
    .sentence-del:hover { color:#cc1414; }
    .approval-actions { display:flex; gap:10px; margin-top:6px; }
    .btn-approve { flex:2; padding:12px; background:#4caf50; color:#fff;
                   border:none; border-radius:7px; font-size:14px;
                   font-weight:bold; cursor:pointer; transition:background 0.2s; }
    .btn-approve:hover { background:#66bb6a; }
    .btn-add-sentence { flex:1; padding:12px; background:#1a3a1a; color:#4caf50;
                        border:1px solid #4caf50; border-radius:7px; font-size:13px;
                        font-weight:bold; cursor:pointer; }
    .btn-add-sentence:hover { background:#2a4a2a; }

    /* ── Editor panel ─────────────────────────────────────────── */
    .editor-wrap { display:flex; gap:20px; flex:1; min-height:0; }
    .editor-left { flex:1.4; display:flex; flex-direction:column; gap:12px; min-width:0; }
    .editor-right { width:280px; display:flex; flex-direction:column; gap:12px; flex-shrink:0; }

    .video-player-wrap { background:#000; border-radius:10px; overflow:hidden;
                         position:relative; border:1px solid var(--border); }
    .video-player-wrap video { width:100%; display:block; max-height:360px; }

    /* custom timeline */
    .timeline-outer { background:#111; border:1px solid var(--border);
                      border-radius:8px; padding:12px; }
    .timeline-label { font-size:11px; color:var(--sub); margin-bottom:8px;
                      display:flex; justify-content:space-between; }
    .timeline { position:relative; height:44px; background:#1a1a1a;
                border-radius:6px; cursor:crosshair; user-select:none; }
    .tl-progress { position:absolute; top:0; left:0; height:100%;
                   background:rgba(204,20,20,0.25); border-radius:6px; }
    .tl-selection { position:absolute; top:0; height:100%;
                    background:rgba(255,215,0,0.35); border:2px solid var(--gold);
                    border-radius:4px; display:none; }
    .tl-handle { position:absolute; top:0; width:6px; height:100%;
                 background:var(--gold); border-radius:3px; cursor:ew-resize; }
    .tl-playhead { position:absolute; top:0; width:2px; height:100%;
                   background:var(--red); pointer-events:none; }
    .tl-time { position:absolute; bottom:-20px; font-size:10px;
               color:var(--sub); transform:translateX(-50%); }

    .sel-info { display:flex; gap:8px; align-items:center; font-size:12px;
                color:var(--sub); margin-top:24px; }
    .sel-info span { color:#fff; font-weight:bold; }
    .sel-info .sep { flex:1; }

    .panel-card { background:var(--card); border:1px solid var(--border);
                  border-radius:10px; padding:16px; }
    .panel-card h3 { font-size:13px; margin-bottom:12px; color:#ccc; }

    .thumb-preview img { width:100%; border-radius:6px; display:block;
                         margin-bottom:10px; }
    .thumb-preview .no-thumb { width:100%; height:120px; background:#111;
                               border-radius:6px; display:flex; align-items:center;
                               justify-content:center; color:#444; font-size:12px; margin-bottom:10px; }

    .btn { padding:9px 14px; border:none; border-radius:6px; font-size:12px;
           font-weight:bold; cursor:pointer; transition:all 0.2s; width:100%;
           margin-bottom:6px; }
    .btn:disabled { opacity:0.4; cursor:not-allowed; }
    .btn-primary  { background:var(--red); color:#fff; }
    .btn-primary:hover:not(:disabled) { background:#ee2020; }
    .btn-secondary{ background:#2a2a2a; color:#fff; }
    .btn-secondary:hover:not(:disabled) { background:#3a3a3a; }
    .btn-success  { background:#1a3a1a; color:var(--green); border:1px solid var(--green); }
    .btn-success:hover:not(:disabled)  { background:#2a4a2a; }
    .btn-warning  { background:#3a2a00; color:var(--gold); border:1px solid var(--gold); }
    .btn-warning:hover:not(:disabled)  { background:#4a3a00; }
    .btn-danger   { background:transparent; color:var(--red); border:1px solid var(--red); }
    .btn-danger:hover:not(:disabled)   { background:var(--red); color:#fff; }

    .regen-fields { display:none; margin-bottom:10px; }
    .regen-fields.show { display:block; }
    .regen-fields input { width:100%; padding:8px 10px; background:#111;
                          border:1px solid var(--border); border-radius:6px;
                          color:#fff; font-size:12px; margin-bottom:6px; outline:none; }

    .status-box { padding:10px; border-radius:6px; font-size:12px; margin-top:6px; display:none; }
    .status-box.ok   { background:#0d2a0d; border:1px solid #2a6a2a; color:var(--green); display:block; }
    .status-box.err  { background:#2a0d0d; border:1px solid #6a2a2a; color:#f44336; display:block; }
    .status-box.info { background:#1a1a2a; border:1px solid #3a3a6a; color:#8888ff; display:block; }

    /* ── Library panel ─────────────────────────────────────────── */
    .lib-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:16px; }
    .lib-card { background:var(--card); border:1px solid var(--border);
                border-radius:10px; overflow:hidden; cursor:pointer; transition:all 0.2s; }
    .lib-card:hover { border-color:var(--red); transform:translateY(-2px); }
    .lib-card img { width:100%; height:160px; object-fit:cover; display:block; }
    .lib-card .no-img { width:100%; height:160px; background:#111;
                        display:flex; align-items:center; justify-content:center;
                        color:#444; font-size:30px; }
    .lib-card .lib-info { padding:12px; }
    .lib-card .lib-title { font-size:13px; margin-bottom:4px; }
    .lib-card .lib-meta  { font-size:11px; color:var(--sub); }
    .lib-actions { display:flex; gap:6px; padding:0 12px 12px; }
    .lib-actions .btn { margin:0; flex:1; }

    /* empty state */
    .empty-state { text-align:center; padding:80px 20px; color:#555; }
    .empty-state .icon { font-size:48px; margin-bottom:16px; }
    .empty-state h3 { font-size:18px; color:#777; margin-bottom:8px; }
    .empty-state p  { font-size:13px; line-height:1.8; }
  </style>
</head>
<body>

<!-- Top bar -->
<div class="topbar">
  <h1>REAL NEWS</h1>
  <span class="badge">STUDIO</span>
  <div class="spacer"></div>
  <div class="folder" title="Videos saved here">📁 {{ folder }}</div>
</div>

<div class="body">

  <!-- Sidebar -->
  <div class="sidebar">
    <div class="sidebar-section">Studio</div>
    <div class="nav-item active" onclick="showPanel('generate')" id="nav-generate">
      <span class="ico">⚡</span> Generate Video
    </div>
    <div class="nav-item" onclick="showPanel('editor')" id="nav-editor">
      <span class="ico">✂️</span> Video Editor
    </div>
    <div class="nav-item" onclick="showPanel('library')" id="nav-library">
      <span class="ico">📂</span> My Videos
    </div>

    <div class="sidebar-section" style="margin-top:12px;">Recent Videos</div>
    <div class="video-list" id="sidebar-videos">
      {% for v in videos %}
      <div class="vitem" onclick="openInEditor('{{ v.video }}','{{ v.thumb or '' }}')">
        <div class="dot" style="background:var(--red)"></div>
        <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
          {{ v.name[:30] }}
        </span>
      </div>
      {% endfor %}
    </div>
  </div>

  <!-- Main -->
  <div class="main">

    <!-- ── GENERATE PANEL ──────────────────────────────── -->
    <div class="panel active" id="panel-generate">
      <div class="gen-card">
        <h2>Generate News Video</h2>
        <p>Paste any article link — the AI builds a full narrated video with images and thumbnail.</p>

        <div class="field">
          <label>Article URL *</label>
          <input type="url" id="g-url" placeholder="https://www.thehindu.com/... or any news link">
        </div>
        <div class="row">
          <div class="field">
            <label>Image Search Topic</label>
            <input type="text" id="g-topic" placeholder="e.g. FIFA World Cup 2026">
          </div>
          <div class="field">
            <label>Video Length</label>
            <select id="g-minutes">
              <option value="3">3 minutes</option>
              <option value="5">5 minutes</option>
              <option value="6" selected>6 minutes</option>
              <option value="8">8 minutes</option>
              <option value="10">10 minutes</option>
            </select>
          </div>
        </div>

        <button class="btn-gen" id="gen-btn" onclick="startGenerate()">
          ⚡ Generate Video
        </button>

        <div class="progress-wrap" id="progress-wrap">
          <div class="progress-steps">
            <div class="step" id="s0">Extract</div>
            <div class="step" id="s1">Summarize</div>
            <div class="step" id="s2">Voice</div>
            <div class="step" id="s3">Images</div>
            <div class="step" id="s4">Build</div>
            <div class="step" id="s5">Thumbnail</div>
          </div>
          <div class="progress-bar-bg"><div class="progress-bar" id="pbar"></div></div>
          <div class="progress-msg" id="pmsg">Starting...</div>
          <div class="progress-log" id="plog"></div>
        </div>

        <!-- Approval panel — shows after summarization -->
        <div class="approval-panel" id="approval-panel">
          <h3>✅ Review & Edit Script</h3>
          <p>These sentences will be spoken in the video. Edit, delete, or add lines before approving.</p>
          <div class="lang-badge" id="approval-lang">English</div>

          <div class="approval-toolbar">
            <button class="btn-toolbar" id="btn-copy-all" onclick="copyAllSentences()">📋 Copy All</button>
            <button class="btn-toolbar" id="btn-paste-toggle" onclick="toggleBulkEdit()">📥 Paste &amp; Rebuild</button>
          </div>

          <div class="bulk-hint" id="bulk-hint">
            Paste your edited text below — keep one line per sentence if you want exact control,
            or paste it as a single paragraph and it'll auto-split on sentence punctuation
            (. ! ? ।). Click "Rebuild Lines" when ready.
          </div>
          <textarea class="bulk-textarea" id="bulk-textarea" placeholder="Paste edited script here..."></textarea>

          <div class="sentence-list" id="sentence-list"></div>

          <div class="approval-actions">
            <button class="btn-add-sentence" id="btn-add-line" onclick="addSentence()">+ Add Line</button>
            <button class="btn-add-sentence" id="btn-rebuild" style="display:none;" onclick="rebuildFromBulk()">↺ Rebuild Lines</button>
            <button class="btn-approve" onclick="approveSentences()">
              ✅ Approve & Generate Voice
            </button>
          </div>
        </div>

      </div>
    </div>

    <!-- ── EDITOR PANEL ────────────────────────────────── -->
    <div class="panel" id="panel-editor">
      <div id="editor-empty" class="empty-state">
        <div class="icon">✂️</div>
        <h3>No video selected</h3>
        <p>Generate a video first, or pick one from<br>My Videos in the sidebar.</p>
      </div>

      <div id="editor-content" class="editor-wrap" style="display:none">

        <!-- Left: player + timeline -->
        <div class="editor-left">
          <div class="video-player-wrap">
            <video id="editor-video" controls preload="metadata"></video>
          </div>

          <div class="timeline-outer">
            <div class="timeline-label">
              <span>Timeline — drag to select a segment to replace</span>
              <span id="tl-dur">0:00</span>
            </div>
            <div class="timeline" id="timeline"
                 onmousedown="tlDown(event)"
                 onmousemove="tlMove(event)"
                 onmouseup="tlUp(event)">
              <div class="tl-progress" id="tl-progress"></div>
              <div class="tl-selection" id="tl-sel">
                <div class="tl-handle" id="tl-h-left"  style="left:0"  onmousedown="handleDown(event,'left')"></div>
                <div class="tl-handle" id="tl-h-right" style="right:0" onmousedown="handleDown(event,'right')"></div>
              </div>
              <div class="tl-playhead" id="tl-playhead"></div>
            </div>
            <div class="sel-info">
              <span>Start: <span id="sel-start-lbl">--</span></span>&nbsp;&nbsp;
              <span>End: <span id="sel-end-lbl">--</span></span>&nbsp;&nbsp;
              <span>Length: <span id="sel-len-lbl">--</span></span>
              <span class="sep"></span>
              <span id="cursor-time" style="color:var(--sub)"></span>
            </div>
          </div>
        </div>

        <!-- Right: controls -->
        <div class="editor-right">

          <!-- Regenerate segment -->
          <div class="panel-card">
            <h3>✂️ Regenerate Segment</h3>
            <p style="font-size:11px;color:var(--sub);margin-bottom:12px;">
              Select a portion on the timeline, then click below to regenerate just that part with new content.
            </p>
            <button class="btn btn-warning" id="regen-btn"
                    onclick="showRegenFields()" disabled>
              Select a segment first
            </button>
            <div class="regen-fields" id="regen-fields">
              <input type="text" id="regen-topic" placeholder="Topic for this segment (optional)">
              <button class="btn btn-primary" onclick="regenSegment()">
                Regenerate Selected Part
              </button>
            </div>
            <div class="status-box" id="regen-status"></div>
          </div>

          <!-- Thumbnail -->
          <div class="panel-card">
            <h3>🖼️ Thumbnail</h3>
            <div class="thumb-preview" id="thumb-preview">
              <div class="no-thumb">No thumbnail</div>
            </div>
            <button class="btn btn-secondary" onclick="regenThumb()">
              Regenerate Thumbnail
            </button>
            <div class="status-box" id="thumb-status"></div>
          </div>

          <!-- Upload -->
          <div class="panel-card">
            <h3>📤 Export & Upload</h3>
            <a id="dl-link" href="#" download>
              <button class="btn btn-success">Download Video</button>
            </a>
            <a id="dl-thumb-link" href="#" download>
              <button class="btn btn-secondary">Download Thumbnail</button>
            </a>
            <button class="btn btn-primary" onclick="uploadYT()" id="yt-btn">
              Upload to YouTube (Unlisted)
            </button>
            <div class="status-box" id="upload-status"></div>
          </div>

        </div>
      </div>
    </div>

    <!-- ── LIBRARY PANEL ───────────────────────────────── -->
    <div class="panel" id="panel-library">
      {% if not videos %}
      <div class="empty-state">
        <div class="icon">📂</div>
        <h3>No videos yet</h3>
        <p>Generate your first video using the Generate tab.</p>
      </div>
      {% else %}
      <div class="lib-grid">
        {% for v in videos %}
        <div class="lib-card">
          {% if v.thumb %}
            <img src="/thumb/{{ v.thumb }}" alt="">
          {% else %}
            <div class="no-img">📹</div>
          {% endif %}
          <div class="lib-info">
            <div class="lib-title">{{ v.name.replace('video_','').replace('.mp4','').replace('_',' ')[:40] }}</div>
            <div class="lib-meta">{{ v.size }} · {{ v.date }}</div>
          </div>
          <div class="lib-actions">
            <button class="btn btn-secondary"
                    onclick="openInEditor('{{ v.video }}','{{ v.thumb or '' }}')">Edit</button>
            <a href="/download/{{ v.video }}" download style="flex:1">
              <button class="btn btn-success" style="width:100%">Download</button>
            </a>
            <button class="btn btn-danger"
                    onclick="deleteVideo('{{ v.video }}', this)">Del</button>
          </div>
        </div>
        {% endfor %}
      </div>
      {% endif %}
    </div>

  </div><!-- /main -->
</div><!-- /body -->

<script>
// ── Panel switching ───────────────────────────────────────
function showPanel(name) {
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('panel-' + name).classList.add('active');
  document.getElementById('nav-' + name).classList.add('active');
}

// ── Generate ──────────────────────────────────────────────
let currentJobId = null;

function startGenerate() {
  const url   = document.getElementById('g-url').value.trim();
  const topic = document.getElementById('g-topic').value.trim();
  const mins  = document.getElementById('g-minutes').value;
  if (!url) { alert('Please enter an article URL'); return; }

  document.getElementById('gen-btn').disabled = true;
  document.getElementById('gen-btn').textContent = 'Generating...';
  document.getElementById('progress-wrap').classList.add('show');
  document.getElementById('plog').textContent = '';
  setPbar(0, 'Starting pipeline...');
  setStep(-1);

  fetch('/generate', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({url, topic, minutes: parseFloat(mins)})
  })
  .then(r => r.json())
  .then(data => {
    if (data.job_id) {
      currentJobId = data.job_id;
      pollJob(data.job_id);
    } else {
      showGenError(data.error || 'Unknown error');
    }
  });
}

function pollJob(jobId) {
  const es = new EventSource('/progress/' + jobId);
  es.onmessage = e => {
    const d = JSON.parse(e.data);
    appendLog(d.message || '');
    setPbar(d.progress || 0, d.message || '');
    if (d.step !== undefined) setStep(d.step);

    if (d.status === 'done') {
      es.close();
      onGenerateDone(d);
    } else if (d.status === 'error') {
      es.close();
      showGenError(d.error || 'Generation failed');
    }
  };
  es.onerror = () => { es.close(); showGenError('Connection lost'); };
}

function onGenerateDone(d) {
  setPbar(100, 'Video ready!');
  setStep(5, true);
  document.getElementById('gen-btn').disabled = false;
  document.getElementById('gen-btn').textContent = '⚡ Generate Video';
  // auto-open in editor
  openInEditor(d.video, d.thumb || '');
  showPanel('editor');
  // refresh sidebar
  addToSidebar(d.video, d.thumb);
}

function showGenError(msg) {
  setPbar(0, 'Error: ' + msg);
  document.getElementById('plog').textContent += '\n❌ ' + msg;
  document.getElementById('gen-btn').disabled = false;
  document.getElementById('gen-btn').textContent = '⚡ Generate Video';
}

function setPbar(pct, msg) {
  document.getElementById('pbar').style.width = pct + '%';
  document.getElementById('pmsg').textContent = msg;
}
function appendLog(msg) {
  const el = document.getElementById('plog');
  el.textContent += msg + '\n';
  el.scrollTop = el.scrollHeight;
}
function setStep(idx, done) {
  for (let i = 0; i < 6; i++) {
    const el = document.getElementById('s' + i);
    el.className = 'step' + (i < idx ? ' done' : i === idx ? ' active' : '');
  }
}

function addToSidebar(video, thumb) {
  const list = document.getElementById('sidebar-videos');
  const div  = document.createElement('div');
  div.className = 'vitem active';
  div.innerHTML = `<div class="dot" style="background:var(--red)"></div>
    <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${video.substring(0,30)}</span>`;
  div.onclick = () => openInEditor(video, thumb || '');
  list.prepend(div);
}

// ── Editor ────────────────────────────────────────────────
let editorVideo = null, editorThumb = null;
let selStart = null, selEnd = null;
let tlDragging = false, tlDragMode = null, tlDragStart = 0;

function openInEditor(videoFile, thumbFile) {
  editorVideo = videoFile;
  editorThumb = thumbFile;
  showPanel('editor');

  document.getElementById('editor-empty').style.display   = 'none';
  document.getElementById('editor-content').style.display = 'flex';

  const vid = document.getElementById('editor-video');
  vid.src = '/video/' + videoFile;

  const dl = document.getElementById('dl-link');
  dl.href = '/download/' + videoFile;
  dl.download = videoFile;

  const dlT = document.getElementById('dl-thumb-link');
  if (thumbFile) {
    dlT.href = '/thumb/' + thumbFile;
    dlT.download = thumbFile;
    dlT.style.display = '';
  } else {
    dlT.style.display = 'none';
  }

  const tp = document.getElementById('thumb-preview');
  tp.innerHTML = thumbFile
    ? `<img src="/thumb/${thumbFile}" alt="thumbnail">`
    : `<div class="no-thumb">No thumbnail</div>`;

  selStart = selEnd = null;
  document.getElementById('tl-sel').style.display = 'none';
  document.getElementById('regen-btn').disabled = true;
  document.getElementById('regen-btn').textContent = 'Select a segment first';

  vid.addEventListener('timeupdate', updatePlayhead);
  vid.addEventListener('loadedmetadata', () => {
    document.getElementById('tl-dur').textContent = fmtTime(vid.duration);
  });
}

function fmtTime(s) {
  const m = Math.floor(s/60), sec = Math.floor(s%60);
  return m + ':' + String(sec).padStart(2,'0');
}

function tlPct(e) {
  const tl  = document.getElementById('timeline');
  const rect = tl.getBoundingClientRect();
  return Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
}

function tlDown(e) {
  if (e.target.classList.contains('tl-handle')) return;
  tlDragging  = true;
  tlDragMode  = 'new';
  tlDragStart = tlPct(e);
  selStart = selEnd = tlDragStart;
  drawSel();
}
function tlMove(e) {
  const vid = document.getElementById('editor-video');
  const dur  = vid.duration || 0;
  const pct  = tlPct(e);
  document.getElementById('cursor-time').textContent = fmtTime(pct * dur);

  if (!tlDragging) return;
  if (tlDragMode === 'new') {
    selStart = Math.min(tlDragStart, pct);
    selEnd   = Math.max(tlDragStart, pct);
  } else if (tlDragMode === 'left')  { selStart = Math.min(pct, selEnd   - 0.01); }
  else if (tlDragMode === 'right')   { selEnd   = Math.max(pct, selStart + 0.01); }
  drawSel();
}
function tlUp(e) {
  tlDragging = false;
  if (selEnd - selStart > 0.01) onSelectionDone();
}
function handleDown(e, side) {
  e.stopPropagation();
  tlDragging = true;
  tlDragMode = side;
}

function drawSel() {
  const sel = document.getElementById('tl-sel');
  if (selStart === null) { sel.style.display='none'; return; }
  sel.style.display  = 'block';
  sel.style.left     = (selStart * 100) + '%';
  sel.style.width    = ((selEnd - selStart) * 100) + '%';
  const vid = document.getElementById('editor-video');
  const dur  = vid.duration || 0;
  document.getElementById('sel-start-lbl').textContent = fmtTime(selStart * dur);
  document.getElementById('sel-end-lbl').textContent   = fmtTime(selEnd   * dur);
  document.getElementById('sel-len-lbl').textContent   = fmtTime((selEnd - selStart) * dur);
}

function onSelectionDone() {
  document.getElementById('regen-btn').disabled = false;
  document.getElementById('regen-btn').textContent = 'Regenerate Selected Segment';
}

function updatePlayhead() {
  const vid = document.getElementById('editor-video');
  if (!vid.duration) return;
  const pct = vid.currentTime / vid.duration;
  document.getElementById('tl-playhead').style.left = (pct*100) + '%';
  document.getElementById('tl-progress').style.width = (pct*100) + '%';
}

function showRegenFields() {
  document.getElementById('regen-fields').classList.toggle('show');
}

function regenSegment() {
  if (selStart === null || selEnd === null) return;
  const vid   = document.getElementById('editor-video');
  const dur   = vid.duration || 0;
  const start = selStart * dur;
  const end   = selEnd   * dur;
  const topic = document.getElementById('regen-topic').value.trim()
              || editorVideo.replace('.mp4','').replace('video_','');

  setStatusBox('regen-status', 'Regenerating segment ' + fmtTime(start) + ' – ' + fmtTime(end) + '...', 'info');
  document.querySelectorAll('.btn-warning,.btn-primary').forEach(b => b.disabled = true);

  fetch('/regen_segment', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({video: editorVideo, start, end, topic})
  })
  .then(r => r.json())
  .then(d => {
    document.querySelectorAll('.btn-warning,.btn-primary').forEach(b => b.disabled = false);
    if (d.ok) {
      setStatusBox('regen-status', 'Done! Reloading edited video...', 'ok');
      openInEditor(d.new_video, editorThumb);
    } else {
      setStatusBox('regen-status', 'Error: ' + d.error, 'err');
    }
  });
}

function regenThumb() {
  setStatusBox('thumb-status','Regenerating thumbnail...','info');
  fetch('/regen_thumb', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({video: editorVideo})
  })
  .then(r=>r.json())
  .then(d => {
    if (d.ok) {
      editorThumb = d.thumb;
      document.getElementById('thumb-preview').innerHTML =
        `<img src="/thumb/${d.thumb}?t=${Date.now()}" alt="thumbnail">`;
      setStatusBox('thumb-status','New thumbnail ready!','ok');
    } else {
      setStatusBox('thumb-status','Error: ' + d.error,'err');
    }
  });
}

function uploadYT() {
  if (!confirm('Upload "' + editorVideo + '" to YouTube as UNLISTED?\n\nYou can make it public from YouTube Studio later.')) return;
  const btn = document.getElementById('yt-btn');
  btn.disabled = true; btn.textContent = 'Uploading...';
  setStatusBox('upload-status','Uploading to YouTube — please wait...','info');

  fetch('/upload', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({video: editorVideo, thumb: editorThumb})
  })
  .then(r=>r.json())
  .then(d => {
    btn.disabled = false; btn.textContent = 'Upload to YouTube (Unlisted)';
    if (d.ok) {
      setStatusBox('upload-status',
        'Uploaded! youtube.com/watch?v=' + d.video_id +
        '\nGo to YouTube Studio to make it public.','ok');
    } else {
      setStatusBox('upload-status','Upload failed: ' + d.error,'err');
    }
  });
}

function deleteVideo(filename, btn) {
  if (!confirm('Delete this video?')) return;
  fetch('/delete',{method:'POST',headers:{'Content-Type':'application/json'},
                   body:JSON.stringify({video:filename})})
  .then(r=>r.json()).then(d=>{
    if (d.ok) btn.closest('.lib-card').remove();
  });
}

function setStatusBox(id, msg, type) {
  const el = document.getElementById(id);
  el.textContent = msg;
  el.className   = 'status-box ' + type;
}

// ── Content Approval ─────────────────────────────────────
let _approvalJobId = null;

function showApprovalPanel(sentences, lang, jobId) {
  _approvalJobId = jobId;
  const panel = document.getElementById('approval-panel');
  const list  = document.getElementById('sentence-list');
  const badge = document.getElementById('approval-lang');

  badge.textContent = lang === 'hi' ? '🇮🇳 Hindi' : '🇺🇸 English';
  list.innerHTML = '';

  sentences.forEach((s, i) => addSentenceRow(s, i + 1));
  panel.classList.add('show');
  panel.scrollIntoView({behavior:'smooth', block:'nearest'});
}

function addSentenceRow(text, num) {
  const list = document.getElementById('sentence-list');
  const row  = document.createElement('div');
  row.className = 'sentence-row';
  const idx = list.children.length + 1;
  row.innerHTML = `
    <span class="sentence-num">${num || idx}</span>
    <textarea class="sentence-input" rows="2">${text || ''}</textarea>
    <button class="sentence-del" onclick="this.parentElement.remove(); renumber()">✕</button>
  `;
  list.appendChild(row);
}

function addSentence() {
  addSentenceRow('', 0);
  renumber();
  // scroll to bottom of list
  const list = document.getElementById('sentence-list');
  list.scrollTop = list.scrollHeight;
  list.lastElementChild.querySelector('textarea').focus();
}

function renumber() {
  document.querySelectorAll('.sentence-num').forEach((el, i) => {
    el.textContent = i + 1;
  });
}

// ── Copy All / Paste & Rebuild ────────────────────────────
function getCurrentSentences() {
  return Array.from(document.querySelectorAll('.sentence-input'))
              .map(t => t.value.trim())
              .filter(s => s.length > 0);
}

function copyAllSentences() {
  const text = getCurrentSentences().join('\n');
  const btn  = document.getElementById('btn-copy-all');
  const done = () => {
    btn.textContent = '✅ Copied!';
    btn.classList.add('copied');
    setTimeout(() => { btn.textContent = '📋 Copy All'; btn.classList.remove('copied'); }, 1400);
  };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(done).catch(() => fallbackCopy(text, done));
  } else {
    fallbackCopy(text, done);
  }
}

function fallbackCopy(text, done) {
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.position = 'fixed';
  ta.style.opacity = '0';
  document.body.appendChild(ta);
  ta.select();
  try { document.execCommand('copy'); } catch (e) {}
  document.body.removeChild(ta);
  done();
}

function toggleBulkEdit() {
  const bulkTA   = document.getElementById('bulk-textarea');
  const hint     = document.getElementById('bulk-hint');
  const list     = document.getElementById('sentence-list');
  const addBtn   = document.getElementById('btn-add-line');
  const rebuild  = document.getElementById('btn-rebuild');
  const toggle   = document.getElementById('btn-paste-toggle');

  const opening = !bulkTA.classList.contains('show');
  if (opening) {
    bulkTA.value = getCurrentSentences().join('\n');
    bulkTA.classList.add('show');
    hint.classList.add('show');
    list.classList.add('hide');
    addBtn.style.display = 'none';
    rebuild.style.display = '';
    toggle.textContent = '✕ Cancel';
    bulkTA.focus();
  } else {
    bulkTA.classList.remove('show');
    hint.classList.remove('show');
    list.classList.remove('hide');
    addBtn.style.display = '';
    rebuild.style.display = 'none';
    toggle.textContent = '📥 Paste & Rebuild';
  }
}

function splitIntoSentences(text) {
  const lines = text.split('\n').map(l => l.trim()).filter(l => l.length > 0);
  if (lines.length > 1) return lines;          // one sentence per line, as-is
  const raw = text.trim();
  if (!raw) return [];
  // single blob — split on sentence terminators (English + Hindi danda)
  const matches = raw.match(/[^.!?।]+[.!?।]+(\s+|$)/g);
  if (matches && matches.length > 0) {
    return matches.map(s => s.trim()).filter(s => s.length > 0);
  }
  return [raw];                                 // no terminators found — one line
}

function rebuildFromBulk() {
  const bulkTA = document.getElementById('bulk-textarea');
  const sentences = splitIntoSentences(bulkTA.value);
  if (sentences.length === 0) {
    alert('Nothing to rebuild — paste some text first.');
    return;
  }
  const list = document.getElementById('sentence-list');
  list.innerHTML = '';
  sentences.forEach((s, i) => addSentenceRow(s, i + 1));
  toggleBulkEdit();  // switch back to row view
}

function approveSentences() {
  const inputs    = document.querySelectorAll('.sentence-input');
  const sentences = Array.from(inputs)
                         .map(t => t.value.trim())
                         .filter(s => s.length > 0);

  if (sentences.length === 0) {
    alert('Please keep at least 1 sentence.');
    return;
  }

  document.getElementById('approval-panel').classList.remove('show');
  setPbar(30, `Approved ${sentences.length} sentences — generating voice...`);
  setStep(2);

  fetch('/approve/' + _approvalJobId, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({sentences})
  });
}

// ── Patch pollJob to handle waiting_approval status ───────
const _origPollJob = pollJob;
function pollJob(jobId) {
  const es = new EventSource('/progress/' + jobId);
  es.onmessage = e => {
    const d = JSON.parse(e.data);
    if (d.message) appendLog(d.message);
    if (d.progress) setPbar(d.progress, d.message || '');
    if (d.step !== undefined) setStep(d.step);

    if (d.status === 'waiting_approval') {
      es.close();
      setPbar(29, 'Waiting for your approval...');
      showApprovalPanel(d.sentences || [], d.lang || 'en', jobId);
      // restart SSE after approval — approval button will re-open connection
      document.querySelector('.btn-approve').addEventListener('click', () => {
        setTimeout(() => {
          const es2 = new EventSource('/progress/' + jobId);
          es2.onmessage = e2 => {
            const d2 = JSON.parse(e2.data);
            if (d2.message) appendLog(d2.message);
            if (d2.progress) setPbar(d2.progress, d2.message || '');
            if (d2.step !== undefined) setStep(d2.step);
            if (d2.status === 'done')  { es2.close(); onGenerateDone(d2); }
            if (d2.status === 'error') { es2.close(); showGenError(d2.error || 'Failed'); }
          };
        }, 500);
      }, {once: true});
    } else if (d.status === 'done')  { es.close(); onGenerateDone(d); }
    else if (d.status === 'error')   { es.close(); showGenError(d.error || 'Failed'); }
  };
  es.onerror = () => { es.close(); };
}

// click on timeline jumps playhead
document.addEventListener('click', e => {
  if (e.target.id === 'timeline' || e.target.id === 'tl-progress') {
    const vid = document.getElementById('editor-video');
    if (!vid.duration) return;
    const pct = tlPct(e);
    vid.currentTime = pct * vid.duration;
  }
});
document.addEventListener('mouseup', () => { if (tlDragging) tlUp({});  });
</script>
</body>
</html>
"""

# ── Video pipeline in background thread with SSE progress ────────────────────
def _run_pipeline(job_id, url, topic, minutes):
    q = _jobs[job_id]['queue']

    def emit(step, pct, msg, status='running', **kw):
        q.put(json.dumps(dict(step=step, progress=pct, message=msg, status=status, **kw)))

    try:
        emit(0, 5,  '1/6 Extracting article...')
        from extract_article import extract_article
        title, text = extract_article(url)
        emit(0, 12, f'  Title: {title}')

        emit(1, 18, '2/6 Detecting language and summarizing...')
        from summarize_text import summarize, get_sentences
        from generate_voice import detect_language
        lang = detect_language(text)
        emit(1, 22, f'  Language: {"Hindi" if lang=="hi" else "English"}')
        # cap at 25 sentences max — enough for 6-7 min, avoids very long voice gen
        desired = min(25, max(8, int((minutes * 60) / 8)))
        summary   = summarize(text, num_sentences=desired)
        sentences = get_sentences(summary)
        emit(1, 28, f'  {len(sentences)} sentences')

        # ── PAUSE: send sentences to UI for review/edit ──────────────────
        emit(1, 29, 'Waiting for your approval...', status='waiting_approval',
             sentences=sentences, lang=lang)

        # block until user clicks Approve
        job = _jobs[job_id]
        job['approval_event'].wait()   # waits indefinitely — no timeout

        # use edited sentences if user changed anything
        sentences = job['approved_sentences'] or sentences
        emit(2, 30, f'Approved! {len(sentences)} sentences — generating voice...')

        emit(2, 30, f'3/6 Generating voice for {len(sentences)} sentences...')
        from generate_voice import generate_voice_segments, combine_audio

        def voice_progress(i, total, preview):
            pct = 30 + int((i / total) * 22)
            emit(2, pct, f'  Voice {i}/{total}: {preview}')

        voice_paths, durations = generate_voice_segments(
            sentences, lang=lang, progress_cb=voice_progress
        )
        audio_path = combine_audio(voice_paths, out_path='voice_combined.mp3')
        emit(2, 52, f'  Voice done — {sum(durations):.0f}s audio')

        emit(3, 54, '4/6 Fetching images...')
        from fetch_images import get_images
        images = get_images(url, topic or title, target=max(len(sentences), 20))
        emit(3, 64, f'  Got {len(images)} images')

        n = min(len(images), len(sentences))
        images    = images[:n]
        captions  = sentences[:n]
        durations = durations[:n]

        emit(4, 66, '5/6 Building video...')
        from build_video import build_video
        import datetime
        date_str = datetime.datetime.now().strftime('%Y-%m-%d')
        slug = ''.join(c if c.isalnum() else '_' for c in title)[:40].strip('_')
        out_path = os.path.join(DOWNLOADS, f'video_{date_str}_{slug}.mp4')
        build_video(images, captions, durations, audio_path, title,
                    out_path=out_path, lang=lang)
        emit(4, 90, '  Video saved')

        emit(5, 92, '6/6 Creating thumbnail...')
        from make_thumbnail import make_thumbnail
        thumb_path = os.path.join(DOWNLOADS, f'thumb_{date_str}_{slug}.jpg')
        make_thumbnail(images[0], title, out_path=thumb_path)
        emit(5, 100, 'Done!', status='done',
             video=os.path.basename(out_path),
             thumb=os.path.basename(thumb_path),
             title=title, lang=lang)

    except Exception as e:
        q.put(json.dumps(dict(status='error', error=str(e), progress=0, message=str(e))))


@app.route('/')
def index():
    videos = get_videos()
    return render_template_string(HTML, videos=videos, folder=DOWNLOADS)


@app.route('/generate', methods=['POST'])
def generate():
    data    = request.get_json()
    job_id  = str(uuid.uuid4())
    _jobs[job_id] = {
        'queue': queue.Queue(),
        'status': 'running',
        'approval_event': threading.Event(),
        'approved_sentences': None,
    }
    t = threading.Thread(target=_run_pipeline,
                         args=(job_id, data['url'], data.get('topic',''), data.get('minutes',6)),
                         daemon=True)
    t.start()
    return jsonify(job_id=job_id)

@app.route('/approve/<job_id>', methods=['POST'])
def approve_content(job_id):
    data = request.get_json()
    job  = _jobs.get(job_id)
    if not job:
        return jsonify(ok=False, error='Job not found')
    job['approved_sentences'] = data.get('sentences', [])
    job['approval_event'].set()
    return jsonify(ok=True)


@app.route('/progress/<job_id>')
def progress(job_id):
    def stream():
        q = _jobs.get(job_id, {}).get('queue')
        if not q:
            yield 'data: {"status":"error","error":"job not found"}\n\n'
            return
        while True:
            try:
                msg = q.get(timeout=8)   # short timeout so we can send keepalives
                yield f'data: {msg}\n\n'
                d = json.loads(msg)
                if d.get('status') in ('done','error'):
                    break
            except Exception:
                # send a keepalive comment so the browser doesnt disconnect
                yield ': keepalive\n\n'
    return Response(stream(), mimetype='text/event-stream',
                    headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})


@app.route('/regen_segment', methods=['POST'])
def regen_segment():
    data = request.get_json()
    try:
        from editor import regenerate_segment
        new_path = regenerate_segment(
            os.path.join(DOWNLOADS, data['video']),
            float(data['start']), float(data['end']),
            data.get('topic','news'), data.get('lang','en')
        )
        # copy to downloads
        import shutil
        dest = os.path.join(DOWNLOADS, os.path.basename(new_path))
        shutil.copy(new_path, dest)
        return jsonify(ok=True, new_video=os.path.basename(dest))
    except Exception as e:
        return jsonify(ok=False, error=str(e))


@app.route('/regen_thumb', methods=['POST'])
def regen_thumb():
    data = request.get_json()
    try:
        from make_thumbnail import make_thumbnail
        video_file = data['video']
        # find first image in images/ folder or use black bg
        image = next(
            (os.path.join('images', f) for f in os.listdir('images')
             if f.endswith('.jpg')), None
        ) if os.path.exists('images') else None
        title = video_file.replace('.mp4','').replace('video_','').replace('_',' ')
        thumb_name = video_file.replace('video_','thumb_').replace('.mp4','.jpg')
        thumb_path = os.path.join(DOWNLOADS, thumb_name)
        make_thumbnail(image or 'black', title, out_path=thumb_path)
        return jsonify(ok=True, thumb=thumb_name)
    except Exception as e:
        return jsonify(ok=False, error=str(e))


@app.route('/upload', methods=['POST'])
def upload():
    data = request.get_json()
    try:
        from upload_youtube import upload_video as yt_upload
        video_file = data['video']
        thumb_file = data.get('thumb','')
        title = video_file.replace('.mp4','').replace('video_','').replace('_',' ')
        parts = video_file.replace('.mp4','').split('_', 2)
        if len(parts) > 2:
            title = parts[2].replace('_',' ')
        video_id = yt_upload(
            os.path.join(DOWNLOADS, video_file),
            title=title,
            thumbnail_path=os.path.join(DOWNLOADS, thumb_file) if thumb_file else None,
            privacy='unlisted',
        )
        return jsonify(ok=True, video_id=video_id)
    except Exception as e:
        return jsonify(ok=False, error=str(e))


@app.route('/video/<path:f>')
def serve_video(f):
    return send_file(os.path.join(DOWNLOADS, f), mimetype='video/mp4')

@app.route('/thumb/<path:f>')
def serve_thumb(f):
    return send_file(os.path.join(DOWNLOADS, f), mimetype='image/jpeg')

@app.route('/download/<path:f>')
def download_file(f):
    return send_file(os.path.join(DOWNLOADS, f), as_attachment=True, download_name=f)

@app.route('/delete', methods=['POST'])
def delete_video():
    data = request.get_json()
    f    = data.get('video','')
    try:
        for name in [f, f.replace('video_','thumb_').replace('.mp4','.jpg')]:
            p = os.path.join(DOWNLOADS, name)
            if os.path.exists(p): os.remove(p)
        return jsonify(ok=True)
    except Exception as e:
        return jsonify(ok=False, error=str(e))


def get_videos():
    if not os.path.exists(DOWNLOADS): return []
    videos = []
    for f in sorted(os.listdir(DOWNLOADS), reverse=True):
        if not f.endswith('.mp4'): continue
        tn = f.replace('.mp4','.jpg').replace('video_','thumb_')
        sz = os.path.getsize(os.path.join(DOWNLOADS, f))
        parts = f.split('_')
        videos.append(dict(
            video=f, thumb=tn if os.path.exists(os.path.join(DOWNLOADS,tn)) else None,
            name=f, size=f'{sz/1024/1024:.1f} MB',
            date=parts[1] if len(parts)>1 else ''
        ))
    return videos


if __name__ == '__main__':
    import webbrowser, threading
    print('\n  Real News Studio')
    print(f'  Videos: {DOWNLOADS}')
    print('  Opening: http://localhost:5000\n')
    threading.Timer(1.2, lambda: webbrowser.open('http://localhost:5000')).start()
    app.run(debug=False, port=5000, threaded=True)
