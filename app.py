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
import time

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
        for attempt in range(2):
            try:
                us10y = yf.Ticker("^TNX").history(period=period)
                if us10y.empty:
                    raise ValueError("US10Y 데이터 빈 값")
                us10y_val = us10y['Close'].iloc[-1]
                us10y_change = (us10y['Close'].iloc[-1] - us10y['Close'].iloc[-2]) / us10y['Close'].iloc[-2] * 100

                dxy = yf.Ticker("DX-Y.NYB").history(period=period)
                if dxy.empty:
                    raise ValueError("DXY 데이터 빈 값")
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

                return {
                    'us10y': {'val': us10y_val, 'change': us10y_change, 'data': us10y},
                    'dxy': {'val': dxy_val, 'change': dxy_change, 'data': dxy},
                    'm2': {'val': m2_latest, 'yoy': m2_yoy, 'data': m2},
                    'qt': {'status': qt_status, 'data': walcl},
                    'dot': dot_latest
                }
            except Exception as e:
                if attempt == 1:
                    return {'error': True, 'message': str(e)}
                time.sleep(1)

    except:
        return {'error': True, 'message': "알 수 없는 에러"}

data = get_data(period)

if data.get('error'):
    st.error(f"데이터 로드 실패: {data.get('message', '인터넷이나 API 확인하세요.')} 다시확인 버튼 눌러보세요.")
else:
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

    # ... (나머지 지표 섹션, 시황 분석, 리포트, 종합 의견, PDF/메일 이전 코드와 동일 – 생략해서 길이 줄임)

st.caption("데이터: yfinance + FRED | Made with ❤️ by Grok | Suwon, 2026.02.18")
