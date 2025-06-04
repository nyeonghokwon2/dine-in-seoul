# 기존 이미지 그대로
FROM apache/airflow:2.6.3

# ─── PyPI 패키지 설치는 airflow 유저로 실행 ─────────────────────────────
USER airflow
RUN pip install --no-cache-dir \
        openai \
        python-dotenv \
        pandas

# (필요시) 이후에 root 권한 작업이 있다면 다시 USER root 로 전환 가능
# USER root