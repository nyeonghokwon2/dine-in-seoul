import os
import time
import csv
import random
import shutil
import tempfile
from datetime import timedelta

import pandas as pd
import pendulum

from airflow import DAG
from airflow.operators.python import PythonOperator

# ────────── 공통 설정 ──────────
DATA_DIR  = "/opt/airflow/data"
SRC_CSV   = f"{DATA_DIR}/서울시_일반음식점_인허가_정보.csv"
STEP1_CSV = f"{DATA_DIR}/seoul_hansik_list.csv"
STEP2_CSV = f"{DATA_DIR}/seoul_hansik_with_reviews.csv"
STEP3_CSV = f"{DATA_DIR}/seoul_hansik_sentiment.csv"
STEP4_CSV = f"{DATA_DIR}/hansik_reco_top10.csv"

MODEL  = "gpt-4o-mini"
DELAY  = 1.2  # API 호출 간 대기(초)

def weighted_star() -> int:
    r = random.random()
    return 1 if r < 0.10 else 2 if r < 0.20 else 3 if r < 0.40 else 4 if r < 0.65 else 5

# ────────── Task 1: 한식 식당 리스트 ──────────
def extract_hansik(**context):
    """
    1) 헤더+최대 MAX_LINES 행만 /tmp로 복사 → osxfs 락 회피
    2) csv.DictReader 로 '한식'만 필터링 → 중복 제거 → STEP1_CSV 에 저장
    """
    import os, tempfile, csv

    MAX_LINES = 100  # 필요하면 더 줄이세요
    # 1) 임시 디렉터리에 원본 일부 복사
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_src = os.path.join(tmpdir, os.path.basename(SRC_CSV))
        with open(SRC_CSV, "r", encoding="euc-kr", newline="") as fin, \
             open(tmp_src,  "w", encoding="euc-kr", newline="") as fout:
            for i, line in enumerate(fin):
                fout.write(line)
                if i >= MAX_LINES:
                    break

        # 2) 잘라낸 파일에서 필터링
        seen = set()
        with open(tmp_src,   "r", encoding="euc-kr", newline="") as fin2, \
             open(STEP1_CSV, "w", encoding="utf-8-sig", newline="") as fout2:

            reader = csv.DictReader(fin2)
            writer = csv.writer(fout2)
            writer.writerow(["사업장명", "지번주소"])
            for row in reader:
                if "한식" in (row.get("업태구분명") or ""):
                    key = (row["사업장명"], row["지번주소"])
                    if key not in seen:
                        writer.writerow(key)
                        seen.add(key)

# ────────── Task 2: 리뷰 + 별점 생성 ──────────
def generate_reviews(**context):
    from dotenv import load_dotenv
    import openai

    load_dotenv(f"{DATA_DIR}/.env")
    openai.api_key = os.getenv("OPENAI_API_KEY")

    df = pd.read_csv(STEP1_CSV)
    ratings, reviews = [], []

    for _, row in df.iterrows():
        rating = weighted_star()
        prompt = (
            f"다음 한식 식당에 대한 자연스러운 한국어 한 문장 리뷰를 작성하세요.\n\n"
            f"식당 이름: {row['사업장명']}\n"
            f"주소: {row['지번주소']}\n"
            f"별점: {rating}점\n\n"
            "규칙: 별점과 어울리는 톤·길이로, 이모지·해시태그 금지."
        )
        try:
            res = openai.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.9,
                max_tokens=60,
            )
            reviews.append(res.choices[0].message.content.strip().replace("\n"," "))
            ratings.append(rating)
        except Exception as e:
            reviews.append("리뷰 생성 실패")
            ratings.append(None)
            print("⚠️", e)
        time.sleep(DELAY)

    df["별점"] = ratings
    df["리뷰"] = reviews
    df.to_csv(STEP2_CSV, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)

# ────────── Task 3: 감성 레이블 파생 ──────────
def add_sentiment(**context):
    df = pd.read_csv(STEP2_CSV)
    df["감성"] = df["별점"].apply(lambda r: "긍정" if r>=4 else ("중립" if r==3 else "부정"))
    df.to_csv(STEP3_CSV, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)

# ────────── Task 4: 긍정 비율 Top 10 ──────────
def calc_reco(**context):
    df = pd.read_csv(STEP3_CSV)
    df["is_positive"] = df["감성"] == "긍정"
    top = (
        df.groupby("사업장명")["is_positive"].mean()
          .reset_index()
          .rename(columns={"is_positive":"긍정비율"})
          .sort_values("긍정비율", ascending=False)
          .head(10)
    )
    top.to_csv(STEP4_CSV, index=False, encoding="utf-8-sig")
    print("\n=== 추천 Top 10 ===")
    print(top)

# ────────── DAG 정의 ──────────
with DAG(
    dag_id="daily_hansik_review_pipeline",
    start_date=pendulum.today("UTC").add(days=-1),
    schedule="@daily",
    catchup=False,
    max_active_runs=1,
    tags=["hansik","openai","review"],
) as dag:

    t1 = PythonOperator(task_id="extract_hansik",   python_callable=extract_hansik)
    t2 = PythonOperator(
        task_i