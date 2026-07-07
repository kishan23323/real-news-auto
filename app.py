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
    .btn-approve-templates { flex:2; padding:12px; background:#4caf50; color:#fff;
                   border:none; border-radius:7px; font-size:14px;
                   font-weight:bold; cursor:pointer; transition:background 0.2s; }
    .btn-approve-templates:hover { background:#66bb6a; }

    .tpl-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
                gap:16px; margin:14px 0; }
    .tpl-card { background:#181818; border:2px solid #2a2a2a; border-radius:10px;
                padding:12px; transition:border-color 0.15s; }
    .tpl-card.checked { border-color:#4caf50; }
    .tpl-card-head { display:flex; align-items:center; gap:8px; margin-bottom:10px;
                     cursor:pointer; }
    .tpl-card-head input { width:16px; height:16px; }
    .tpl-card-head strong { font-size:13px; }
    .tpl-card-head span { color:var(--sub); font-size:11px; }
    .tpl-preview-box { width:100%; display:flex; align-items:center; justify-content:center;
                        background:#0d0d0d; border-radius:6px; overflow:hidden; }
    .tpl-preview-box svg { max-width:100%; max-height:220px; display:block; }

    .tpl-style-panel { background:#141414; border:1px solid #2a2a2a; border-radius:10px;
                        padding:14px; margin-bottom:14px; }
    .tpl-style-panel h4 { margin:0 0 10px 0; font-size:13px; color:var(--sub); }
    .tpl-style-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
                       gap:14px; }
    .tpl-ctrl { display:flex; flex-direction:column; gap:6px; font-size:12px; color:var(--sub); }
    .tpl-ctrl select, .tpl-ctrl input[type=color] { padding:6px; border-radius:6px;
        border:1px solid #333; background:#0d0d0d; color:#fff; }
    .tpl-ctrl input[type=range] { width:100%; }
    .tpl-ctrl span { color:#fff; font-weight:bold; }
    .btn-add-sentence { flex:1; padding:12px; background:#1a3a1a; color:#4caf50;
                        border:1px solid #4caf50; border-radius:7px; font-size:13px;
                        font-weight:bold; cursor:pointer; }
    .btn-add-sentence:hover { background:#2a4a2a; }

    /* ── Image review panel ──────────────────────────────────── */
    .btn-img-tool { padding:9px 16px; border-radius:6px; font-size:12px;
                    font-weight:bold; cursor:pointer; transition:all 0.15s; }
    .btn-add-img-search { background:#1a1a3a; color:#8888ff; border:1px solid #4444aa; }
    .btn-add-img-search:hover { background:#2a2a4a; }
    .btn-add-img-file { background:#1a2a1a; color:#4caf50; border:1px solid #2a6a2a; }
    .btn-add-img-file:hover { background:#2a3a2a; }
    .btn-approve-images { background:#cc1414; color:#fff; border:none;
                          border-radius:7px; font-size:14px; font-weight:bold;
                          cursor:pointer; transition:background 0.2s; }
    .btn-approve-images:hover { background:#ee2020; }
    .img-grid { display:grid;
                grid-template-columns:repeat(auto-fill,minmax(220px,1fr));
                gap:14px; }
    .img-grid.horizontal { display:flex; flex-direction:row; overflow-x:auto;
                            overflow-y:hidden; gap:14px; padding-bottom:8px; }
    .img-grid.horizontal .img-card { flex:0 0 220px; }
    .img-card { background:#1a1a1a; border:2px solid #2a2a2a; border-radius:10px;
                overflow:hidden; position:relative; transition:all 0.2s;
                display:flex; flex-direction:column; }
    .img-card:hover { border-color:var(--red); transform:translateY(-2px);
                      box-shadow:0 6px 20px rgba(204,20,20,0.2); }
    .img-card-thumb { position:relative; cursor:grab; flex-shrink:0; }
    .img-card-thumb img { width:100%; height:150px; object-fit:cover; display:block; }
    .img-card-thumb .img-card-num {
      position:absolute; top:8px; left:8px;
      background:rgba(0,0,0,0.8); color:#fff;
      font-size:11px; font-weight:bold; padding:3px 9px; border-radius:12px; }
    .img-card-thumb .img-overlay {
      position:absolute; inset:0; background:rgba(0,0,0,0);
      display:flex; align-items:center; justify-content:center;
      transition:background 0.2s; }
    .img-card-thumb:hover .img-overlay { background:rgba(0,0,0,0.35); }
    .img-overlay-text { color:#fff; font-size:11px; opacity:0;
                        transition:opacity 0.2s; }
    .img-card-thumb:hover .img-overlay-text { opacity:1; }
    .img-card-btns { display:grid; grid-template-columns:1fr 1fr 1fr;
                     gap:4px; padding:8px; background:#111; }
    .btn-img-action { padding:7px 4px; border:none; border-radius:6px;
                      font-size:11px; font-weight:bold; cursor:pointer;
                      transition:all 0.15s; text-align:center; }
    .btn-img-regen   { background:#1a1a3a; color:#8888ff; border:1px solid #3a3a6a; }
    .btn-img-regen:hover   { background:#2a2a5a; }
    .btn-img-replace { background:#1a2a1a; color:#4caf50; border:1px solid #2a5a2a; }
    .btn-img-replace:hover { background:#2a4a2a; }
    .btn-img-del     { background:#2a1a1a; color:#cc4444; border:1px solid #5a2a2a; }
    .btn-img-del:hover     { background:#4a1a1a; }
    .img-loading { opacity:0.4; pointer-events:none; }
    .img-add-search { display:none; gap:8px; }
    .img-add-search.show { display:flex; }
    .img-add-search input { flex:1; padding:9px 13px; background:#111;
                            border:1px solid #3a3a3a; border-radius:7px;
                            color:#fff; font-size:13px; outline:none; }
    .img-add-search input:focus { border-color:var(--red); }
    .img-add-search button { padding:9px 18px; background:var(--red); color:#fff;
                              border:none; border-radius:7px; cursor:pointer;
                              font-size:13px; font-weight:bold; }

    /* ── Audio review panel ──────────────────────────────────── */
    .audio-panel { background:#0d0d1a; border:1px solid #3a3a8a;
                   border-radius:10px; padding:20px; margin-top:18px; display:none; }
    .audio-panel.show { display:block; }
    .audio-panel h3 { font-size:15px; color:#8888ff; margin-bottom:4px; }
    .audio-panel p  { font-size:12px; color:#888; margin-bottom:14px; }
    .audio-row { display:flex; align-items:center; gap:10px; padding:10px 12px;
                 background:#111; border:1px solid #2a2a2a; border-radius:8px;
                 margin-bottom:8px; flex-wrap:wrap; }
    .audio-num  { font-size:11px; color:#555; min-width:24px; text-align:right; flex-shrink:0; }
    .audio-text { flex:1; font-size:12px; color:#ccc; min-width:160px; line-height:1.4; }
    .audio-dur  { font-size:11px; color:#555; min-width:38px; text-align:right; flex-shrink:0; }
    .audio-player { width:200px; height:32px; flex-shrink:0; }
    .audio-actions { display:flex; gap:6px; flex-shrink:0; }
    .btn-audio { padding:5px 10px; border:none; border-radius:5px; font-size:11px;
                 font-weight:bold; cursor:pointer; transition:all 0.15s; white-space:nowrap; }
    .btn-regen-audio { background:#1a1a3a; color:#8888ff; border:1px solid #4444aa; }
    .btn-regen-audio:hover { background:#2a2a4a; }
    .btn-replace-audio { background:#1a2a1a; color:#4caf50; border:1px solid #2a6a2a; }
    .btn-replace-audio:hover { background:#2a3a2a; }
    .btn-approve-audio { width:100%; padding:12px; background:#4444cc; color:#fff;
                         border:none; border-radius:7px; font-size:14px;
                         font-weight:bold; cursor:pointer; margin-top:8px;
                         transition:background 0.2s; }
    .btn-approve-audio:hover { background:#6666ee; }
    .audio-list { max-height:380px; overflow-y:auto; margin-bottom:10px; }
    .file-input-hidden { display:none; }

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
    <div class="nav-item" onclick="showPanel('templates')" id="nav-templates">
      <span class="ico">🎨</span> Templates
    </div>
    <div class="nav-item" onclick="showPanel('images')" id="nav-images" style="display:none">
      <span class="ico">🖼️</span> Images
      <span id="img-count-badge" style="margin-left:auto;background:var(--red);
            color:#fff;font-size:10px;padding:1px 6px;border-radius:8px;"></span>
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

        <!-- Audio review panel — shows after voice generation -->
        <div class="audio-panel" id="audio-panel">
          <h3>🎙️ Review Audio</h3>
          <p>Listen to each sentence. Re-generate or replace any clip, then approve to continue building the video.</p>
          <div class="audio-list" id="audio-list"></div>
          <button class="btn-approve-audio" onclick="approveAudio()">
            ✅ Approve All Audio — Continue to Video
          </button>
        </div>

        <!-- Template Studio — shows after image approval -->
        <div class="approval-panel" id="template-panel">
          <h3>🎬 Template Studio</h3>
          <p>Pick one or more formats to build, and customize how they look. The previews update live.</p>

          <div class="tpl-grid" id="template-grid"></div>

          <div class="tpl-style-panel">
            <h4>Customize style (applies to every template you build)</h4>
            <div class="tpl-style-grid">
              <label class="tpl-ctrl">
                Logo position
                <select id="style-logo-position">
                  <option value="top-right">Top Right</option>
                  <option value="top-left">Top Left</option>
                </select>
              </label>
              <label class="tpl-ctrl">
                Logo shape
                <select id="style-logo-shape">
                  <option value="circle">Circle</option>
                  <option value="square">Square</option>
                </select>
              </label>
              <label class="tpl-ctrl">
                Top banner color
                <input type="color" id="style-banner-color">
              </label>
              <label class="tpl-ctrl">
                Bottom banner color
                <input type="color" id="style-bottom-color">
              </label>
              <label class="tpl-ctrl">
                Frame / border color
                <input type="color" id="style-frame-color">
              </label>
              <label class="tpl-ctrl">
                Frame corner radius <span id="val-container-radius">36px</span>
                <input type="range" id="style-container-radius" min="0" max="80" step="2">
              </label>
              <label class="tpl-ctrl">
                Image corner radius <span id="val-corner-radius">28px</span>
                <input type="range" id="style-corner-radius" min="0" max="60" step="2">
              </label>
              <label class="tpl-ctrl">
                "BREAKING NEWS" size <span id="val-headline-size">64px</span>
                <input type="range" id="style-headline-size" min="30" max="90" step="2">
              </label>
              <label class="tpl-ctrl">
                Caption text size <span id="val-caption-size">30px</span>
                <input type="range" id="style-caption-size" min="18" max="44" step="1">
              </label>
            </div>
          </div>

          <div class="approval-actions">
            <button class="btn-approve-templates" onclick="approveTemplates()">
              ✅ Apply &amp; Build Video
            </button>
          </div>
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

    <!-- ── IMAGES PANEL ────────────────────────────────── -->
    <div class="panel" id="panel-images">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:18px;flex-shrink:0;">
        <div>
          <h2 style="font-size:18px;margin-bottom:4px;">🖼️ Image Review</h2>
          <p style="font-size:12px;color:var(--sub);">
            Review, replace, regenerate, reorder or add images before the video is built.
            Drag cards to reorder.
          </p>
        </div>
        <button class="btn-approve-images" id="approve-images-btn"
                onclick="approveImages()"
                style="width:auto;padding:11px 24px;font-size:13px;">
          ✅ Approve &amp; Continue
        </button>
      </div>

      <!-- toolbar -->
      <div style="display:flex;gap:10px;margin-bottom:14px;flex-shrink:0;flex-wrap:wrap;">
        <button class="btn-img-tool btn-add-img-search" onclick="toggleImgSearch()">
          + Search &amp; Add
        </button>
        <button class="btn-img-tool btn-add-img-file"
                onclick="document.getElementById('img-add-file').click()">
          + Upload from PC
        </button>
        <input type="file" id="img-add-file" accept="image/*"
               style="display:none" onchange="addImageFile(this)">
        <span style="flex:1"></span>
        <button class="btn-img-tool" id="btn-img-layout" onclick="toggleImgLayout()"
                style="background:#1a1a2a;color:#aaa;border:1px solid #3a3a3a;">
          ☰ Horizontal
        </button>
        <span id="img-panel-count" style="font-size:12px;color:var(--sub);align-self:center;"></span>
      </div>

      <!-- search bar -->
      <div class="img-add-search" id="img-add-search" style="margin-bottom:12px;">
        <input type="text" id="img-search-q"
               placeholder="e.g. FIFA World Cup stadium crowd"
               onkeydown="if(event.key==='Enter') addImageSearch()">
        <button onclick="addImageSearch()">Search &amp; Add</button>
      </div>

      <!-- image grid — scrollable -->
      <div class="img-grid" id="img-grid"
           style="max-height:none;flex:1;overflow-y:auto;align-content:start;">
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

    <!-- ── TEMPLATES PANEL (standalone browser/editor) ─────── -->
    <div class="panel" id="panel-templates">
      <h2 style="margin-top:0;">🎨 Templates</h2>
      <p style="color:var(--sub);">
        Browse every format, customize the look, and save it as your default —
        it'll be pre-filled automatically the next time you generate a video.
      </p>
      <div class="tpl-grid" id="std-template-grid"></div>
      <div class="tpl-style-panel">
        <h4>Customize style</h4>
        <div class="tpl-style-grid">
          <label class="tpl-ctrl">
            Logo position
            <select id="std-style-logo-position">
              <option value="top-right">Top Right</option>
              <option value="top-left">Top Left</option>
            </select>
          </label>
          <label class="tpl-ctrl">
            Logo shape
            <select id="std-style-logo-shape">
              <option value="circle">Circle</option>
              <option value="square">Square</option>
            </select>
          </label>
          <label class="tpl-ctrl">
            Top banner color
            <input type="color" id="std-style-banner-color">
          </label>
          <label class="tpl-ctrl">
            Bottom banner color
            <input type="color" id="std-style-bottom-color">
          </label>
          <label class="tpl-ctrl">
            Frame / border color
            <input type="color" id="std-style-frame-color">
          </label>
          <label class="tpl-ctrl">
            Frame corner radius <span id="std-val-container-radius">36px</span>
            <input type="range" id="std-style-container-radius" min="0" max="80" step="2">
          </label>
          <label class="tpl-ctrl">
            Image corner radius <span id="std-val-corner-radius">28px</span>
            <input type="range" id="std-style-corner-radius" min="0" max="60" step="2">
          </label>
          <label class="tpl-ctrl">
            "BREAKING NEWS" size <span id="std-val-headline-size">64px</span>
            <input type="range" id="std-style-headline-size" min="30" max="90" step="2">
          </label>
          <label class="tpl-ctrl">
            Caption text size <span id="std-val-caption-size">30px</span>
            <input type="range" id="std-style-caption-size" min="18" max="44" step="1">
          </label>
        </div>
      </div>
      <div class="approval-actions">
        <button class="btn-approve-templates" onclick="saveStandaloneDefaults()">
          💾 Save as My Default
        </button>
        <button class="btn-add-sentence" onclick="resetStandaloneDefaults()">
          ↺ Reset to Built-in Defaults
        </button>
      </div>
      <p id="std-save-confirm" style="color:#4caf50;font-size:13px;display:none;margin-top:8px;">
        Saved — this will be pre-filled next time you generate a video.
      </p>
    </div>

  </div><!-- /main -->
</div><!-- /body -->

<script>
const ALL_TEMPLATES = {{ templates_json|safe }};
const SERVER_DEFAULT_STYLE = {{ default_style_json|safe }};

// ── Panel switching ───────────────────────────────────────
function showPanel(name) {
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('panel-' + name).classList.add('active');
  document.getElementById('nav-' + name).classList.add('active');
  if (name === 'templates') initStandaloneTemplates();
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

// (pollJob is defined once, further down, after the approval-panel
//  helper functions it depends on — see "pollJob: resumes itself..." below)

function onGenerateDone(d) {
  setPbar(100, 'Video ready!');
  setStep(5, true);
  document.getElementById('gen-btn').disabled = false;
  document.getElementById('gen-btn').textContent = '⚡ Generate Video';
  // auto-open in editor (primary/first selected template)
  openInEditor(d.video, d.thumb || '');
  showPanel('editor');
  // refresh sidebar
  addToSidebar(d.video, d.thumb);
  // if more than one template was built, the rest are saved alongside it —
  // they show up in the Library tab too.
  if (d.videos && d.videos.length > 1) {
    appendLog(`Also built: ${d.videos.filter(v => v !== d.video).join(', ')} (see Library tab)`);
  }
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

// ── Image Review ──────────────────────────────────────────
let _imageJobId = null;
let _imgOrder   = [];   // current ordered list of filenames

function toggleImgLayout() {
  const grid = document.getElementById('img-grid');
  const btn  = document.getElementById('btn-img-layout');
  const goingHorizontal = !grid.classList.contains('horizontal');
  grid.classList.toggle('horizontal', goingHorizontal);
  btn.textContent = goingHorizontal ? '☰ Horizontal' : '↕ Vertical';
}

function showImagePanel(images, jobId) {
  _imageJobId = jobId;
  _imgOrder   = images.map(i => i.filename);
  const grid  = document.getElementById('img-grid');
  grid.innerHTML = '';
  images.forEach(img => appendImgCard(img.index, img.filename, jobId));
  updateImgCount();
  // reveal Images tab in sidebar and switch to it
  const navEl = document.getElementById('nav-images');
  if (navEl) navEl.style.display = 'flex';
  showPanel('images');
}

function appendImgCard(idx, filename, jobId) {
  jobId = jobId || _imageJobId;
  const grid = document.getElementById('img-grid');
  const card = document.createElement('div');
  card.className = 'img-card';
  card.id = 'imgcard-' + idx;
  card.dataset.filename = filename;
  card.dataset.idx = idx;
  card.innerHTML = `
    <div class="img-card-thumb"
         draggable="true"
         ondragstart="imgDragStart(event,'imgcard-${idx}')"
         ondragover="event.preventDefault()"
         ondrop="imgDrop(event,'imgcard-${idx}')">
      <img src="/review_image/${jobId}/${filename}?t=${Date.now()}"
           alt="image ${idx+1}">
      <span class="img-card-num">${idx + 1}</span>
      <div class="img-overlay">
        <span class="img-overlay-text">Drag to reorder</span>
      </div>
    </div>
    <div class="img-card-btns">
      <button class="btn-img-action btn-img-regen"
              onclick="regenImg('imgcard-${idx}')">🔍 Search</button>
      <button class="btn-img-action btn-img-replace"
              onclick="replaceImgClick('imgcard-${idx}')">📁 Replace</button>
      <button class="btn-img-action btn-img-del"
              onclick="deleteImg('imgcard-${idx}')">🗑 Delete</button>
    </div>
    <input type="file" id="imgfile-${idx}" accept="image/*" style="display:none"
           onchange="replaceImgFile('imgcard-${idx}', this)">
  `;
  grid.appendChild(card);
}

function updateImgCount() {
  const n = document.querySelectorAll('.img-card').length;
  const badge = document.getElementById('img-count-badge');
  if (badge) badge.textContent = n;
  const counter = document.getElementById('img-panel-count');
  if (counter) counter.textContent = n + ' image' + (n!==1?'s':'') + ' — drag to reorder';
}

function renumberImgCards() {
  document.querySelectorAll('.img-card').forEach((c, i) => {
    const num = c.querySelector('.img-card-num');
    if (num) num.textContent = i + 1;
  });
  _imgOrder = Array.from(document.querySelectorAll('.img-card'))
                   .map(c => c.dataset.filename);
  updateImgCount();
}

// drag to reorder
let _dragCardId = null;
function imgDragStart(e, cardId) {
  _dragCardId = cardId;
  e.dataTransfer.effectAllowed = 'move';
}
function imgDrop(e, toCardId) {
  if (!_dragCardId || _dragCardId === toCardId) return;
  const grid = document.getElementById('img-grid');
  const from = document.getElementById(_dragCardId);
  const to   = document.getElementById(toCardId);
  if (!from || !to) return;
  grid.insertBefore(from, to);
  _dragCardId = null;
  renumberImgCards();
}

function _getCardAndIdx(cardId) {
  const card = document.getElementById(cardId);
  const idx  = parseInt(card.dataset.idx);
  return {card, idx};
}
function _setLoading(card, on) {
  card.classList.toggle('img-loading', on);
}

function regenImg(cardId) {
  const q = prompt('Search query for replacement image (e.g. "FIFA World Cup stadium crowd"):');
  if (q === null || !q.trim()) return;
  const {card, idx} = _getCardAndIdx(cardId);
  _setLoading(card, true);
  fetch('/regen_image/' + _imageJobId + '/' + idx, {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({query: q.trim()})
  })
  .then(r => r.json()).then(d => {
    _setLoading(card, false);
    if (d.ok) {
      card.querySelector('img').src =
        '/review_image/' + _imageJobId + '/' + d.filename + '?t=' + Date.now();
      card.dataset.filename = d.filename;
    } else alert('Search failed: ' + d.error);
  });
}

function replaceImgClick(cardId) {
  const {idx} = _getCardAndIdx(cardId);
  document.getElementById('imgfile-' + idx).click();
}
function replaceImgFile(cardId, input) {
  if (!input.files[0]) return;
  const {card, idx} = _getCardAndIdx(cardId);
  const form = new FormData();
  form.append('image', input.files[0]);
  _setLoading(card, true);
  fetch('/replace_image/' + _imageJobId + '/' + idx, {method:'POST', body:form})
  .then(r => r.json()).then(d => {
    _setLoading(card, false);
    if (d.ok) {
      card.querySelector('img').src =
        '/review_image/' + _imageJobId + '/' + d.filename + '?t=' + Date.now();
      card.dataset.filename = d.filename;
    } else alert('Replace failed: ' + d.error);
  });
}

function deleteImg(cardId) {
  if (!confirm('Remove this image from the video?')) return;
  const {card, idx} = _getCardAndIdx(cardId);
  fetch('/delete_image/' + _imageJobId + '/' + idx, {method:'POST'})
  .then(r => r.json()).then(d => {
    if (d.ok) { card.remove(); renumberImgCards(); }
  });
}

function toggleImgSearch() {
  document.getElementById('img-add-search').classList.toggle('show');
  document.getElementById('img-search-q').focus();
}

function addImageSearch() {
  const q = document.getElementById('img-search-q').value.trim();
  if (!q) return;
  fetch('/add_image/' + _imageJobId, {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({query:q})
  })
  .then(r=>r.json()).then(d=>{
    if (d.ok) {
      appendImgCard(d.index, d.filename, _imageJobId);
      renumberImgCards();
      document.getElementById('img-search-q').value = '';
    } else alert('Could not find image: ' + d.error);
  });
}

function addImageFile(input) {
  if (!input.files[0]) return;
  const form = new FormData();
  form.append('image', input.files[0]);
  fetch('/add_image/' + _imageJobId, {method:'POST', body:form})
  .then(r=>r.json()).then(d=>{
    if (d.ok) { appendImgCard(d.index, d.filename, _imageJobId); renumberImgCards(); }
    else alert('Upload failed: ' + d.error);
  });
}

function approveImages() {
  const order = Array.from(document.querySelectorAll('.img-card'))
                     .map(c => c.dataset.filename);
  if (order.length === 0) { alert('Please keep at least 1 image'); return; }
  showPanel('generate');   // images live in their own nav tab, not an inline panel
  setPbar(66, `${order.length} images approved — generating voice...`);
  setStep(3);
  fetch('/approve_images/' + _imageJobId, {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({order})
  });
}

// ── Template Studio ──────────────────────────────────────
let _templateJobId = null;
let _templateList   = [];
let _currentStyle    = {};

const STYLE_STORAGE_KEY = 'realNewsTemplateStyle';
const TEMPLATES_STORAGE_KEY = 'realNewsSelectedTemplates';

function loadSavedStyle() {
  try {
    const raw = localStorage.getItem(STYLE_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (e) { return null; }
}

function saveStyle(style, templateKeys) {
  try {
    localStorage.setItem(STYLE_STORAGE_KEY, JSON.stringify(style));
    localStorage.setItem(TEMPLATES_STORAGE_KEY, JSON.stringify(templateKeys));
  } catch (e) { /* localStorage unavailable — silently skip persistence */ }
}

function showTemplatePanel(templateList, jobId, defaultStyle) {
  _templateJobId = jobId;
  _templateList  = templateList || [];
  const builtIn = {
    logo_position: 'top-right', logo_shape: 'circle', banner_color: '#FFD100',
    bottom_color: '#121212', frame_color: '#C81414', corner_radius: 28,
    container_radius: 36, headline_size: 64, caption_size: 30,
  };
  // precedence: your last saved choice (localStorage) > server default > built-in fallback
  _currentStyle = Object.assign({}, builtIn, defaultStyle || {}, loadSavedStyle() || {});

  // pre-fill controls from defaults
  document.getElementById('style-logo-position').value    = _currentStyle.logo_position;
  document.getElementById('style-logo-shape').value        = _currentStyle.logo_shape;
  document.getElementById('style-banner-color').value      = _currentStyle.banner_color;
  document.getElementById('style-bottom-color').value      = _currentStyle.bottom_color;
  document.getElementById('style-frame-color').value       = _currentStyle.frame_color;
  document.getElementById('style-container-radius').value  = _currentStyle.container_radius;
  document.getElementById('style-corner-radius').value     = _currentStyle.corner_radius;
  document.getElementById('style-headline-size').value     = _currentStyle.headline_size;
  document.getElementById('style-caption-size').value      = _currentStyle.caption_size;
  document.getElementById('val-container-radius').textContent = _currentStyle.container_radius + 'px';
  document.getElementById('val-corner-radius').textContent    = _currentStyle.corner_radius + 'px';
  document.getElementById('val-headline-size').textContent    = _currentStyle.headline_size + 'px';
  document.getElementById('val-caption-size').textContent     = _currentStyle.caption_size + 'px';

  document.getElementById('template-panel').classList.add('show');
  renderTemplateCards();

  // restore last-selected templates, if any
  const savedTemplates = (() => {
    try { return JSON.parse(localStorage.getItem(TEMPLATES_STORAGE_KEY) || 'null'); }
    catch (e) { return null; }
  })();
  if (savedTemplates && savedTemplates.length) {
    document.querySelectorAll('.template-checkbox').forEach(cb => {
      cb.checked = savedTemplates.includes(cb.value);
      onTemplateCheck(cb.value, cb.checked);
    });
  }

  // wire live-update listeners once
  if (!showTemplatePanel._wired) {
    showTemplatePanel._wired = true;
    const bind = (id, key, isNum, labelId) => {
      document.getElementById(id).addEventListener('input', e => {
        _currentStyle[key] = isNum ? Number(e.target.value) : e.target.value;
        if (labelId) document.getElementById(labelId).textContent = e.target.value + 'px';
        renderAllPreviews();
      });
    };
    bind('style-logo-position', 'logo_position', false);
    bind('style-logo-shape',    'logo_shape',     false);
    bind('style-banner-color',  'banner_color',   false);
    bind('style-bottom-color',  'bottom_color',    false);
    bind('style-frame-color',   'frame_color',     false);
    bind('style-container-radius', 'container_radius', true, 'val-container-radius');
    bind('style-corner-radius', 'corner_radius',   true, 'val-corner-radius');
    bind('style-headline-size','headline_size',    true, 'val-headline-size');
    bind('style-caption-size', 'caption_size',      true, 'val-caption-size');
  }
}

function renderTemplateCards() {
  const grid = document.getElementById('template-grid');
  grid.innerHTML = '';
  _templateList.forEach((t, i) => {
    const card = document.createElement('div');
    card.className = 'tpl-card' + (i === 0 ? ' checked' : '');
    card.id = 'tpl-card-' + t.key;
    card.innerHTML = `
      <label class="tpl-card-head" onclick="event.stopPropagation()">
        <input type="checkbox" class="template-checkbox" value="${t.key}" ${i === 0 ? 'checked' : ''}
               onchange="onTemplateCheck('${t.key}', this.checked)">
        <span style="flex:1;"><strong>${t.label}</strong><br><span>${t.size[0]}×${t.size[1]}</span></span>
      </label>
      <div class="tpl-preview-box" id="tpl-preview-${t.key}"></div>`;
    grid.appendChild(card);
  });
  renderAllPreviews();
}

function onTemplateCheck(key, checked) {
  const card = document.getElementById('tpl-card-' + key);
  if (card) card.classList.toggle('checked', checked);
}

function renderAllPreviews() {
  _templateList.forEach(t => {
    const box = document.getElementById('tpl-preview-' + t.key);
    if (box) box.innerHTML = buildTemplateSVG(t, _currentStyle);
  });
}

// Builds an SVG mockup of what the real render will look like: banner
// with logo, BREAKING NEWS bar, image area (rounded per corner_radius),
// caption strip, and bottom banner — scaled to the template's real
// aspect ratio so 16:9 / 9:16 / 1:1 previews look proportionally correct.
function buildTemplateSVG(t, s) {
  const [W, H] = t.size;
  const scale = 220 / Math.max(W, H);
  const vw = 260, vh = 260; // fixed viewBox, content centered inside
  const w = W * scale, h = H * scale;
  const ox = (vw - w) / 2, oy = (vh - h) / 2;
  const topH = h * 0.10, botH = h * 0.10, midH = h - topH - botH;
  const logoLeft = s.logo_position === 'top-left';
  const logoD = topH * 0.78;
  const logoX = logoLeft ? ox + 6 + logoD/2 : ox + w - 6 - logoD/2;
  const logoY = oy + topH/2;
  const isCircle = s.logo_shape !== 'square';
  const isStacked = (t.key !== 'landscape_16_9'); // shorts/square use stacked layout
  const contRadius = Math.min(s.container_radius * scale, midH/2, 40);
  const imgRadius = Math.min(s.corner_radius * scale, 30);
  const gradId = 'grad-' + t.key;

  let mid = '';
  const uid = t.key;
  if (!isStacked) {
    // landscape: rounded red container, left image (white border + gradient), right pill + rounded caption
    const pad = midH * 0.05, contentH = midH - 2 * pad, halfW = (w - 3 * pad) / 2;
    const cy = oy + topH + pad, cx0 = ox;
    mid += `<rect x="${cx0}" y="${oy+topH}" width="${w}" height="${midH}" rx="${contRadius}" fill="${s.frame_color}"/>`;
    const lx = cx0 + pad;
    mid += `<rect x="${lx}" y="${cy}" width="${halfW}" height="${contentH}" rx="${imgRadius}" fill="#fff"/>`;
    mid += `<rect x="${lx+3}" y="${cy+3}" width="${halfW-6}" height="${contentH-6}" rx="${Math.max(0,imgRadius-3)}" fill="#666"/>`;
    mid += `<rect x="${lx+3}" y="${cy+3}" width="${halfW-6}" height="${contentH-6}" rx="${Math.max(0,imgRadius-3)}" fill="url(#${gradId})"/>`;
    mid += `<text x="${lx+halfW/2}" y="${cy+contentH/2}" font-size="9" fill="#eee" text-anchor="middle">IMAGE</text>`;
    const rx = lx + halfW + pad;
    const pillH = contentH * 0.20;
    mid += `<rect x="${rx}" y="${cy}" width="${halfW*0.85}" height="${pillH}" rx="${pillH/2}" fill="${s.frame_color}" stroke="#fff" stroke-width="1"/>`;
    mid += `<text x="${rx+halfW*0.425}" y="${cy+pillH/2+3}" font-size="${Math.max(6,s.headline_size*scale*0.4)}" fill="#fff" text-anchor="middle" font-weight="bold">BREAKING</text>`;
    const yy = cy + pillH + 8, yh = contentH - pillH - 8;
    mid += `<rect x="${rx}" y="${yy}" width="${halfW}" height="${yh}" rx="8" fill="${s.banner_color}"/>`;
    mid += `<text x="${rx+halfW/2}" y="${yy+yh/2+3}" font-size="${Math.max(6,s.caption_size*scale*0.7)}" fill="#000" text-anchor="middle">Caption text</text>`;
  } else {
    // stacked: rounded container, pill badge centered, image w/ gradient, rounded caption
    const pad = midH * 0.035, contentH = midH - 2 * pad, cx0 = ox + pad, cw = w - 2 * pad;
    const cy = oy + topH + pad;
    mid += `<rect x="${ox}" y="${oy+topH}" width="${w}" height="${midH}" rx="${contRadius}" fill="${s.frame_color}"/>`;
    const pillH = contentH * 0.11, pillW = cw * 0.7;
    mid += `<rect x="${cx0+(cw-pillW)/2}" y="${cy}" width="${pillW}" height="${pillH}" rx="${pillH/2}" fill="${s.frame_color}" stroke="#fff" stroke-width="1"/>`;
    mid += `<text x="${cx0+cw/2}" y="${cy+pillH/2+3}" font-size="${Math.max(6,s.headline_size*scale*0.32)}" fill="#fff" text-anchor="middle" font-weight="bold">BREAKING</text>`;
    const iy = cy + pillH + 8, imgH = contentH * 0.52;
    mid += `<rect x="${cx0}" y="${iy}" width="${cw}" height="${imgH}" rx="${imgRadius}" fill="#fff"/>`;
    mid += `<rect x="${cx0+3}" y="${iy+3}" width="${cw-6}" height="${imgH-6}" rx="${Math.max(0,imgRadius-3)}" fill="#666"/>`;
    mid += `<rect x="${cx0+3}" y="${iy+3}" width="${cw-6}" height="${imgH-6}" rx="${Math.max(0,imgRadius-3)}" fill="url(#${gradId})"/>`;
    mid += `<text x="${cx0+cw/2}" y="${iy+imgH/2}" font-size="9" fill="#eee" text-anchor="middle">IMAGE</text>`;
    const yy = iy + imgH + 8, yh = contentH - pillH - imgH - 16;
    mid += `<rect x="${cx0}" y="${yy}" width="${cw}" height="${yh}" rx="8" fill="${s.banner_color}"/>`;
    mid += `<text x="${cx0+cw/2}" y="${yy+yh/2+3}" font-size="${Math.max(6,s.caption_size*scale*0.55)}" fill="#000" text-anchor="middle">Caption text</text>`;
  }

  return `<svg viewBox="0 0 ${vw} ${vh}" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="${gradId}" x1="0" y1="0" x2="0" y2="1">
        <stop offset="10%" stop-color="#000" stop-opacity="0"/>
        <stop offset="50%" stop-color="#000" stop-opacity="0.4"/>
        <stop offset="90%" stop-color="#000" stop-opacity="0"/>
      </linearGradient>
    </defs>
    <rect x="0" y="0" width="${vw}" height="${vh}" fill="#0d0d0d"/>
    <rect x="${ox}" y="${oy}" width="${w}" height="${h}" fill="#000"/>
    <rect x="${ox}" y="${oy}" width="${w}" height="${topH}" fill="${s.banner_color}"/>
    ${isCircle
      ? `<circle cx="${logoX}" cy="${logoY}" r="${logoD/2}" fill="#fff" stroke="#333" stroke-width="1.5"/>`
      : `<rect x="${logoX-logoD/2}" y="${logoY-logoD/2}" width="${logoD}" height="${logoD}" rx="3" fill="#fff" stroke="#333" stroke-width="1.5"/>`}
    <text x="${logoX}" y="${logoY+2}" font-size="4.5" fill="#333" text-anchor="middle">LOGO</text>
    <text x="${logoLeft ? logoX+logoD/2+8 : ox+6}" y="${oy+topH/2+3}" font-size="6" fill="#000" text-anchor="start">headline text…</text>
    ${mid}
    <rect x="${ox}" y="${oy+h-botH}" width="${w}" height="${botH}" fill="${s.bottom_color}"/>
    <rect x="${ox+4}" y="${oy+h-botH+3}" width="${botH*0.8}" height="${botH-6}" fill="#900" rx="3"/>
    <text x="${ox+botH*0.8+16}" y="${oy+h-botH/2+2}" font-size="6" fill="#fff">share text…</text>
  </svg>`;
}

function approveTemplates() {
  const selected = Array.from(document.querySelectorAll('.template-checkbox:checked'))
                        .map(cb => cb.value);
  if (selected.length === 0) { alert('Please select at least 1 template'); return; }
  saveStyle(_currentStyle, selected);
  document.getElementById('template-panel').classList.remove('show');
  setPbar(68, `${selected.length} template(s) selected — building video...`);
  setStep(4);
  fetch('/approve_templates/' + _templateJobId, {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({templates: selected, style: _currentStyle})
  }).then(r=>r.json()).then(d=>{
    if (!d.ok) alert(d.error || 'Failed to approve templates');
  });
}

// ── Standalone "Templates" tab (browse/edit defaults, no job needed) ──
let _stdStyle = {};
let _stdWired = false;

function initStandaloneTemplates() {
  const builtIn = {
    logo_position: 'top-right', logo_shape: 'circle', banner_color: '#FFD100',
    bottom_color: '#121212', frame_color: '#C81414', corner_radius: 28,
    container_radius: 36, headline_size: 64, caption_size: 30,
  };
  _stdStyle = Object.assign({}, builtIn, SERVER_DEFAULT_STYLE || {}, loadSavedStyle() || {});
  fillStandaloneControls();
  renderStandaloneCards();

  if (!_stdWired) {
    _stdWired = true;
    const bind = (id, key, isNum, labelId) => {
      document.getElementById(id).addEventListener('input', e => {
        _stdStyle[key] = isNum ? Number(e.target.value) : e.target.value;
        if (labelId) document.getElementById(labelId).textContent = e.target.value + 'px';
        renderStandaloneCards();
        document.getElementById('std-save-confirm').style.display = 'none';
      });
    };
    bind('std-style-logo-position', 'logo_position', false);
    bind('std-style-logo-shape',    'logo_shape',     false);
    bind('std-style-banner-color',  'banner_color',   false);
    bind('std-style-bottom-color',  'bottom_color',    false);
    bind('std-style-frame-color',   'frame_color',     false);
    bind('std-style-container-radius', 'container_radius', true, 'std-val-container-radius');
    bind('std-style-corner-radius', 'corner_radius',   true, 'std-val-corner-radius');
    bind('std-style-headline-size','headline_size',    true, 'std-val-headline-size');
    bind('std-style-caption-size', 'caption_size',      true, 'std-val-caption-size');
  }
}

function fillStandaloneControls() {
  document.getElementById('std-style-logo-position').value    = _stdStyle.logo_position;
  document.getElementById('std-style-logo-shape').value        = _stdStyle.logo_shape;
  document.getElementById('std-style-banner-color').value      = _stdStyle.banner_color;
  document.getElementById('std-style-bottom-color').value      = _stdStyle.bottom_color;
  document.getElementById('std-style-frame-color').value       = _stdStyle.frame_color;
  document.getElementById('std-style-container-radius').value  = _stdStyle.container_radius;
  document.getElementById('std-style-corner-radius').value     = _stdStyle.corner_radius;
  document.getElementById('std-style-headline-size').value     = _stdStyle.headline_size;
  document.getElementById('std-style-caption-size').value      = _stdStyle.caption_size;
  document.getElementById('std-val-container-radius').textContent = _stdStyle.container_radius + 'px';
  document.getElementById('std-val-corner-radius').textContent    = _stdStyle.corner_radius + 'px';
  document.getElementById('std-val-headline-size').textContent    = _stdStyle.headline_size + 'px';
  document.getElementById('std-val-caption-size').textContent     = _stdStyle.caption_size + 'px';
}

function renderStandaloneCards() {
  const grid = document.getElementById('std-template-grid');
  grid.innerHTML = '';
  const savedTemplates = (() => {
    try { return JSON.parse(localStorage.getItem(TEMPLATES_STORAGE_KEY) || 'null'); }
    catch (e) { return null; }
  })() || [ALL_TEMPLATES[0] ? ALL_TEMPLATES[0].key : null];

  ALL_TEMPLATES.forEach(t => {
    const isDefault = savedTemplates.includes(t.key);
    const card = document.createElement('div');
    card.className = 'tpl-card' + (isDefault ? ' checked' : '');
    card.innerHTML = `
      <div class="tpl-card-head">
        <span style="flex:1;"><strong>${t.label}</strong><br><span>${t.size[0]}×${t.size[1]}${isDefault ? ' — ✓ default' : ''}</span></span>
      </div>
      <div class="tpl-preview-box" id="std-preview-${t.key}"></div>`;
    grid.appendChild(card);
  });
  ALL_TEMPLATES.forEach(t => {
    document.getElementById('std-preview-' + t.key).innerHTML = buildTemplateSVG(t, _stdStyle);
  });
}

function saveStandaloneDefaults() {
  const savedTemplates = (() => {
    try { return JSON.parse(localStorage.getItem(TEMPLATES_STORAGE_KEY) || 'null'); }
    catch (e) { return null; }
  })() || [ALL_TEMPLATES[0].key];
  saveStyle(_stdStyle, savedTemplates);
  const msg = document.getElementById('std-save-confirm');
  msg.style.display = 'block';
  setTimeout(() => { msg.style.display = 'none'; }, 3000);
}

function resetStandaloneDefaults() {
  try {
    localStorage.removeItem(STYLE_STORAGE_KEY);
    localStorage.removeItem(TEMPLATES_STORAGE_KEY);
  } catch (e) {}
  initStandaloneTemplates();
}

// ── Audio Review ──────────────────────────────────────────
let _audioJobId = null;

function showAudioPanel(segments, jobId) {
  _audioJobId = jobId;
  const list = document.getElementById('audio-list');
  list.innerHTML = '';

  segments.forEach(seg => {
    const row = document.createElement('div');
    row.className = 'audio-row';
    row.id = 'audio-row-' + seg.index;
    row.innerHTML = `
      <span class="audio-num">${seg.index + 1}</span>
      <span class="audio-text" id="atext-${seg.index}">${seg.text}</span>
      <span class="audio-dur" id="adur-${seg.index}">${seg.duration}s</span>
      <audio class="audio-player" controls
             src="/audio_segment/${jobId}/${seg.index}?t=${Date.now()}">
      </audio>
      <div class="audio-actions">
        <button class="btn-audio btn-regen-audio"
                onclick="regenAudioSeg(${seg.index})">Re-generate</button>
        <button class="btn-audio btn-replace-audio"
                onclick="replaceAudioSeg(${seg.index})">Replace File</button>
        <input type="file" class="file-input-hidden"
               id="file-${seg.index}" accept="audio/*"
               onchange="uploadAudioFile(${seg.index}, this)">
      </div>
    `;
    list.appendChild(row);
  });

  document.getElementById('audio-panel').classList.add('show');
  document.getElementById('audio-panel').scrollIntoView({behavior:'smooth', block:'nearest'});
}

function regenAudioSeg(idx) {
  const textEl = document.getElementById('atext-' + idx);
  const newText = prompt('Edit text for this sentence (or keep as is):', textEl.textContent);
  if (newText === null) return;
  const durEl = document.getElementById('adur-' + idx);
  durEl.textContent = '...';

  fetch('/regen_audio/' + _audioJobId + '/' + idx, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({text: newText, lang: document.getElementById('approval-lang')?.textContent.includes('Hindi') ? 'hi' : 'en'})
  })
  .then(r => r.json())
  .then(d => {
    if (d.ok) {
      textEl.textContent = newText;
      durEl.textContent = d.duration + 's';
      // reload audio player
      const row = document.getElementById('audio-row-' + idx);
      const audio = row.querySelector('audio');
      audio.src = '/audio_segment/' + _audioJobId + '/' + idx + '?t=' + Date.now();
      audio.load();
    } else {
      alert('Re-generate failed: ' + d.error);
    }
  });
}

function replaceAudioSeg(idx) {
  document.getElementById('file-' + idx).click();
}

function uploadAudioFile(idx, input) {
  if (!input.files[0]) return;
  const durEl = document.getElementById('adur-' + idx);
  durEl.textContent = 'uploading...';
  const form = new FormData();
  form.append('audio', input.files[0]);
  fetch('/replace_audio/' + _audioJobId + '/' + idx, {method:'POST', body:form})
  .then(r => r.json())
  .then(d => {
    if (d.ok) {
      durEl.textContent = d.duration + 's';
      const row   = document.getElementById('audio-row-' + idx);
      const audio = row.querySelector('audio');
      audio.src = '/audio_segment/' + _audioJobId + '/' + idx + '?t=' + Date.now();
      audio.load();
    } else {
      alert('Upload failed: ' + d.error);
      durEl.textContent = '?s';
    }
  });
}

function approveAudio() {
  document.getElementById('audio-panel').classList.remove('show');
  setPbar(54, 'Audio approved — building video...');
  setStep(3);
  fetch('/approve_audio/' + _audioJobId, {method:'POST',
        headers:{'Content-Type':'application/json'}, body:'{}'});
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

// ── pollJob: resumes itself after every approval stage ────
// (recursive instead of nested — avoids missing a stage as more get added)
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
      document.querySelector('.btn-approve').addEventListener('click', () => {
        setTimeout(() => pollJob(jobId), 500);
      }, {once: true});

    } else if (d.status === 'waiting_audio_approval') {
      es.close();
      setPbar(53, 'Audio ready — please review each clip');
      showAudioPanel(d.segments || [], d.job_id || jobId);
      document.querySelector('.btn-approve-audio').addEventListener('click', () => {
        setTimeout(() => pollJob(jobId), 600);
      }, {once: true});

    } else if (d.status === 'waiting_image_approval') {
      es.close();
      setPbar(65, 'Images ready — please review');
      showImagePanel(d.images || [], d.job_id || jobId);
      document.querySelector('.btn-approve-images').addEventListener('click', () => {
        setTimeout(() => pollJob(jobId), 600);
      }, {once: true});

    } else if (d.status === 'waiting_template_approval') {
      es.close();
      setPbar(67, 'Choose which template(s) to build');
      showTemplatePanel(d.templates || [], d.job_id || jobId, d.default_style || {});
      document.querySelector('#template-panel .btn-approve-templates').addEventListener('click', () => {
        setTimeout(() => pollJob(jobId), 600);
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
        job = _jobs[job_id]
        job['voice_paths'] = voice_paths
        job['sentences']   = sentences
        job['durations']   = durations
        emit(2, 52, f'  Voice done - {len(voice_paths)} clips ready')

        seg_info = [{'index':i,'text':sentences[i],'duration':round(durations[i],2)}
                    for i in range(len(sentences))]
        job['audio_approval_event'] = threading.Event()
        job['approved_voice_paths'] = None
        emit(2, 53, 'Audio ready — please review', status='waiting_audio_approval',
             segments=seg_info, job_id=job_id)
        job['audio_approval_event'].wait()

        if job['approved_voice_paths']:
            voice_paths = job['approved_voice_paths']
            from moviepy import AudioFileClip as _AFC
            durations = []
            for p in voice_paths:
                try:    durations.append(_AFC(p).duration)
                except: durations.append(3.0)

        audio_path = combine_audio(voice_paths, out_path='voice_combined.mp3')
        emit(2, 54, 'Audio approved - continuing...')

        emit(3, 54, '4/6 Fetching images...')
        from fetch_images import get_images
        images = get_images(url, topic or title, target=max(len(sentences), 20))
        emit(3, 64, f'  Got {len(images)} images')

        # save images in job for serving to UI
        import shutil as _shutil
        img_review_dir = os.path.join(DOWNLOADS, f'img_review_{job_id}')
        os.makedirs(img_review_dir, exist_ok=True)
        saved_imgs = []
        for i, src in enumerate(images):
            dst = os.path.join(img_review_dir, f'img_{i:03d}.jpg')
            try:
                from PIL import Image as _PILImg
                _PILImg.open(src).convert('RGB').save(dst, 'JPEG')
                saved_imgs.append(dst)
            except:
                pass
        job['image_paths']     = saved_imgs
        job['img_review_dir']  = img_review_dir

        # ── PAUSE: image review ──────────────────────────────────────────
        img_info = [{'index':i,'filename':f'img_{i:03d}.jpg'}
                    for i in range(len(saved_imgs))]
        job['image_approval_event'] = threading.Event()
        job['approved_image_paths'] = None
        emit(3, 65, 'Images ready — please review', status='waiting_image_approval',
             images=img_info, job_id=job_id, count=len(saved_imgs))
        job['image_approval_event'].wait()

        # use approved/edited image list
        final_images = job['approved_image_paths'] or saved_imgs
        images = [p for p in final_images if os.path.exists(p)]
        emit(3, 66, f'Images approved — {len(images)} images confirmed')

        n = min(len(images), len(sentences))
        images    = images[:n]
        captions  = sentences[:n]
        durations = durations[:n]

        # ── PAUSE: template selection ─────────────────────────────────────
        from templates import list_templates, default_style
        job['template_approval_event'] = threading.Event()
        job['approved_templates'] = None
        job['approved_style'] = None
        emit(3, 67, 'Choose which template(s) to build', status='waiting_template_approval',
             templates=list_templates(), default_style=default_style(), job_id=job_id)
        job['template_approval_event'].wait()

        selected_templates = job['approved_templates'] or ['landscape_16_9']
        selected_style = job.get('approved_style')
        emit(4, 68, f"Templates selected: {', '.join(selected_templates)}")

        emit(4, 68, '5/6 Building video...')
        from build_video import build_video
        import datetime
        date_str = datetime.datetime.now().strftime('%Y-%m-%d')
        slug = ''.join(c if c.isalnum() else '_' for c in title)[:40].strip('_')
        out_path = os.path.join(DOWNLOADS, f'video_{date_str}_{slug}.mp4')
        build_result = build_video(images, captions, durations, audio_path, title,
                                    out_path=out_path, templates=selected_templates, lang=lang,
                                    style=selected_style)
        # build_result is a single path if only one template was chosen,
        # or {template_key: path} if several were chosen.
        if isinstance(build_result, dict):
            out_paths = list(build_result.values())
            for key, path in build_result.items():
                emit(4, 88, f'  Built {key}: {os.path.basename(path)}')
        else:
            out_paths = [build_result]
        primary_out_path = out_paths[0]
        emit(4, 90, '  Video saved')

        emit(5, 92, '6/6 Creating thumbnail...')
        from make_thumbnail import make_thumbnail
        thumb_path = os.path.join(DOWNLOADS, f'thumb_{date_str}_{slug}.jpg')
        make_thumbnail(images[0], title, out_path=thumb_path)
        emit(5, 100, 'Done!', status='done',
             video=os.path.basename(primary_out_path),
             videos=[os.path.basename(p) for p in out_paths],
             thumb=os.path.basename(thumb_path),
             title=title, lang=lang)

    except Exception as e:
        q.put(json.dumps(dict(status='error', error=str(e), progress=0, message=str(e))))


@app.route('/')
def index():
    videos = get_videos()
    from templates import list_templates, default_style
    return render_template_string(
        HTML, videos=videos, folder=DOWNLOADS,
        templates_json=json.dumps(list_templates()),
        default_style_json=json.dumps(default_style()),
    )


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

@app.route('/review_image/<job_id>/<filename>')
def serve_review_image(job_id, filename):
    job = _jobs.get(job_id, {})
    img_dir = job.get('img_review_dir', '')
    path = os.path.join(img_dir, filename)
    if not os.path.exists(path):
        return jsonify(error='not found'), 404
    return send_file(path, mimetype='image/jpeg')

@app.route('/replace_image/<job_id>/<int:idx>', methods=['POST'])
def replace_image(job_id, idx):
    job = _jobs.get(job_id, {})
    if not job: return jsonify(ok=False, error='Job not found')
    f = request.files.get('image')
    if not f: return jsonify(ok=False, error='No file')
    from PIL import Image as PILImg
    img_dir = job['img_review_dir']
    path = os.path.join(img_dir, f'img_{idx:03d}.jpg')
    try:
        PILImg.open(f).convert('RGB').save(path, 'JPEG')
        if idx < len(job['image_paths']):
            job['image_paths'][idx] = path
        else:
            job['image_paths'].append(path)
        return jsonify(ok=True, filename=f'img_{idx:03d}.jpg')
    except Exception as e:
        return jsonify(ok=False, error=str(e))

@app.route('/regen_image/<job_id>/<int:idx>', methods=['POST'])
def regen_image(job_id, idx):
    job = _jobs.get(job_id, {})
    if not job: return jsonify(ok=False, error='Job not found')
    data  = request.get_json() or {}
    query = data.get('query', 'news')
    img_dir = job['img_review_dir']
    path = os.path.join(img_dir, f'img_{idx:03d}.jpg')
    import requests as _req
    import os as _os
    api_key = _os.getenv('PEXELS_API_KEY','')
    try:
        r = _req.get(
            f'https://api.pexels.com/v1/search?query={query}&per_page=1&orientation=landscape',
            headers={'Authorization': api_key}, timeout=20
        )
        photos = r.json().get('photos', [])
        if not photos: return jsonify(ok=False, error='No image found for that query')
        img_bytes = _req.get(photos[0]['src']['large'], timeout=20).content
        from PIL import Image as PILImg
        import io
        PILImg.open(io.BytesIO(img_bytes)).convert('RGB').save(path, 'JPEG')
        if idx < len(job['image_paths']):
            job['image_paths'][idx] = path
        else:
            job['image_paths'].append(path)
        return jsonify(ok=True, filename=f'img_{idx:03d}.jpg')
    except Exception as e:
        return jsonify(ok=False, error=str(e))

@app.route('/add_image/<job_id>', methods=['POST'])
def add_image(job_id):
    job = _jobs.get(job_id, {})
    if not job: return jsonify(ok=False, error='Job not found')
    img_dir = job['img_review_dir']
    idx  = len(job['image_paths'])
    path = os.path.join(img_dir, f'img_{idx:03d}.jpg')
    # check if file upload or search query
    f = request.files.get('image')
    if f:
        from PIL import Image as PILImg
        try:
            PILImg.open(f).convert('RGB').save(path, 'JPEG')
            job['image_paths'].append(path)
            return jsonify(ok=True, index=idx, filename=f'img_{idx:03d}.jpg')
        except Exception as e:
            return jsonify(ok=False, error=str(e))
    data  = request.get_json() or {}
    query = data.get('query','news')
    import requests as _req, os as _os
    api_key = _os.getenv('PEXELS_API_KEY','')
    try:
        r = _req.get(
            f'https://api.pexels.com/v1/search?query={query}&per_page=1&orientation=landscape',
            headers={'Authorization': api_key}, timeout=20
        )
        photos = r.json().get('photos', [])
        if not photos: return jsonify(ok=False, error='No image found')
        img_bytes = _req.get(photos[0]['src']['large'], timeout=20).content
        from PIL import Image as PILImg
        import io
        PILImg.open(io.BytesIO(img_bytes)).convert('RGB').save(path, 'JPEG')
        job['image_paths'].append(path)
        return jsonify(ok=True, index=idx, filename=f'img_{idx:03d}.jpg')
    except Exception as e:
        return jsonify(ok=False, error=str(e))

@app.route('/delete_image/<job_id>/<int:idx>', methods=['POST'])
def delete_image(job_id, idx):
    job = _jobs.get(job_id, {})
    if not job: return jsonify(ok=False, error='Job not found')
    if idx < len(job['image_paths']):
        job['image_paths'].pop(idx)
    return jsonify(ok=True)

@app.route('/approve_images/<job_id>', methods=['POST'])
def approve_images(job_id):
    job = _jobs.get(job_id)
    if not job: return jsonify(ok=False, error='Job not found')
    data = request.get_json() or {}
    ordered = data.get('order', [])  # list of filenames in user-chosen order
    if ordered:
        img_dir = job['img_review_dir']
        job['approved_image_paths'] = [
            os.path.join(img_dir, fn) for fn in ordered
            if os.path.exists(os.path.join(img_dir, fn))
        ]
    job['image_approval_event'].set()
    return jsonify(ok=True)

@app.route('/approve_templates/<job_id>', methods=['POST'])
def approve_templates(job_id):
    job = _jobs.get(job_id)
    if not job: return jsonify(ok=False, error='Job not found')
    data = request.get_json() or {}
    selected = data.get('templates', [])
    from templates import TEMPLATES as _TEMPLATE_REGISTRY
    from templates.common import DEFAULT_STYLE
    selected = [t for t in selected if t in _TEMPLATE_REGISTRY]
    if not selected:
        return jsonify(ok=False, error='Please select at least 1 template')

    raw_style = data.get('style') or {}
    style = {}
    for key, default_val in DEFAULT_STYLE.items():
        if key not in raw_style:
            continue
        val = raw_style[key]
        if key == 'logo_position' and val not in ('top-left', 'top-right'):
            continue
        if key == 'logo_shape' and val not in ('circle', 'square'):
            continue
        if key in ('corner_radius', 'container_radius', 'headline_size', 'caption_size'):
            try:
                val = int(val)
            except (TypeError, ValueError):
                continue
        if key in ('banner_color', 'bottom_color', 'frame_color'):
            if not isinstance(val, str) or not val.startswith('#') or len(val) != 7:
                continue
        style[key] = val

    job['approved_templates'] = selected
    job['approved_style'] = style
    job['template_approval_event'].set()
    return jsonify(ok=True)

@app.route('/audio_segment/<job_id>/<int:idx>')
def serve_audio_segment(job_id, idx):
    job = _jobs.get(job_id, {})
    paths = job.get('voice_paths', [])
    if idx >= len(paths) or not os.path.exists(paths[idx]):
        return jsonify(error='not found'), 404
    return send_file(paths[idx], mimetype='audio/mpeg')

@app.route('/replace_audio/<job_id>/<int:idx>', methods=['POST'])
def replace_audio_segment(job_id, idx):
    job = _jobs.get(job_id, {})
    if not job:
        return jsonify(ok=False, error='Job not found')
    f = request.files.get('audio')
    if not f:
        return jsonify(ok=False, error='No file uploaded')
    import shutil
    orig_path = job['voice_paths'][idx]
    backup    = orig_path + '.orig'
    if not os.path.exists(backup):
        shutil.copy(orig_path, backup)
    f.save(orig_path)
    from moviepy import AudioFileClip
    try:
        dur = AudioFileClip(orig_path).duration
    except:
        dur = 3.0
    job['durations'][idx] = dur
    return jsonify(ok=True, duration=round(dur,2))

@app.route('/regen_audio/<job_id>/<int:idx>', methods=['POST'])
def regen_audio_segment(job_id, idx):
    job = _jobs.get(job_id, {})
    if not job:
        return jsonify(ok=False, error='Job not found')
    data = request.get_json() or {}
    text = data.get('text', job['sentences'][idx])
    lang = data.get('lang', 'en')
    from generate_voice import pick_voice
    import asyncio, edge_tts
    voice = pick_voice(lang)
    path  = job['voice_paths'][idx]
    async def _gen():
        await edge_tts.Communicate(text, voice).save(path)
    asyncio.run(_gen())
    from moviepy import AudioFileClip
    try:
        dur = AudioFileClip(path).duration
    except:
        dur = 3.0
    job['durations'][idx] = dur
    job['sentences'][idx] = text
    return jsonify(ok=True, duration=round(dur,2))

@app.route('/approve_audio/<job_id>', methods=['POST'])
def approve_audio(job_id):
    job = _jobs.get(job_id)
    if not job:
        return jsonify(ok=False, error='Job not found')
    job['audio_approval_event'].set()
    return jsonify(ok=True)

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
    in_codespaces = bool(os.environ.get('CODESPACES') or os.environ.get('GITPOD_WORKSPACE_URL'))
    if in_codespaces:
        print('  Running in a cloud dev environment — open the forwarded port')
        print('  from the "Ports" tab instead of a local browser window.\n')
    else:
        print('  Opening: http://localhost:5000\n')
        threading.Timer(1.2, lambda: webbrowser.open('http://localhost:5000')).start()
    app.run(debug=False, host='0.0.0.0', port=5000, threaded=True)
