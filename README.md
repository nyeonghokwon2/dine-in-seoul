# 🍽️ Dine in Seoul

서울시 음식점 데이터를 기반으로 한 리뷰 생성 및 추천 시스템

## 📋 프로젝트 개요

이 프로젝트는 서울시 일반음식점 인허가 정보를 활용하여:

- 음식점 데이터 추출
- AI 기반 리뷰 생성
- 감성 분석
- 추천 Top 10 선정

## 🚀 시작하기

### 필수 요구사항

- Docker
- Docker Compose
- OpenAI API 키

### 설치 및 실행

1. 데이터 준비

   ```bash
   # 서울시 일반음식점 인허가 정보 다운로드
   # 서울시 열린데이터 광장: https://data.seoul.go.kr/dataList/OA-390/S/1/datasetView.do
   # 파일명: 서울시_일반음식점_인허가_정보.csv

   data/
   ├── .env                    # OpenAI API 키 설정
   └── 서울시_일반음식점_인허가_정보.csv  # 다운로드한 파일을 이 위치에 저장
   ```

2. 환경 변수 설정

   ```bash
   # data/.env 파일 생성
   OPENAI_API_KEY=your_api_key_here
   ```

3. Docker 컨테이너 실행

   ```bash
   docker-compose up -d
   ```

4. Airflow 웹 인터페이스 접속
   - URL: http://localhost:8080
   - 계정: admin
   - 비밀번호: admin

## 📊 데이터 파이프라인

1. **데이터 추출**

   - 서울시 일반음식점 데이터에서 한식 식당 추출
   - 중복 제거 및 기본 정보 정리

2. **리뷰 생성**

   - GPT-3.5를 활용한 자연스러운 리뷰 생성
   - 식당별 1~3개의 리뷰 생성

3. **감성 분석**

   - 별점 기반 감성 분석
   - 긍정/중립/부정 분류

4. **추천 시스템**
   - 긍정 리뷰 비율 기반 Top 10 선정
   - CSV 파일로 결과 저장

## 📁 프로젝트 구조

```
.
├── dags/                      # Airflow DAG 파일
│   └── dine_in_seoul_pipeline.py
├── data/                      # 데이터 파일
│   ├── .env
│   └── 서울시_일반음식점_인허가_정보.csv
├── logs/                      # Airflow 로그
├── docker-compose.yml         # Docker 설정
└── Dockerfile                 # Docker 이미지 설정
```

## 🔧 기술 스택

- **Airflow**: 워크플로우 관리
- **PostgreSQL**: 메타데이터 저장
- **OpenAI GPT-3.5**: 리뷰 생성
- **Pandas**: 데이터 처리
- **Docker**: 컨테이너화

## 📝 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.
