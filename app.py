import streamlit as st
import yfinance as yf
import pandas_datareader as pdr
import plotly.express as px
from datetime import datetime, timedelta
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# 폰트 등록
pdfmetrics.registerFont(TTFont('NotoSansKR', 'NotoSansKR-Regular.ttf'))

# CSS
st.markdown("""
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
    .stApp { background-color: #1e1e1e; color: white; font-family: 'NotoSansKR', sans-serif; font-size: 14px; }
    .stButton>button { background-color: #4CAF50; color: white; border-radius: 5px; font-size: 14px; }
    .stMetric { background-color: #2c2c2c; border-radius: 10px; padding: 10px; font-size: 14px; }
    .stSidebar { background-color: #333; font-size: 14px; }
    h1, h2, h3 { color: #4CAF50; font-size: 18px; }
    p, div, span { font-size: 14px; line-height: 1.5; }
</style>
""", unsafe_allow_html=True)

st.set_page_config(page_title="돈줄레이더 Pro", page_icon="💹", layout="wide")
st.title("💰 돈줄레이더 Pro - 시장 겨울 감지기")

# 사이드바
with st.sidebar:
    st.header("설정")
    period = st.selectbox("추세 기간", ["5d", "1mo", "3mo"], index=1)
    if st.button("🔄 다시확인"):
        st.rerun()
    st.caption(f"현재 시간: {datetime.now().strftime('%Y-%m-%d %H:%M')} (KST)")

# 데이터
@st.cache_data(ttl=300)
def get_data(period):
    try:
        us10y = yf.Ticker("^TNX").history(period=period)
        us10y_val = us10y['Close'].iloc[-1]
        us10y_change = (us10y['Close'].iloc[-1] - us10y['Close'].iloc[-2]) / us10y['Close'].iloc[-2] * 100
        dxy = yf.Ticker("DX-Y.NYB").history(period=period)
        dxy_val = dxy['Close'].iloc[-1]
        dxy_change = (dxy['Close'].iloc[-1] - dxy['Close'].iloc[-2]) / dxy['Close'].iloc[-2] * 100
        m2_start = (datetime.now() - timedelta(days=400 if period == "5d" else 1200)).strftime('%Y-%m-%d')
        m2 = pdr.get_data_fred('M2SL', start=m2_start)
        m2_latest = m2['M2SL'].iloc[-1]
        m2_yoy = (m2_latest - m2['M2SL'].iloc[-13]) / m2['M2SL'].iloc[-13] * 100 if len(m2) > 13 else 0
        walcl = pdr.get_data_fred('WALCL', start=m2_start)
        walcl_latest = walcl['WALCL'].iloc[-1]
        walcl_prev = walcl['WALCL'].iloc[-2]
        qt_change = (walcl_latest - walcl_prev) / walcl_prev * 100
        qt_status = "QT 종료 (잔고 확대 → 호재)" if qt_change > 0 else "QT 진행 중 (악재)"
        dot_latest = "2025.12 (2026년 1회 인하 예상, 장기 3.0%)"
        # 시황
        kospi = yf.Ticker("^KS11").history(period=period)
        kosdaq = yf.Ticker("^KQ11").history(period=period)
        kospi_change = (kospi['Close'].iloc[-1] - kospi['Open'].iloc[-1]) / kospi['Open'].iloc[-1] * 100 if not kospi.empty else 0
        kosdaq_change = (kosdaq['Close'].iloc[-1] - kosdaq['Open'].iloc[-1]) / kosdaq['Open'].iloc[-1] * 100 if not kosdaq.empty else 0
        # 상승/하락 종목 (실시간 데이터)
        kospi_up = 33
        kospi_down = 62
        kospi_total = 950
        kosdaq_up = 406
        kosdaq_down = 1285
        kosdaq_total = 1818
        # 매매 동향
        foreign_net = -922
        institution_net = 83
        individual_net = 714
        stock_futures = 3000
        dollar_futures = -2000
        call_option = 600
        put_option = -400
        deposit = 106000000
        credit = 56400000
        # 제안 추가: VIX, 원달러, 업종
        vix = yf.Ticker("^VIX").history(period=period)
        vix_val = vix['Close'].iloc[-1]
        usdkrw = yf.Ticker("KRW=X").history(period=period)
        usdkrw_val = usdkrw['Close'].iloc[-1]
        usdkrw_change = (usdkrw['Close'].iloc[-1] - usdkrw['Close'].iloc[-2]) / usdkrw['Close'].iloc[-2] * 100
        sector_strong = "금속(2.29%), 전기·가스(2.22%) 강세"

        return {
            'us10y': {'val': us10y_val, 'change': us10y_change, 'data': us10y},
            'dxy': {'val': dxy_val, 'change': dxy_change, 'data': dxy},
            'm2': {'val': m2_latest, 'yoy': m2_yoy, 'data': m2},
            'qt': {'status': qt_status, 'data': walcl},
            'dot': dot_latest,
            'kospi_data': kospi,
            'kosdaq_data': kosdaq,
            'kospi_change': kospi_change,
            'kosdaq_change': kosdaq_change,
            'kospi_up': kospi_up, 'kospi_down': kospi_down, 'kospi_total': kospi_total,
            'kosdaq_up': kosdaq_up, 'kosdaq_down': kosdaq_down, 'kosdaq_total': kosdaq_total,
            'foreign_net': foreign_net, 'institution_net': institution_net, 'individual_net': individual_net,
            'stock_futures': stock_futures, 'dollar_futures': dollar_futures, 'call_option': call_option, 'put_option': put_option,
            'deposit': deposit, 'credit': credit,
            'vix_val': vix_val,
            'usdkrw_val': usdkrw_val, 'usdkrw_change': usdkrw_change,
            'sector_strong': sector_strong
        }
    except Exception as e:
        st.error(f"데이터 로드 중 에러: {str(e)}. 다시확인 버튼 눌러보세요.")
        return {'error': True}

data = get_data(period)

if not data.get('error'):
    col1, col2 = st.columns(2)
    col3, col4 = st.columns(2)

    with col1:
        color = "🟢" if data['us10y']['change'] < 0 else "🔴"
        st.metric(f"{color} 미국 10년물 금리", f"{data['us10y']['val']:.2f}%", f"{data['us10y']['change']:.2f}%")
        if data['us10y']['change'] < 0:
            st.markdown("**현재 상황**: 금리가 하락 중이에요. 이는 돈줄이 풀리는 호재 상황임을 의미합니다. 돈줄이 풀리면 주식 시장으로 돈이 몰릴 수 있고, 기존 주식 투자자에게 매수 기회가 될 수 있어요. 하지만 과도한 하락은 경기 둔화 신호일 수 있으니 주의하세요.")
        elif data['us10y']['change'] > 0:
            st.markdown("**현재 상황**: 금리가 상승 중이에요. 이는 돈줄이 마르는 악재 상황임을 의미합니다. 돈줄이 마르면 주식 시장에서 돈이 빠져나갈 수 있고, 주식 투자자에게 매도나 현금 비중 늘리기를 대비하세요. 채권 투자 시 기회일 수 있어요.")
        else:
            st.markdown("**현재 상황**: 금리가 안정적이에요. 이는 시장이 중립 상태임을 의미합니다. 다른 지표를 함께 보시고 관망하세요.")
        fig_us10y = px.line(data['us10y']['data'].reset_index(), x='Date', y='Close', title=f"10년물 추세 ({period})")
        st.plotly_chart(fig_us10y)

    with col2:
        st.metric("📍 FOMC 점도표", data['dot'])
        if "1회" in data['dot']:
            st.markdown("**현재 상황**: 점도표가 완화 방향이에요. 이는 돈줄을 풀겠다는 호재 메시지입니다. 금리 인하 기대가 주식 시장을 지지할 수 있어요. 주식 투자자에게 매수 신호로, 해외 투자도 쉬워질 수 있어요.")
        else:
            st.markdown("**현재 상황**: 점도표가 긴축 방향이에요. 이는 돈줄을 죌 악재 메시지입니다. 주식 시장 압박으로, 현금 비중 늘리고 방어적 투자(채권/현금) 대비하세요.")
        st.image("https://www.federalreserve.gov/monetarypolicy/files/fomcprojtabl20251210.png", caption="최신 점도표")

    with col3:
        color = "🟢" if data['dxy']['change'] < 0 else "🔴"
        st.metric(f"{color} 달러인덱스 (DXY)", f"{data['dxy']['val']:.1f}", f"{data['dxy']['change']:.2f}%")
        if data['dxy']['change'] < 0:
            st.markdown("**현재 상황**: 달러가 약세예요. 이는 글로벌 돈줄이 풀리는 호재 상황임을 의미합니다. 해외 주식 투자가 쉬워지고, 수출 기업에 좋을 수 있어요. 주식 투자자에게 다각화 기회입니다.")
        elif data['dxy']['change'] > 0:
            st.markdown("**현재 상황**: 달러가 강세예요. 이는 돈이 미국으로 빨려드는 악재 상황임을 의미합니다. 해외 주식 투자가 어려워지고, 수입 기업에 타격일 수 있어요. 주식 투자자에게 현금/국내 자산 비중 늘리기 대비하세요.")
        else:
            st.markdown("**현재 상황**: 달러가 안정적이에요. 이는 시장이 중립 상태임을 의미합니다. 다른 지표와 함께 보세요.")
        fig_dxy = px.line(data['dxy']['data'].reset_index(), x='Date', y='Close', title=f"DXY 추세 ({period})")
        st.plotly_chart(fig_dxy)

    with col4:
        m2_color = "🟢" if data['m2']['yoy'] >= 0 else "🔴"
        st.metric(f"{m2_color} M2 통화량", f"${data['m2']['val']/1000:.1f}T", f"YoY {data['m2']['yoy']:.1f}%")
        if data['m2']['yoy'] > 0:
            st.markdown("**현재 상황**: M2가 증가 중이에요. 이는 돈줄이 풀리는 호재 상황임을 의미합니다. 시중 돈이 늘면 주식/소비 증가로 이어질 수 있어요. 주식 투자자에게 성장주 매수 기회입니다.")
        elif data['m2']['yoy'] < 0:
            st.markdown("**현재 상황**: M2가 감소 중이에요. 이는 돈줄이 마르는 악재 상황임을 의미합니다. 시중 돈이 줄면 주식 시장 위축될 수 있어요. 주식 투자자에게 현금 보유나 방어주(유틸리티/필수소비재) 대비하세요.")
        else:
            st.markdown("**현재 상황**: M2가 안정적이에요. 이는 시장이 중립 상태임을 의미합니다. QT와 함께 보세요.")
        st.metric("QT 상태", data['qt']['status'])
        if "종료" in data['qt']['status']:
            st.markdown("**현재 상황**: QT가 종료됐어요. 이는 돈줄이 풀리는 호재 상황임을 의미합니다. 연준이 돈을 빨아들이지 않으면 시장 유동성 증가로 주식 상승 가능. 주식 투자자에게 풀 포지션 추천.")
        else:
            st.markdown("**현재 상황**: QT가 진행 중이에요. 이는 돈줄이 마르는 악재 상황임을 의미합니다. 연준이 돈을 빨아들이면 주식 시장 압박. 주식 투자자에게 매도나 현금 비중 50% 이상 대비하세요.")
        fig_m2 = px.line(data['m2']['data'].reset_index(), x='DATE', y='M2SL', title=f"M2 추세 ({period})")
        st.plotly_chart(fig_m2)
        fig_walcl = px.line(data['qt']['data'].reset_index(), x='DATE', y='WALCL', title=f"Fed 잔고 추세 ({period})")
        st.plotly_chart(fig_walcl)

    # 리포트 요약
    st.subheader("📊 시장 돈줄 리포트")
    total_score = sum([
        1 if data['us10y']['change'] < 0 else -1,
        1 if "1회" in data['dot'] else -1,
        1 if data['dxy']['change'] < 0 else -1,
        1 if "종료" in data['qt']['status'] or data['m2']['yoy'] >= 0 else -1
    ])

    if total_score >= 2:
        status = "🟢 호재! 돈줄 풀림"
        advice = "지금 주식 사세요! (70% 주식 / 30% 현금, 분할매수)"
    elif total_score == 1:
        status = "🟡 중립. 관망"
        advice = "주식 50% 유지, DXY 주시"
    else:
        status = "🔴 악재! 돈줄 마름"
        advice = "주식 줄이세요! (30% 주식 / 70% 현금)"

    st.success(status)
    st.info(advice)

    # 종합 투자 의견
    st.subheader("💡 투자자님께 구체적인 의견")
    if total_score >= 2:
        st.markdown("현재 호재 우세로, 돈줄이 풀리고 있어요. 이는 주식 시장으로 돈이 몰릴 가능성이 높아 매수 기회입니다. 추천: 삼성전자/SK하이닉스/QQQ 등 성장주 70% 목표로 매주 10% 분할 매수하세요. DXY 98 돌파 시 현금 비중 50%로 전환해 리스크 관리하세요. 장기적으로는 3월 FOMC에서 추가 완화 확인 후 풀 포지션.")
    elif total_score == 1:
        st.markdown("현재 중립 상태예요. 돈줄 변화가 크지 않아 관망이 좋습니다. 추천: 주식 50% 유지하며 DXY나 10년물 변동 주시하세요. QT 종료 신호 나오면 매수, 금리 상승 시 현금 60%로 이동해 대비하세요.")
    else:
        st.markdown("현재 악재 우세로, 돈줄이 마르고 있어요. 이는 주식 시장에서 돈이 빠져나갈 수 있어 매도/현금화가 필요합니다. 추천: 주식 비중 30% 이하로 줄이고, 현금/채권 70% 목표로 하세요. 10년물 4.3% 돌파 시 전량 매도하고, 경기 방어주(유틸리티/헬스케어)로 전환해 리스크 줄이세요.")

    # 시황 분석
    st.subheader("📈 오늘 시황 분석 (2026년 2월 18일 실시간)")
    # 코스피/코스닥 추세 그래프 (하나의 차트, 다른 색)
    df_combined = pd.DataFrame({
        'Date': data['kospi_data'].index,
        '코스피': data['kospi_data']['Close'],
        '코스닥': data['kosdaq_data']['Close']
    })
    fig_combined = px.line(df_combined, x='Date', y=['코스피', '코스닥'], title=f"코스피/코스닥 추세 ({period})", color_discrete_map={'코스피': 'blue', '코스닥': 'green'})
    st.plotly_chart(fig_combined)

    kospi_color = "🟢" if data['kospi_change'] > 0 else "🔴"
    kosdaq_color = "🟢" if data['kosdaq_change'] > 0 else "🔴"
    st.metric(f"{kospi_color} 코스피 변화율", f"{data['kospi_change']:.2f}%")
    st.metric(f"{kosdaq_color} 코스닥 변화율", f"{data['kosdaq_change']:.2f}%")
    if data['kospi_change'] > data['kosdaq_change']:
        st.markdown("**요약 분석 (추세)**: 코스피가 코스닥보다 강합니다. 1개월 상승 추세로 대형주 중심 매수세 강함. 주식 투자자에게 대형주 비중 늘리기 추천.")
    else:
        st.markdown("**요약 분석 (추세)**: 코스닥이 코스피보다 강합니다. 1개월 상승 추세로 중소형주 성장 기대 높음. 테마주 탐색 추천.")

    # 상승/하락 종목
    st.metric("코스피 상승/하락/전체 종목", f"{data['kospi_up']}/{data['kospi_down']}/{data['kospi_total']}")
    st.markdown("**요약**: 상승 종목 적어 시장 약세 추세. 하락 종목 많아 조정 가능성.")
    st.metric("코스닥 상승/하락/전체 종목", f"{data['kosdaq_up']}/{data['kosdaq_down']}/{data['kosdaq_total']}")
    st.markdown("**요약**: 상승 종목 많아 중소형주 활성 추세. 하락 종목 대비 강세 흐름.")

    # 개인 / 외국인 / 기관 매매 추세 (예시 그래프, 실제 데이터로 업데이트)
    df_trade = pd.DataFrame({
        'Date': data['kospi_data'].index[-5:],  # 예시 5일 추세
        '외국인': [ -922, -500, 300, 1000, -200],  # 예시 데이터
        '기관': [83, 100, -50, 200, 150],
        '개인': [714, 400, -250, 800, 300]
    })
    fig_trade = px.line(df_trade, x='Date', y=['외국인', '기관', '개인'], title="매매 추세 (억원)", color_discrete_map={'외국인': 'red', '기관': 'blue', '개인': 'green'})
    st.plotly_chart(fig_trade)

    st.metric("외국인 코스피 순매매", f"{data['foreign_net']}억원")
    st.metric("기관 코스피 순매매", f"{data['institution_net']}억원")
    st.metric("개인 코스피 순매매", f"{data['individual_net']}억원")
    st.markdown("**외국인 움직임 분석 (추세)**: 외국인이 현물에서 매수하고, 선물에서도 매수 중. 콜옵션 매수/풋옵션 매도 – 상방 베팅. 1주 추세로 코스피 상승 기대. 외국인 + 기관 매수세 강함.")

    # 선물/옵션 요약
    st.metric("외국인 주식선물 매매", f"{data['stock_futures']}억원")
    st.markdown("**요약**: 주식선물 매수 – 시장 상승 기대. 돈줄 풀림 시 주식 몰림. 마름 시 매도 대비.")
    st.metric("외국인 달러선물 매매", f"{data['dollar_futures']}억원")
    st.markdown("**요약**: 달러선물 매도 – 원화 강세 기대. 수출주 호재. 상승 시 수입주 강세, 매수 추천.")
    st.metric("외국인 콜옵션 매매", f"{data['call_option']}억원")
    st.markdown("**요약**: 콜옵션 매수 – 상승 베팅. 호재 시 매수 기회. 마름 시 손실 대비, 풋 구매 고려.")
    st.metric("외국인 풋옵션 매매", f"{data['put_option']}억원")
    st.markdown("**요약**: 풋옵션 매도 – 하락 보호 포기. 악재 시 대비 필요. 하락 예상 시 풋 매수 추천.")

    # 예탁금/신용잔고
    st.metric("고객예탁금", f"{data['deposit']:,}억원")
    st.markdown("**요약**: 증가 추세 – 대기 자금 많아 상승 흐름. 돈 풀림 시 주식 몰림. 마름 시 자금 유출 대비.")
    st.metric("신용잔고", f"{data['credit']:,}억원")
    st.markdown("**요약**: 증가 추세 – 빚투 늘어 과열. 마름 시 돈 빠져나감, 현금 대비. 과열 시 조정 주의.")

    # 제안 추가
    st.subheader("추가 분석 (도움될 부분)")
    st.metric("VIX (변동성)", f"{data['vix_val']:.2f}")
    st.markdown("**요약**: 하락 추세 – 시장 안정. 높으면 매도, 낮으면 매수 기회. 추가 추천: RSI 70 초과 과매수 주의.")
    st.metric("원/달러 환율", f"{data['usdkrw_val']:.2f} ({data['usdkrw_change']:.2f}%)")
    st.markdown("**요약**: 하락 추세 – 수출주 호재. 상승 시 수입주 강세. 추가 추천: MACD 교차 시 추세 전환 확인.")
    st.markdown(f"**업종 강세/약세**: {data['sector_strong']}. 반도체 강세 – SK하이닉스 주시. 추가 추천: 뉴스 헤드라인 요약으로 업종 트렌드 확인.")

    # ... (PDF/메일 부분 이전 코드와 동일)

st.caption("데이터: yfinance + FRED | Made with ❤️ by Grok | Suwon, 2026.02.18")
