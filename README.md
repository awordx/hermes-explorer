
# Hermes Explorer - Web File Manager & IDE

A lightweight, high-performance web-based file manager and IDE built with Python. Designed for rapid file management, code editing, and directory organization directly through your browser.

![Hermes Explorer](https://img.shields.io/badge/Status-Pro_Workstation-blue)
![Version](https://img.shields.io/badge/Version-2.6_Final-green)

## 🚀 Features

- **📂 Layered Browsing**: Navigate through your directory structure just like a native file explorer.
- **📥 Smart Download/ZIP**: Download individual files or package entire folders into ZIP archives on the fly.
- **👁️ Dark Mode Preview**: Built-in code preview with syntax-like line numbering and a "GitHub Dark" inspired theme.
- **✍️ Online Web IDE**: Edit your code files directly in the browser and save them back to the server instantly.
- **🔍 Real-time Search**: Instant client-side filtering to find files in large directories.
- **📤 Directory Upload**: Supports uploading multiple files and entire folders (preserving structure).
- **🛠️ Management Tools**: Rename, delete, and create folders with safety confirmations.
- **✨ Modern UI**: Smooth CSS animations, loading progress bars, and responsive design.

## 🐳 Docker Deployment

The fastest way to get started is using Docker.

### 1. Pull Image (from Aliyun CR)
```bash
docker pull crpi-zutrieltt9z6q9p7.cn-shanghai.personal.cr.aliyuncs.com/awordx/file_share:v1.0
```

### 2. Run Container
```bash
docker run -d \
  --name hermes-explorer \
  -p 8083:8083 \
  -v /your/local/share:/root/hermes_shared \
  --restart always \
  crpi-zutrieltt9z6q9p7.cn-shanghai.personal.cr.aliyuncs.com/awordx/file_share:v1.0
```

## 🛠️ Manual Installation (Python 3.13+)

No dependencies required beyond the Python standard library.

```bash
python3 app.py
```
Access via: `http://localhost:8083`

## ⚙️ Configuration

By default, the server shares `/root/hermes_shared`. You can modify `ROOT_DIR` in `app.py` to point to any local directory.

---
*Created by awordx.*
