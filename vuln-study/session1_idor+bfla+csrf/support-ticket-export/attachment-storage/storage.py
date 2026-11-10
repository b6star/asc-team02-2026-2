import os
import secrets
import xml.etree.ElementTree as ET

from flask import Flask, Response, jsonify, render_template, request
from werkzeug.utils import secure_filename


app = Flask(__name__)
files = {}
BOT_BASE = os.getenv("BOT_BASE", "http://gateway:8080")
MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024


def detect_image_type(content):
    """파일 내용으로 허용된 이미지 형식을 판별합니다."""
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    try:
        root = ET.fromstring(content)
        if root.tag in ("svg", "{http://www.w3.org/2000/svg}svg"):
            return "image/svg+xml"
    except (ET.ParseError, UnicodeDecodeError):
        pass
    return None


@app.get("/health")
def health():
    return jsonify(status="ok")


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/files")
def save_file():
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        return jsonify(error="업로드할 파일을 선택해 주세요."), 400
    filename = secure_filename(uploaded.filename)
    content = uploaded.read(MAX_ATTACHMENT_BYTES + 1)
    if not content or len(content) > MAX_ATTACHMENT_BYTES:
        return jsonify(error="첨부파일은 비어 있지 않은 5MB 이하의 파일이어야 합니다."), 400
    content_type = detect_image_type(content)
    if content_type is None:
        return jsonify(error="PNG, JPG, GIF, WEBP, SVG 이미지만 업로드할 수 있습니다."), 400
    file_id = secrets.token_hex(4)
    files[file_id] = {
        "filename": filename,
        "content": content,
        "content_type": content_type,
    }
    return jsonify(
        filename=filename,
        fileId=file_id,
        contentType=content_type,
        reviewUrl=f"{BOT_BASE}/files/{file_id}",
    )


@app.get("/files/<file_id>")
def uploaded_file(file_id):
    uploaded = files.get(file_id)
    if uploaded is None:
        return "첨부파일을 찾을 수 없습니다.", 404
    return Response(uploaded["content"], content_type=uploaded["content_type"])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)

