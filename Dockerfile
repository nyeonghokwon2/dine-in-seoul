FROM apache/airflow:2.6.3

USER airflow
RUN pip install --no-cache-dir \
        openai \
        python-dotenv \
        pandas
