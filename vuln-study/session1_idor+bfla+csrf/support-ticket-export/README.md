# Support Ticket Export

IDOR(Insecure Direct Object Reference), BFLA(Broken Function Level Authorization), CSRF(Cross-Site Request Forgery)를 연계해 풀이하는 Web CTF 문제입니다.

쇼핑몰 고객지원 센터에서 다른 고객과 사내 직원의 티켓을 조회하고, 내부 첨부파일의 외부 공유 기능을 악용해 FLAG를 획득하는 시나리오입니다.

## 실행 방법

WSL 또는 Linux 환경에서 다음 명령을 실행합니다.

```bash
sudo docker compose up -d --build
```

브라우저 접속 주소:

```text
http://127.0.0.1:18080
```

실습 계정:

```text
아이디: customer11
비밀번호: givemetheflag
```

컨테이너 상태와 로그는 다음 명령으로 확인할 수 있습니다.

```bash
sudo docker compose ps
sudo docker compose logs -f
```

서버 종료:

```bash
sudo docker compose down
```

문의, 첨부파일 교체, Export Job은 컨테이너 내부에만 저장됩니다. `docker compose down` 후 다시 실행하면 초기 상태로 돌아갑니다.

## 서비스 구성

```text
브라우저
   │
   ▼
gateway:8080 ──▶ app:5000
                    │
                    ├──▶ storage:5001
                    └──▶ bot:3000

bot ──▶ gateway:8081 ──▶ storage:5001
```

- `app`: Flask 고객지원 애플리케이션과 SQLite 데이터베이스
- `storage`: PNG, JPG, GIF, WEBP, SVG 첨부파일 저장소
- `bot`: 첨부파일을 확인하는 Playwright 관리자 브라우저
- `gateway`: 고객 서비스와 내부 첨부파일 Origin을 분리하는 Nginx

참가자에게 노출되는 포트는 `18080` 하나입니다. 첨부파일은 최대 5MB까지 업로드할 수 있습니다.

## 디렉터리 구조

```text
support-ticket-export/
├─ app/
│  ├─ static/
│  ├─ templates/
│  ├─ tests/
│  ├─ app.py
│  └─ Dockerfile
├─ attachment-storage/
├─ bot/
├─ gateway/
├─ docker-compose.yaml
└─ README.md
```

## 문제 화면

- 일반 티켓은 쇼핑몰의 배송, 반품, 환불, 쿠폰 문의로 구성됩니다.
- 사내 티켓은 다크 블루 화면과 `INTERNAL · 사내 업무` 배지로 구분됩니다.
- 공개 문의 번호는 `1081`부터 `1111`까지 순차적으로 존재합니다.
- `customer11`에는 11월 11일 빼빼로데이 문의 하나만 표시됩니다.
- 문의 번호 뒤의 6자리 값은 최초 응답 정보의 SHA-256(Secure Hash Algorithm 256-bit) 앞 6자리입니다.

## 주요 티켓

| 번호 | 날짜 | 구분 | 내용 |
| --- | --- | --- | --- |
| `1081` | 2026-11-01 | 사내 | 운영 환경 인증 정보 백업 |
| `1090` | 2026-11-04 | 고객 | SVG 이미지 미리보기 문의 |
| `1091` | 2026-11-04 | 사내 | SVG 미리보기 개선 요청 |
| `1101` | 2026-11-07 | 사내 | 첨부파일 공유 기능 정리 |
| `1110` | 2026-11-10 | 고객 | 배송지 변경 문의 |
| `1111` | 2026-11-11 | 고객 | 빼빼로데이 이벤트 문의 |

## 취약점 구성

> 아래 내용에는 풀이 스포일러가 포함되어 있습니다.

### 1. 문의 참조값 검증 오류

문의 참조값은 다음 구조를 사용합니다.

```text
YYMMDD | TID | 6자리 suffix
```

서버는 `YYMMDDTID` 10자리만 조회 조건으로 사용합니다. suffix는 생략하거나 임의 문자열로 변경해도 조회 결과에 영향을 주지 않습니다.

### 2. IDOR

```http
GET /api/tickets/<ticket_reference>
```

티켓 조회 API는 로그인 여부만 확인하고 소유권을 검사하지 않습니다. 유효한 순차 문의 번호를 탐색하면 다른 고객 및 사내 티켓의 제목, 대화, 첨부파일 ID를 조회할 수 있습니다.

첨부파일 다운로드 API에는 정상적인 Workspace 권한 검사가 있으므로 IDOR만으로 내부 파일을 읽을 수 없습니다.

### 3. BFLA

`app.js.map`에는 `createExport`, `shareExport`, `attachmentId`, `jobId` 이름과 사내 프런트엔드 파일의 흔적이 남아 있습니다. 실제 번들인 `app.js`에서 관리자 Export API의 경로와 HTTP Method를 확인할 수 있습니다.

```http
POST /api/admin/attachments/<attachment_id>/exports
```

이 API는 관리자 전용 기능이지만 역할 검사가 누락되어 있어 일반 고객도 내부 첨부파일을 `private` Export Job으로 복사할 수 있습니다.

### 4. CSRF

```http
POST /api/admin/exports/<job_id>/share
Content-Type: application/x-www-form-urlencoded

enabled=true
```

공유 API는 관리자 역할을 검사하지만 CSRF 토큰과 Origin 검사가 없습니다. 저장소는 파일 내용을 검사해 이미지 형식만 허용하지만, JavaScript를 포함할 수 있는 SVG 원본 문서를 그대로 제공합니다.

악성 SVG가 관리자 브라우저에서 열리면 공유 API가 실행되고 Export Job이 `shared` 상태로 변경됩니다. 발급된 공개 URL에서는 내부 백업 파일과 FLAG를 확인할 수 있습니다.

## 전체 풀이 흐름

```text
문의 번호 구조 파악
→ 순차 번호 탐색
→ IDOR로 1081 사내 티켓과 첨부파일 ID 확인
→ 직접 다운로드 403 확인
→ Source Map과 번들에서 관리자 Export API 발견
→ BFLA로 private Export Job 생성
→ SVG에 공유 요청 삽입
→ 기존 문의의 첨부 이미지 교체
→ CSRF로 Export를 shared 상태로 변경
→ 공개 URL에서 FLAG 획득
```

## 초기 설정값

로컬 실습용 값은 `docker-compose.yaml`에 정의되어 있습니다.

```text
FLAG=ASC{n0_d1r3ct_4cc3ss_n0_pr0bl3m_l3t_4dm1n_sh4r3_1t}
SECRET_KEY=local-development-secret
ADMIN_BOT_TOKEN=local-admin-bot-token
```

실제 운영 환경에 배포하기 위한 값이 아니며, 이 서버는 외부 인터넷에 공개하지 않는 것을 권장합니다.
