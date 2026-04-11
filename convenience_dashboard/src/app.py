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

    def parse_area(area_str):
        # "지상 1층, 33㎡ / 10평" -> 33
        try:
            match = re.search(r'([\d.]+)\s*㎡', str(area_str))
            if match:
                return float(match.group(1))
        except: pass
        return 0.0

    nemo_combined['Deposit'], nemo_combined['Rent'] = zip(*nemo_combined['price'].apply(parse_price))
    nemo_combined['Walk_Min'] = nemo_combined['category_location'].apply(parse_distance)
    nemo_combined['Distance_m'] = nemo_combined['Walk_Min'] * 70 # 1분당 70m 가정
    nemo_combined['Area_m2'] = nemo_combined['area_floor'].apply(parse_area)
    
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
        # [수정] 지역명과 연동된 전략 제목 표시
        st.subheader(f"💡 {target_dong} 편의점 입점 전략")
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
        
        st.markdown("---")
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
            # [원복] 단일 지역 매출 추이 그래프
            trend_df = rev_summary[rev_summary['Dong'] == target_dong].groupby('Quarter')['Estimated_Rev_Per_Store_M'].mean().reset_index()
            trend_df['Quarter_Label'] = trend_df['Quarter'].apply(lambda x: f"{str(x)[:4]}년 {str(x)[4]}분기")
            
            fig_trend = px.line(trend_df, x='Quarter_Label', y='Estimated_Rev_Per_Store_M', 
                                title=f"2025년 {target_dong} 매출액 추이",
                                markers=True, text='Estimated_Rev_Per_Store_M',
                                template="plotly_white")
            fig_trend.update_traces(texttemplate='%{text:.1f}M', textposition='top center', line_color='#007bff')
            fig_trend.update_layout(xaxis_title="기준 분기", yaxis_title="매출 (백만 원)")
            st.plotly_chart(fig_trend, use_container_width=True)
            
        with c2:
            # [원복] 기본 브랜드 점유율 도넛 그래프
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
        # 필터 레이아웃
        st.markdown("### 🔍 필터")
        f_col1, f_col2, f_col3, f_col4 = st.columns(4)
        with f_col1:
            st.session_state.dist_range = st.slider("역과의 거리 (m)", 0, 1000, st.session_state.dist_range, step=50)
        with f_col2:
            max_rent = int(nemo_data['Rent'].max())
            st.session_state.rent_range = st.slider("월세 범위 (만 원)", 0, max_rent, st.session_state.rent_range, step=10)
        with f_col3:
            max_dep = int(nemo_data['Deposit'].max())
            st.session_state.dep_range = st.slider("보증금 범위 (만 원)", 0, max_dep, st.session_state.dep_range, step=500)
        with f_col4:
            area_options = ["전체", "33㎡ 이하 (~10평)", "33-66㎡ (10-20평)", "66-99㎡ (20-30평)", "99㎡ 이상 (30평~)"]
            selected_area = st.selectbox("전용면적", options=area_options)

        st.markdown("---") # 필터 밑에 회색 바 추가

        # 데이터 필터링 로직 강화
        n_filtered = nemo_data[
            (nemo_data['District'] == target_dong) & 
            (nemo_data['Distance_m'] >= st.session_state.dist_range[0]) & (nemo_data['Distance_m'] <= st.session_state.dist_range[1]) &
            (nemo_data['Rent'] >= st.session_state.rent_range[0]) & (nemo_data['Rent'] <= st.session_state.rent_range[1]) &
            (nemo_data['Deposit'] >= st.session_state.dep_range[0]) & (nemo_data['Deposit'] <= st.session_state.dep_range[1])
        ].dropna(subset=['Walk_Min']).copy()

        # 전용면적 추가 필터링
        if selected_area == "33㎡ 이하 (~10평)":
            n_filtered = n_filtered[n_filtered['Area_m2'] <= 33]
        elif selected_area == "33-66㎡ (10-20평)":
            n_filtered = n_filtered[(n_filtered['Area_m2'] > 33) & (n_filtered['Area_m2'] <= 66)]
        elif selected_area == "66-99㎡ (20-30평)":
            n_filtered = n_filtered[(n_filtered['Area_m2'] > 66) & (n_filtered['Area_m2'] <= 99)]
        elif selected_area == "99㎡ 이상 (30평~)":
            n_filtered = n_filtered[n_filtered['Area_m2'] > 99]

        # 매물 KPI 지표 (필터 밑으로 이동)
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

        # [수정] 그래프 제목 스타일 통일 및 아이콘 추가
        st.subheader("📈 역과의 거리 VS. 월세 분포")
        
        # 산점도 시각화
        if not n_filtered.empty:
            fig_scatter = px.scatter(n_filtered, x='Distance_m', y='Rent', 
                                     color='Is_1F', size='Deposit', hover_name='description',
                                     # title 제거 (st.subheader로 대체)
                                     labels={'Distance_m': '역과의 거리 (m)', 'Rent': '월세 (만 원)', 'Is_1F': '1층 여부'},
                                     color_discrete_map={True: '#ef4444', False: '#64748b'},
                                     template="plotly_white")
            
            # 가이드 영역 (200-300m)
            fig_scatter.add_vrect(x0=200, x1=300, fillcolor="#22c55e", opacity=0.1, 
                                  annotation_text="🎯 최적 입지", annotation_position="top left")
            
            fig_scatter.update_layout(title=None) # 차트 내부 제목 제거
            st.plotly_chart(fig_scatter, use_container_width=True)
            st.caption("※ 보증금 크기에 따라 원의 크기가 결정됩니다. 붉은색 점은 접근성이 높은 1층 매물입니다.")

            st.markdown("---")
            
            # 핵심 전략 매물 Top 3
            st.subheader("✨ 핵심 전략 매물 Top 3")
            best_pick = n_filtered[
                (n_filtered['Is_1F'] == True)
            ].sort_values('Rent')

            if not best_pick.empty:
                cols = st.columns(3)
                for i, (idx, row) in enumerate(best_pick.head(3).iterrows()):
                    with cols[i]:
                        st.success(f"""
                        **[{i+1}순위]**  
                        **{row['category_location']}**  
                        - **임대료**: {row['Rent']}만 / {row['Deposit']}만  
                        - **면적**: {row['Area_m2']:.1f}㎡  
                        - **거리**: {row['Distance_m']}m  
                        """)
            else:
                st.info("현재 필터링된 조건에 부합하는 매물이 없습니다.")

            st.markdown("---")
            st.markdown(f"### 📋 주요 매물 리스트 ({st.session_state.dist_range[0]}m ~ {st.session_state.dist_range[1]}m 이내)")
            st.dataframe(n_filtered.sort_values('Distance_m')[['category_location', 'price', 'area_floor', 'description']].reset_index(drop=True), use_container_width=True)
        else:
            st.info("선택한 필터 조건에 맞는 매물이 없습니다. 필터를 조정해 주세요.")

    with tab3:
        st.subheader("🏢 데이터 기반 가산동 vs 여의동 상권 비교")
        
        # 분석 리포트 요약 데이터
        compare_data = {
            "비교 항목": ["주요 고객군 (평균)", "상권 핵심 업종", "매출 피크 시간", "시간당 평균 매출", "핵심 입점 전략"],
            "가산동 (IT/직장인 상권)": [
                "2030세대 (약 2.7만명)",
                "IT 본사, 경영컨설팅, 광고",
                "11~14시 (점심 집중형)",
                "약 43.7억 원 (11~14시)",
                "무인 병행 매장 및 간편식 특화"
            ],
            "여의동 (금융/프리미엄 상권)": [
                "3040세대 (약 4.3만명)",
                "금융, 사무직 지원 서비스, 카페",
                "일과 시간 전반 (고른 분포)",
                "약 24.2억 원 (11~14시)",
                "프리미엄 도시락 및 디저트 라인업"
            ]
        }
        
        st.table(pd.DataFrame(compare_data))
        
        col_eda1, col_eda2 = st.columns(2)
        
        # 요약 데이터 로드
        fp_sum_path = "15. fp_summary.csv"
        rev_sum_path = "16. rev_time_summary.csv"
        
        with col_eda1:
            st.markdown("#### 👥 전 연령대 생활인구 비교")
            if os.path.exists(fp_sum_path):
                fp_summary = pd.read_csv(fp_sum_path)
                # 전 연령대 컬럼 정의 (EDA 스크립트와 동일)
                age_buckets = ['10세 미만', '10대', '20대', '30대', '40대', '50대', '60대', '70대 이상']
                # 데이터 재구조화 (Melt)
                plot_df = fp_summary.melt(id_vars='DongName', value_vars=age_buckets, 
                                        var_name='연령대', value_name='인구수')
                
                fig_age = px.bar(plot_df, x='연령대', y='인구수', color='DongName', barmode='group',
                                labels={'DongName': '행정동', '인구수': '평균 생활인구'},
                                color_discrete_sequence=['#3b82f6', '#f59e0b'])
                fig_age.update_layout(height=400)
                st.plotly_chart(fig_age, use_container_width=True)
            else:
                st.info("생활인구 분석 데이터가 없습니다.")
                
        with col_eda2:
            st.markdown("#### 🕒 시간대별 매출 패턴 비교")
            if os.path.exists(rev_sum_path):
                rev_summary = pd.read_csv(rev_sum_path, index_col=0)
                # 데이터 재구조화
                rev_plot_df = rev_summary.T.reset_index()
                rev_plot_df.columns = ['시간대'] + rev_summary.index.tolist()
                rev_plot_df = rev_plot_df.melt(id_vars='시간대', var_name='행정동', value_name='매출금액')
                
                fig_rev = px.line(rev_plot_df, x='시간대', y='매출금액', color='행정동', markers=True,
                                labels={'매출금액': '평균 매출액'},
                                color_discrete_sequence=['#ef4444', '#10b981'])
                fig_rev.update_layout(height=400)
                st.plotly_chart(fig_rev, use_container_width=True)
            else:
                st.info("매출 분석 데이터가 없습니다.")

        st.markdown("---")
        
        # 상세 데이터 근거 (Expander)
        with st.expander("📊 데이터 기반 상세 근거 보기 (EDA 리포트 요약)"):
            st.markdown("""
            **1. 주요 고객군 차이**
            - **가산동**은 2030 IT 직장인 비중이 높아 가성비와 편의성을 중시하는 '간편식 시장'이 매우 큽니다.
            - **여의동**은 3040 전문직 직장인과 고소득 사무직 인구가 밀집되어 '프리미엄 F&B'에 대한 지불 용의가 높습니다.

            **2. 상권 업종 구성**
            - 가산동은 '본사·경영 컨설팅', '전문 디자인' 등 B2B 지원 업종이 강력한 상권을 형성하고 있습니다.
            - 여의동은 '금융' 외에도 '비알코올(카페)', '기타 간이' 업종이 발달하여 유동인구가 머무르는 시간이 깁니다.

            **3. 매출 발생 패턴**
            - 가산동은 점심시간(11~14시) 매출이 전체의 상당 부분을 차지하며, 야근 집중 지역의 경우 20시 이후에도 안정적인 매출이 발생합니다.
            - 여의동은 특정 시간 집중보다는 오전 10시부터 오후 18시까지 고르게 높은 매출을 유지하는 특성을 보입니다.
            """)
        
        st.info("💡 **전략 제언**: 가산동은 '회전율'과 '가성비'에 집중하고, 여의동은 '객단가'와 '상품 다양성'에 집중하는 매장 운영 전략이 유리합니다.")

except Exception as e:
    st.error(f"데이터 로드 중 오류가 발생했습니다: {e}")
    st.info("Project3/data 폴더 내에 필요한 CSV 파일들이 있는지 확인해 주세요.")
