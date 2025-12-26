#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
モバイル対応 動画管理アプリケーション
スマホ・タブレット完全対応版
"""

from flask import Flask, render_template_string, jsonify, request, send_file
import sqlite3
import os
from pathlib import Path
import webbrowser
from threading import Thread, Lock
import time
import random
import logging
import json
from datetime import datetime

# --- 設定 ---
DB_DIR = Path.home() / '.video_manager'
DB_PATH = DB_DIR / 'videos.db'
DB_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = DB_DIR / 'scan.log'
EXPORT_DIR = DB_DIR / 'exports'
EXPORT_DIR.mkdir(parents=True, exist_ok=True)
VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg', '.ts', '.m2ts'}
BATCH_SIZE = 500

# ログ設定
logging.basicConfig(filename=str(LOG_PATH), level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger('').addHandler(console)

app = Flask(__name__)

# スキャンステータス
scan_status = {'is_scanning': False, 'total': 0, 'processed': 0, 'current_path': ''}
scan_lock = Lock()

# --- DB ヘルパー ---

def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("CREATE TABLE IF NOT EXISTS videos (id INTEGER PRIMARY KEY, path TEXT UNIQUE, size INTEGER, modified INTEGER)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_videos_path ON videos(path)")
    conn.execute("CREATE TABLE IF NOT EXISTS video_meta (video_id INTEGER PRIMARY KEY, play_count INTEGER DEFAULT 0, favorite INTEGER DEFAULT 0, tags TEXT DEFAULT '', last_played INTEGER)")
    conn.execute("CREATE TABLE IF NOT EXISTS playlists (id INTEGER PRIMARY KEY, name TEXT, created INTEGER, video_ids TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS watch_history (id INTEGER PRIMARY KEY, video_id INTEGER, watched_at INTEGER)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_history_video ON watch_history(video_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_history_time ON watch_history(watched_at)")
    conn.commit()
    conn.close()


init_db()

# --- スキャンワーカー ---

def scan_worker(target_dir):
    target_dir = str(Path(target_dir).expanduser())
    with scan_lock:
        scan_status.update({'is_scanning': True, 'total': 0, 'processed': 0, 'current_path': target_dir})

    conn = get_db()
    cur = conn.cursor()

    processed = 0
    total_guess = 0
    batch = []

    try:
        for root, dirs, files in os.walk(target_dir):
            for f in files:
                if Path(f).suffix.lower() in VIDEO_EXTENSIONS:
                    total_guess += 1
        with scan_lock:
            scan_status['total'] = total_guess

        for root, dirs, files in os.walk(target_dir):
            for file in files:
                try:
                    if Path(file).suffix.lower() not in VIDEO_EXTENSIONS:
                        continue
                    p = Path(root) / file
                    stat = p.stat()
                    norm_path = str(p.resolve().as_posix())
                    batch.append((norm_path, stat.st_size, int(stat.st_mtime)))

                    if len(batch) >= BATCH_SIZE:
                        cur.executemany("INSERT OR IGNORE INTO videos (path, size, modified) VALUES (?, ?, ?)", batch)
                        conn.commit()
                        batch = []
                    processed += 1
                    if processed % 50 == 0:
                        with scan_lock:
                            scan_status['processed'] = processed
                            scan_status['current_path'] = root
                except PermissionError as pe:
                    logging.warning(f"Permission denied: {root}/{file} — {pe}")
                except FileNotFoundError:
                    continue
                except Exception as e:
                    logging.exception(f"Unexpected error scanning {root}/{file}: {e}")

        if batch:
            cur.executemany("INSERT OR IGNORE INTO videos (path, size, modified) VALUES (?, ?, ?)", batch)
            conn.commit()

        cur.execute("SELECT id, path FROM videos")
        rows = cur.fetchall()
        removals = []
        for r in rows:
            if not Path(r['path']).exists():
                removals.append((r['id'],))
                if len(removals) >= BATCH_SIZE:
                    cur.executemany("DELETE FROM videos WHERE id=?", removals)
                    conn.commit()
                    removals = []
        if removals:
            cur.executemany("DELETE FROM videos WHERE id=?", removals)
            conn.commit()

        try:
            cur.execute("VACUUM")
        except Exception as e:
            logging.warning(f"VACUUM failed: {e}")

    finally:
        conn.close()
        with scan_lock:
            scan_status['is_scanning'] = False
            scan_status['processed'] = processed
            scan_status['current_path'] = ''


# --- API ---

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/scan', methods=['POST'])
def start_scan():
    d = request.json.get('directory')
    if not d:
        return jsonify({'error': 'no path'}), 400
    Thread(target=scan_worker, args=(d,), daemon=True).start()
    return jsonify({'success': True})


@app.route('/api/scan/status')
def get_status():
    with scan_lock:
        return jsonify(scan_status)


@app.route('/api/stats')
def get_stats():
    try:
        conn = get_db()
        total = conn.execute("SELECT COUNT(*) as cnt FROM videos").fetchone()['cnt']
        favorites = conn.execute("SELECT COUNT(*) as cnt FROM video_meta WHERE favorite = 1").fetchone()['cnt']
        total_size = conn.execute("SELECT SUM(size) as total FROM videos").fetchone()['total'] or 0
        
        tags_raw = conn.execute("SELECT tags FROM video_meta WHERE tags != '' AND tags IS NOT NULL").fetchall()
        tag_count = {}
        for row in tags_raw:
            if row['tags']:
                for tag in row['tags'].split(','):
                    tag = tag.strip()
                    if tag:
                        tag_count[tag] = tag_count.get(tag, 0) + 1
        
        recent_watched = conn.execute("""
            SELECT v.id, v.path, h.watched_at
            FROM watch_history h
            JOIN videos v ON h.video_id = v.id
            ORDER BY h.watched_at DESC
            LIMIT 10
        """).fetchall()
        
        conn.close()
        
        def format_size(bytes):
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if bytes < 1024:
                    return f"{bytes:.1f} {unit}"
                bytes /= 1024
            return f"{bytes:.1f} PB"
        
        return jsonify({
            'total': total,
            'favorites': favorites,
            'total_size': format_size(total_size),
            'total_size_bytes': total_size,
            'tags': [{'name': k, 'count': v} for k, v in sorted(tag_count.items(), key=lambda x: -x[1])][:20],
            'recent_watched': [{'id': r['id'], 'path': r['path'], 'filename': os.path.basename(r['path']), 'watched_at': r['watched_at']} for r in recent_watched]
        })
    except Exception as e:
        logging.error(f"Stats error: {e}")
        return jsonify({
            'total': 0,
            'favorites': 0,
            'total_size': '0 B',
            'total_size_bytes': 0,
            'tags': [],
            'recent_watched': []
        })


@app.route('/api/folders')
def get_folders():
    conn = get_db()
    rows = conn.execute("SELECT path FROM videos").fetchall()
    conn.close()
    folder_map = {}
    for row in rows:
        folder = os.path.dirname(row['path'])
        folder_map[folder] = folder_map.get(folder, 0) + 1
    folders = [{'path': k, 'count': v, 'name': os.path.basename(k) or k} for k, v in folder_map.items()]
    folders.sort(key=lambda x: (-x['count'], x['path']))
    return jsonify({'folders': folders})


@app.route('/api/videos')
def get_videos():
    folder = request.args.get('folder')
    limit = int(request.args.get('limit') or 50)
    offset = int(request.args.get('offset') or 0)
    favorites_only = request.args.get('favorites_only') == 'true'
    search = request.args.get('search', '').strip()
    sort_by = request.args.get('sort', 'modified_desc')
    tag_filter = request.args.get('tag', '').strip()
    
    conn = get_db()
    videos = []
    
    order_map = {
        'modified_desc': 'v.modified DESC',
        'modified_asc': 'v.modified ASC',
        'name_asc': 'v.path ASC',
        'name_desc': 'v.path DESC',
        'play_count_desc': 'COALESCE(m.play_count, 0) DESC',
        'size_desc': 'v.size DESC',
        'size_asc': 'v.size ASC',
    }
    order_clause = order_map.get(sort_by, 'v.modified DESC')

    where_parts = []
    params = []

    if folder:
        folder_norm = str(Path(folder).as_posix())
        like_pattern = folder_norm.rstrip('/') + '/%'
        where_parts.append("v.path LIKE ?")
        params.append(like_pattern)
        
    if favorites_only:
        where_parts.append("m.favorite = 1")
    
    if search:
        where_parts.append("(v.path LIKE ? OR COALESCE(m.tags, '') LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])
    
    if tag_filter:
        where_parts.append("COALESCE(m.tags, '') LIKE ?")
        params.append(f"%{tag_filter}%")
    
    join_type = "INNER JOIN" if (favorites_only or tag_filter) else "LEFT JOIN"
    where_clause = "WHERE " + " AND ".join(where_parts) if where_parts else ""
    
    query = f"""
        SELECT v.id, v.path, v.size, v.modified, m.play_count, m.favorite, m.tags 
        FROM videos v 
        {join_type} video_meta m ON v.id = m.video_id 
        {where_clause}
        ORDER BY {order_clause} 
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])
    
    rows = conn.execute(query, params).fetchall()

    if not rows and folder and not favorites_only and not search and not tag_filter:
        p = Path(folder)
        if p.exists() and p.is_dir():
            for entry in p.iterdir():
                try:
                    if entry.is_file() and entry.suffix.lower() in VIDEO_EXTENSIONS:
                        stat = entry.stat()
                        norm_path = str(entry.resolve().as_posix())
                        conn.execute("INSERT OR IGNORE INTO videos (path, size, modified) VALUES (?, ?, ?)", (norm_path, stat.st_size, int(stat.st_mtime)))
                except:
                    pass
            conn.commit()
            rows = conn.execute(query, params).fetchall()

    videos = [{'id': r['id'], 'path': r['path'], 'filename': os.path.basename(r['path']), 'play_count': r['play_count'] or 0, 'favorite': bool(r['favorite']), 'tags': (r['tags'] or '').split(',') if r['tags'] else [], 'size': r['size'] or 0, 'size_str': format_size_helper(r['size'])} for r in rows]
    
    count_query = f"""
        SELECT COUNT(*) as total
        FROM videos v
        {join_type} video_meta m ON v.id = m.video_id
        {where_clause}
    """
    total = conn.execute(count_query, params[:-2]).fetchone()['total']

    conn.close()
    return jsonify({'videos': videos, 'total': total})


def format_size_helper(bytes):
    if bytes is None or bytes == 0:
        return "0B"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024:
            return f"{bytes:.0f}{unit}"
        bytes /= 1024
    return f"{bytes:.1f}GB"


@app.route('/api/shorts')
def get_shorts():
    conn = get_db()
    rows = conn.execute("SELECT id, path FROM videos").fetchall()
    conn.close()

    folder_groups = {}
    for r in rows:
        parent = os.path.dirname(r['path'])
        folder_groups.setdefault(parent, []).append(r)

    shorts = []
    keys = list(folder_groups.keys())
    random.shuffle(keys)
    for k in keys:
        if not folder_groups[k]: continue
        video = random.choice(folder_groups[k])
        shorts.append({'id': video['id'], 'path': video['path'], 'filename': os.path.basename(video['path']), 'folder_path': k, 'folder_name': os.path.basename(k) or k})
        if len(shorts) >= 50:
            break
    return jsonify({'shorts': shorts})


@app.route('/video/<int:vid>')
def stream(vid):
    conn = get_db()
    row = conn.execute("SELECT path FROM videos WHERE id=?", (vid,)).fetchone()
    conn.close()
    if row and Path(row['path']).exists():
        return send_file(row['path'])
    return "Not Found", 404


@app.route('/api/playlists', methods=['GET', 'POST', 'DELETE'])
def playlists():
    conn = get_db()
    if request.method == 'GET':
        rows = conn.execute("SELECT * FROM playlists ORDER BY created DESC").fetchall()
        conn.close()
        return jsonify({'playlists': [{'id': r['id'], 'name': r['name'], 'created': r['created'], 'video_ids': r['video_ids'].split(',') if r['video_ids'] else []} for r in rows]})
    elif request.method == 'POST':
        data = request.json
        name = data.get('name', '新しいプレイリスト')
        video_ids = ','.join(map(str, data.get('video_ids', [])))
        created = int(time.time())
        conn.execute("INSERT INTO playlists (name, created, video_ids) VALUES (?, ?, ?)", (name, created, video_ids))
        conn.commit()
        playlist_id = conn.execute("SELECT last_insert_rowid() as id").fetchone()['id']
        conn.close()
        return jsonify({'id': playlist_id, 'name': name})
    elif request.method == 'DELETE':
        playlist_id = request.json.get('id')
        conn.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
        conn.commit()
        conn.close()
        return jsonify({'ok': True})


@app.route('/api/export')
def export_data():
    conn = get_db()
    videos = conn.execute("SELECT v.*, m.play_count, m.favorite, m.tags FROM videos v LEFT JOIN video_meta m ON v.id = m.video_id").fetchall()
    conn.close()
    
    data = {
        'exported_at': datetime.now().isoformat(),
        'videos': [{
            'path': r['path'],
            'size': r['size'],
            'modified': r['modified'],
            'play_count': r['play_count'] or 0,
            'favorite': bool(r['favorite']),
            'tags': r['tags'] or ''
        } for r in videos]
    }
    
    filename = f"video_manager_export_{int(time.time())}.json"
    filepath = EXPORT_DIR / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return send_file(filepath, as_attachment=True, download_name=filename)


@app.route('/api/bulk_action', methods=['POST'])
def bulk_action():
    data = request.json
    action = data.get('action')
    video_ids = data.get('video_ids', [])
    conn = get_db()
    cur = conn.cursor()
    if action == 'add_favorite':
        for vid in video_ids:
            cur.execute("INSERT INTO video_meta(video_id, favorite) VALUES (?, 1) ON CONFLICT(video_id) DO UPDATE SET favorite=1", (vid,))
    elif action == 'remove_favorite':
        for vid in video_ids:
            cur.execute("UPDATE video_meta SET favorite=0 WHERE video_id=?", (vid,))
    elif action == 'add_tags':
        tags_to_add = data.get('tags', '')
        for vid in video_ids:
            cur.execute("SELECT tags FROM video_meta WHERE video_id=?", (vid,))
            r = cur.fetchone()
            existing = r['tags'] if r and r['tags'] else ''
            existing_set = set(existing.split(',')) if existing else set()
            new_set = existing_set | set(tags_to_add.split(','))
            new_tags = ','.join(filter(None, new_set))
            cur.execute("INSERT INTO video_meta(video_id, tags) VALUES (?, ?) ON CONFLICT(video_id) DO UPDATE SET tags=?", (vid, new_tags, new_tags))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/meta', methods=['POST', 'GET'])
def meta():
    if request.method == 'GET':
        vid = request.args.get('video_id')
        if not vid:
            return jsonify({'error': 'no id'}), 400
        conn = get_db()
        r = conn.execute("SELECT play_count, favorite, tags FROM video_meta WHERE video_id=?", (vid,)).fetchone()
        conn.close()
        if r:
            return jsonify({'play_count': r['play_count'], 'favorite': bool(r['favorite']), 'tags': (r['tags'] or '').split(',') if r['tags'] else []})
        return jsonify({'play_count': 0, 'favorite': False, 'tags': []})

    data = request.json
    vid = data.get('video_id')
    action = data.get('action')
    conn = get_db()
    cur = conn.cursor()
    if action == 'play':
        now = int(time.time())
        cur.execute("INSERT INTO video_meta(video_id, play_count, last_played) VALUES (?, 1, ?) ON CONFLICT(video_id) DO UPDATE SET play_count = play_count + 1, last_played = ?", (vid, now, now))
        cur.execute("INSERT INTO watch_history (video_id, watched_at) VALUES (?, ?)", (vid, now))
    elif action == 'toggle_favorite':
        cur.execute("SELECT favorite FROM video_meta WHERE video_id=?", (vid,))
        r = cur.fetchone()
        if r:
            new = 0 if r['favorite'] else 1
            cur.execute("UPDATE video_meta SET favorite=? WHERE video_id=?", (new, vid))
        else:
            cur.execute("INSERT INTO video_meta(video_id, favorite) VALUES (?, 1)", (vid,))
    elif action == 'set_tags':
        tags = data.get('tags', '')
        cur.execute("INSERT INTO video_meta(video_id, tags) VALUES (?, ?) ON CONFLICT(video_id) DO UPDATE SET tags=?", (vid, tags or '', tags or ''))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


# --- HTML テンプレート ---
HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<link rel="icon" href="data:,"> 
<title>Video Manager Pro</title>
<style>
* { box-sizing: border-box; -webkit-tap-highlight-color: transparent; margin: 0; padding: 0; }
body { 
    margin: 0; 
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; 
    background: #0a0a0a; 
    color: #e0e0e0; 
    height: 100vh; 
    overflow: hidden; 
    display: flex; 
    flex-direction: row;
    width: 100vw;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
}

/* モバイルヘッダー */
.mobile-header { 
    display: none; 
    background: #111; 
    border-bottom: 1px solid #222; 
    padding: 12px 16px; 
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    z-index: 1001;
    height: 56px;
}
.header-content {
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.header-title { font-size: 18px; font-weight: 600; }
.menu-btn {
    background: #1a1a1a;
    border: 1px solid #333;
    border-radius: 8px;
    padding: 8px 12px;
    color: #fff;
    cursor: pointer;
    font-size: 14px;
    min-height: 44px;
    min-width: 44px;
}

/* ナビゲーション */
.nav-rail { 
    width:72px; 
    background:#111; 
    border-right:1px solid #222; 
    display:flex; 
    flex-direction:column; 
    align-items:center; 
    padding-top:20px; 
    z-index:2000;
    transition: transform 0.3s ease;
}
.nav-item { 
    width:52px; 
    height:52px; 
    margin-bottom:16px; 
    border-radius:12px; 
    display:flex; 
    flex-direction:column; 
    align-items:center; 
    justify-content:center; 
    cursor:pointer; 
    color:#666; 
    transition:all 0.2s; 
    position:relative;
}
.nav-item:active { transform:scale(0.95); }
.nav-item:hover { background:#1a1a1a; color:#00aaff; }
.nav-item.active { background:#00aaff; color:#fff; }
.nav-icon { font-size:24px; margin-bottom:2px; }
.nav-label { font-size:9px; font-weight:500; }

/* メインコンテンツ */
#content-area { 
    flex: 1; 
    position: relative; 
    overflow: hidden; 
    display: flex;
    flex-direction: column;
    width: 100%;
    height: 100%;
}

/* ライブラリビュー */
#library-view { 
    display:flex; 
    height:100%; 
    width:100%;
    flex-direction:column;
}

/* サイドバー - モバイルでは上部に表示 */
#sidebar { 
    width:100%; 
    background:#0f0f0f; 
    display:flex; 
    flex-direction:column;
    max-height:60vh;
    overflow-y:auto;
}

.sidebar-header { 
    padding:12px 16px; 
    background:#111; 
    border-bottom:1px solid #222;
    position:sticky;
    top:0;
    z-index:100;
}

.search-box { 
    width:100%; 
    padding:10px 12px; 
    background:#1a1a1a; 
    border:1px solid #333; 
    border-radius:8px; 
    color:#fff; 
    font-size:14px; 
    margin-bottom:10px;
}
.search-box:focus { outline:none; border-color:#00aaff; }

.filter-section { margin-top:12px; }
.filter-title { 
    font-size:11px; 
    color:#666; 
    text-transform:uppercase; 
    margin-bottom:8px; 
    font-weight:600; 
    letter-spacing:0.5px;
}

.filter-btn { 
    padding:10px 14px; 
    background:#1a1a1a; 
    border:1px solid #333; 
    border-radius:8px; 
    cursor:pointer; 
    font-size:13px; 
    color:#999; 
    transition:all 0.2s; 
    margin-bottom:6px; 
    display:flex; 
    align-items:center; 
    justify-content:space-between;
}
.filter-btn:active { transform:scale(0.98); }
.filter-btn.active { background:#00aaff; color:#fff; border-color:#00aaff; }

.sort-select { 
    width:100%; 
    padding:10px; 
    background:#1a1a1a; 
    border:1px solid #333; 
    border-radius:8px; 
    color:#fff; 
    font-size:13px; 
    cursor:pointer;
}

#folderList { 
    flex:1; 
    overflow-y:auto; 
    padding:8px;
}

.folder-item { 
    padding:12px 14px; 
    font-size:13px; 
    cursor:pointer; 
    color:#999; 
    border-radius:8px; 
    margin-bottom:4px; 
    display:flex; 
    justify-content:space-between; 
    align-items:center; 
    transition:all 0.15s;
    min-height:48px;
}
.folder-item:active { transform:scale(0.98); }
.folder-item.active { background:#00aaff; color:#fff; }
.folder-count { 
    font-size:10px; 
    background:#1a1a1a; 
    padding:4px 8px; 
    border-radius:12px;
}

/* メインライブラリ */
#main-lib { 
    flex:1; 
    display:flex; 
    flex-direction:column; 
    background:#0a0a0a;
    overflow:hidden;
}

.lib-header { 
    padding:16px; 
    background:#111; 
    border-bottom:1px solid #222;
    position:sticky;
    top:0;
    z-index:100;
}
.lib-title { margin:0 0 4px 0; font-size:20px; font-weight:600; }
.lib-stats { font-size:12px; color:#666; }

/* ビデオグリッド - モバイル最適化 */
#videoGrid { 
    flex:1; 
    overflow-y:auto; 
    padding:12px; 
    display:grid; 
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); 
    gap:12px; 
    align-content:start;
}

.card { 
    background:#151515; 
    border-radius:10px; 
    overflow:hidden; 
    cursor:pointer; 
    transition:all 0.2s; 
    aspect-ratio: 16/9; 
    position:relative; 
    border:2px solid transparent;
}
.card:active { transform:scale(0.95); }
.card.selected { border-color:#00ff88; box-shadow:0 0 12px rgba(0,255,136,0.4); }

.card-thumb { 
    height:100%; 
    background:#000; 
    display:flex; 
    align-items:center; 
    justify-content:center; 
    font-size:32px; 
    color:#333; 
    position:relative; 
    overflow:hidden;
}

.card-info { 
    position:absolute; 
    bottom:0; 
    width:100%; 
    background:linear-gradient(transparent, rgba(0,0,0,0.95)); 
    padding:10px; 
    font-size:11px;
}
.card-filename { 
    font-weight:500; 
    margin-bottom:4px; 
    white-space:nowrap; 
    overflow:hidden; 
    text-overflow:ellipsis;
}
.card-meta-row { 
    display:flex; 
    gap:6px; 
    font-size:9px; 
    color:#888; 
    flex-wrap:wrap;
}

.card-meta { 
    position:absolute; 
    top:6px; 
    left:6px; 
    display:flex; 
    gap:4px; 
    z-index:10;
}
.meta-btn { 
    background:rgba(0,0,0,0.85); 
    border-radius:6px; 
    padding:6px 8px; 
    font-size:14px; 
    cursor:pointer; 
    border:1px solid #333; 
    backdrop-filter:blur(10px); 
    transition:all 0.2s;
    min-width:32px;
    min-height:32px;
    display:flex;
    align-items:center;
    justify-content:center;
}
.meta-btn:active { transform:scale(0.9); }

/* ページネーション - モバイル最適化 */
.pagination { 
    padding:12px; 
    background:#111; 
    border-top:1px solid #222; 
    display:flex; 
    justify-content:center; 
    gap:8px; 
    align-items:center;
}
.page-btn { 
    padding:10px 16px; 
    background:#1a1a1a; 
    border:1px solid #333; 
    border-radius:8px; 
    cursor:pointer; 
    color:#999; 
    transition:all 0.2s;
    min-height:44px;
}
.page-btn:active { transform:scale(0.95); }
.page-btn.active { background:#00aaff; color:#fff; border-color:#00aaff; }
.page-btn.disabled { opacity:0.3; cursor:not-allowed; }

/* Shorts ビュー */
#shorts-view { 
    display:none; 
    width:100%; 
    height:100%; 
    overflow-y:scroll; 
    scroll-snap-type:y mandatory; 
    scroll-behavior:smooth;
}
.short-item { 
    width:100%; 
    height:100%; 
    scroll-snap-align:start; 
    position:relative; 
    display:flex; 
    align-items:center; 
    justify-content:center; 
    background:#000;
}
.short-video { 
    max-width:100%; 
    max-height:100%; 
    width:100%; 
    height:100%; 
    object-fit:contain;
}
.short-overlay { 
    position:absolute; 
    bottom:0; 
    left:0; 
    width:100%; 
    padding:20px; 
    background:linear-gradient(transparent, rgba(0,0,0,0.9)); 
    display:flex; 
    justify-content:space-between; 
    align-items:flex-end;
}
.short-info { max-width:70%; }
.short-folder-name { 
    font-size:11px; 
    color:#00aaff; 
    margin-bottom:6px; 
    font-weight:600;
}
.short-title { font-size:16px; margin-bottom:12px; font-weight:600; }
.short-actions { 
    display:flex; 
    flex-direction:column; 
    gap:12px;
}
.action-btn { 
    width:48px; 
    height:48px; 
    background:rgba(255,255,255,0.12); 
    border-radius:50%; 
    display:flex; 
    align-items:center; 
    justify-content:center; 
    cursor:pointer; 
    transition:all 0.2s; 
    backdrop-filter:blur(10px); 
    font-size:20px;
}
.action-btn:active { transform:scale(0.9); }

/* プレイヤーモーダル */
#playerModal { 
    display:none; 
    position:fixed; 
    top:0; 
    left:0; 
    width:100%; 
    height:100%; 
    background:#000; 
    z-index:3000;
}
#playerVideo { width:100%; height:100%; }
.player-ui { 
    position:absolute; 
    top:0; 
    left:0; 
    width:100%; 
    height:100%; 
    pointer-events:none; 
    display:flex; 
    flex-direction:column; 
    justify-content:space-between; 
    padding:16px; 
    opacity:0; 
    transition:opacity 0.3s;
}
#playerModal:hover .player-ui, 
#playerModal:active .player-ui { opacity:1; }

.player-header { 
    display:flex; 
    justify-content:space-between; 
    pointer-events:auto; 
    align-items:flex-start;
    flex-wrap:wrap;
    gap:8px;
}
.player-title { 
    background:rgba(0,0,0,0.85); 
    padding:10px 14px; 
    border-radius:8px; 
    backdrop-filter:blur(10px); 
    max-width:100%;
    font-size:14px;
}
.player-controls { 
    display:flex; 
    gap:8px; 
    flex-wrap:wrap;
}

.player-playback-controls {
    pointer-events:auto;
    padding: 12px 0;
    background: rgba(0,0,0,0.85);
    border-radius: 12px;
    margin-bottom: 12px;
    backdrop-filter: blur(10px);
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
}
.time-display {
    font-size: 12px;
    color: #ccc;
}
#playerSeek {
    width: 90%;
    height: 8px;
    -webkit-appearance: none;
    background: rgba(255,255,255,0.2);
    border-radius: 4px;
    cursor: pointer;
}
#playerSeek::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #00aaff;
    cursor: pointer;
}
.playback-buttons {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    justify-content: center;
}
.player-footer { 
    display:flex; 
    justify-content:center; 
    gap:12px; 
    pointer-events:auto;
    flex-wrap:wrap;
}

.ui-btn { 
    background:rgba(0,0,0,0.85); 
    color:#fff; 
    border:1px solid #444; 
    padding:10px 16px; 
    border-radius:24px; 
    cursor:pointer; 
    backdrop-filter:blur(10px); 
    transition:all 0.2s; 
    font-size:13px; 
    font-weight:500;
    min-height:44px;
}
.ui-btn:active { transform:scale(0.95); }

/* タグモーダル */
.tag-modal { 
    position:fixed; 
    left:50%; 
    top:50%; 
    transform:translate(-50%,-50%); 
    background:#111; 
    border:1px solid #333; 
    padding:20px; 
    z-index:4000; 
    display:none; 
    border-radius:12px; 
    min-width:min(400px, 90vw); 
    max-width:90vw;
    box-shadow:0 8px 32px rgba(0,0,0,0.5);
}
.tag-modal-title { font-size:18px; font-weight:600; margin-bottom:16px; }
.tag-input-row { display:flex; gap:8px; margin-bottom:16px; }
.tag-modal input { 
    flex:1; 
    padding:10px; 
    background:#1a1a1a; 
    border:1px solid #333; 
    color:#fff; 
    border-radius:8px; 
    font-size:13px;
}
.tag-list { 
    display:flex; 
    flex-wrap:wrap; 
    gap:8px; 
    margin-bottom:16px; 
    min-height:40px;
}
.tag-chip { 
    display:inline-flex; 
    align-items:center; 
    gap:6px; 
    padding:6px 12px; 
    background:#1a1a1a; 
    border:1px solid #333; 
    border-radius:16px; 
    font-size:12px;
}
.tag-chip button { 
    background:none; 
    border:none; 
    color:#999; 
    cursor:pointer; 
    font-size:14px; 
    padding:0; 
    margin-left:4px;
}
.modal-actions { 
    display:flex; 
    justify-content:flex-end; 
    gap:8px;
}

/* スキャンバー */
.scan-bar { 
    padding:12px; 
    background:#111; 
    border-bottom:1px solid #222; 
    display:flex; 
    gap:8px;
    flex-wrap:wrap;
}
.scan-bar input { 
    flex:1; 
    min-width:200px;
    background:#1a1a1a; 
    border:1px solid #333; 
    color:#fff; 
    padding:10px; 
    border-radius:8px; 
    font-size:13px;
}
.scan-bar button { 
    padding:10px 16px; 
    background:#00aaff; 
    border:none; 
    color:#fff; 
    border-radius:8px; 
    cursor:pointer; 
    font-weight:500; 
    transition:all 0.2s;
    min-height:44px;
}
.scan-bar button:active { transform:scale(0.95); }

/* 空メッセージ */
.empty-msg { 
    padding:40px 20px; 
    color:#666; 
    text-align:center;
}
.empty-msg-icon { font-size:48px; margin-bottom:12px; opacity:0.3; }

/* 統計パネル */
.stats-panel { 
    padding:12px; 
    background:#1a1a1a; 
    border-radius:8px; 
    margin-top:12px;
}
.stat-item { 
    display:flex; 
    justify-content:space-between; 
    padding:6px 0; 
    font-size:12px; 
    border-bottom:1px solid #222;
}
.stat-item:last-child { border-bottom:none; }
.stat-label { color:#999; }
.stat-value { color:#00aaff; font-weight:600; }

/* タグフィルターボタン */
.tag-filter-btn { 
    display:inline-block; 
    padding:6px 10px; 
    margin:4px; 
    background:#1a1a1a; 
    border:1px solid #333; 
    border-radius:12px; 
    cursor:pointer; 
    font-size:11px; 
    transition:all 0.2s;
}
.tag-filter-btn:active { transform:scale(0.95); }
.tag-filter-btn.active { background:#00aaff; border-color:#00aaff; color:#fff; }

/* ツールカード */
.tool-card { 
    background:#151515; 
    border:1px solid #222; 
    border-radius:12px; 
    padding:20px; 
    margin-bottom:16px;
}
.tool-card h4 { margin:0 0 8px 0; font-size:18px; }
.tool-card p { margin:0 0 12px 0; color:#999; font-size:14px; }

/* プレイリスト・履歴アイテム */
.playlist-item, .history-item { 
    background:#151515; 
    border:1px solid #222; 
    border-radius:8px; 
    padding:16px; 
    margin-bottom:12px; 
    cursor:pointer; 
    transition:all 0.2s;
}
.playlist-item:active, .history-item:active { transform:scale(0.98); }

/* ショートカットヘルプ */
#shortcutHelp {
    position:absolute;
    top:50%;
    left:50%;
    transform:translate(-50%,-50%);
    background:rgba(0,0,0,0.95);
    padding:24px;
    border-radius:12px;
    max-width:min(500px, 90vw);
    backdrop-filter:blur(10px);
    border:1px solid #333;
}

/* スクロールバー */
::-webkit-scrollbar { width:8px; height:8px; }
::-webkit-scrollbar-track { background:#0a0a0a; }
::-webkit-scrollbar-thumb { background:#333; border-radius:4px; }
::-webkit-scrollbar-thumb:hover { background:#555; }

/* モバイル対応 */
@media (max-width: 768px) {
    body {
        flex-direction: column;
    }
    
    .mobile-header { 
        display: block; 
    }
    
    .nav-rail {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        width: 100%;
        height: 70px;
        flex-direction: row;
        padding: 8px 0;
        border-right: none;
        border-top: 1px solid #222;
        z-index: 2000;
        justify-content: space-around;
    }
    
    .nav-item {
        width: 60px;
        height: 56px;
        margin: 0;
    }
    
    .nav-item::before {
        display: none;
    }
    
    .nav-icon {
        font-size: 22px;
    }
    
    .nav-label { 
        font-size: 10px; 
    }
    
    #content-area {
        padding-top: 56px;
        padding-bottom: 70px;
        flex: 1;
        width: 100%;
        height: 100vh;
    }
    
    #library-view {
        flex-direction: column;
        height: 100%;
        width: 100%;
    }
    
    #sidebar {
        width: 100%;
        max-height: 0;
        overflow: hidden;
        transition: max-height 0.3s ease;
        border-right: none;
        border-bottom: 1px solid #222;
        flex-shrink: 0;
    }
    
    #sidebar.open {
        max-height: 50vh;
        overflow-y: auto;
    }
    
    .sidebar-header {
        position: relative;
    }
    
    #main-lib {
        flex: 1;
        width: 100%;
        overflow: hidden;
        display: flex;
        flex-direction: column;
    }
    
    #videoGrid {
        grid-template-columns: repeat(2, 1fr);
        gap: 10px;
        padding: 10px;
        width: 100%;
    }
    
    .lib-header {
        padding: 12px 16px;
        flex-shrink: 0;
    }
    
    .lib-title { 
        font-size: 16px; 
    }
    
    .lib-stats {
        font-size: 11px;
    }
    
    .player-ui {
        padding: 12px;
    }
    
    .player-header {
        flex-direction: column;
        gap: 8px;
    }
    
    .player-title {
        max-width: 100%;
        width: 100%;
    }
    
    .player-controls {
        width: 100%;
        justify-content: flex-end;
    }
    
    .player-footer {
        flex-wrap: wrap;
        gap: 8px;
    }
    
    .ui-btn {
        font-size: 12px;
        padding: 8px 14px;
        min-height: 40px;
    }
    
    .short-overlay {
        padding: 16px 12px;
    }
    
    .short-title {
        font-size: 14px;
    }
    
    #folderList {
        max-height: none;
    }
    
    .folder-item {
        padding: 14px 12px;
    }
    
    .scan-bar {
        flex-direction: column;
    }
    
    .scan-bar input {
        width: 100%;
        min-width: 100%;
    }
    
    .scan-bar button {
        width: 100%;
    }
    
    .tag-modal {
        min-width: 90vw;
        padding: 16px;
    }
    
    .tool-card {
        padding: 16px;
    }
    
    .tool-card input {
        width: 100%;
        min-width: 100%;
    }
    
    .pagination {
        padding: 10px;
        flex-shrink: 0;
    }
    
    .page-btn {
        padding: 8px 12px;
        font-size: 12px;
    }
    
    #playlists-view,
    #history-view,
    #tools-view {
        padding: 12px;
        padding-top: 68px;
        padding-bottom: 82px;
        overflow-y: auto;
        height: 100vh;
    }
    
    .card-info {
        padding: 8px;
    }
    
    .card-filename {
        font-size: 11px;
    }
    
    .card-meta-row {
        font-size: 9px;
    }
    
    .meta-btn {
        min-width: 36px;
        min-height: 36px;
        font-size: 16px;
    }
    
    #shorts-view {
        padding-top: 56px;
        padding-bottom: 70px;
        height: 100vh;
    }
}

@media (max-width: 480px) {
    #videoGrid {
        grid-template-columns: repeat(2, 1fr);
        gap: 8px;
        padding: 8px;
    }
    
    .card-filename { 
        font-size: 10px; 
    }
    
    .card-meta-row { 
        font-size: 8px; 
    }
    
    .nav-item {
        width: 55px;
        height: 52px;
    }
    
    .nav-icon { 
        font-size: 20px; 
    }
    
    .nav-label { 
        font-size: 9px; 
    }
    
    .lib-title {
        font-size: 15px;
    }
    
    .filter-btn,
    .folder-item {
        padding: 12px 10px;
    }
    
    .ui-btn {
        padding: 8px 12px;
        font-size: 11px;
    }
    
    .player-footer .ui-btn {
        padding: 6px 10px;
    }
}

@media (min-width: 769px) {
    body {
        flex-direction: row;
    }
    
    .mobile-header {
        display: none;
    }
    
    .nav-rail {
        position: relative;
        width: 72px;
        height: auto;
        flex-direction: column;
        border-right: 1px solid #222;
        border-top: none;
    }
    
    #content-area {
        padding-bottom: 0;
        padding-top: 0;
    }
    
    #library-view {
        flex-direction: row;
    }
    
    #sidebar {
        width: 280px;
        max-height: none;
        overflow-y: auto;
        border-right: 1px solid #222;
        border-bottom: none;
    }
    
    #playlists-view,
    #history-view,
    #tools-view {
        padding: 24px;
        height: auto;
    }
}

/* プルトゥリフレッシュ */
.pull-to-refresh {
    position:absolute;
    top:-60px;
    left:0;
    right:0;
    height:60px;
    display:flex;
    align-items:center;
    justify-content:center;
    color:#00aaff;
    font-size:14px;
    transition:transform 0.3s;
}
.pull-to-refresh.active {
    transform:translateY(60px);
}

/* ローディングアニメーション */
.loading {
    display:inline-block;
    width:20px;
    height:20px;
    border:3px solid #333;
    border-top-color:#00aaff;
    border-radius:50%;
    animation:spin 1s linear infinite;
}
@keyframes spin {
    to { transform:rotate(360deg); }
}

/* タッチフィードバック改善 */
button, .card, .folder-item, .filter-btn, .nav-item, .action-btn, .meta-btn {
    -webkit-touch-callout:none;
    -webkit-user-select:none;
    user-select:none;
}

/* セーフエリア対応 */
@supports (padding: max(0px)) {
    .mobile-header, .nav-rail {
        padding-left: max(12px, env(safe-area-inset-left));
        padding-right: max(12px, env(safe-area-inset-right));
    }
    .nav-rail {
        padding-bottom: max(8px, env(safe-area-inset-bottom));
    }
}

</style>
</head>
<body>

<div class="mobile-header">
    <div class="header-content">
        <div class="header-title">📱 Video Manager</div>
        <button class="menu-btn" onclick="toggleMobileMenu()">☰ フィルター</button>
    </div>
</div>

<div class="nav-rail">
    <div class="nav-item active" id="btn-lib" onclick="switchTab('library')">
        <div class="nav-icon">📚</div>
        <div class="nav-label">ライブラリ</div>
    </div>
    <div class="nav-item" id="btn-shorts" onclick="switchTab('shorts')">
        <div class="nav-icon">🔥</div>
        <div class="nav-label">発見</div>
    </div>
    <div class="nav-item" id="btn-playlists" onclick="switchTab('playlists')">
        <div class="nav-icon">📋</div>
        <div class="nav-label">リスト</div>
    </div>
    <div class="nav-item" id="btn-history" onclick="switchTab('history')">
        <div class="nav-icon">🕐</div>
        <div class="nav-label">履歴</div>
    </div>
    <div class="nav-item" id="btn-tools" onclick="switchTab('tools')">
        <div class="nav-icon">🛠️</div>
        <div class="nav-label">ツール</div>
    </div>
</div>

<div id="content-area">
    
    <div id="library-view">
        <div id="sidebar">
            <div class="scan-bar">
                <input type="text" id="scanPath" placeholder="スキャンするフォルダパス..." value="">
                <button onclick="startScan()">🔍 Scan</button>
            </div>
            <div id="scanMsg" style="font-size:10px; color:#666; padding:8px 12px;"></div>
            
            <div class="sidebar-header">
                <input type="text" class="search-box" id="searchBox" placeholder="🔍 動画を検索..." onkeyup="handleSearch()">
                
                <div class="filter-section">
                    <div class="filter-title">フィルタ</div>
                    <div class="filter-btn" id="favFilter" onclick="toggleFavoriteFilter()">
                        <span>⭐ お気に入り</span>
                        <span id="favCount">0</span>
                    </div>
                </div>
                
                <div class="filter-section">
                    <div class="filter-title">並び替え</div>
                    <select class="sort-select" id="sortSelect" onchange="handleSort()">
                        <option value="modified_desc">📅 更新日時(新)</option>
                        <option value="modified_asc">📅 更新日時(古)</option>
                        <option value="name_asc">🔤 名前(A-Z)</option>
                        <option value="name_desc">🔤 名前(Z-A)</option>
                        <option value="play_count_desc">▶️ 再生回数順</option>
                        <option value="size_desc">📦 サイズ(大→小)</option>
                        <option value="size_asc">📦 サイズ(小→大)</option>
                    </select>
                </div>
                
                <div class="stats-panel" id="statsPanel">
                    <div class="stat-item">
                        <span class="stat-label">総動画数</span>
                        <span class="stat-value" id="statTotal">0</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">お気に入り</span>
                        <span class="stat-value" id="statFav">0</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">総サイズ</span>
                        <span class="stat-value" id="statSize">0</span>
                    </div>
                </div>
                
                <div class="filter-section" id="tagFilterSection" style="display:none;">
                    <div class="filter-title">人気タグ</div>
                    <div id="popularTags"></div>
                </div>
            </div>
            
            <div class="filter-section" style="padding:8px 12px;">
                <div class="filter-title">フォルダ</div>
            </div>
            
            <div id="folderList"></div>
        </div>
        
        <div id="main-lib">
            <div class="lib-header">
                <h3 class="lib-title" id="libTitle">すべての動画</h3>
                <div class="lib-stats" id="libStats">読み込み中...</div>
            </div>
            <div class="pull-to-refresh" id="pullToRefresh">
                <div class="loading"></div>
                <span style="margin-left:8px;">更新中...</span>
            </div>
            <div id="videoGrid"></div>
            <div class="pagination" id="pagination"></div>
        </div>
    </div>

    <div id="shorts-view"></div>
    
    <div id="playlists-view" style="display:none; padding:16px; overflow-y:auto;">
        <div class="lib-header" style="position:sticky; top:0; z-index:100;">
            <h3 class="lib-title">📋 プレイリスト</h3>
            <button class="ui-btn" onclick="createPlaylist()">➕ 新規作成</button>
        </div>
        <div id="playlistsContainer"></div>
    </div>
    
    <div id="history-view" style="display:none; padding:16px; overflow-y:auto;">
        <div class="lib-header" style="position:sticky; top:0; z-index:100;">
            <h3 class="lib-title">🕐 視聴履歴</h3>
        </div>
        <div id="historyContainer"></div>
    </div>
    
    <div id="tools-view" style="display:none; padding:16px; overflow-y:auto; background:#0a0a0a;">
        <div class="lib-header" style="position:sticky; top:0; z-index:100;">
            <h3 class="lib-title">🛠️ 管理ツール</h3>
        </div>
        <div style="max-width:800px; margin:0 auto;">
            <div class="tool-card">
                <h4>💾 データエクスポート</h4>
                <p>お気に入りやタグなどのメタデータをJSONで保存</p>
                <button class="ui-btn" onclick="exportData()">エクスポート</button>
            </div>
            
            <div class="tool-card">
                <h4>🏷️ 一括タグ編集</h4>
                <p>選択した動画にまとめてタグを追加</p>
                <div style="display:flex; gap:8px; margin-top:12px; flex-wrap:wrap;">
                    <input type="text" id="bulkTagInput" placeholder="追加するタグ" style="flex:1; min-width:200px; padding:10px; background:#1a1a1a; border:1px solid #333; color:#fff; border-radius:8px;">
                    <button class="ui-btn" onclick="bulkAddTags()">選択中の動画に追加</button>
                </div>
                <div style="margin-top:8px; color:#666; font-size:12px;">※ライブラリでCtrl+クリックで複数選択</div>
            </div>
            
            <div class="tool-card">
                <h4>⭐ 一括お気に入り追加</h4>
                <p>選択した動画をまとめてお気に入りに追加</p>
                <button class="ui-btn" onclick="bulkAddFavorites()">選択中の動画をお気に入りに</button>
            </div>
        </div>
    </div>

</div>

<div id="playerModal">
    <video id="playerVideo" autoplay playsinline></video>
    
    <div class="player-ui">
        <div class="player-header">
            <div class="player-title" id="playerTitle">Title</div>
            <div class="player-controls">
                <button class="ui-btn" id="playerFolderBtn" onclick="jumpToFolderFromPlayer()">📂</button>
                <button class="ui-btn" id="playerFavBtn" onclick="togglePlayerFavorite()">☆</button>
                <button class="ui-btn" onclick="closePlayer()">✕</button>
            </div>
        </div>
        <div class="player-playback-controls">
                <div class="time-display"><span id="currentTime">0:00</span> / <span id="durationTime">0:00</span></div>
                <input type="range" id="playerSeek" value="0" min="0" max="100" step="0.1" oninput="seekVideo(this.value)">
                <div class="playback-buttons">
                    <button class="ui-btn" onclick="pVideo.currentTime = Math.max(0, pVideo.currentTime - 10)">⏪ 10s</button>
                    <button class="ui-btn" id="playPauseBtn" onclick="togglePlayPause()">⏯ 再生</button>
                    <button class="ui-btn" onclick="pVideo.currentTime = Math.min(pVideo.duration, pVideo.currentTime + 10)">10s ⏩</button>
                    <button class="ui-btn" onclick="pVideo.muted = !pVideo.muted" id="muteBtn">🔊</button>
                    <button class="ui-btn" onclick="toggleFullscreen()">⛶ 全画面</button>
                </div>
            </div>
            <div class="player-footer">
            <button class="ui-btn" onclick="playPrev()">⮜ 前へ</button>
            <button class="ui-btn" onclick="togglePlayPause()">⏯ 再生</button>
            <button class="ui-btn" onclick="toggleFullscreen()">⛶ 全画面</button>
            <button class="ui-btn" onclick="playNext()">次へ ⮞</button>
        </div>
    </div>
    
    <div id="shortcutHelp" style="display:none;">
        <h3 style="margin:0 0 20px 0; text-align:center;">⌨️ キーボードショートカット</h3>
        <div style="display:grid; grid-template-columns:120px 1fr; gap:12px; font-size:14px;">
            <div style="color:#00aaff; font-weight:600;">Space / K</div><div>再生/一時停止</div>
            <div style="color:#00aaff; font-weight:600;">← / →</div><div>前/次の動画</div>
            <div style="color:#00aaff; font-weight:600;">J / L</div><div>10秒戻る/進む</div>
            <div style="color:#00aaff; font-weight:600;">↑ / ↓</div><div>音量アップ/ダウン</div>
            <div style="color:#00aaff; font-weight:600;">F</div><div>全画面切り替え</div>
            <div style="color:#00aaff; font-weight:600;">M</div><div>ミュート切り替え</div>
            <div style="color:#00aaff; font-weight:600;">S</div><div>お気に入り登録</div>
            <div style="color:#00aaff; font-weight:600;">Esc</div><div>プレイヤーを閉じる</div>
        </div>
        <div style="text-align:center; margin-top:20px;">
            <button class="ui-btn" onclick="toggleShortcutHelp()">閉じる</button>
        </div>
    </div>
</div>

<div id="tagModal" class="tag-modal">
    <div class="tag-modal-title">🏷️ タグ編集</div>
    <div class="tag-input-row">
        <input id="tagInput" placeholder="タグを入力してEnter" onkeypress="if(event.key==='Enter')addTagToCurrent()">
        <button class="ui-btn" onclick="addTagToCurrent()">追加</button>
    </div>
    <div class="tag-list" id="tagList"></div>
    <div class="modal-actions">
        <button class="ui-btn" onclick="closeTagModal()" style="background:#333;">キャンセル</button>
        <button class="ui-btn" onclick="saveTags()">💾 保存</button>
    </div>
</div>

<script>
let currentLib = [];
let currentIndex = 0;
let shortsData = [];
let scanTimer = null;
let shortObserver = null;
let tagModalState = { video_id: null, tags: [] };
let searchTimeout = null;
let selectedVideos = new Set();
let currentFolderForJump = null;

let currentViewState = {
    folder: null,
    title: 'すべての動画',
    favoritesOnly: false,
    search: '',
    sort: 'modified_desc',
    page: 1,
    perPage: 50,
    total: 0,
    tagFilter: ''
};

// プルトゥリフレッシュ
let pullStartY = 0;
let pulling = false;

const videoGrid = document.getElementById('videoGrid');
const pullIndicator = document.getElementById('pullToRefresh');

videoGrid.addEventListener('touchstart', (e) => {
    if (videoGrid.scrollTop === 0) {
        pullStartY = e.touches[0].clientY;
        pulling = true;
    }
}, { passive: true });

videoGrid.addEventListener('touchmove', (e) => {
    if (!pulling) return;
    const touchY = e.touches[0].clientY;
    const pullDistance = touchY - pullStartY;
    
    if (pullDistance > 0 && videoGrid.scrollTop === 0) {
        pullIndicator.classList.add('active');
    }
}, { passive: true });

videoGrid.addEventListener('touchend', () => {
    if (pulling && pullIndicator.classList.contains('active')) {
        loadLibrary();
        loadStats();
        setTimeout(() => {
            pullIndicator.classList.remove('active');
        }, 1000);
    }
    pulling = false;
    pullStartY = 0;
}, { passive: true });

window.onload = () => {
    history.replaceState({tab: 'library'}, '', '#library');
    loadStats();
    loadFolders();
    loadLibrary();
};

function toggleMobileMenu() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('open');
    // フィルターが開いたときにスクロールをリセット
    if (sidebar.classList.contains('open')) {
        sidebar.scrollTop = 0;
    }
}

window.addEventListener('popstate', (event) => {
    const pModal = document.getElementById('playerModal');
    if (pModal.style.display === 'flex') {
        if (!event.state || event.state.modal !== 'player') {
            closePlayer(false);
        }
    }
    if (event.state && event.state.tab) {
        switchTab(event.state.tab, false);
    }
});

async function loadStats() {
    try {
        const res = await fetch('/api/stats');
        const data = await res.json();
        document.getElementById('statTotal').innerText = data.total;
        document.getElementById('statFav').innerText = data.favorites;
        document.getElementById('statSize').innerText = data.total_size;
        document.getElementById('favCount').innerText = data.favorites;
        
        if (data.tags && data.tags.length > 0) {
            const tagSection = document.getElementById('tagFilterSection');
            const tagContainer = document.getElementById('popularTags');
            tagSection.style.display = 'block';
            tagContainer.innerHTML = data.tags.slice(0, 10).map(t => 
                `<span class="tag-filter-btn" onclick="filterByTag('${t.name}')">${t.name} (${t.count})</span>`
            ).join('');
        }
    } catch (e) {
        console.error('Stats load error:', e);
    }
}

function filterByTag(tag) {
    currentViewState.tagFilter = currentViewState.tagFilter === tag ? '' : tag;
    currentViewState.page = 1;
    document.querySelectorAll('.tag-filter-btn').forEach(btn => {
        if (btn.textContent.startsWith(tag)) btn.classList.toggle('active');
        else btn.classList.remove('active');
    });
    loadLibrary();
}

function switchTab(mode, pushHistory = true) {
    document.querySelectorAll('.nav-item').forEach(e => e.classList.remove('active'));
    document.getElementById('library-view').style.display = 'none';
    document.getElementById('shorts-view').style.display = 'none';
    document.getElementById('playlists-view').style.display = 'none';
    document.getElementById('history-view').style.display = 'none';
    document.getElementById('tools-view').style.display = 'none';
    
    if (mode === 'library') {
        document.getElementById('btn-lib').classList.add('active');
        document.getElementById('library-view').style.display = 'flex';
        stopShorts();
    } else if (mode === 'shorts') {
        document.getElementById('btn-shorts').classList.add('active');
        document.getElementById('shorts-view').style.display = 'block';
        loadShorts();
    } else if (mode === 'playlists') {
        document.getElementById('btn-playlists').classList.add('active');
        document.getElementById('playlists-view').style.display = 'block';
        loadPlaylists();
    } else if (mode === 'history') {
        document.getElementById('btn-history').classList.add('active');
        document.getElementById('history-view').style.display = 'block';
        loadHistory();
    } else if (mode === 'tools') {
        document.getElementById('btn-tools').classList.add('active');
        document.getElementById('tools-view').style.display = 'block';
    }

    if (pushHistory) {
        history.pushState({tab: mode}, '', '#' + mode);
    }
}

function toggleFavoriteFilter() {
    currentViewState.favoritesOnly = !currentViewState.favoritesOnly;
    currentViewState.page = 1;
    const btn = document.getElementById('favFilter');
    btn.classList.toggle('active');
    loadLibrary();
}

function handleSearch() {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        currentViewState.search = document.getElementById('searchBox').value;
        currentViewState.page = 1;
        loadLibrary();
    }, 500);
}

function handleSort() {
    currentViewState.sort = document.getElementById('sortSelect').value;
    currentViewState.page = 1;
    loadLibrary();
}

async function loadFolders() {
    const res = await fetch('/api/folders');
    const data = await res.json();
    const list = document.getElementById('folderList');
    list.innerHTML = '';
    
    const allBtn = document.createElement('div');
    allBtn.className = 'folder-item';
    allBtn.innerHTML = '<span>📂 すべての動画</span><span class="folder-count">ALL</span>';
    allBtn.onclick = () => {
        currentViewState.folder = null;
        currentViewState.title = 'すべての動画';
        currentViewState.page = 1;
        document.querySelectorAll('.folder-item').forEach(e => e.classList.remove('active'));
        allBtn.classList.add('active');
        loadLibrary();
    };
    list.appendChild(allBtn);

    data.folders.forEach(f => {
        const d = document.createElement('div');
        d.className = 'folder-item';
        d.title = f.path;
        d.innerHTML = `<span>📁 ${f.name}</span><span class="folder-count">${f.count}</span>`;
        d.onclick = () => {
            currentViewState.folder = f.path;
            currentViewState.title = f.name;
            currentViewState.page = 1;
            document.querySelectorAll('.folder-item').forEach(e => e.classList.remove('active'));
            d.classList.add('active');
            loadLibrary();
        };
        list.appendChild(d);
    });
}

async function loadLibrary() {
    const offset = (currentViewState.page - 1) * currentViewState.perPage;
    const params = new URLSearchParams({
        limit: currentViewState.perPage,
        offset: offset,
        favorites_only: currentViewState.favoritesOnly,
        search: currentViewState.search,
        sort: currentViewState.sort,
        tag: currentViewState.tagFilter
    });
    
    if (currentViewState.folder) {
        params.append('folder', currentViewState.folder);
    }
    
    const url = `/api/videos?${params.toString()}`;
    const res = await fetch(url);
    const data = await res.json();
    currentLib = data.videos;
    currentViewState.total = data.total;

    let displayTitle = currentViewState.title;
    if (currentViewState.favoritesOnly) displayTitle += ' (お気に入り)';
    if (currentViewState.search) displayTitle += ` - "${currentViewState.search}"`;
    if (currentViewState.tagFilter) displayTitle += ` - #${currentViewState.tagFilter}`;
    
    document.getElementById('libTitle').innerText = displayTitle;
    document.getElementById('libStats').innerText = `${data.total}件の動画`;

    const grid = document.getElementById('videoGrid');
    grid.innerHTML = '';

    if (currentLib.length === 0) {
        const msg = document.createElement('div');
        msg.className = 'empty-msg';
        msg.innerHTML = '<div class="empty-msg-icon">🔭</div>';
        if (currentViewState.search) {
            msg.innerHTML += `<div>「${currentViewState.search}」に一致する動画が見つかりませんでした</div>`;
        } else if (currentViewState.favoritesOnly) {
            msg.innerHTML += '<div>お気に入りに登録された動画がありません</div>';
        } else {
            msg.innerHTML += '<div>このフォルダに動画がありません</div>';
            if (currentViewState.folder) {
                const btn = document.createElement('button');
                btn.className = 'ui-btn';
                btn.style.marginTop = '10px';
                btn.innerText = 'このフォルダをスキャン';
                btn.onclick = () => { document.getElementById('scanPath').value = currentViewState.folder; startScan(); };
                msg.appendChild(document.createElement('br'));
                msg.appendChild(btn);
            }
        }
        grid.appendChild(msg);
        renderPagination();
        return;
    }

    currentLib.forEach((v, idx) => {
        const c = document.createElement('div');
        c.className = 'card';
        c.dataset.videoId = v.id;
        
        const tags = v.tags.filter(t => t).slice(0, 2).map(t => `<span style="background:#333;padding:2px 6px;border-radius:4px;font-size:10px;">#${t}</span>`).join(' ');
        
        c.innerHTML = `
            <div class="card-meta">
                <div class="meta-btn" onclick="toggleFavorite(event, ${v.id})" title="お気に入り">${v.favorite ? '★' : '☆'}</div>
                <div class="meta-btn" onclick="openTagModal(${v.id}, ${JSON.stringify(v.tags).replace(/"/g, '&quot;')})" title="タグ編集">🏷️</div>
            </div>
            <div class="card-thumb">
                <div style="font-size:48px;">🎬</div>
            </div>
            <div class="card-info">
                <div class="card-filename" title="${v.filename}">${v.filename}</div>
                <div class="card-meta-row">
                    <span>▶️ ${v.play_count}</span>
                    <span>📦 ${v.size_str}</span>
                    ${tags}
                </div>
            </div>
        `;
        
        c.onclick = (e) => { 
            if (e.target.closest('.meta-btn')) return;
            
            if (e.ctrlKey || e.metaKey) {
                if (selectedVideos.has(v.id)) {
                    selectedVideos.delete(v.id);
                    c.classList.remove('selected');
                } else {
                    selectedVideos.add(v.id);
                    c.classList.add('selected');
                }
            } else {
                selectedVideos.clear();
                document.querySelectorAll('.card.selected').forEach(card => card.classList.remove('selected'));
                openPlayer(idx);
            }
        };
        grid.appendChild(c);
    });
    
    renderPagination();
}

function renderPagination() {
    const container = document.getElementById('pagination');
    container.innerHTML = '';
    const totalPages = Math.ceil(currentViewState.total / currentViewState.perPage);
    if (totalPages <= 1) return;
    
    const prevBtn = document.createElement('button');
    prevBtn.className = 'page-btn' + (currentViewState.page === 1 ? ' disabled' : '');
    prevBtn.innerText = '← 前へ';
    prevBtn.onclick = () => {
        if (currentViewState.page > 1) {
            currentViewState.page--;
            loadLibrary();
            document.getElementById('videoGrid').scrollTop = 0;
        }
    };
    container.appendChild(prevBtn);
    
    const pageInfo = document.createElement('span');
    pageInfo.style.color = '#999';
    pageInfo.innerText = `${currentViewState.page} / ${totalPages}`;
    container.appendChild(pageInfo);
    
    const nextBtn = document.createElement('button');
    nextBtn.className = 'page-btn' + (currentViewState.page === totalPages ? ' disabled' : '');
    nextBtn.innerText = '次へ →';
    nextBtn.onclick = () => {
        if (currentViewState.page < totalPages) {
            currentViewState.page++;
            loadLibrary();
            document.getElementById('videoGrid').scrollTop = 0;
        }
    };
    container.appendChild(nextBtn);
}

const pModal = document.getElementById('playerModal');
const pVideo = document.getElementById('playerVideo');
let currentPlayingVideoId = null;
let swipeStartX = 0;
let swipeEndX = 0;
const SWIPE_THRESHOLD = 80; // スワイプと認識するピクセル数

function openPlayer(idx) {
    currentIndex = idx;
    const v = currentLib[idx];
    if(!v) return;
    
    currentPlayingVideoId = v.id;
    pModal.style.display = 'flex';
    pVideo.src = `/video/${v.id}`;
    document.getElementById('playerTitle').innerText = v.filename;
    updatePlayerFavoriteButton(v.favorite);
    
    try {
        const pathParts = v.path.split('/');
        pathParts.pop();
        const folderPath = pathParts.join('/');
        const folderName = pathParts.pop() || folderPath;
        
        currentFolderForJump = { path: folderPath, name: folderName };
        document.getElementById('playerFolderBtn').style.display = 'inline-block';
        document.getElementById('playerFolderBtn').title = `${folderName} を開く`;
    } catch(e) {
        document.getElementById('playerFolderBtn').style.display = 'none';
    }

    history.pushState({modal: 'player'}, '', '#player');

    fetch('/api/meta', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({video_id: v.id, action:'play'})});
    pVideo.play().catch(()=>{});
    
    // プレイヤーコントロールの初期化
    pVideo.onloadedmetadata = updatePlayerTime;
    pVideo.ontimeupdate = updatePlayerTime;
    pVideo.onended = playNext;
    pVideo.onplay = () => document.getElementById('playPauseBtn').innerHTML = '⏸ 一時停止';
    pVideo.onpause = () => document.getElementById('playPauseBtn').innerHTML = '▶️ 再生';
    pVideo.onvolumechange = () => document.getElementById('muteBtn').innerHTML = pVideo.muted ? '🔇' : '🔊';
    document.getElementById('playPauseBtn').innerHTML = pVideo.paused ? '▶️ 再生' : '⏸ 一時停止';
    document.getElementById('muteBtn').innerHTML = pVideo.muted ? '🔇' : '🔊';
}

function updatePlayerTime() {
    const current = formatTime(pVideo.currentTime);
    const duration = formatTime(pVideo.duration);
    document.getElementById('currentTime').innerText = current;
    document.getElementById('durationTime').innerText = duration;
    
    const seek = document.getElementById('playerSeek');
    if (!pVideo.seeking && pVideo.duration > 0) {
        seek.value = (pVideo.currentTime / pVideo.duration) * 100;
    }
}

function seekVideo(value) {
    if (pVideo.duration > 0) {
        const time = (value / 100) * pVideo.duration;
        pVideo.currentTime = time;
    }
}

function formatTime(seconds) {
    if (isNaN(seconds) || seconds === Infinity) return '0:00';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    const m_str = m.toString().padStart(h > 0 ? 2 : 1, '0');
    const s_str = s.toString().padStart(2, '0');
    return h > 0 ? `${h}:${m_str}:${s_str}` : `${m_str}:${s_str}`;
}

// スワイプ機能
pModal.addEventListener('touchstart', (e) => {
    // UI要素上でのタッチは無視
    if (e.target.closest('.player-ui')) return;
    swipeStartX = e.touches[0].clientX;
    swipeEndX = swipeStartX;
}, { passive: true });

pModal.addEventListener('touchmove', (e) => {
    // UI要素上でのタッチは無視
    if (e.target.closest('.player-ui')) return;
    swipeEndX = e.touches[0].clientX;
}, { passive: true });

pModal.addEventListener('touchend', () => {
    const diff = swipeStartX - swipeEndX;
    if (Math.abs(diff) > SWIPE_THRESHOLD) {
        if (diff > 0) {
            // 左スワイプ (次の動画)
            playNext();
        } else {
            // 右スワイプ (前の動画)
            playPrev();
        }
    }
    swipeStartX = 0;
    swipeEndX = 0;
});

function updatePlayerFavoriteButton(isFavorite) {
    const btn = document.getElementById('playerFavBtn');
    if (isFavorite) {
        btn.innerHTML = '★';
        btn.style.background = '#00aaff';
    } else {
        btn.innerHTML = '☆';
        btn.style.background = 'rgba(0,0,0,0.85)';
    }
}

async function togglePlayerFavorite() {
    if (!currentPlayingVideoId) return;
    
    await fetch('/api/meta', {
        method:'POST', 
        headers:{'Content-Type':'application/json'}, 
        body: JSON.stringify({video_id: currentPlayingVideoId, action:'toggle_favorite'})
    });
    
    const currentVideo = currentLib[currentIndex];
    if (currentVideo) {
        currentVideo.favorite = !currentVideo.favorite;
        updatePlayerFavoriteButton(currentVideo.favorite);
        const card = document.querySelector(`.card[data-video-id="${currentPlayingVideoId}"]`);
        if (card) {
            const metaBtn = card.querySelector('.meta-btn');
            if (metaBtn) metaBtn.innerText = currentVideo.favorite ? '★' : '☆';
        }
    }
    loadStats();
}

function closePlayer(goBack = true) {
    pModal.style.display = 'none';
    pVideo.pause();
    pVideo.src = '';
    currentPlayingVideoId = null;
    if (document.fullscreenElement) document.exitFullscreen();
    
    if (goBack && history.state && history.state.modal === 'player') {
        history.back();
    }
}

function jumpToFolderFromPlayer() {
    if (!currentFolderForJump) return;
    closePlayer(true);
    setTimeout(() => {
        jumpToFolder(currentFolderForJump.path, currentFolderForJump.name);
    }, 50);
}

function togglePlayPause() {
    const btn = document.getElementById('playPauseBtn');
    if (pVideo.paused) {
        pVideo.play();
        btn.innerHTML = '⏸ 一時停止';
    } else {
        pVideo.pause();
        btn.innerHTML = '▶️ 再生';
    }
}

function playNext() {
    if (currentIndex < currentLib.length - 1) {
        currentIndex++;
        const v = currentLib[currentIndex];
        
        currentPlayingVideoId = v.id;
        pVideo.src = `/video/${v.id}`;
        document.getElementById('playerTitle').innerText = v.filename;
        updatePlayerFavoriteButton(v.favorite);
        
        try {
            const pathParts = v.path.split('/');
            pathParts.pop();
            const folderPath = pathParts.join('/');
            const folderName = pathParts.pop() || folderPath;
            currentFolderForJump = { path: folderPath, name: folderName };
            document.getElementById('playerFolderBtn').title = `${folderName} を開く`;
        } catch(e){}

        fetch('/api/meta', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({video_id: v.id, action:'play'})});
        pVideo.play().catch(()=>{});
    }
}

function playPrev() {
    if (currentIndex > 0) {
        currentIndex--;
        const v = currentLib[currentIndex];
        currentPlayingVideoId = v.id;
        pVideo.src = `/video/${v.id}`;
        document.getElementById('playerTitle').innerText = v.filename;
        updatePlayerFavoriteButton(v.favorite);
        fetch('/api/meta', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({video_id: v.id, action:'play'})});
        pVideo.play().catch(()=>{});
    }
}

function toggleFullscreen() {
    if (!document.fullscreenElement) {
        pModal.requestFullscreen().catch(err => { alert(`Error: ${err.message}`); });
    } else {
        document.exitFullscreen();
    }
}

function toggleShortcutHelp() {
    const helpDiv = document.getElementById('shortcutHelp');
    helpDiv.style.display = helpDiv.style.display === 'none' ? 'block' : 'none';
}

document.addEventListener('keydown', e => {
    if (pModal.style.display !== 'flex') return;
    if (e.code === 'Space') { e.preventDefault(); togglePlayPause(); }
    if (e.code === 'ArrowRight') { e.preventDefault(); playNext(); }
    if (e.code === 'ArrowLeft') { e.preventDefault(); playPrev(); }
    if (e.key.toLowerCase() === 'f') { e.preventDefault(); toggleFullscreen(); }
    if (e.key === 'Escape') { e.preventDefault(); closePlayer(); }
    if (e.key.toLowerCase() === 's') { e.preventDefault(); togglePlayerFavorite(); }
    if (e.key.toLowerCase() === 'j') { e.preventDefault(); pVideo.currentTime = Math.max(0, pVideo.currentTime - 10); }
    if (e.key.toLowerCase() === 'l') { e.preventDefault(); pVideo.currentTime = Math.min(pVideo.duration, pVideo.currentTime + 10); }
    if (e.key.toLowerCase() === 'k') { e.preventDefault(); togglePlayPause(); }
    if (e.key.toLowerCase() === 'm') { e.preventDefault(); pVideo.muted = !pVideo.muted; }
    if (e.code === 'ArrowUp') { e.preventDefault(); pVideo.volume = Math.min(1, pVideo.volume + 0.1); }
    if (e.code === 'ArrowDown') { e.preventDefault(); pVideo.volume = Math.max(0, pVideo.volume - 0.1); }
});

async function toggleFavorite(e, video_id) {
    e.stopPropagation();
    await fetch('/api/meta', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({video_id, action:'toggle_favorite'})});
    loadStats();
    loadLibrary();
}

function openTagModal(video_id, tags) {
    tagModalState.video_id = video_id;
    tagModalState.tags = Array.isArray(tags) ? tags.filter(t => t) : [];
    updateTagList();
    document.getElementById('tagModal').style.display = 'block';
    document.getElementById('tagInput').focus();
}

function updateTagList() {
    const html = tagModalState.tags.map(t => 
        `<span class="tag-chip">${t}<button onclick="removeTag('${t.replace(/'/g, "\\'")}')">×</button></span>`
    ).join('');
    document.getElementById('tagList').innerHTML = html || '<div style="color:#666;font-size:12px;">タグがありません</div>';
}

function closeTagModal() { document.getElementById('tagModal').style.display = 'none'; }
function addTagToCurrent() {
    const input = document.getElementById('tagInput');
    const val = input.value.trim();
    if (!val) return;
    if (!tagModalState.tags.includes(val)) {
        tagModalState.tags.push(val);
        updateTagList();
    }
    input.value = '';
    input.focus();
}
function removeTag(tag) {
    tagModalState.tags = tagModalState.tags.filter(t => t !== tag);
    updateTagList();
}
async function saveTags() {
    const tags = tagModalState.tags.join(',');
    await fetch('/api/meta', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({video_id: tagModalState.video_id, action:'set_tags', tags})});
    closeTagModal();
    loadLibrary();
    loadStats();
}

async function loadShorts() {
    const container = document.getElementById('shorts-view');
    if(container.children.length > 0 && shortObserver) return;
    
    if(container.children.length > 0) {
        reinitializeShortsObserver();
        return;
    }
    
    container.innerHTML = '<div style="padding:40px;text-align:center;color:#666;">🔥 動画を探しています...</div>';
    const res = await fetch('/api/shorts');
    const data = await res.json();
    shortsData = data.shorts;
    container.innerHTML = '';
    shortsData.forEach(v => {
        const item = document.createElement('div');
        item.className = 'short-item';
        item.innerHTML = `
            <video class="short-video" data-src="/video/${v.id}" preload="none" muted playsinline loop></video>
            <div class="short-overlay">
                <div class="short-info">
                    <div class="short-folder-name">📂 ${v.folder_name}</div>
                    <div class="short-title">${v.filename}</div>
                </div>
                <div class="short-actions">
                    <div class="action-btn" onclick="jumpToFolder('${v.folder_path.replace(/\\/g, "\\\\")}', '${v.folder_name.replace(/'/g, "\\'")}')">📂</div>
                    <div class="action-btn" onclick="toggleMute(this)">🔊</div>
                </div>
            </div>
        `;
        container.appendChild(item);
    });
    
    reinitializeShortsObserver();
    
    container.addEventListener('wheel', e => {
        if (Math.abs(e.deltaY) > 40) {
            e.preventDefault();
            if (e.deltaY > 0) container.scrollBy({top: window.innerHeight, behavior: 'smooth'});
            else container.scrollBy({top: -window.innerHeight, behavior: 'smooth'});
        }
    }, { passive: false });
}

function stopShorts() {
    if (shortObserver) {
        shortObserver.disconnect();
        shortObserver = null;
    }
    document.querySelectorAll('.short-video').forEach(v => {
        try { v.pause(); v.removeAttribute('src'); } catch(e) {}
    });
}

function reinitializeShortsObserver() {
    if (shortObserver) shortObserver.disconnect();
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            const vid = entry.target.querySelector('video');
            if (!vid) return;
            if (entry.isIntersecting && entry.intersectionRatio >= 0.85) {
                if (!vid.src) {
                    vid.src = vid.dataset.src;
                    const id = vid.dataset.src.split('/').pop();
                    fetch('/api/meta', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({video_id: parseInt(id), action:'play'})});
                }
                vid.play().catch(()=>{});
            } else {
                vid.pause();
                try { vid.currentTime = 0; } catch(e) {}
            }
        });
    }, { threshold: 0.85 });
    
    document.querySelectorAll('.short-item').forEach(el => observer.observe(el));
    shortObserver = observer;
}

function toggleMute(btn) {
    const video = btn.closest('.short-item').querySelector('video');
    video.muted = !video.muted;
    btn.innerText = video.muted ? '🔇' : '🔊';
}

function jumpToFolder(path, name) {
    switchTab('library');
    currentViewState.folder = path;
    currentViewState.title = name;
    currentViewState.page = 1;
    loadLibrary();
    document.querySelectorAll('.folder-item').forEach(e => {
        if (e.title === path) e.classList.add('active');
        else e.classList.remove('active');
    });
}

async function startScan() {
    const path = document.getElementById('scanPath').value.trim();
    if (!path) { alert('スキャンするフォルダパスを入力してください'); return; }
    await fetch('/api/scan', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({directory:path})});
    document.getElementById('scanMsg').innerText = 'スキャン開始...';
    scanTimer = setInterval(async()=>{
        const r = await fetch('/api/scan/status');
        const d = await r.json();
        document.getElementById('scanMsg').innerText = `📊 ${d.processed}/${d.total} 処理中...`;
        if(!d.is_scanning) { 
            clearInterval(scanTimer); 
            document.getElementById('scanMsg').innerText = '✅ スキャン完了';
            loadFolders();
            loadStats();
            loadLibrary();
            setTimeout(() => { document.getElementById('scanMsg').innerText = ''; }, 3000);
        }
    }, 1000);
}

async function loadPlaylists() {
    const res = await fetch('/api/playlists');
    const data = await res.json();
    const container = document.getElementById('playlistsContainer');
    if (data.playlists.length === 0) {
        container.innerHTML = '<div class="empty-msg"><div class="empty-msg-icon">📋</div><div>プレイリストがありません</div></div>';
        return;
    }
    container.innerHTML = data.playlists.map(p => `
        <div class="playlist-item">
            <h4>${p.name}</h4>
            <div style="color:#666; font-size:12px;">${p.video_ids.length}件の動画 - ${new Date(p.created * 1000).toLocaleDateString()}</div>
            <div style="margin-top:8px;">
                <button class="ui-btn" style="padding:6px 12px;" onclick="deletePlaylist(${p.id})">🗑️ 削除</button>
            </div>
        </div>
    `).join('');
}

async function createPlaylist() {
    if (selectedVideos.size === 0) { alert('プレイリストに追加する動画を選択してください'); return; }
    const name = prompt('プレイリスト名を入力してください:', '新しいプレイリスト');
    if (!name) return;
    await fetch('/api/playlists', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ name: name, video_ids: Array.from(selectedVideos) })
    });
    alert('プレイリストを作成しました!');
    selectedVideos.clear();
    document.querySelectorAll('.card.selected').forEach(c => c.classList.remove('selected'));
    loadPlaylists();
}

async function deletePlaylist(id) {
    if (!confirm('このプレイリストを削除しますか?')) return;
    await fetch('/api/playlists', {
        method: 'DELETE',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({id: id})
    });
    loadPlaylists();
}

async function loadHistory() {
    const res = await fetch('/api/stats');
    const data = await res.json();
    const container = document.getElementById('historyContainer');
    if (!data.recent_watched || data.recent_watched.length === 0) {
        container.innerHTML = '<div class="empty-msg"><div class="empty-msg-icon">🕐</div><div>視聴履歴がありません</div></div>';
        return;
    }
    container.innerHTML = data.recent_watched.map(h => `
        <div class="history-item">
            <div>
                <div style="font-weight:500;">${h.filename}</div>
                <div style="font-size:11px; color:#666;">${new Date(h.watched_at * 1000).toLocaleString()}</div>
            </div>
            <button class="ui-btn" style="padding:8px 12px;" onclick="playVideoById(${h.id})">▶️</button>
        </div>
    `).join('');
}

function playVideoById(videoId) {
    switchTab('library');
    setTimeout(() => {
        const idx = currentLib.findIndex(v => v.id === videoId);
        if (idx >= 0) openPlayer(idx);
    }, 500);
}

async function exportData() {
    window.location.href = '/api/export';
    alert('データをエクスポートしました!');
}

async function bulkAddTags() {
    if (selectedVideos.size === 0) { alert('タグを追加する動画を選択してください'); return; }
    const tags = document.getElementById('bulkTagInput').value.trim();
    if (!tags) { alert('追加するタグを入力してください'); return; }
    await fetch('/api/bulk_action', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ action: 'add_tags', video_ids: Array.from(selectedVideos), tags: tags })
    });
    alert(`${selectedVideos.size}件の動画にタグを追加しました!`);
    selectedVideos.clear();
    document.querySelectorAll('.card.selected').forEach(c => c.classList.remove('selected'));
    document.getElementById('bulkTagInput').value = '';
    loadLibrary();
    loadStats();
}

async function bulkAddFavorites() {
    if (selectedVideos.size === 0) { alert('お気に入りに追加する動画を選択してください'); return; }
    await fetch('/api/bulk_action', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ action: 'add_favorite', video_ids: Array.from(selectedVideos) })
    });
    alert(`${selectedVideos.size}件の動画をお気に入りに追加しました!`);
    selectedVideos.clear();
    document.querySelectorAll('.card.selected').forEach(c => c.classList.remove('selected'));
    loadStats();
    loadLibrary();
}
</script>
</body>
</html>
"""

def open_browser():
    try:
        webbrowser.open(f'http://{LOCAL_IP}:5000')
    except:
        pass

import socket

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip

LOCAL_IP = get_local_ip()

if __name__ == '__main__':
    Thread(target=open_browser, daemon=True).start()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
        use_reloader=False
    )