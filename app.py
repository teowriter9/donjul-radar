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
import time  # 재시도 위해 추가

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

# 데이터 (에러 핸들링 강화)
@st.cache_data(ttl=300)
def get_data(period):
    try:
        # 재시도 로직
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
                dxy_change = (dxy['Close'].iloc[-1] - dxy['Close'].iloc[-2]) / dxy['Close'].일이 [-2] / dxy['Close'].iloc[-2] * 100

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
                time.sleep(1)  # 재시도 대기

    except:
        return {'error': True, 'message': "알 수 없는 에러"}

data = get_data(period)

if data.get('error'):
    st.error(f"데이터 로드 실패: {data.get('message', '인터넷이나 API 확인하세요.')} 다시확인 버튼 눌러보세요.")
else:
    # ... (이전 지표 섹션 동일, 생략하여 길이 줄임)

    # PDF 및 메일 (이전 동일, 생략)

st.caption("데이터: yfinance + FRED | Made with ❤️ by Grok | Suwon, 2026.02.18")
