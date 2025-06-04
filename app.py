import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import folium_static
from pathlib import Path

# 페이지 설정
st.set_page_config(
    page_title="서울 맛집 분석",
    page_icon="🍽️",
    layout="wide"
)

# 타이틀
st.title("🍽️ 서울 맛집 분석 대시보드")

# 데이터 로드
@st.cache_data
def load_data():
    data_dir = Path("data")
    restaurants = pd.read_csv(data_dir / "restaurants.csv")
    return restaurants

try:
    restaurants = load_data()
    
    # 사이드바
    st.sidebar.title("필터")
    
    # 지역 선택
    addresses = sorted(restaurants['address'].unique())
    selected_addresses = st.sidebar.multiselect(
        "지역 선택",
        addresses,
        default=addresses[:3]
    )
    
    # 별점 범위 선택
    min_rating = st.sidebar.slider(
        "최소 별점",
        min_value=0.0,
        max_value=1.0,
        value=0.0,
        step=0.1
    )
    
    # 필터링
    filtered_restaurants = restaurants[
        (restaurants['address'].isin(selected_addresses)) &
        (restaurants['rating'] >= min_rating)
    ]
    
    # 메인 컨텐츠
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏆 Top 10 식당")
        # 별점 기준으로 내림차순 정렬
        top_restaurants = filtered_restaurants.sort_values('rating', ascending=False).head(10)
        # 인덱스 재설정
        top_restaurants = top_restaurants.reset_index(drop=True)
        # 인덱스를 1부터 시작하도록 설정
        top_restaurants.index = top_restaurants.index + 1
        st.dataframe(
            top_restaurants[['name', 'address', 'rating']],
            use_container_width=True
        )
        
        # 지역별 평균 별점
        st.subheader("📊 지역별 평균 별점")
        avg_ratings = filtered_restaurants.groupby('address')['rating'].mean().reset_index()
        fig = px.line(
            avg_ratings,
            x='address',
            y='rating',
            title="지역별 평균 별점",
            labels={'address': '지역', 'rating': '평균 별점'},
            markers=True  # 데이터 포인트에 마커 표시
        )
        # Y축 범위 설정 (0.6 ~ 1.0)
        fig.update_layout(
            yaxis=dict(range=[0.6, 1.0]),
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🗺️ 식당 위치")
        # 지도 생성
        m = folium.Map(
            location=[filtered_restaurants['latitude'].mean(), filtered_restaurants['longitude'].mean()],
            zoom_start=12
        )
        
        # 식당 위치 표시
        for _, row in filtered_restaurants.iterrows():
            # 별점에 따라 마커 색상 변경
            color = 'red' if row['rating'] >= 0.8 else 'orange' if row['rating'] >= 0.6 else 'blue'
            
            folium.Marker(
                [row['latitude'], row['longitude']],
                popup=f"""
                    <b>{row['name']}</b><br>
                    별점: {row['rating']}<br>
                    주소: {row['address']}
                """,
                tooltip=row['name'],
                icon=folium.Icon(color=color)
            ).add_to(m)
        
        folium_static(m, width=600, height=400)
        
        # 지역별 식당 수
        st.subheader("📌 지역별 식당 수")
        address_counts = filtered_restaurants['address'].value_counts()
        fig = px.bar(
            x=address_counts.index,
            y=address_counts.values,
            title="지역별 식당 수",
            labels={'x': '지역', 'y': '식당 수'}
        )
        st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {str(e)}")
    st.info("data/restaurants.csv 파일이 올바른 형식인지 확인해주세요.") 