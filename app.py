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

# 폰트 등록 (한글 깨짐 방지)
pdfmetrics.registerFont(TTFont('NotoSansKR', 'NotoSansKR-Regular.ttf'))

# 커스텀 CSS (이전 그대로)
st.markdown("""
<style>
    .stApp { background-color: #1e1e1e; color: white; }
    .stButton>button { background-color: #4CAF50; color: white; border-radius: 5px; }
    .stMetric { background-color: #2c2c2c; border-radius: 10px; padding: 10px; }
    .stSidebar { background-color: #333; }
    h1, h2, h3 { color: #4CAF50; }
</style>
""", unsafe_allow_html=True)

st.set_page_config(page_title="돈줄레이더 Pro", page_icon="💹", layout="wide")
st.title("💰 돈줄레이더 Pro - 시장 겨울 감지기")

# 사이드바 (이전 그대로)
with st.sidebar:
    st.header("설정")
    period = st.selectbox("추세 기간", ["5d", "1mo", "3mo"], index=1)
    if st.button("🔄 다시확인 (데이터 새로고침)"):
        st.rerun()
    st.caption(f"현재 시간: {datetime.now().strftime('%Y-%m-%d %H:%M')} (KST)")

# 데이터 가져오기 (이전 그대로)
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

        return {
            'us10y': {'val': us10y_val, 'change': us10y_change, 'data': us10y},
            'dxy': {'val': dxy_val, 'change': dxy_change, 'data': dxy},
            'm2': {'val': m2_latest, 'yoy': m2_yoy, 'data': m2},
            'qt': {'status': qt_status, 'data': walcl},
            'dot': dot_latest
        }
    except:
        return {'error': True}

data = get_data(period)

if data.get('error'):
    st.error("데이터 로드 실패. 인터넷 확인 후 다시확인 버튼 눌러주세요.")
else:
    # 대시보드 (이전 그대로)
    col1, col2 = st.columns(2)
    col3, col4 = st.columns(2)

    with col1:
        color = "🟢" if data['us10y']['change'] < 0 else "🔴"
        st.metric(f"{color} 미국 10년물 금리", f"{data['us10y']['val']:.2f}%", f"{data['us10y']['change']:.2f}%")
        st.markdown("**해석**: 상승 = 돈 마름, 겨울 온다 ☃️")
        fig_us10y = px.line(data['us10y']['data'].reset_index(), x='Date', y='Close', title=f"10년물 추세 ({period})")
        st.plotly_chart(fig_us10y)

    with col2:
        st.metric("📍 FOMC 점도표", data['dot'])
        st.markdown("**해석**: 위로 = 긴축 경고!")
        st.image("https://www.federalreserve.gov/monetarypolicy/files/fomcprojtabl20251210.png", caption="최신 점도표")

    with col3:
        color = "🟢" if data['dxy']['change'] < 0 else "🔴"
        st.metric(f"{color} 달러인덱스 (DXY)", f"{data['dxy']['val']:.1f}", f"{data['dxy']['change']:.2f}%")
        st.markdown("**해석**: 강세 = 주식 악재")
        fig_dxy = px.line(data['dxy']['data'].reset_index(), x='Date', y='Close', title=f"DXY 추세 ({period})")
        st.plotly_chart(fig_dxy)

    with col4:
        m2_color = "🟢" if data['m2']['yoy'] >= 0 else "🔴"
        st.metric(f"{m2_color} M2 통화량", f"${data['m2']['val']/1000:.1f}T", f"YoY {data['m2']['yoy']:.1f}%")
        st.metric("QT 상태", data['qt']['status'])
        st.markdown("**해석**: M2↓ or QT = 돈 빨아들임")
        fig_m2 = px.line(data['m2']['data'].reset_index(), x='DATE', y='M2SL', title=f"M2 추세 ({period})")
        st.plotly_chart(fig_m2)
        fig_walcl = px.line(data['qt']['data'].reset_index(), x='DATE', y='WALCL', title=f"Fed 잔고 추세 ({period})")
        st.plotly_chart(fig_walcl)

    # 리포트 요약 (이전 그대로)
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

    # PDF 생성 (업그레이드: 테이블 + 폰트 + 스타일)
    def generate_pdf():
        pdf_filename = "donjul_report.pdf"
        doc = SimpleDocTemplate(pdf_filename, pagesize=letter)
        styles = getSampleStyleSheet()
        styles['Normal'].fontName = 'NotoSansKR'
        styles['Heading1'].fontName = 'NotoSansKR'
        elements = []

        # 헤더
        elements.append(Paragraph("돈줄레이더 리포트", styles['Heading1']))
        elements.append(Paragraph(f"날짜: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))

        # 테이블 데이터
        table_data = [
            ["지표", "현재 값", "변화율", "해석"],
            ["미국 10년물 금리", f"{data['us10y']['val']:.2f}%", f"{data['us10y']['change']:.2f}%", "상승 = 돈 마름"],
            ["달러인덱스 (DXY)", f"{data['dxy']['val']:.1f}", f"{data['dxy']['change']:.2f}%", "강세 = 주식 악재"],
            ["M2 통화량", f"${data['m2']['val']/1000:.1f}T", f"YoY {data['m2']['yoy']:.1f}%", "감소 = 돈 빨아들임"],
            ["QT 상태", data['qt']['status'], "", "QT = 악재"],
            ["FOMC 점도표", data['dot'], "", "위로 = 긴축"],
            ["전체 상태", status, "", advice]
        ]
        table = Table(table_data)
        table_style = TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,-1), 'NotoSansKR'),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('BACKGROUND', (0,1), (-1,-1), colors.beige),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ])
        table.setStyle(table_style)
        elements.append(table)

        doc.build(elements)
        return pdf_filename

    pdf_file = generate_pdf()
    with open(pdf_file, "rb") as f:
        st.download_button("📥 리포트 PDF 다운로드", f, file_name="donjul_report.pdf")

    # 메일 보내기 (이전 그대로)
    st.subheader("📧 리포트 메일 보내기")
    st.info("지인 메일 주소 입력 후 보내기. (당신의 Gmail로 보냄)")
    email_form = st.form(key="email_form")
    recipient = email_form.text_input("지인 메일 주소")
    submit = email_form.form_submit_button("보내기")

    if submit and recipient:
        sender_email = "teo.writer9@gmail.com"  # 변경
        sender_password = "fvimuihnikgikfrc"  # 변경
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient
        msg['Subject'] = "돈줄레이더 리포트"
        body = f"{status}\n{advice}\n자세한 내용 PDF 첨부."
        msg.attach(MIMEText(body, 'plain'))
        with open(pdf_file, "rb") as attachment:
            part = MIMEApplication(attachment.read(), Name="report.pdf")
            part['Content-Disposition'] = 'attachment; filename="report.pdf"'
            msg.attach(part)
        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient, msg.as_string())
            server.quit()
            st.success(f"{recipient}로 메일 보냄!")
        except:
            st.error("메일 보내기 실패. Gmail 설정 확인.")

st.caption("데이터: yfinance + FRED | Made with ❤️ by Grok | Suwon, 2026.02.17")