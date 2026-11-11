# Session 2 · SQL Injection

- **조건 조작 SQL 인젝션(Structured Query Language Injection):** 입력값으로 쿼리 조건을 바꿔 숨겨진 데이터나 접근이 제한된 데이터를 조회하는 취약점이다.
- **UNION 기반 SQL 인젝션(UNION-based SQL Injection):** 기존 쿼리 결과에 공격자가 만든 조회 결과를 결합해 다른 테이블의 데이터를 읽는 취약점이다.
- **참·거짓 기반 블라인드 SQL 인젝션(Boolean-based Blind SQL Injection):** 조건에 따라 달라지는 응답을 비교해 데이터 값을 한 글자씩 추론한다.
- **시간 기반 블라인드 SQL 인젝션(Time-based Blind SQL Injection):** 조건이 참일 때 응답을 지연시키고, 지연 시간의 차이로 데이터 값을 추론한다.
