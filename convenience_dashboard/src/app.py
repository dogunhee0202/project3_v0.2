import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
import os

# 페이지 설정
st.set_page_config(
    page_title="편의점 입점 전략 대시보드",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 CSS (Premium Look)
st.markdown("""
<style>
    /* 기본 폰트 설정 */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    * {
        font-family: 'Outfit', 'Pretendard', sans-serif;
    }

    .main {
        background-color: #f8f9fa;
    }
    
    /* 메트릭 카드 스타일 */
    [data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border: 1px solid #eef2f6;
    }
    
    /* 탭 디자인 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: transparent;
    }

    .stTabs [data-baseweb="tab"] {
        background-color: #f1f3f5;
        border-radius: 8px 8px 0px 0px;
        padding: 12px 24px;
        font-weight: 600;
        color: #495057;
        border: none;
    }

    .stTabs [aria-selected="true"] {
        background-color: #007bff !important;
        color: white !important;
    }
    
    /* 제목 스타일 */
    h1 {
        color: #1e293b;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    
    h2, h3 {
        color: #334155;
    }

    /* 사이드바 */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
    }
</style>
""", unsafe_allow_html=True)

# 데이터 로드 함수
@st.cache_data
def load_data():
    # 1. 매출 요약 데이터
    rev_summary = pd.read_csv("revenue_analysis_summary.csv")
    
    # 2. 브랜드 점포 데이터
    branded_stores = pd.read_csv("7. branded_Convenience_Store.csv")
    
    # 3. 네모 상가 데이터 (가산, 여의)
    # 파일 경로가 프로젝트 폴더 외부에 있으므로 절대 경로 혹은 상대 경로 조절 필요
    # 현재 위치: convenience_dashboard/src/app.py -> Project3는 상위 디렉토리의 Project3에 있음
    nemo_gasan = pd.read_csv("10. nemo_stores_gasan.csv")
    nemo_yeui = pd.read_csv("9. nemo_stores_yeui.csv")
    
    nemo_gasan['District'] = '가산동'
    nemo_yeui['District'] = '여의동'
    nemo_combined = pd.concat([nemo_gasan, nemo_yeui], ignore_index=True)
    
    # 데이터 파싱 로직
    def parse_price(price_str):
        # "월세 7,000만/320만" -> 보증금 7000, 월세 320
        deposit, rent = 0, 0
        if '매매' in str(price_str): return 0, 0 
        try:
            parts = str(price_str).replace("월세 ", "").split("/")
            if len(parts) == 2:
                dep_str = parts[0].replace("만", "").replace(",", "").strip()
                rent_str = parts[1].replace("만", "").replace(",", "").strip()
                # "7,000" 같은 형태 처리
                deposit = int(re.sub(r'[^0-9]', '', dep_str))
                rent = int(re.sub(r'[^0-9]', '', rent_str))
        except: pass
        return deposit, rent

    def parse_distance(loc_str):
        # "... 도보 4분" -> 4
        try:
            match = re.search(r'도보 (\d+)분', str(loc_str))
            if match:
                return int(match.group(1))
        except: pass
        return None

    nemo_combined['Deposit'], nemo_combined['Rent'] = zip(*nemo_combined['price'].apply(parse_price))
    nemo_combined['Walk_Min'] = nemo_combined['category_location'].apply(parse_distance)
    nemo_combined['Distance_m'] = nemo_combined['Walk_Min'] * 70 # 1분당 70m 가정
    
    # 지상 1층 여부
    nemo_combined['Is_1F'] = nemo_combined['area_floor'].astype(str).str.contains('지상 1층')
    
    return rev_summary, branded_stores, nemo_combined

# 메 메 메 레 이 아 웃
try:
    rev_summary, branded_stores, nemo_data = load_data()

    st.title("🏪 편의점 입점 전략 Analytics Dashboard")
    st.markdown("가산동 및 여의동 상권 분석 데이터를 기반으로 최적의 입지 추천을 제공합니다.")

    # 사이드바 설정
    st.sidebar.header("📍 분석 지역")
    target_dong = st.sidebar.selectbox("지역을 선택하세요", ["가산동", "여의동"])

    # 지표 계산
    district_rev = rev_summary[rev_summary['Dong'] == target_dong]
    latest_q = district_rev['Quarter'].max()
    q_data = district_rev[district_rev['Quarter'] == latest_q]
    
    if not q_data.empty:
        avg_rev_per_store = q_data['Estimated_Rev_Per_Store_M'].iloc[0]
        total_stores = q_data['StoreCount'].sum()
    else:
        avg_rev_per_store, total_stores = 0, 0

    # 주요 지표 (KPIs)
    st.markdown("### 🔑 주요 상권 지표")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("총 점포 수", f"{total_stores}개", help="2025년 4분기 기준 점포 수")
    with col2:
        st.metric("점포당 평균 매출", f"{avg_rev_per_store:.1f} M", help="월간 추정 매출액 (단위: 백만 원)")
    with col3:
        market_val = (avg_rev_per_store * total_stores / 10)
        st.metric("월간 시장 규모", f"{market_val:.1f} 억", help="행정동 전체 편의점 합산 매출액")

    st.markdown("---")

    # 탭 구성
    tab1, tab2, tab3 = st.tabs(["📊 시장 트렌드", "📍 임대료 & 입지 분석", "💡 추천 입점 전략"])

    with tab1:
        st.subheader("📈 성과 트렌드 분석")
        c1, c2 = st.columns([3, 2])
        
        with c1:
            # 분기별 매출 추이
            trend_df = rev_summary[rev_summary['Dong'] == target_dong].groupby('Quarter')['Estimated_Rev_Per_Store_M'].mean().reset_index()
            trend_df['Quarter_Label'] = trend_df['Quarter'].apply(lambda x: f"{str(x)[:4]}년 {str(x)[4]}분기")
            
            fig_trend = px.line(trend_df, x='Quarter_Label', y='Estimated_Rev_Per_Store_M', 
                                title="2025년 분기별 매출액 추이",
                                markers=True, text='Estimated_Rev_Per_Store_M',
                                template="plotly_white")
            fig_trend.update_traces(texttemplate='%{text:.1f}M', textposition='top center', line_color='#007bff')
            fig_trend.update_layout(xaxis_title="기준 분기", yaxis_title="매출 (백만 원)")
            st.plotly_chart(fig_trend, use_container_width=True)
            
        with c2:
            # 브랜드 점유율
            brand_share = q_data[['Brand', 'StoreCount']]
            fig_pie = px.pie(brand_share, values='StoreCount', names='Brand', 
                             title="브랜드 점유율 현황",
                             hole=0.5, color_discrete_sequence=px.colors.qualitative.Bold)
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)

    with tab2:
        st.subheader("💰 임대 시세 및 거리 분석")
        
        n_filtered = nemo_data[nemo_data['District'] == target_dong].dropna(subset=['Walk_Min'])
        
        # 산점도 시각화
        fig_scatter = px.scatter(n_filtered, x='Distance_m', y='Rent', 
                                 color='Is_1F', size='Deposit', hover_name='description',
                                 title="역과의 거리 vs 월세 분포",
                                 labels={'Distance_m': '역과의 거리 (m)', 'Rent': '월세 (만 원)', 'Is_1F': '1층 여부'},
                                 color_discrete_map={True: '#ef4444', False: '#64748b'},
                                 template="plotly_white")
        
        # 가이드 영역 (200-300m)
        fig_scatter.add_vrect(x0=200, x1=300, fillcolor="#22c55e", opacity=0.1, 
                              annotation_text="🎯 최적 입지", annotation_position="top left")
        
        st.plotly_chart(fig_scatter, use_container_width=True)
        st.caption("※ 보증금 크기에 따라 원의 크기가 결정됩니다. 붉은색 점은 접근성이 높은 1층 매물입니다.")

        st.markdown("### 📋 주요 매물 리스트 (역세권 350m 이내)")
        st.dataframe(n_filtered[n_filtered['Distance_m'] <= 350].sort_values('Distance_m')[['category_location', 'price', 'area_floor', 'description']].reset_index(drop=True), use_container_width=True)

    with tab3:
        st.subheader("🚀 전략적 입점 추천")
        
        # 추천 매물 선정 (200-350m 이내 1층 매물 중 저렴한 순)
        best_pick = n_filtered[
            (n_filtered['Distance_m'] >= 200) & (n_filtered['Distance_m'] <= 350) & (n_filtered['Is_1F'] == True)
        ].sort_values('Rent')

        col_a, col_b = st.columns([1, 1])
        
        with col_a:
            st.markdown("#### ✨ 핵심 전략 매물 Top 3")
            if not best_pick.empty:
                for idx, row in best_pick.head(3).iterrows():
                    st.success(f"""
                    **[{idx+1}] {row['category_location']}**  
                    - **임대료**: 월 {row['Rent']}만 (보증금 {row['Deposit']}만)  
                    - **거리**: 약 {row['Distance_m']}m (도보 {row['Walk_Min']}분)  
                    - **설명**: {row['description'][:60]}...
                    """)
            else:
                st.info("현재 필터링된 조건(200-350m, 1층)에 부합하는 매물이 없습니다.")

        with col_b:
            st.markdown("#### 💡 지역별 추천 브랜드 전략")
            if target_dong == '여의동':
                st.info("""
                **브랜드 전략: 프리미엄 & F&B 특화**
                - 높은 점포당 수익성을 바탕으로 고가 도시락 및 디저트 라인업 강화
                - **GS25**와 **세븐일레븐**의 경쟁이 치열하므로, 오피스 빌딩 내 폐쇄적 환경보다 오픈된 사거리 코너 입지 우선 확보 권장.
                """)
            else:
                st.info("""
                **브랜드 전략: 가성비 & 물류 특화**
                - IT 단지 특성상 야근/조식 수요가 많으므로 간편식 재고 회전율이 높은 브랜드 추천
                - **CU**가 현재 점유율 1위이나, 경쟁 완화 구역인 역외곽 300m 지점에 **이마트24** 등 신규 브랜드의 '무인 시스템' 병행 매장 입점 시 유리.
                """)

except Exception as e:
    st.error(f"데이터 로드 중 오류가 발생했습니다: {e}")
    st.info("Project3/data 폴더 내에 필요한 CSV 파일들이 있는지 확인해 주세요.")
