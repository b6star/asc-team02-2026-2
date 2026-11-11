# Session 5 · Command Injection and Memory Corruption

- **커맨드 인젝션(OS Command Injection):** 사용자 입력이 운영체제 명령의 일부로 해석되어 공격자가 의도한 명령이 서버에서 실행되는 취약점이다.
- **블라인드 커맨드 인젝션(Blind OS Command Injection):** 명령의 출력이 응답에 직접 보이지 않지만 시간 지연이나 외부 요청 같은 변화로 실행 여부를 확인할 수 있다.
- **C 스택 버퍼 오버플로(Stack-based Buffer Overflow):** 스택 버퍼의 경계를 넘어 데이터를 써서 인접 메모리나 함수의 제어 흐름을 손상시키는 취약점이다.
- **서버 권한 오설정(Server Permission Misconfiguration):** 실행 계정이나 파일·디렉터리에 불필요한 권한을 부여해 침해 범위가 커지는 설정 문제다.
