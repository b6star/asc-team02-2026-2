# Session 4 · File and Server-Side Vulnerabilities

- **경로 순회(Path Traversal):** 파일 경로를 조작해 애플리케이션이 허용한 디렉터리 밖의 파일을 읽거나 수정하는 취약점이다.
- **안전하지 않은 파일 업로드(Insecure File Upload):** 파일 형식·내용·저장 위치·실행 권한을 충분히 검증하지 않아 악성 파일이 저장되거나 실행되는 취약점이다.
- **SSRF(Server-Side Request Forgery):** 사용자 입력으로 서버가 내부 시스템이나 허용되지 않은 외부 주소에 요청을 보내도록 만드는 취약점이다.
- **민감 정보 노출(Sensitive Information Exposure):** 소스 코드, 설정 파일, 운영 토큰 같은 정보가 외부에 노출되어 추가 공격에 이용되는 문제다.
