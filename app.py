
import os
import re
import urllib.parse
import html
import shutil
import tempfile
from http.server import SimpleHTTPRequestHandler, HTTPServer

ROOT_DIR = '/root/hermes_shared'
TEXT_EXTS = {'.txt', '.py', '.yml', '.yaml', '.json', '.sh', '.md', '.ini', '.log', '.html', '.css', '.js', '.env', '.conf'}

class UploadHandler(SimpleHTTPRequestHandler):
    def get_current_rel_path(self):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        rel_path = params.get('path', [''])[0].strip('/')
        # 路径安全清理
        safe_path = os.path.normpath(rel_path).replace('..', '')
        if safe_path == '.' or safe_path == '/' or not safe_path:
            return ''
        return safe_path

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed_path.query)
        rel_dir = self.get_current_rel_path()
        
        # 定义当前文件夹的绝对路径
        current_abs_dir = os.path.join(ROOT_DIR, rel_dir)

        # 1. 处理强制下载 (?download=filename)
        if 'download' in query:
            filename = query['download'][0]
            f_path = os.path.join(current_abs_dir, filename)
            if os.path.exists(f_path) and os.path.isfile(f_path):
                self.send_response(200)
                self.send_header('Content-type', 'application/octet-stream')
                self.send_header('Content-Disposition', f'attachment; filename="{urllib.parse.quote(filename)}"')
                self.send_header('Content-Length', str(os.path.getsize(f_path)))
                self.end_headers()
                with open(f_path, 'rb') as f: shutil.copyfileobj(f, self.wfile)
                return

        # 2. 处理预览/编辑界面 (?preview=filename)
        if 'preview' in query:
            filename = query['preview'][0]
            edit_mode = 'edit' in query
            f_path = os.path.join(current_abs_dir, filename)
            if os.path.exists(f_path):
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                try:
                    with open(f_path, 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read()
                    
                    nav = f'<a href="/?path={urllib.parse.quote(rel_dir)}">Back to Files</a> / {filename}'
                    if not edit_mode:
                        lines = content.splitlines()
                        line_html = "".join([f'<div style="display:flex;"><span style="width:3.5em; color:#484f58; text-align:right; padding-right:15px; user-select:none; border-right:1px solid #30363d; margin-right:15px;">{i+1}</span><span style="white-space:pre-wrap;">{html.escape(l)}</span></div>' for i, l in enumerate(lines)])
                        btn = f'<a href="/?path={urllib.parse.quote(rel_dir)}&preview={urllib.parse.quote(filename)}&edit=1" class="edit-btn">进入编辑模式</a>'
                        body_content = f'<div class="content">{line_html}</div>'
                    else:
                        btn = f'<button onclick="saveFile()" class="save-btn">保存修改</button>'
                        body_content = f'<textarea id="editor" spellcheck="false" name="content">{html.escape(content)}</textarea>'

                    self.wfile.write(f'''
                    <html><head><title>{"编辑" if edit_mode else "预览"} - {filename}</title>
                    <style>
                        body {{ font-family: "SF Mono", Menlo, monospace; padding: 0; background: #0d1117; color: #c9d1d9; margin: 0; display:flex; flex-direction:column; height:100vh; }}
                        .nav {{ padding: 15px 30px; background: #161b22; border-bottom: 1px solid #30363d; font-family: -apple-system, sans-serif; display:flex; justify-content:space-between; align-items:center; }}
                        .nav a {{ color: #58a6ff; text-decoration: none; font-weight: 600; }}
                        .edit-btn, .save-btn {{ background: #238636; color: white; border: none; padding: 8px 16px; border-radius: 6px; font-weight: 600; cursor: pointer; text-decoration: none; font-size: 13px; }}
                        .content {{ padding: 20px 0; font-size: 13px; flex:1; overflow:auto; }}
                        textarea {{ width: 100%; flex: 1; background: #0d1117; color: #c9d1d9; border: none; padding: 30px; font-family: inherit; font-size: 14px; outline: none; resize: none; line-height: 1.6; }}
                    </style>
                    <script>
                        async function saveFile() {{
                            const btn = document.querySelector('.save-btn');
                            const content = document.getElementById('editor').value;
                            btn.innerText = '正在保存...';
                            const body = new URLSearchParams();
                            body.append('content', content);
                            try {{
                                const resp = await fetch("/save?path={urllib.parse.quote(rel_dir)}&file={urllib.parse.quote(filename)}", {{
                                    method: 'POST',
                                    headers: {{ 'Content-Type': 'application/x-www-form-urlencoded' }},
                                    body: body
                                }});
                                if (resp.ok) {{
                                    btn.innerText = '保存成功！';
                                    setTimeout(() => btn.innerText = '保存修改', 2000);
                                }} else {{ alert('保存失败'); btn.innerText = '保存修改'; }}
                            }} catch(e) {{ alert('保存错误: ' + e); btn.innerText = '保存修改'; }}
                        }}
                    </script>
                    </head>
                    <body><div class="nav"><div>{nav}</div>{btn}</div>{body_content}</body></html>
                    '''.encode())
                except Exception as e: self.send_error(500, str(e))
            return

        # 3. 处理新建/重命名/删除/ZIP
        if 'new_folder' in query:
            try:
                os.makedirs(os.path.join(current_abs_dir, query['new_folder'][0]), exist_ok=True)
                self.send_response(303); self.send_header('Location', f'/?path={urllib.parse.quote(rel_dir)}'); self.end_headers(); return
            except Exception as e: self.send_error(500, str(e)); return

        if 'rename' in query and 'newname' in query:
            try:
                os.rename(os.path.join(current_abs_dir, query['rename'][0]), os.path.join(current_abs_dir, query['newname'][0]))
                self.send_response(303); self.send_header('Location', f'/?path={urllib.parse.quote(rel_dir)}'); self.end_headers(); return
            except Exception as e: self.send_error(500, str(e)); return

        if 'delete' in query:
            target_p = os.path.join(current_abs_dir, query['delete'][0])
            try:
                if os.path.isdir(target_p): shutil.rmtree(target_p)
                else: os.remove(target_p)
                self.send_response(303); self.send_header('Location', f'/?path={urllib.parse.quote(rel_dir)}'); self.end_headers(); return
            except Exception as e: self.send_error(500, str(e)); return

        if 'zip' in query:
            target_p = os.path.join(current_abs_dir, query['zip'][0])
            try:
                with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
                    shutil.make_archive(tmp.name[:-4], 'zip', target_p)
                    z_path = tmp.name[:-4] + '.zip'
                with open(z_path, 'rb') as f:
                    self.send_response(200); self.send_header('Content-type', 'application/zip')
                    self.send_header('Content-Disposition', f'attachment; filename="{urllib.parse.quote(query["zip"][0])}.zip"')
                    self.end_headers(); shutil.copyfileobj(f, self.wfile)
                os.remove(z_path); return
            except Exception as e: self.send_error(500, str(e)); return

        # 4. 主界面渲染
        if parsed_path.path != '/': return super().do_GET()

        self.send_response(200); self.send_header('Content-type', 'text/html; charset=utf-8'); self.end_headers()
        path_parts = rel_dir.split('/') if rel_dir else []
        breadcrumb = '<a href="/">🏠 Root</a>'
        curr_acc = ""
        for p in path_parts:
            if not p: continue
            curr_acc = os.path.join(curr_acc, p)
            breadcrumb += f' <span style="color:#d0d7de; margin: 0 8px;">/</span> <a href="/?path={urllib.parse.quote(curr_acc)}">{p}</a>'

        html_content = f'''
        <!DOCTYPE html><html><head><title>Hermes Explorer v2.6</title><meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            :root {{ --primary: #0969da; --success: #2da44e; --border: #d0d7de; --bg: #f6f8fa; }}
            @keyframes slideUp {{ from {{ opacity:0; transform:translateY(15px); }} to {{ opacity:1; transform:translateY(0); }} }}
            body {{ font-family: -apple-system, sans-serif; background: var(--bg); color: #24292f; padding: 40px 20px; margin: 0; }}
            .main-card {{ max-width: 1100px; margin: auto; background: white; border: 1px solid var(--border); border-radius: 12px; box-shadow: 0 8px 24px rgba(149,157,165,0.1); animation: slideUp 0.4s ease-out; overflow: hidden; }}
            .header {{ padding: 20px 24px; border-bottom: 1px solid #f0f2f5; display:flex; justify-content: space-between; align-items: center; }}
            .breadcrumb {{ font-size: 18px; font-weight: 600; }}
            .breadcrumb a {{ color: var(--primary); text-decoration: none; }}
            .search-box {{ flex: 1; padding: 6px 12px; border: 1px solid var(--border); border-radius: 6px; font-size: 14px; margin-left: 20px; }}
            .toolbar {{ display: flex; gap: 15px; padding: 16px 24px; background: #fafafa; border-bottom: 1px solid #f0f2f5; align-items: center; }}
            .btn {{ padding: 6px 14px; font-size: 13px; font-weight: 600; border-radius: 6px; cursor: pointer; border: 1px solid rgba(27,31,36,0.15); transition: 0.2s; text-decoration: none; display: inline-flex; align-items: center; }}
            .btn-green {{ background: var(--success); color: white; }}
            .btn-white {{ background: white; color: #24292f; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th {{ text-align: left; padding: 12px 24px; background: #fafafa; border-bottom: 1px solid var(--border); font-size: 12px; color: #57606a; }}
            td {{ padding: 12px 24px; border-bottom: 1px solid #f6f8fa; font-size: 14px; transition: 0.1s; }}
            tr:hover td {{ background: #f9fbff; }}
            tr.hidden {{ display: none; }}
            .file-link {{ color: #24292f; text-decoration: none; font-weight: 500; display: flex; align-items: center; }}
            .icon {{ margin-right: 12px; font-size: 18px; }}
            .actions {{ opacity: 0; transition: 0.2s; text-align: right; }}
            tr:hover .actions {{ opacity: 1; }}
            .act-btn {{ color: #57606a; text-decoration: none; font-size: 12px; margin-left: 12px; font-weight: 600; cursor: pointer; }}
            .tag {{ padding: 2px 5px; border-radius: 4px; font-size: 10px; font-weight: 800; margin-left: 8px; background: #eff6ff; color: #1d4ed8; }}
            #loading-bar {{ position: fixed; top: 0; left: 0; height: 3px; background: var(--success); width: 0; transition: 0.3s; z-index: 9999; }}
        </style>
        <script>
            function startLoading() {{ document.getElementById('loading-bar').style.width = '100%'; }}
            function filterFiles() {{
                let val = document.getElementById('search').value.toLowerCase();
                document.querySelectorAll('tbody tr.file-row').forEach(row => {{
                    row.classList.toggle('hidden', !row.getAttribute('data-name').toLowerCase().includes(val));
                }});
            }}
            function createFolder() {{
                let name = prompt("文件夹名称:");
                if (name) window.location.href = "/?path=" + encodeURIComponent("{rel_dir}") + "&new_folder=" + encodeURIComponent(name);
            }}
            function rename(oldName) {{
                let name = prompt("重命名为:", oldName);
                if (name && name !== oldName) window.location.href = "/?path=" + encodeURIComponent("{rel_dir}") + "&rename=" + encodeURIComponent(oldName) + "&newname=" + encodeURIComponent(name);
            }}
        </script>
        </head><body><div id="loading-bar"></div><div class="main-card"><div class="header"><div class="breadcrumb">{breadcrumb}</div><input type="text" id="search" class="search-box" placeholder="🔍 搜索文件..." oninput="filterFiles()"></div><div class="toolbar"><form enctype="multipart/form-data" method="post" action="/upload?path={urllib.parse.quote(rel_dir)}" style="display:flex; align-items:center; gap:10px;"><input type="file" name="file" multiple webkitdirectory directory><button type="submit" class="btn btn-green">📤 上传</button></form><button onclick="createFolder()" class="btn btn-white">📁 新建</button></div><table><thead><tr><th style="padding:12px 24px;">名称</th><th style="text-align:right; padding:12px 24px;">操作 / 大小</th></tr></thead><tbody>
        '''
        
        try:
            items = sorted(os.listdir(current_abs_dir))
            if rel_dir: html_content += f'<tr><td colspan="2"><a href="/?path={urllib.parse.quote(os.path.dirname(rel_dir))}" class="file-link" style="color:#57606a;"><span class="icon">⇠</span> 返回上级</a></td></tr>'
            for d in [i for i in items if os.path.isdir(os.path.join(current_abs_dir, i))]:
                d_url = f"/?path={urllib.parse.quote(os.path.join(rel_dir, d))}"
                html_content += f'''<tr class="file-row" data-name="{html.escape(d)}"><td><a href="{d_url}" class="file-link"><span class="icon">📂</span> {d}</a></td><td class="actions"><span class="act-btn" onclick="rename('{html.escape(d)}')">改名</span><a href="/?path={urllib.parse.quote(rel_dir)}&zip={urllib.parse.quote(d)}" class="act-btn" style="color:var(--success)">打包</a><a href="/?path={urllib.parse.quote(rel_dir)}&delete={urllib.parse.quote(d)}" class="act-btn" style="color:#cf222e" onclick="return confirm('删除?')">删</a></td></tr>'''
            for f in [i for i in items if os.path.isfile(os.path.join(current_abs_dir, i))]:
                f_ext = os.path.splitext(f)[1].lower(); is_txt = f_ext in TEXT_EXTS
                prev_u = f"/?path={urllib.parse.quote(rel_dir)}&preview={urllib.parse.quote(f)}"
                dl_u = f"/?path={urllib.parse.quote(rel_dir)}&download={urllib.parse.quote(f)}"
                main_l = prev_u if is_txt else dl_u
                size = os.path.getsize(os.path.join(current_abs_dir, f)) / 1024
                html_content += f'''<tr class="file-row" data-name="{html.escape(f)}"><td><a href="{main_l}" class="file-link" {'target="_blank"' if is_txt else ''}><span class="icon">📄</span> {f} {('<span class="tag">EDIT</span>' if is_txt else '')}</a></td><td style="text-align:right;"><span style="color:#8b949e; font-size:12px; margin-right:10px;">{size:.1f} KB</span><span class="actions"><a href="{dl_u}" class="act-btn" style="color:var(--success)">下载</a><span class="act-btn" onclick="rename('{html.escape(f)}')">改名</span><a href="/?path={urllib.parse.quote(rel_dir)}&delete={urllib.parse.quote(f)}" class="act-btn" style="color:#cf222e" onclick="return confirm('删除?')">删</a></td></tr>'''
        except Exception as e: html_content += f'<tr><td colspan="2">Error: {e}</td></tr>'
        self.wfile.write((html_content + '</tbody></table></div><div style="text-align:center; padding:40px; color:#888; font-size:11px;">Hermes Explorer v2.6 • Pro Workstation</div></body></html>').encode())

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path); query = urllib.parse.parse_qs(parsed.query); rel_dir = self.get_current_rel_path()
        if parsed.path == '/save':
            f_name = query.get('file', [''])[0]; full_p = os.path.join(ROOT_DIR, rel_dir, f_name)
            content_length = int(self.headers.get('Content-Length'))
            body = self.rfile.read(content_length).decode('utf-8')
            content = urllib.parse.parse_qs(body).get('content', [''])[0]
            try:
                with open(full_p, 'w', encoding='utf-8') as f: f.write(content)
                self.send_response(200); self.end_headers(); return
            except Exception as e: self.send_error(500, str(e)); return

        if parsed.path.startswith('/upload'):
            try:
                upload_base = os.path.join(ROOT_DIR, rel_dir)
                boundary = self.headers.get('Content-Type').split("boundary=")[1].encode()
                remain_bytes = int(self.headers.get('Content-Length'))
                line = self.rfile.readline(); remain_bytes -= len(line)
                while remain_bytes > 0:
                    if boundary in line: line = self.rfile.readline(); remain_bytes -= len(line)
                    if remain_bytes <= 0: break
                    content_disposition = line.decode()
                    fn_match = re.findall(r'filename="(.*)"', content_disposition)
                    if not fn_match or not fn_match[0]:
                        while line.strip() and remain_bytes > 0: line = self.rfile.readline(); remain_bytes -= len(line)
                        continue
                    raw_fn = fn_match[0].replace('\\', '/')
                    target_path = os.path.join(upload_base, raw_fn.replace('../', ''))
                    while line.strip() and remain_bytes > 0: line = self.rfile.readline(); remain_bytes -= len(line)
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    with open(target_path, 'wb') as f:
                        pre_line = self.rfile.readline(); remain_bytes -= len(pre_line)
                        while remain_bytes > 0:
                            line = self.rfile.readline(); remain_bytes -= len(line)
                            if boundary in line:
                                pre_line = pre_line[0:-1]
                                if pre_line.endswith(b'\r'): pre_line = pre_line[0:-1]
                                f.write(pre_line); break
                            else: f.write(pre_line); pre_line = line
                self.send_response(303); self.send_header('Location', f'/?path={urllib.parse.quote(rel_dir)}'); self.end_headers()
            except Exception as e: self.send_error(500, str(e))

if __name__ == '__main__':
    os.makedirs(ROOT_DIR, exist_ok=True); os.chdir(ROOT_DIR)
    server = HTTPServer(('0.0.0.0', 8083), UploadHandler)
    print("Hermes Explorer v2.6 Ready..."); server.serve_forever()
