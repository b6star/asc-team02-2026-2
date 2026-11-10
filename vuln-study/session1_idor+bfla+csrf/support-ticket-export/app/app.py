import os
import json
import hashlib
import re
import secrets
import sqlite3
import struct
import time
import zlib
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from flask import (
    Flask,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_sock import Sock
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "support.db"))
FLAG = os.getenv("FLAG", "ASC{n0_d1r3ct_4cc3ss_n0_pr0bl3m_l3t_4dm1n_sh4r3_1t}")
BOT_URL = os.getenv("BOT_URL", "http://127.0.0.1:3000")
STORAGE_URL = os.getenv("STORAGE_URL", "http://127.0.0.1:5001")
ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN", "local-admin-bot-token")
MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024
BITMAP_FONT = {
    "A": ("010", "101", "111", "101", "101"), "B": ("110", "101", "110", "101", "110"),
    "C": ("011", "100", "100", "100", "011"), "D": ("110", "101", "101", "101", "110"),
    "E": ("111", "100", "110", "100", "111"), "F": ("111", "100", "110", "100", "100"),
    "G": ("011", "100", "101", "101", "011"), "H": ("101", "101", "111", "101", "101"),
    "I": ("111", "010", "010", "010", "111"), "J": ("001", "001", "001", "101", "010"),
    "K": ("101", "101", "110", "101", "101"), "L": ("100", "100", "100", "100", "111"),
    "M": ("101", "111", "111", "101", "101"), "N": ("101", "111", "111", "111", "101"),
    "O": ("010", "101", "101", "101", "010"), "P": ("110", "101", "110", "100", "100"),
    "Q": ("010", "101", "101", "111", "011"), "R": ("110", "101", "110", "101", "101"),
    "S": ("011", "100", "010", "001", "110"), "T": ("111", "010", "010", "010", "010"),
    "U": ("101", "101", "101", "101", "111"), "V": ("101", "101", "101", "101", "010"),
    "W": ("101", "101", "111", "111", "101"), "X": ("101", "101", "010", "101", "101"),
    "Y": ("101", "101", "010", "010", "010"), "Z": ("111", "001", "010", "100", "111"),
    "0": ("111", "101", "101", "101", "111"), "1": ("010", "110", "010", "010", "111"),
    "2": ("110", "001", "010", "100", "111"), "3": ("110", "001", "010", "001", "110"),
    "4": ("101", "101", "111", "001", "001"), "5": ("111", "100", "110", "001", "110"),
    "6": ("011", "100", "111", "101", "111"), "7": ("111", "001", "010", "010", "010"),
    "8": ("111", "101", "111", "101", "111"), "9": ("111", "101", "111", "001", "110"),
    "#": ("101", "111", "101", "111", "101"), "-": ("000", "000", "111", "000", "000"),
    ".": ("000", "000", "000", "000", "010"), " ": ("000", "000", "000", "000", "000"),
}


def make_sample_png(seed=0, variant=0):
    """문의 종류와 번호에 따라 서로 다른 화면 형태의 PNG를 생성합니다."""
    width, height = 640, 360
    accent = (55 + seed * 29 % 155, 90 + seed * 17 % 130, 150 + seed * 11 % 90)
    pixels = bytearray(bytes((244, 247, 252)) * width * height)

    def rect(left, top, right, bottom, color):
        left, top = max(0, left), max(0, top)
        right, bottom = min(width, right), min(height, bottom)
        fill = bytes(color) * max(0, right - left)
        for y in range(top, bottom):
            start = (y * width + left) * 3
            pixels[start:start + len(fill)] = fill

    def circle(cx, cy, radius, color):
        for y in range(max(0, cy - radius), min(height, cy + radius + 1)):
            span = int(max(0, radius * radius - (y - cy) ** 2) ** 0.5)
            rect(cx - span, y, cx + span + 1, y + 1, color)

    def draw_text(x, y, text, color, scale=2):
        cursor = x
        for character in text.upper():
            glyph = BITMAP_FONT.get(character, BITMAP_FONT[" "])
            for row_index, row in enumerate(glyph):
                for column_index, pixel in enumerate(row):
                    if pixel == "1":
                        rect(
                            cursor + column_index * scale,
                            y + row_index * scale,
                            cursor + (column_index + 1) * scale,
                            y + (row_index + 1) * scale,
                            color,
                        )
            cursor += 4 * scale

    # 브라우저에서 캡처한 서비스 화면처럼 보이는 공통 프레임입니다.
    rect(0, 0, width, 48, (25, 32, 52))
    circle(25, 24, 10, accent)
    draw_text(43, 18, "HELPDESK", (236, 240, 248), 2)
    draw_text(470, 20, "SUPPORT", (151, 163, 187), 1)
    draw_text(535, 20, "ACCOUNT", (151, 163, 187), 1)
    circle(608, 24, 12, (225, 230, 240))
    rect(0, 48, 132, height, (231, 236, 246))
    navigation = ("HOME", "ORDERS", "CART", "COUPON", "HELP")
    for item in range(5):
        y = 82 + item * 43
        circle(22, y, 6, accent if item == variant % 5 else (172, 182, 201))
        draw_text(38, y - 4, navigation[item], (109, 122, 148), 1)
    page_titles = (
        "ORDER TRACKING", "RETURN REQUEST", "WRONG ITEM", "COUPON ERROR",
        "PAYMENT STATUS", "ADDRESS CHANGE", "DAMAGE REPORT", "RESTOCK ALERT",
    )
    page_subtitles = (
        "DELIVERY DETAILS", "REQUEST DETAILS", "ITEM COMPARISON", "COUPON DETAILS",
        "PAYMENT DETAILS", "ADDRESS DETAILS", "DAMAGE DETAILS", "ALERT SETTINGS",
    )
    draw_text(166, 72, page_titles[variant % len(page_titles)], (39, 48, 70), 3)
    draw_text(166, 99, page_subtitles[variant % len(page_subtitles)], (143, 154, 175), 1)

    if variant == 0:  # 로그인/비밀번호 화면
        rect(245, 125, 535, 326, (255, 255, 255))
        circle(390, 154, 21, accent)
        rect(282, 190, 498, 218, (242, 244, 249))
        rect(282, 230, 498, 258, (242, 244, 249))
        rect(282, 275, 498, 307, accent)
        draw_text(302, 286, "SEARCH", (245, 248, 255), 2)
        draw_text(287, 199, "ORDER ID", (142, 153, 173), 1)
        draw_text(287, 239, "PHONE", (142, 153, 173), 1)
    elif variant == 1:  # 결제 내역 표
        rect(166, 126, 604, 326, (255, 255, 255))
        rect(184, 144, 586, 174, (232, 238, 249))
        draw_text(198, 154, "ITEM", (91, 104, 128), 1)
        draw_text(305, 154, "REASON", (91, 104, 128), 1)
        draw_text(505, 154, "STATUS", (91, 104, 128), 1)
        for row in range(4):
            y = 188 + row * 30
            circle(198, y, 7, accent)
            rect(216, y - 4, 326 + row * 13, y + 3, (121, 133, 156))
            rect(448, y - 4, 555, y + 3, (91, 104, 128))
            rect(184, y + 13, 586, y + 14, (231, 234, 240))
    elif variant == 2:  # 프로필 설정
        rect(166, 126, 604, 326, (255, 255, 255))
        circle(232, 196, 42, accent)
        circle(232, 186, 14, (240, 243, 250))
        rect(205, 211, 259, 230, (240, 243, 250))
        for row in range(3):
            y = 154 + row * 48
            rect(306, y, 390, y + 7, (116, 128, 151))
            rect(306, y + 15, 560 - row * 20, y + 39, (241, 244, 249))
        rect(475, 288, 560, 313, accent)
        draw_text(491, 296, "SAVE", (255, 255, 255), 2)
        draw_text(306, 146, "ORDER", (116, 128, 151), 1)
        draw_text(306, 194, "EXPECTED", (116, 128, 151), 1)
        draw_text(306, 242, "RECEIVED", (116, 128, 151), 1)
    elif variant == 3:  # 알림 설정
        rect(166, 126, 604, 326, (255, 255, 255))
        for row in range(4):
            y = 153 + row * 41
            circle(195, y + 10, 12, (226, 232, 243))
            rect(218, y + 1, 355 + row * 18, y + 8, (92, 105, 130))
            rect(218, y + 15, 420, y + 21, (183, 191, 207))
            rect(522, y, 568, y + 22, accent if (seed + row) % 2 else (197, 204, 216))
            circle(557 if (seed + row) % 2 else 533, y + 11, 8, (255, 255, 255))
            draw_text(218, y + 1, ("COUPON", "CART", "DISCOUNT", "TOTAL")[row], (92, 105, 130), 1)
    elif variant == 4:  # 모바일 화면 캡처
        rect(166, 126, 604, 326, (255, 255, 255))
        rect(340, 135, 466, 322, (32, 39, 57))
        rect(347, 147, 459, 307, (242, 245, 250))
        rect(347, 147, 459, 176, accent)
        draw_text(360, 157, "PAYMENT", (255, 255, 255), 1)
        for row in range(3):
            rect(358, 190 + row * 35, 448, 216 + row * 35, (255, 255, 255))
            circle(369, 203 + row * 35, 6, accent)
            rect(382, 199 + row * 35, 435, 205 + row * 35, (156, 166, 184))
            draw_text(382, 198 + row * 35, ("ORDER", "PAYMENT", "TOTAL")[row], (112, 123, 143), 1)
        circle(403, 315, 4, (152, 161, 178))
    elif variant == 5:  # 회원정보 입력 폼
        rect(166, 126, 604, 326, (255, 255, 255))
        for row in range(3):
            y = 148 + row * 48
            rect(192, y, 270, y + 7, (99, 112, 137))
            rect(292, y - 7, 566, y + 22, (241, 244, 249))
        rect(458, 292, 566, 316, accent)
        draw_text(478, 300, "SAVE", (255, 255, 255), 2)
        for row, label in enumerate(("NAME", "PHONE", "ADDRESS")):
            draw_text(196, 150 + row * 48, label, (99, 112, 137), 1)
    elif variant == 6:  # 첨부파일 목록
        rect(166, 126, 604, 326, (255, 255, 255))
        for row in range(4):
            y = 145 + row * 42
            rect(188, y, 216, y + 31, (228, 234, 245))
            rect(194, y + 6, 210, y + 10, accent)
            rect(234, y + 4, 390 + row * 15, y + 11, (87, 101, 127))
            rect(234, y + 18, 322, y + 24, (182, 191, 207))
            circle(558, y + 15, 4, (135, 148, 172))
            draw_text(234, y + 4, f"PHOTO {row + 1}", (87, 101, 127), 1)
    else:  # 도움말/FAQ
        rect(166, 126, 604, 326, (255, 255, 255))
        rect(190, 145, 578, 178, (239, 243, 250))
        circle(211, 161, 7, accent)
        draw_text(228, 157, "SEARCH ITEM", (126, 138, 160), 1)
        for row in range(3):
            y = 196 + row * 36
            circle(201, y + 8, 10, (227, 233, 244))
            rect(224, y + 3, 490 - row * 17, y + 10, (92, 105, 130))
            rect(224, y + 17, 548, y + 22, (190, 198, 213))
            draw_text(224, y + 3, ("EMAIL", "PUSH", "RESTOCK")[row], (92, 105, 130), 1)

    rows = []
    for y in range(height):
        start = y * width * 3
        rows.append(b"\x00" + bytes(pixels[start:start + width * 3]))

    def chunk(kind, data):
        return (
            struct.pack(">I", len(data)) + kind + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"".join(rows), 9))
        + chunk(b"IEND", b"")
    )


SAMPLE_PNG = make_sample_png(7238, 0)

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", "local-development-secret"),
    SESSION_COOKIE_NAME="support_session",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)
sock = Sock(app)


def get_db():
    """요청마다 사용할 SQLite 연결을 생성합니다."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    """실습에 필요한 사용자와 티켓 데이터를 초기화합니다."""
    Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with get_db() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                workspace TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS attachments (
                id INTEGER PRIMARY KEY,
                reference TEXT UNIQUE,
                filename TEXT NOT NULL,
                content TEXT NOT NULL,
                content_type TEXT NOT NULL DEFAULT 'text/plain',
                review_url TEXT,
                workspace TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY,
                reference TEXT UNIQUE,
                title TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                opened_at TEXT NOT NULL DEFAULT '',
                claimed_by TEXT,
                body TEXT NOT NULL DEFAULT '',
                answer TEXT,
                owner_id INTEGER NOT NULL,
                workspace TEXT NOT NULL,
                classification TEXT NOT NULL,
                attachment_id INTEGER NOT NULL,
                exportable INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(owner_id) REFERENCES users(id),
                FOREIGN KEY(attachment_id) REFERENCES attachments(id)
            );

            CREATE TABLE IF NOT EXISTS export_jobs (
                id TEXT PRIMARY KEY,
                ticket_id INTEGER NOT NULL,
                creator_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                content TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'private',
                share_token TEXT UNIQUE,
                FOREIGN KEY(ticket_id) REFERENCES tickets(id),
                FOREIGN KEY(creator_id) REFERENCES users(id)
            );
            """
        )

        # 이전 버전의 볼륨을 그대로 사용해도 공개 문의 번호를 추가합니다.
        ticket_columns = {
            column["name"] for column in db.execute("PRAGMA table_info(tickets)").fetchall()
        }
        if "reference" not in ticket_columns:
            db.execute("ALTER TABLE tickets ADD COLUMN reference TEXT")
        for column_name, definition in (
            ("status", "TEXT NOT NULL DEFAULT 'open'"),
            ("opened_at", "TEXT NOT NULL DEFAULT ''"),
            ("claimed_by", "TEXT"),
            ("body", "TEXT NOT NULL DEFAULT ''"),
            ("answer", "TEXT"),
        ):
            if column_name not in ticket_columns:
                db.execute(f"ALTER TABLE tickets ADD COLUMN {column_name} {definition}")
        db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_tickets_reference ON tickets(reference)"
        )

        attachment_columns = {
            column["name"]
            for column in db.execute("PRAGMA table_info(attachments)").fetchall()
        }
        if "reference" not in attachment_columns:
            db.execute("ALTER TABLE attachments ADD COLUMN reference TEXT")
        if "content_type" not in attachment_columns:
            db.execute(
                "ALTER TABLE attachments ADD COLUMN content_type TEXT NOT NULL DEFAULT 'text/plain'"
            )
        if "review_url" not in attachment_columns:
            db.execute("ALTER TABLE attachments ADD COLUMN review_url TEXT")
        db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_attachments_reference ON attachments(reference)"
        )

        db.execute(
            "INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?)",
            (1, "admin", generate_password_hash("admin-not-for-players"), "admin", "internal"),
        )
        db.execute(
            "INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?)",
            (2, "customer11", generate_password_hash("givemetheflag"), "customer", "public"),
        )
        db.execute(
            "UPDATE users SET username = ?, password_hash = ?, role = 'customer' WHERE id = 2",
            ("customer11", generate_password_hash("givemetheflag")),
        )
        fake_customers = tuple(
            f"customer{number:02d}" for number in range(1, 11)
        )
        for index, username in enumerate(fake_customers):
            db.execute(
                "INSERT OR IGNORE INTO users VALUES (?, ?, ?, 'customer', 'public')",
                (
                    100 + index,
                    username,
                    generate_password_hash(f"disabled-{username}"),
                ),
            )
        employee_accounts = (
            (200, "frontend01"), (201, "frontend02"), (202, "backend02"),
            (203, "platform01"), (204, "ops01"), (205, "security01"),
            (206, "support01"),
        )
        for user_id, username in employee_accounts:
            db.execute(
                "INSERT OR IGNORE INTO users VALUES (?, ?, ?, 'employee', 'internal')",
                (
                    user_id, username,
                    generate_password_hash(f"disabled-{username}"),
                ),
            )

        db.execute(
            """INSERT OR IGNORE INTO attachments
               (id, reference, filename, content, content_type, workspace)
               VALUES (5000, NULL, '', '', 'application/octet-stream', 'public')"""
        )
        db.execute(
            """INSERT OR IGNORE INTO attachments
               (id, reference, filename, content, content_type, workspace)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                5001, "c3d4e5f6", "delivery-address.png", sqlite3.Binary(SAMPLE_PNG),
                "image/png", "public",
            ),
        )
        db.execute(
            """INSERT OR IGNORE INTO attachments
               (id, reference, filename, content, content_type, workspace)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (9182, "a8f2c19e", "production-backup.txt", "", "text/plain", "internal"),
        )
        db.execute(
            """UPDATE attachments
               SET reference = 'c3d4e5f6', filename = 'delivery-address.png',
                   content = ?, content_type = 'image/png'
               WHERE id = 5001""",
            (sqlite3.Binary(SAMPLE_PNG),),
        )
        db.execute("UPDATE attachments SET reference = 'a8f2c19e' WHERE id = 9182")
        # 컨테이너를 다시 시작해 FLAG가 변경되어도 내부 첨부파일에 반영합니다.
        db.execute(
            "UPDATE attachments SET content = ? WHERE id = 9182",
            (f"Production credential backup\nFLAG={FLAG}\n",),
        )

        db.execute(
            """
            INSERT OR IGNORE INTO tickets
                (id, reference, title, status, opened_at, claimed_by, body,
                 owner_id, workspace, classification, attachment_id, exportable)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1001, "CS-261110-07238-seed00", "배송지 변경 문의", "closed",
                "2026년 11월 10일 오후 2:37", "고객지원팀", "주문한 상품의 배송지를 이전 주소에서 새 주소로 변경하고 싶습니다.",
                100, "public", "normal", 5001, 0,
            ),
        )
        db.execute(
            """
            INSERT OR IGNORE INTO tickets
                (id, reference, title, status, opened_at, claimed_by, body,
                 owner_id, workspace, classification, attachment_id, exportable)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                7231, "CS-261101-07209-d91a77", "운영 환경 인증 정보 백업", "closed",
                "2026년 11월 1일 오후 12:37", "운영 관리자", "운영 환경 백업 파일 보관 요청",
                1, "internal", "internal", 9182, 1,
            ),
        )
        db.execute(
            """UPDATE tickets SET reference = 'CS-261110-07238-seed00', title = '배송지 변경 문의', status = 'closed', exportable = 0,
               opened_at = '2026년 11월 10일 오후 2:37', claimed_by = '고객지원팀',
               body = '주문한 상품의 배송지를 이전 주소에서 새 주소로 변경하고 싶습니다.' WHERE id = 1001"""
        )

        # 목록이 실제 고객지원 서비스처럼 보이도록 10월 20일부터 문의 이력을 채웁니다.
        fake_topics = (
            ("배송 조회 문의", "배송 중으로 표시된 상품이 이틀째 같은 위치에 있습니다. 언제 받을 수 있는지 확인해 주세요.", "delivery-tracking.png"),
            ("반품 접수 요청", "상품 크기가 맞지 않아 반품하려고 합니다. 반품 수거 절차를 안내해 주세요.", "return-request.png"),
            ("다른 상품이 배송됐어요", "주문한 색상과 다른 상품이 도착했습니다. 교환 가능한지 확인 부탁드립니다.", "wrong-item.png"),
            ("할인 쿠폰 적용 문의", "장바구니에서 보유 중인 할인 쿠폰을 선택해도 결제 금액에 반영되지 않습니다.", "coupon-error.png"),
            ("결제 승인 내역 문의", "결제는 완료됐는데 주문 내역에 상품이 표시되지 않습니다. 결제 상태를 확인해 주세요.", "payment-receipt.png"),
            ("배송지 변경 요청", "상품이 출고되기 전에 배송지를 새 주소로 변경하고 싶습니다.", "address-change.png"),
            ("파손 상품 환불 문의", "배송받은 상품의 포장이 찢어져 있고 내부 상품도 파손되어 있습니다.", "damaged-package.png"),
            ("재입고 알림 문의", "품절된 상품의 재입고 알림을 신청했는데 알림을 받지 못했습니다.", "restock-alert.png"),
        )
        fake_answers = (
            "안녕하세요 고객님,\n배송 흐름을 확인한 결과 현재 지역 배송센터에서 이동 중입니다. 영업일 기준 1~2일 이내 배송될 예정이며 추가 지연이 발생하면 다시 안내드리겠습니다.\n감사합니다.",
            "안녕하세요 고객님,\n반품 접수가 완료되었습니다. 포장한 상품을 문 앞에 놓아 주시면 영업일 기준 2일 이내에 택배기사가 방문할 예정입니다.\n감사합니다.",
            "안녕하세요 고객님,\n오배송으로 불편을 드려 죄송합니다. 잘못 배송된 상품의 회수와 주문하신 상품의 재배송을 접수했습니다.\n감사합니다.",
            "안녕하세요 고객님,\n해당 쿠폰은 일부 할인 상품과 중복으로 사용할 수 없는 쿠폰으로 확인됩니다. 쿠폰 상세 조건을 확인한 뒤 적용 가능한 상품에서 사용해 주세요.\n감사합니다.",
            "안녕하세요 고객님,\n결제 승인 내역을 확인했으며 주문 정보 반영이 지연된 상태입니다. 결제 취소 없이 주문 내역에 정상 반영되도록 처리했습니다.\n감사합니다.",
            "안녕하세요 고객님,\n상품이 아직 출고 전인 것으로 확인되어 요청하신 주소로 배송지를 변경했습니다. 주문 상세 화면에서 변경된 주소를 확인해 주세요.\n감사합니다.",
            "안녕하세요 고객님,\n파손된 상품으로 불편을 드려 죄송합니다. 첨부해 주신 사진을 확인했으며 전액 환불과 상품 회수를 접수했습니다.\n감사합니다.",
            "안녕하세요 고객님,\n재입고 알림 신청 상태를 다시 등록했습니다. 상품이 입고되면 앱 알림과 이메일로 안내드리겠습니다.\n감사합니다.",
        )
        # 공개 문의 번호는 07209부터 07239까지만 사용합니다.
        db.execute("DELETE FROM export_jobs")
        db.execute("DELETE FROM tickets WHERE id BETWEEN 7160 AND 7200")
        db.execute("DELETE FROM attachments WHERE id BETWEEN 107160 AND 107200")
        fake_ticket_ids = list(range(7201, 7230))
        ordered_ticket_ids = [7231] + list(range(7201, 7229)) + [1001, 7229]
        public_tid_by_id = {
            ticket_id: 7209 + index
            for index, ticket_id in enumerate(ordered_ticket_ids)
        }
        order_by_id = {
            ticket_id: index for index, ticket_id in enumerate(ordered_ticket_ids)
        }
        for index, ticket_id in enumerate(fake_ticket_ids):
            public_tid = public_tid_by_id[ticket_id]
            ordered_index = order_by_id[ticket_id]
            date = (
                datetime(2026, 11, 11)
                if public_tid == 7239
                else datetime(2026, 11, 1)
                + timedelta(days=((public_tid - 7209) * 9 + 14) // 29)
            )
            image_variant = index % len(fake_topics)
            title, body, filename = fake_topics[image_variant]
            filename = f"{Path(filename).stem}-{public_tid}.png"
            hour = 9 + (index * 3) % 9
            minute = (index * 17) % 60
            period = "오전" if hour < 12 else "오후"
            display_hour = (hour - 1) % 12 + 1
            status = "waiting" if public_tid % 11 == 0 else "closed"
            confirmation_code = f"{(public_tid * 2654435761) & 0xFFFFFF:06x}"
            has_attachment = ticket_id == 7229 or public_tid % 2 == 0
            attachment_id = 100_000 + ticket_id if has_attachment else 5000
            owner_id = 2 if ticket_id == 7229 else 100 + index % len(fake_customers)
            attachment_reference = f"{(ticket_id * 2246822519) & 0xFFFFFFFF:08x}"
            if has_attachment:
                sample_content = make_sample_png(public_tid, image_variant)
                db.execute(
                    """
                    INSERT OR IGNORE INTO attachments
                        (id, reference, filename, content, content_type, workspace)
                    VALUES (?, ?, ?, ?, 'image/png', 'public')
                    """,
                    (
                        attachment_id, attachment_reference, filename,
                        sqlite3.Binary(sample_content),
                    ),
                )
                db.execute(
                    """UPDATE attachments
                       SET filename = ?, content = ?, content_type = 'image/png'
                       WHERE id = ?""",
                    (filename, sqlite3.Binary(sample_content), attachment_id),
                )
            db.execute(
                """
                INSERT OR IGNORE INTO tickets
                    (id, reference, title, status, opened_at, claimed_by, body,
                     owner_id, workspace, classification, attachment_id, exportable)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'public', 'normal', ?, 0)
                """,
                (
                    ticket_id,
                    f"CS-{date:%y%m%d}-{public_tid:05d}-{confirmation_code}",
                    title,
                    status,
                    f"{date.year}년 {date.month}월 {date.day}일 {period} "
                    f"{display_hour}:{minute:02d}",
                    None if status == "waiting" else "고객지원팀",
                    body,
                    owner_id,
                    attachment_id,
                ),
            )
            db.execute(
                """UPDATE tickets
                   SET reference = ?, title = ?, status = ?, opened_at = ?,
                       claimed_by = ?, body = ?, owner_id = ?, attachment_id = ?
                   WHERE id = ?""",
                (
                    f"CS-{date:%y%m%d}-{public_tid:05d}-{confirmation_code}", title, status,
                    f"{date.year}년 {date.month}월 {date.day}일 {period} "
                    f"{display_hour}:{minute:02d}",
                    None if status == "waiting" else "고객지원팀",
                    body, owner_id, attachment_id, ticket_id,
                ),
            )
            db.execute(
                "UPDATE tickets SET answer = ? WHERE id = ?",
                (fake_answers[image_variant] if status == "closed" else None, ticket_id),
            )
        db.execute(
            """UPDATE tickets
               SET reference = 'CS-261111-' || substr(reference, 11),
                   title = '11월 11일 빼빼로데이 이벤트 문의',
                   opened_at = '2026년 11월 11일 오전 11:11',
                   body = '오늘이 무슨 날이게요~? 11월 11일 빼빼로데이잖아요, 기념 이벤트나 쿠폰은 따로 없나요? 11월 11일 오늘 집에서 빼빼로 261111개째 먹으면서 이벤트 기다리고 있습니다.',
                   answer = '죄송하지만 현재 진행 중인 빼빼로데이 이벤트나 할인 쿠폰은 없습니다.'
               WHERE id = 7229"""
        )
        db.execute(
            "UPDATE attachments SET filename = 'event-banner.png' WHERE id = 107229"
        )
        db.execute(
            """UPDATE tickets
               SET title = '첨부파일 공유 기능 정리', classification = 'internal',
                   workspace = 'internal', owner_id = 200, claimed_by = 'backend02',
                   attachment_id = 5000,
                   body = '이번 고객 화면 개편에서 첨부파일 공유 버튼은 제거했습니다.\n운영 도구에서 사용 중인 Export 기능은 그대로 유지하는 게 맞을까요?',
                   answer = '운영팀에서 사용 중이라 관련 API는 당분간 유지합니다.\n프런트엔드 배포 파일에 남아 있는 호출 코드와 디버그 파일은 다음 배포 때 정리해 주세요.'
               WHERE id = 7220"""
        )
        db.execute(
            """UPDATE tickets
               SET title = 'SVG 이미지 미리보기가 안 됩니다', status = 'closed',
                   opened_at = '2026년 11월 4일 오전 10:20', claimed_by = '고객지원팀',
                   body = '상품 문의에 SVG 이미지를 첨부했는데 미리보기 대신 새 페이지로 열립니다. 다른 이미지처럼 화면에서 바로 확인할 수 있게 해주세요.',
                   answer = '안녕하세요 고객님,\n사용에 불편을 드려 죄송합니다.\nSVG 파일 형식이 현재 이미지 미리보기를 지원하지 않는 상황을 확인했습니다. 개발팀에게 전달하여 빠른 시일 내에 조치하겠습니다.',
                   owner_id = 108, workspace = 'public', classification = 'normal'
               WHERE id = 7209"""
        )
        db.execute(
            """UPDATE attachments
               SET filename = 'product-preview.svg',
                   content = '<svg xmlns="http://www.w3.org/2000/svg" width="320" height="120"><rect width="320" height="120" fill="#fff7ed"/><text x="24" y="68" font-size="20">Product preview</text></svg>',
                   content_type = 'image/svg+xml', workspace = 'public'
               WHERE id = 107209"""
        )
        db.execute(
            """UPDATE tickets
               SET title = 'SVG 미리보기 개선 요청', classification = 'internal',
                   workspace = 'internal', owner_id = 206, claimed_by = 'frontend02',
                   attachment_id = 5000,
                   opened_at = '2026년 11월 4일 오전 11:05',
                   body = '사용자로부터 SVG 파일이 미리보기로 표시되지 않고 별도 페이지로 열린다는 문의가 접수되었습니다.\nPNG와 JPG처럼 화면 안에서 바로 확인할 수 있도록 수정해 주세요.',
                   answer = '현재 SVG는 미리보기 이미지로 변환하지 않고 업로드된 원본 문서를 그대로 여는 방식입니다.\n일반 이미지와 동일하게 표시할 수 있도록 변환 처리 방안을 검토하겠습니다.'
               WHERE id = 7210"""
        )
        db.execute("DELETE FROM attachments WHERE id IN (107210, 107220)")
        db.execute(
            """UPDATE tickets SET reference = 'CS-261101-07209-d91a77',
               title = '운영 환경 인증 정보 백업', status = 'closed', owner_id = 204,
               opened_at = '2026년 11월 1일 오후 12:37', claimed_by = 'security01',
               body = '운영 환경 백업 파일 보관 요청',
               answer = '요청한 운영 환경 인증 정보 백업 파일의 보관을 완료했습니다.\n외부 공유가 필요한 경우 관리자 승인 후 공유 링크를 생성해 주세요.'
               WHERE id = 7231"""
        )
        # 07238번은 11월 10일에 등록된 일반 고객 문의입니다.
        ticket_7238_code = f"{(7238 * 2654435761) & 0xFFFFFF:06x}"
        db.execute(
            """UPDATE tickets
               SET reference = ?, title = '배송지 변경 문의', status = 'closed', exportable = 0,
                   opened_at = '2026년 11월 10일 오후 2:37', claimed_by = '고객지원팀',
                   body = '주문한 상품이 아직 출고 전인데 배송지를 이전 주소에서 새 주소로 변경하고 싶습니다.',
                   answer = '안녕하세요 고객님,\n상품이 아직 출고 전인 것으로 확인되어 요청하신 새 주소로 배송지를 변경했습니다. 주문 상세 화면에서 변경된 배송지를 확인해 주세요.\n감사합니다.',
                   owner_id = 100
               WHERE id = 1001""",
            (f"CS-261110-07238-{ticket_7238_code}",),
        )
        db.execute(
            """UPDATE tickets
               SET status = 'waiting', answer = NULL
               WHERE substr(reference, 4, 6) > '261110'"""
        )
        pepero = db.execute(
            """SELECT tickets.title, tickets.status, tickets.opened_at, tickets.claimed_by,
                      tickets.body, users.username, attachments.filename,
                      attachments.content_type
               FROM tickets
               JOIN users ON users.id = tickets.owner_id
               LEFT JOIN attachments ON attachments.id = tickets.attachment_id
               WHERE tickets.id = 7229"""
        ).fetchone()
        first_response_body = {
            "title": pepero["title"],
            "status": "답변 대기" if pepero["status"] == "waiting" else "처리 완료",
            "openedBy": pepero["username"],
            "openedAt": pepero["opened_at"],
            "claimedBy": pepero["claimed_by"] or "미배정",
            "reason": pepero["body"],
            "answer": None,
            "attachmentFilename": pepero["filename"],
            "attachmentContentType": pepero["content_type"],
        }
        response_hash = hashlib.sha256(
            json.dumps(
                first_response_body, ensure_ascii=False, sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()[:6]
        db.execute(
            "UPDATE tickets SET reference = ? WHERE id = 7229",
            (f"CS-261111-07239-{response_hash}",),
        )


def display_ticket_number(reference):
    """확인 코드를 제외한 공개 문의번호를 표시합니다."""
    matched = re.fullmatch(
        r"(CS-\d{6}-\d{5})(?:-([A-Za-z0-9]{1,32}))?", reference
    )
    return matched.group(1) if matched else reference


def ticket_code(reference):
    """공개 문의 링크에 사용하는 확인 코드를 반환합니다."""
    matched = re.fullmatch(
        r"CS-\d{6}-\d{5}(?:-([A-Za-z0-9]{1,32}))?", reference
    )
    return matched.group(1) if matched and matched.group(1) else None


def find_ticket_by_reference(db, reference):
    """취약점: code와 Ticket 소유권을 검사하지 않습니다."""
    matched = re.fullmatch(r"(CS-\d{6}-\d{5})", reference)
    if not matched:
        return None
    return db.execute(
        """SELECT tickets.*, users.username AS opened_by,
                  attachments.reference AS attachment_reference,
                  attachments.filename AS attachment_filename,
                  attachments.content_type AS attachment_content_type
           FROM tickets
           JOIN users ON users.id = tickets.owner_id
           LEFT JOIN attachments ON attachments.id = tickets.attachment_id
           WHERE substr(tickets.reference, 1, 15) = ?""",
        (matched.group(1),),
    ).fetchone()


def store_image(uploaded):
    """이미지를 내부 저장소에 전달하고 DB 보관용 정보를 반환합니다."""
    if not uploaded or not uploaded.filename:
        raise ValueError("첨부할 이미지를 선택해 주세요.")
    filename = secure_filename(uploaded.filename)
    content = uploaded.read(MAX_ATTACHMENT_BYTES + 1)
    if not content or len(content) > MAX_ATTACHMENT_BYTES:
        raise ValueError("첨부파일은 비어 있지 않은 5MB 이하의 파일이어야 합니다.")
    try:
        response = requests.post(
            f"{STORAGE_URL}/api/files",
            files={"file": (filename, content, uploaded.mimetype)},
            timeout=10,
        )
        result = response.json()
        if not response.ok:
            raise ValueError(result.get("error", "이미지를 저장하지 못했습니다."))
    except requests.RequestException as error:
        raise RuntimeError("첨부파일 저장소에 연결할 수 없습니다.") from error
    return result, content


def request_admin_review(review_url):
    """새 첨부파일을 관리자 봇의 검토 대기열에 전달합니다."""
    try:
        response = requests.post(f"{BOT_URL}/visit", json={"url": review_url}, timeout=15)
        response.raise_for_status()
    except requests.RequestException as error:
        raise RuntimeError("관리자 검토 서비스를 사용할 수 없습니다.") from error


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    with get_db() as db:
        return db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            if request.path.startswith("/api/"):
                return jsonify(error="로그인이 필요합니다."), 401
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user:
            return jsonify(error="Authentication required"), 401
        if user["role"] != "admin":
            return jsonify(error="Administrator role required"), 403
        return view(*args, **kwargs)

    return wrapped


@app.get("/health")
def health():
    return jsonify(status="ok")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        with get_db() as db:
            user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("dashboard"))
        return render_template("login.html", error="아이디 또는 비밀번호가 올바르지 않습니다."), 401
    return render_template("login.html")


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.get("/bot-login")
def bot_login():
    """관리자 봇만 사용하는 내부 로그인 경로입니다."""
    if not secrets.compare_digest(request.args.get("token", ""), ADMIN_BOT_TOKEN):
        return "Forbidden", 403
    session.clear()
    session["user_id"] = 1
    return redirect(url_for("dashboard"))


@app.get("/")
@login_required
def dashboard():
    user = current_user()
    with get_db() as db:
        ticket_rows = db.execute(
            """SELECT reference, title, status FROM tickets
               WHERE owner_id = ? ORDER BY reference DESC""",
            (user["id"],),
        ).fetchall()
    tickets = [
        {
            **dict(ticket),
            "display_number": display_ticket_number(ticket["reference"]),
            "detail_url": url_for(
                "ticket_page",
                ticket_reference=display_ticket_number(ticket["reference"]),
                code=ticket_code(ticket["reference"]),
            ),
            "status_label": "답변 대기" if ticket["status"] == "waiting" else "처리 완료",
        }
        for ticket in ticket_rows
    ]
    return render_template(
        "dashboard.html", user=user, tickets=tickets, ticket_count=len(tickets)
    )


@app.get("/ticket/<ticket_reference>")
@login_required
def ticket_page(ticket_reference):
    """문의 상세 화면을 표시하고 실제 데이터는 문의 API에서 불러옵니다."""
    user = current_user()
    with get_db() as db:
        ticket_count = db.execute(
            "SELECT COUNT(*) FROM tickets WHERE owner_id = ?", (user["id"],)
        ).fetchone()[0]
    return render_template(
        "ticket.html",
        user=user,
        ticket_count=ticket_count,
        ticket_reference=ticket_reference,
    )


@sock.route("/ws/notifications")
def notifications(websocket):
    """로그인한 고객이 등록한 문의 내역만 전송합니다."""
    user = current_user()
    if not user:
        websocket.close()
        return
    with get_db() as db:
        tickets = db.execute(
            """SELECT reference, title FROM tickets
               WHERE owner_id = ? ORDER BY reference DESC LIMIT 2""",
            (user["id"],),
        ).fetchall()
    for ticket in tickets:
        websocket.send(
            json.dumps(
                {
                    "event": "ticket.created",
                    "ticketNumber": display_ticket_number(ticket["reference"]),
                    "title": ticket["title"],
                },
                ensure_ascii=False,
            )
        )
        time.sleep(0.2)


@app.get("/api/tickets/<ticket_reference>")
@login_required
def get_ticket(ticket_reference):
    """취약점: 확인 코드와 Ticket 소유권을 검사하지 않습니다."""
    with get_db() as db:
        ticket = find_ticket_by_reference(db, ticket_reference)
    if not ticket:
        return jsonify(error="문의를 찾을 수 없습니다."), 404
    return jsonify(
        id=ticket["reference"],
        ticketNumber=display_ticket_number(ticket["reference"]),
        title=ticket["title"],
        status="답변 대기" if ticket["status"] == "waiting" else "처리 완료",
        openedBy=ticket["opened_by"],
        openedAt=ticket["opened_at"],
        claimedBy=ticket["claimed_by"] or "미배정",
        reason=ticket["body"],
        answer=ticket["answer"],
        attachmentId=ticket["attachment_reference"],
        attachmentFilename=ticket["attachment_filename"],
        attachmentContentType=ticket["attachment_content_type"],
        classification="일반" if ticket["classification"] == "normal" else "내부",
        exportable=bool(ticket["exportable"]),
        canReplaceAttachment=ticket["status"] != "closed",
    )


@app.post("/api/tickets")
@login_required
def create_ticket():
    """고객의 새 문의와 이미지 첨부파일을 등록합니다."""
    user = current_user()
    title = request.form.get("title", "").strip()
    body = request.form.get("body", "").strip()
    if not title or not body:
        return jsonify(error="제목과 문의 내용을 입력해 주세요."), 400
    try:
        stored, content = store_image(request.files.get("file"))
    except ValueError as error:
        return jsonify(error=str(error)), 400
    except RuntimeError as error:
        return jsonify(error=str(error)), 502

    now = datetime.now(ZoneInfo("Asia/Seoul"))
    with get_db() as db:
        last_tid = db.execute(
            "SELECT MAX(CAST(substr(reference, 11, 5) AS INTEGER)) FROM tickets"
        ).fetchone()[0] or 7208
        ticket_reference = (
            f"CS-{now:%y%m%d}-{last_tid + 1:05d}-{secrets.token_hex(3)}"
        )
        attachment = db.execute(
            """
            INSERT INTO attachments
                (reference, filename, content, content_type, review_url, workspace)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                stored["fileId"], stored["filename"], sqlite3.Binary(content),
                stored["contentType"], stored["reviewUrl"], user["workspace"],
            ),
        )
        db.execute(
            """
            INSERT INTO tickets
                (reference, title, status, opened_at, claimed_by, body, owner_id,
                 workspace, classification, attachment_id, exportable)
            VALUES (?, ?, 'waiting', ?, NULL, ?, ?, ?, 'normal', ?, 1)
            """,
            (
                ticket_reference, title,
                f"{now.year}년 {now.month}월 {now.day}일 "
                f"{'오전' if now.hour < 12 else '오후'} "
                f"{(now.hour - 1) % 12 + 1}:{now.minute:02d}",
                body, user["id"], user["workspace"], attachment.lastrowid,
            ),
        )
    try:
        request_admin_review(stored["reviewUrl"])
    except RuntimeError as error:
        return jsonify(error=str(error), ticketId=ticket_reference), 502
    return jsonify(ticketId=ticket_reference, status="답변 대기"), 201


@app.post("/api/tickets/<ticket_reference>/attachment")
@login_required
def replace_ticket_attachment(ticket_reference):
    """종료되지 않은 본인 문의의 첨부 이미지를 교체합니다."""
    user = current_user()
    with get_db() as db:
        ticket = db.execute(
            "SELECT * FROM tickets WHERE reference = ? AND owner_id = ?",
            (ticket_reference, user["id"]),
        ).fetchone()
    if not ticket:
        return jsonify(error="문의를 찾을 수 없습니다."), 404
    if ticket["status"] == "closed":
        return jsonify(error="종료된 문의의 첨부파일은 교체할 수 없습니다."), 409
    try:
        stored, content = store_image(request.files.get("file"))
    except ValueError as error:
        return jsonify(error=str(error)), 400
    except RuntimeError as error:
        return jsonify(error=str(error)), 502

    with get_db() as db:
        attachment = db.execute(
            """
            INSERT INTO attachments
                (reference, filename, content, content_type, review_url, workspace)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                stored["fileId"], stored["filename"], sqlite3.Binary(content),
                stored["contentType"], stored["reviewUrl"], user["workspace"],
            ),
        )
        db.execute(
            "UPDATE tickets SET attachment_id = ?, status = 'waiting' WHERE id = ?",
            (attachment.lastrowid, ticket["id"]),
        )
    try:
        request_admin_review(stored["reviewUrl"])
    except RuntimeError as error:
        return jsonify(error=str(error)), 502
    return jsonify(status="첨부파일 교체 완료", attachmentId=stored["fileId"])


@app.get("/api/attachments/<attachment_reference>")
@login_required
def get_attachment(attachment_reference):
    """첨부파일 직접 조회에는 정상적인 Workspace 검사를 적용합니다."""
    user = current_user()
    with get_db() as db:
        attachment = db.execute(
            "SELECT * FROM attachments WHERE reference = ?", (attachment_reference,)
        ).fetchone()
    if not attachment:
        return jsonify(error="첨부파일을 찾을 수 없습니다."), 404
    if user["role"] != "admin" and attachment["workspace"] != user["workspace"]:
        return jsonify(error="첨부파일에 접근할 권한이 없습니다."), 403
    response = Response(attachment["content"], content_type=attachment["content_type"])
    preview_types = {"image/png", "image/jpeg", "image/gif", "image/webp"}
    if request.args.get("preview") == "1" and attachment["content_type"] in preview_types:
        response.headers["Content-Disposition"] = "inline"
    else:
        response.headers["Content-Disposition"] = (
            f'attachment; filename="{secure_filename(attachment["filename"])}"'
        )
    return response


@app.post("/api/admin/attachments/<attachment_reference>/exports")
@login_required
def create_export(attachment_reference):
    """취약점: 관리자 전용 기능이지만 역할 검사가 누락되어 있습니다."""
    user = current_user()
    with get_db() as db:
        ticket = db.execute(
            """
            SELECT tickets.*, attachments.filename, attachments.content
            FROM tickets
            JOIN attachments ON attachments.id = tickets.attachment_id
            WHERE attachments.reference = ?
            """,
            (attachment_reference,),
        ).fetchone()
        if not ticket or not ticket["exportable"]:
            return jsonify(error="Ticket cannot be exported"), 404

        job_id = f"exp-{secrets.token_hex(5)}"
        db.execute(
            """
            INSERT INTO export_jobs(id, ticket_id, creator_id, filename, content, status)
            VALUES (?, ?, ?, ?, ?, 'private')
            """,
            (job_id, ticket["id"], user["id"], ticket["filename"], ticket["content"]),
        )
    return jsonify(jobId=job_id, status="private", publicUrl=None), 201


@app.get("/api/exports/<job_id>")
@login_required
def get_export(job_id):
    user = current_user()
    with get_db() as db:
        job = db.execute("SELECT * FROM export_jobs WHERE id = ?", (job_id,)).fetchone()
    if not job:
        return jsonify(error="Export job not found"), 404
    if user["role"] != "admin" and job["creator_id"] != user["id"]:
        return jsonify(error="Export job access denied"), 403
    public_url = f"/shared/{job['share_token']}" if job["share_token"] else None
    return jsonify(jobId=job["id"], status=job["status"], publicUrl=public_url)


@app.get("/api/exports/<job_id>/download")
@login_required
def download_export(job_id):
    user = current_user()
    with get_db() as db:
        job = db.execute("SELECT * FROM export_jobs WHERE id = ?", (job_id,)).fetchone()
    if not job:
        return jsonify(error="Export job not found"), 404
    if user["role"] != "admin" and job["creator_id"] != user["id"]:
        return jsonify(error="Export job access denied"), 403
    if job["status"] != "shared":
        return jsonify(error="External sharing is disabled"), 403
    return Response(job["content"], mimetype="text/plain")


@app.post("/api/admin/exports/<job_id>/share")
@admin_required
def share_export(job_id):
    """취약점: 관리자 권한은 검사하지만 CSRF 방어가 없습니다."""
    enabled = request.form.get("enabled") == "true"
    if not enabled:
        return jsonify(error="enabled=true is required"), 400

    with get_db() as db:
        job = db.execute("SELECT * FROM export_jobs WHERE id = ?", (job_id,)).fetchone()
        if not job:
            return jsonify(error="Export job not found"), 404
        token = job["share_token"] or secrets.token_urlsafe(12)
        db.execute(
            "UPDATE export_jobs SET status = 'shared', share_token = ? WHERE id = ?",
            (token, job_id),
        )
    return jsonify(jobId=job_id, status="shared", publicUrl=f"/shared/{token}")


@app.get("/shared/<token>")
def shared_export(token):
    with get_db() as db:
        job = db.execute(
            """SELECT export_jobs.*, tickets.reference AS ticket_reference
               FROM export_jobs
               JOIN tickets ON tickets.id = export_jobs.ticket_id
               WHERE export_jobs.share_token = ? AND export_jobs.status = 'shared'""",
            (token,),
        ).fetchone()
    if not job:
        return "Shared export not found", 404
    body = (
        f"Ticket #{display_ticket_number(job['ticket_reference'])} export\n\n"
        f"Attachment: {job['filename']}\n"
        f"{job['content']}"
    )
    return Response(body, mimetype="text/plain")


init_db()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)

