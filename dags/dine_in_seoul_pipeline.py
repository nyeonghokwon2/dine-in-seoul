import os
import time
import csv
import random
import logging
import tempfile
from datetime import timedelta
from typing import List, Tuple

import pandas as pd
import pendulum
from dotenv import load_dotenv
import openai

from airflow import DAG
from airflow.operators.python import PythonOperator

# ────────── 로깅 설정 ──────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ────────── 공통 설정 ──────────
DATA_DIR  = "data"
SRC_CSV   = f"{DATA_DIR}/서울시_일반음식점_인허가_정보.csv"
STEP1_CSV = f"{DATA_DIR}/seoul_hansik_list.csv"
STEP2_CSV = f"{DATA_DIR}/seoul_hansik_with_reviews.csv"
STEP3_CSV = f"{DATA_DIR}/seoul_hansik_sentiment.csv"
STEP4_CSV = f"{DATA_DIR}/hansik_reco_top10.csv"

MODEL  = "gpt-3.5-turbo"  # OpenAI의 실제 모델명
DELAY  = 1.2  # API 호출 간 대기(초)
MAX_LINES = 30  # 처리할 최대 라인 수

class ReviewGenerator:
    def __init__(self):
        load_dotenv(f"{DATA_DIR}/.env")
        openai.api_key = os.getenv("OPENAI_API_KEY")
        if not openai.api_key:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")

    @staticmethod
    def weighted_star() -> int:
        """가중치를 적용한 별점 생성"""
        r = random.random()
        return 1 if r < 0.10 else 2 if r < 0.20 else 3 if r < 0.40 else 4 if r < 0.65 else 5

    @staticmethod
    def get_review_count() -> int:
        """1~3 사이의 랜덤한 리뷰 개수 생성"""
        return random.randint(1, 3)

    def generate_review(self, restaurant_name: str, address: str, rating: int) -> str:
        """식당 정보를 기반으로 리뷰 생성"""
        prompt = (
            f"다음 한식 식당에 대한 자연스러운 한국어 한 문장 리뷰를 작성하세요.\n\n"
            f"식당 이름: {restaurant_name}\n"
            f"주소: {address}\n"
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
            return res.choices[0].message.content.strip().replace("\n", " ")
        except Exception as e:
            logger.error(f"리뷰 생성 실패: {e}")
            return f"리뷰 생성 실패 (별점: {rating}점)"

def extract_hansik(**context) -> None:
    """한식 식당 데이터 추출"""
    logger.info("한식 식당 데이터 추출 시작")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_src = os.path.join(tmpdir, os.path.basename(SRC_CSV))
        
        # 1) 임시 파일로 데이터 복사
        with open(SRC_CSV, "r", encoding="euc-kr", newline="") as fin, \
             open(tmp_src, "w", encoding="euc-kr", newline="") as fout:
            for i, line in enumerate(fin):
                fout.write(line)
                if i >= MAX_LINES:
                    break

        # 2) 한식 식당 필터링
        seen = set()
        with open(tmp_src, "r", encoding="euc-kr", newline="") as fin2, \
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
    
    logger.info(f"한식 식당 데이터 추출 완료: {len(seen)}개 식당")

def generate_reviews(**context) -> None:
    """가상 리뷰 생성"""
    logger.info("가상 리뷰 생성 시작")
    
    generator = ReviewGenerator()
    df = pd.read_csv(STEP1_CSV)
    
    # 결과를 저장할 리스트
    all_restaurants = []
    all_ratings = []
    all_reviews = []
    
    for _, row in df.iterrows():
        # 각 식당마다 1~3개의 리뷰 생성
        review_count = generator.get_review_count()
        logger.info(f"{row['사업장명']}에 대한 {review_count}개의 리뷰 생성 중...")
        
        for _ in range(review_count):
            rating = generator.weighted_star()
            review = generator.generate_review(row['사업장명'], row['지번주소'], rating)
            
            all_restaurants.append(row['사업장명'])
            all_ratings.append(rating)
            all_reviews.append(review)
            time.sleep(DELAY)
    
    # 결과를 새로운 DataFrame으로 변환
    result_df = pd.DataFrame({
        '사업장명': all_restaurants,
        '지번주소': [row['지번주소'] for _ in range(len(all_restaurants))],
        '별점': all_ratings,
        '리뷰': all_reviews
    })
    
    result_df.to_csv(STEP2_CSV, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
    logger.info(f"가상 리뷰 생성 완료: 총 {len(result_df)}개의 리뷰 생성됨")

def add_sentiment(**context) -> None:
    """감성 분석 추가"""
    logger.info("감성 분석 시작")
    
    df = pd.read_csv(STEP2_CSV)
    df["감성"] = df["별점"].apply(lambda r: "추천해요" if r>=4 else ("적당해요" if r==3 else "별로예요"))
    df.to_csv(STEP3_CSV, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
    
    logger.info("감성 분석 완료")

def calc_reco(**context) -> None:
    """추천 Top 10 계산"""
    logger.info("추천 Top 10 계산 시작")
    
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
    
    logger.info("추천 Top 10 계산 완료")
    logger.info("\n=== 추천 Top 10 ===\n%s", top)

# ────────── DAG 정의 ──────────
with DAG(
    dag_id="daily_dine_in_seoul_pipeline",
    start_date=pendulum.today("UTC").add(days=-1),
    schedule="@daily",
    catchup=False,
    max_active_runs=1,
    tags=["seoul", "restaurant", "review"],
) as dag:

    t1 = PythonOperator(
        task_id="extract_hansik",
        python_callable=extract_hansik,
        retries=2,
        retry_delay=timedelta(minutes=2),
    )
    t2 = PythonOperator(
        task_id="generate_reviews",
        python_callable=generate_reviews,
        retries=2,
        retry_delay=timedelta(minutes=2),
    )
    t3 = PythonOperator(
        task_id="add_sentiment",
        python_callable=add_sentiment,
        retries=2,
        retry_delay=timedelta(minutes=2),
    )
    t4 = PythonOperator(
        task_id="calc_reco",
        python_callable=calc_reco,
        retries=2,
        retry_delay=timedelta(minutes=2),
    )

    t1 >> t2 >> t3 >> t4
