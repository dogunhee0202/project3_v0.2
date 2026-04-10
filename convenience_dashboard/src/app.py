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

# 디버깅: 현재 작업 디렉토리 출력
# st.write(f"Current Working Directory: {os.getcwd()}")

# 커스텀 CSS (Premium Look)
st.markdown("""
<style>
    /* 기본 폰트 설정 */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    * {
        font-family: 'Outfit', 'Pretendard', sans-serif;
    }

    .main {
        background-color: #ffffff;
    }
    
    /* 메트릭 카드 스타일 */
    [data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        border: 1px solid #f1f5f9;
        transition: transform 0.2s ease-in-out;
    }

    [data-testid="stMetric"]:hover {
        transform: translateY(-2px);
    }

    /* 메트릭 텍스트 색상 (가독성 문제 해결) */
    [data-testid="stMetricLabel"] {
        color: #64748b !important;
        font-weight: 500 !important;
    }

    [data-testid="stMetricValue"] {
        color: #1e293b !important;
        font-weight: 700 !important;
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
        background-color: #f8f9fa;
        border-right: 1px solid #e2e8f0;
    }
</style>
""", unsafe_allow_html=True)

# 데이터 로드 함수
@st.cache_data
def load_data():
    # 1. 매출 요약 데이터
    rev_summary = pd.read_csv("13. revenue_analysis_summary.csv")
    
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

    # 사이드바 설정 (필터 변수 우선 정의)
    st.sidebar.header("📍 분석 지역")
    target_dong = st.sidebar.selectbox("지역을 선택하세요", ["가산동", "여의동"])

    # 상권 지표 데이터 계산 (기존 위치 유지)

    # 상권 지표 데이터 계산
    district_rev = rev_summary[rev_summary['Dong'] == target_dong]
    latest_q = district_rev['Quarter'].max()
    q_data = district_rev[district_rev['Quarter'] == latest_q]
    
    if not q_data.empty:
        avg_rev_per_store = q_data['Estimated_Rev_Per_Store_M'].iloc[0]
        total_stores = q_data['StoreCount'].sum()
    else:
        avg_rev_per_store, total_stores = 0, 0

    st.markdown("---")

    # [수정] 탭 간 데이터 공유를 위해 필터 기본값 및 데이터 필터링 사전 수행
    # 위젯은 tab2에 배치하지만, 변수는 여기서 초기화하여 tab3 등에서도 에러 없이 사용 가능하게 함
    if 'dist_range' not in st.session_state: st.session_state.dist_range = (0, 500)
    if 'rent_range' not in st.session_state: st.session_state.rent_range = (0, int(nemo_data['Rent'].max()))
    if 'dep_range' not in st.session_state: st.session_state.dep_range = (0, int(nemo_data['Deposit'].max()))

    # 탭 구성
    tab1, tab2, tab3 = st.tabs(["📊 편의점 현황", "📍 임대료 & 입지 분석", "💡 추천 입점 전략"])

    with tab1:
        st.subheader("📊 주요 상권 지표")
        kpi1, kpi2, kpi3 = st.columns(3)
        with kpi1:
            st.metric("총 점포 수", f"{total_stores}개", help="2025년 4분기 기준 점포 수")
        with kpi2:
            st.metric("점포당 평균 매출", f"{avg_rev_per_store:.1f} M", help="월간 추정 매출액 (단위: 백만 원)")
        with kpi3:
            market_val = (avg_rev_per_store * total_stores / 10)
            st.metric("월간 시장 규모", f"{market_val:.1f} 억", help="행정동 전체 편의점 합산 매출액")
        
        st.markdown("---")
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
            # 브랜드 점유율 도넛 그래프
            brand_share = q_data[['Brand', 'StoreCount']]
            fig_pie = px.pie(brand_share, values='StoreCount', names='Brand', 
                             title="브랜드 점유율 현황",
                             hole=0.5, color_discrete_sequence=px.colors.qualitative.Bold)
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)

        st.markdown("---")
        st.subheader("🗺️ 지역별 편의점 분포 지도")
        
        # 브랜드 선택 필터 (지도 강조용)
        all_brands = sorted(branded_stores['Brand'].unique().tolist())
        selected_brands = st.multiselect(
            "강조할 브랜드를 선택하세요 (미선택 시 전체 표시)", 
            options=all_brands,
            default=[],
            help="선택한 브랜드의 마커가 강조되어 표시됩니다."
        )

        # 브랜드 색상 매핑
        brand_colors_base = {
            'GS25': '#00B0F0',      # 하늘색
            'CU': '#744199',        # 보라색
            '세븐일레븐': '#008000',   # 초록색
            '이마트24': '#FFB81C',    # 노란색
            '미니스톱': '#0055A4',    # 파란색
            '기타': '#808080'         # 회색
        }

        # 강조 로직 적용 데이터 준비
        map_df = branded_stores[branded_stores['행정동명'] == target_dong].copy()
        
        if not map_df.empty:
            # 강조 조건 설정
            if selected_brands:
                map_df['Highlight'] = map_df['Brand'].apply(lambda x: x if x in selected_brands else '기타(흐림)')
                map_df['MarkerSize'] = map_df['Brand'].apply(lambda x: 15 if x in selected_brands else 7)
                map_df['Opacity'] = map_df['Brand'].apply(lambda x: 1.0 if x in selected_brands else 0.3)
                
                # 색상 매핑 확장
                highlight_colors = {k: v for k, v in brand_colors_base.items()}
                highlight_colors['기타(흐림)'] = '#e2e8f0' # 매우 연한 회색
            else:
                map_df['Highlight'] = map_df['Brand']
                map_df['MarkerSize'] = 10
                map_df['Opacity'] = 0.8
                highlight_colors = brand_colors_base

            # 지하철역 데이터 정의
            stations = [
                {'name': '가산디지털단지역', 'lat': 37.4807, 'lon': 126.8842, 'dong': '가산동'},
                {'name': '여의도역', 'lat': 37.5216, 'lon': 126.9243, 'dong': '여의동'},
                {'name': '여의나루역', 'lat': 37.5271, 'lon': 126.9328, 'dong': '여의동'},
                {'name': '국회의사당역', 'lat': 37.5281, 'lon': 126.9179, 'dong': '여의동'}
            ]
            
            # 현재 동에 해당하는 역 필터링
            filtered_stations = [s for s in stations if s['dong'] == target_dong]

            fig_map = px.scatter_mapbox(
                map_df, 
                lat="위도", lon="경도", 
                color="Highlight",
                hover_name="상호명",
                hover_data={"Highlight": False, "위도": False, "경도": False, "Brand": True},
                color_discrete_map=highlight_colors,
                zoom=14,
                height=600,
                size="MarkerSize",
                size_max=15,
                mapbox_style="carto-positron"
            )

            # 지하철역 마커 추가 (회색 바탕 텍스트 레이아웃)
            if filtered_stations:
                # 1. 배경용 회색 상자 레이어
                fig_map.add_trace(go.Scattermapbox(
                    lat=[s['lat'] for s in filtered_stations],
                    lon=[s['lon'] for s in filtered_stations],
                    mode='markers',
                    marker=go.scattermapbox.Marker(
                        size=34, # 텍스트를 감쌀 정도로 넉넉한 크기
                        color='lightgrey',
                        opacity=0.8,
                        symbol='square' # 사각형 배경
                    ),
                    showlegend=False,
                    hoverinfo='none'
                ))

                # 2. 검정색 역 이름 텍스트 레이어
                fig_map.add_trace(go.Scattermapbox(
                    lat=[s['lat'] for s in filtered_stations],
                    lon=[s['lon'] for s in filtered_stations],
                    mode='text',
                    text=[s['name'] for s in filtered_stations],
                    textposition='middle center',
                    textfont=dict(
                        size=14,
                        color='black', # 검정색 글씨
                        family='Pretendard, Arial Black'
                    ),
                    name='지하철역',
                    hoverinfo='text'
                ))
                
                # 역 위치를 점(Dot)으로 한 번 더 강조
                fig_map.add_trace(go.Scattermapbox(
                    lat=[s['lat'] for s in filtered_stations],
                    lon=[s['lon'] for s in filtered_stations],
                    mode='markers',
                    marker=go.scattermapbox.Marker(
                        size=12,
                        color='#ff0000',
                        opacity=0.8
                    ),
                    showlegend=False,
                    hoverinfo='none'
                ))

            fig_map.update_layout(
                margin={"r":0,"t":0,"l":0,"b":0},
                showlegend=True,
                legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(255,255,255,0.7)")
            )
            st.plotly_chart(fig_map, use_container_width=True)
            st.info(f"💡 현재 **{target_dong}**의 편의점 분포를 보여주고 있습니다. {'브랜드를 선택하여 특정 점포를 강조해 보세요.' if not selected_brands else f'{', '.join(selected_brands)} 브랜드가 강조되었습니다.'}")
        else:
            st.warning(f"{target_dong}에 대한 편의점 위치 데이터가 없습니다.")

    with tab2:
        st.subheader("💰 임대 시세 및 입지 분석")
        
        # 필터 레이아웃
        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            st.session_state.dist_range = st.slider("역과의 거리 (m)", 0, 1000, st.session_state.dist_range, step=50)
        with f_col2:
            max_rent = int(nemo_data['Rent'].max())
            st.session_state.rent_range = st.slider("월세 범위 (만 원)", 0, max_rent, st.session_state.rent_range, step=10)
        with f_col3:
            max_dep = int(nemo_data['Deposit'].max())
            st.session_state.dep_range = st.slider("보증금 범위 (만 원)", 0, max_dep, st.session_state.dep_range, step=500)

        # 데이터 필터링
        n_filtered = nemo_data[
            (nemo_data['District'] == target_dong) & 
            (nemo_data['Distance_m'] >= st.session_state.dist_range[0]) & (nemo_data['Distance_m'] <= st.session_state.dist_range[1]) &
            (nemo_data['Rent'] >= st.session_state.rent_range[0]) & (nemo_data['Rent'] <= st.session_state.rent_range[1]) &
            (nemo_data['Deposit'] >= st.session_state.dep_range[0]) & (nemo_data['Deposit'] <= st.session_state.dep_range[1])
        ].dropna(subset=['Walk_Min'])

        # 매물 KPI 지표 (탭 내부로 이동)
        m_col1, m_col2, m_col3 = st.columns(3)
        with m_col1:
            st.metric("매물 개수", f"{len(n_filtered)}개", help="선택된 필터 조건에 맞는 매물 수")
        with m_col2:
            avg_rent = n_filtered['Rent'].mean() if not n_filtered.empty else 0
            st.metric("평균 월세", f"{avg_rent:.1f} 만", help="필터링된 매물의 평균 월세")
        with m_col3:
            avg_deposit = n_filtered['Deposit'].mean() if not n_filtered.empty else 0
            st.metric("평균 보증금", f"{avg_deposit:.0f} 만", help="필터링된 매물의 평균 보증금")
        
        st.markdown("---")

        # 산점도 시각화
        if not n_filtered.empty:
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

            st.markdown(f"### 📋 주요 매물 리스트 ({st.session_state.dist_range[0]}m ~ {st.session_state.dist_range[1]}m 이내)")
            st.dataframe(n_filtered.sort_values('Distance_m')[['category_location', 'price', 'area_floor', 'description']].reset_index(drop=True), use_container_width=True)
        else:
            st.info("선택한 필터 조건에 맞는 매물이 없습니다. 필터를 조정해 주세요.")

    with tab3:
        st.subheader("🚀 전략적 입점 추천")
        
        # 추천 매물 선정 (선택된 거리 범위 내 1층 매물 중 저렴한 순)
        best_pick = n_filtered[
            (n_filtered['Is_1F'] == True)
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
