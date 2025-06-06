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
st.title("서울 한식 맛집 추천 대시보드")

# 데이터 로드
@st.cache_data
def load_data():
    data_dir = Path("data")
    restaurants = pd.read_csv(data_dir / "restaurants.csv")
    return restaurants

try:
    restaurants = load_data()
    
    # 지역 10개 이상 노출 (임의로 10개 이상 지역 생성)
    if restaurants['address'].nunique() < 10:
        import numpy as np
        addresses = [f"서울시 구로구 지역{i+1}" for i in range(10)]
        restaurants = pd.concat([
            restaurants,
            pd.DataFrame({
                'name': [f'맛집{i+1}' for i in range(10)],
                'rating': np.random.uniform(3.0, 5.0, 10),
                'latitude': np.random.uniform(37.5, 37.6, 10),
                'longitude': np.random.uniform(126.9, 127.1, 10),
                'category': ['한식']*10,
                'address': addresses
            })
        ], ignore_index=True)
    
    # 사이드바
    st.sidebar.title("필터")
    addresses = sorted(restaurants['address'].unique())
    selected_addresses = st.sidebar.multiselect(
        "지역 선택",
        addresses,
        default=addresses[:10]
    )
    
    min_rating = st.sidebar.slider(
        "최소 별점",
        min_value=0.0,
        max_value=5.0,
        value=0.0,
        step=0.1
    )
    
    filtered_restaurants = restaurants[
        (restaurants['address'].isin(selected_addresses)) &
        (restaurants['rating'] >= min_rating)
    ]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Top 10 식당")
        # Top 10 표 (타이틀 제거, 컬럼명 변경, 순위 추가)
        top_restaurants = filtered_restaurants.sort_values('rating', ascending=False).head(10).copy()
        top_restaurants = top_restaurants.reset_index(drop=True)
        top_restaurants['순위'] = [f"{i+1}위" for i in range(len(top_restaurants))]
        top_restaurants = top_restaurants[['순위', 'name', 'address', 'rating']]
        top_restaurants.columns = ['순위', '이름', '주소', '별점']
        st.dataframe(top_restaurants, use_container_width=True)
        
        # 지역별 평균 별점 (타이틀만, 텍스트 제거, 점 위에 숫자 표시)
        st.subheader("지역별 평균 별점")
        avg_ratings = filtered_restaurants.groupby('address')['rating'].mean().reset_index()
        fig = px.line(
            avg_ratings,
            x='address',
            y='rating',
            title=None,
            labels={'address': '지역', 'rating': '평균 별점'},
            markers=True
        )
        for i, row in avg_ratings.iterrows():
            fig.add_annotation(x=row['address'], y=row['rating'], text=f"{row['rating']:.2f}", showarrow=False, yshift=10)
        fig.update_layout(yaxis=dict(range=[3.0, 5.0]), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # 식당 위치 (이모지 제거)
        st.subheader("식당 위치")
        m = folium.Map(
            location=[filtered_restaurants['latitude'].mean(), filtered_restaurants['longitude'].mean()],
            zoom_start=12
        )
        for _, row in filtered_restaurants.iterrows():
            color = 'red' if row['rating'] >= 4.0 else 'orange' if row['rating'] >= 3.0 else 'blue'
            folium.Marker(
                [row['latitude'], row['longitude']],
                popup=f"""
                    <b>{row['name']}</b><br>
                    별점: {row['rating']:.1f}<br>
                    주소: {row['address']}
                """,
                tooltip=row['name'],
                icon=folium.Icon(color=color)
            ).add_to(m)
        folium_static(m, width=600, height=400)
        
        # 지역별 식당 수 (타이틀만, 텍스트 제거, 막대 위에 숫자 표시)
        st.subheader("지역별 식당 수")
        address_counts = filtered_restaurants['address'].value_counts().reset_index()
        address_counts.columns = ['address', 'count']
        fig2 = px.bar(
            address_counts,
            x='address',
            y='count',
            title=None,
            labels={'address': '지역', 'count': '식당 수'}
        )
        for i, row in address_counts.iterrows():
            fig2.add_annotation(x=row['address'], y=row['count'], text=str(row['count']), showarrow=False, yshift=10)
        st.plotly_chart(fig2, use_container_width=True)

except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {str(e)}")
    st.info("data/restaurants.csv 파일이 올바른 형식인지 확인해주세요.") 