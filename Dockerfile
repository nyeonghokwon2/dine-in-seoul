# 기존 이미지 그대로
FROM apache/airflow:2.6.3

# ─── PyPI 패키지 설치는 airflow 유저로 실행 ─────────────────────────────
USER airflow
RUN