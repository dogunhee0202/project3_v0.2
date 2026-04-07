import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
import os

# --- [추가] 경로 인식 로직 시작 ---
# 이 부분은 배포 환경(Streamlit Cloud)에서 데이터를 정확히 찾기 위해 필요합니다.
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(CURRENT_DIR))

def get_data_path(relative_path):
    # 상위 폴더(ROOT_DIR) 기준으로 경로를 생성하고, 없으면 현재 작업 디렉토리에서도 찾습니다.
    path = os.path.join(ROOT_DIR, relative_path)
    if not os.path.exists(path):
        path = os.path.join(os.getcwd(), relative_path)
    return path
# --- 경로 인식 로직 끝 ---

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
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    * { font-family: 'Outfit', 'Pretendard', sans-serif; }
    .main { background-color: #f8f9fa; }
    [data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border: 1px solid #eef2f6;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; background-color: transparent; }
    .stTabs [data-baseweb="tab"] {
        background-color: #f1f3f5;
        border-radius: 8px 8px 0px 0px;
        padding: 12px 24px;
        font-weight: 600;
        color: #495057;
        border: none;
    }
    .stTabs [aria-selected="true"] { background-color: #007bff !important; color: white !important; }
    h1 { color: #1e293b; font-weight: 700; letter-spacing: -0.5px; }
    h2, h3 { color: #334155; }
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e2e8f0; }
</style>
""", unsafe_allow_html=True)

# 데이터 로드 함수 (자동 경로 적용)
@st.cache_data
def load_data():
    # 경로 설정 (중요: GitHub 폴더명이 Project3 인지 확인 필요)
    rev_path = get_data_path("Project3/data/revenue_analysis_summary.csv")
    brand_path = get_data_path("Project3/data/7. branded_Convenience_Store.csv")
    nemo_yeui_path = get_data_path("Project3/data/9. nemo_stores_yeui.csv")
    nemo_gasan_path = get_data_path("Project3/data/10. nemo_stores_gasan.csv")

    rev_summary = pd.read_csv(rev_path)
    branded_stores = pd.read_csv(brand_path)
    nemo_gasan = pd.read_csv(nemo_gasan_path)
    nemo_yeui = pd.read_csv(nemo_yeui_path)
    
    nemo_gasan['District'] = '가산동'
    nemo_yeui['District'] = '여의동'
    nemo_combined = pd.concat([nemo_gasan, nemo_yeui], ignore_index=True)
    
    # 데이터 파싱 로직
    def parse_price(price_str):
        deposit, rent = 0, 0
        if '매매' in str(price_str): return 0, 0 
        try:
            parts = str(price_str).replace("월세 ", "").split("/")
            if len(parts) == 2:
                dep_str = parts[0].replace("만", "").replace(",", "").strip()
                rent_str = parts[1].replace("만", "").replace(",", "").strip()
                deposit = int(re.sub(r'[^0-9]', '', dep_str))
                rent = int(re.sub(r'[^0-9]', '', rent_str))
        except: pass
        return deposit, rent

    def parse_distance(loc_str):
        try:
            match = re.search(r'도보 (\d+)분', str(loc_str))
            if match: return int(match.group(1))
        except: pass
        return None

    nemo_combined['Deposit'], nemo_combined['Rent'] = zip(*nemo_combined['price'].apply(parse_price))
    nemo_combined['Walk_Min'] = nemo_combined['category_location'].apply(parse_distance)
    nemo_combined['Distance_m'] = nemo_combined['Walk_Min'] * 70 
    nemo_combined['Is_1F'] = nemo_combined['area_floor'].astype(str).str.contains('지상 1층')
    
    return rev_summary, branded_stores, nemo_combined

# 메인 레이아웃
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
            trend_df = rev_summary[rev_summary['Dong'] == target_dong].groupby('Quarter')['Estimated_Rev_Per_Store_M'].mean().reset_index()
            trend_df['Quarter_Label'] = trend_df['Quarter'].apply(lambda x: f"{str(x)[:4]}년 {str(x)[4]}분기")
            fig_trend = px.line(trend_df, x='Quarter_Label', y='Estimated_Rev_Per_Store_M', 
                                title="2025년 분기별 매출액 추이", markers=True, text='Estimated_Rev_Per_Store_M', template="plotly_white")
            fig_trend.update_traces(texttemplate='%{text:.1f}M', textposition='top center', line_color='#007bff')
            fig_trend.update_layout(xaxis_title="기준 분기", yaxis_title="매출 (백만 원)")
            st.plotly_chart(fig_trend, use_container_width=True)
        with c2:
            brand_share = q_data[['Brand', 'StoreCount']]
            fig_pie = px.pie(brand_share, values='StoreCount', names='Brand', title="브랜드 점유율 현황", hole=0.5, color_discrete_sequence=px.colors.qualitative.Bold)
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)

    with tab2:
        st.subheader("💰 임대 시세 및 거리 분석")
        n_filtered = nemo_data[nemo_data['District'] == target_dong].dropna(subset=['Walk_Min'])
        fig_scatter = px.scatter(n_filtered, x='Distance_m', y='Rent', color='Is_1F', size='Deposit', hover_name='description',
                                 title="역과의 거리 vs 월세 분포", labels={'Distance_m': '역과의 거리 (m)', 'Rent': '월세 (만 원)', 'Is_1F': '1층 여부'},
                                 color_discrete_map={True: '#ef4444', False: '#64748b'}, template="plotly_white")
        fig_scatter.add_vrect(x0=200, x1=300, fillcolor="#22c55e", opacity=0.1, annotation_text="🎯 최적 입지", annotation_position="top left")
        st.plotly_chart(fig_scatter, use_container_width=True)
        st.markdown("### 📋 주요 매물 리스트 (역세권 350m 이내)")
        st.dataframe(n_filtered[n_filtered['Distance_m'] <= 350].sort_values('Distance_m')[['category_location', 'price', 'area_floor', 'description']].reset_index(drop=True), use_container_width=True)

    with tab3:
        st.subheader("🚀 전략적 입점 추천")
        best_pick = n_filtered[(n_filtered['Distance_m'] >= 200) & (n_filtered['Distance_m'] <= 350) & (n_filtered['Is_1F'] == True)].sort_values('Rent')
        col_a, col_b = st.columns([1, 1])
        with col_a:
            st.markdown("#### ✨ 핵심 전략 매물 Top 3")
            if not best_pick.empty:
                for idx, row in best_pick.head(3).iterrows():
                    st.success(f"**[{idx+1}] {row['category_location']}**\n- **임대료**: 월 {row['Rent']}만 (보증금 {row['Deposit']}만)\n- **거리**: 약 {row['Distance_m']}m (도보 {row['Walk_Min']}분)\n- **설명**: {row['description'][:60]}...")
            else:
                st.info("현재 필터링된 조건(200-350m, 1층)에 부합하는 매물이 없습니다.")
        with col_b:
            st.markdown("#### 💡 지역별 추천 브랜드 전략")
            if target_dong == '여의동':
                st.info("**브랜드 전략: 프리미엄 & F&B 특화**\n- 높은 점포당 수익성을 바탕으로 고가 도시락 및 디저트 라인업 강화\n- 사거리 코너 입지 우선 확보 권장.")
            else:
                st.info("**브랜드 전략: 가성비 & 물류 특화**\n- IT 단지 특성상 간편식 재고 회전율이 높은 브랜드 추천\n- 무인 시스템 병행 매장 유리.")

except Exception as e:
    st.error(f"데이터 로드 중 오류가 발생했습니다: {e}")
    st.info("GitHub 저장소 내에 'Project3/data' 폴더와 CSV 파일들이 정확히 있는지 확인해 주세요.")
