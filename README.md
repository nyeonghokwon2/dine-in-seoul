# 서울 맛집 추천 대시보드

이 프로젝트는 서울의 다양한 식당 데이터를 바탕으로, 지역별 맛집을 시각적으로 탐색하고 추천하는 웹 대시보드입니다.

## 주요 기능

- 서울시 주요 지역별 식당 정보 제공
- 별점, 위치, 지역별 통계 등 시각화
- 필터를 통한 맞춤형 맛집 탐색

## 실행 방법

1. 의존성 설치
   ```bash
   pip install -r requirements.txt
   ```
2. 대시보드 실행
   ```bash
   streamlit run app.py
   ```

## 데이터

- 식당 정보 및 평점 데이터: data/restaurants.csv
- 감성 및 리뷰 데이터: data/seoul_hansik_sentiment.csv

## 환경

- Python 3.9 이상
- 주요 라이브러리: streamlit, pandas, plotly, folium 등

## 라이선스

MIT License
