import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go  
from plotly.subplots import make_subplots
import numpy as np
from streamlit_autorefresh import st_autorefresh  

# --- 1. 頁面基礎設定 ---
st.set_page_config(layout="wide", page_title="詹VICTOR帥 | AI 戰略終極版")
st_autorefresh(interval=60 * 1000, key="data_refresh")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background: #ffffff; border: 1px solid #dee2e6; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stTabs [aria-selected="true"] { color: #007bff !important; font-weight: bold; border-bottom: 2px solid #007bff; }
    .summary-card { background-color: #ffffff; padding: 20px; border-radius: 15px; border-left: 8px solid #007bff; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px; }
    .indicator-box { background: #f0f2f6; padding: 15px; border-radius: 8px; margin-bottom: 12px; border-left: 5px solid #007bff; line-height: 1.6; }
    .diag-section-title { font-weight: bold; color: #1f77b4; margin-top: 15px; margin-bottom: 10px; border-bottom: 1px solid #eee; padding-bottom: 5px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ 詹VICTOR帥 | AI 戰情室")

# --- 2. 數據下載函數 ---
@st.cache_data(ttl=300)
def load_stock_data_safe(sid):
    for suffix in [".TW", ".TWO"]:
        try:
            full_sid = f"{sid}{suffix}"
            df = yf.download(full_sid, period="2y", interval="1d", auto_adjust=False, progress=False, timeout=5)
            if not df.empty and len(df) > 10:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                return df, full_sid
        except: continue
    return None, None

def get_poc_data(df_slice, bins):
    p_min, p_max = df_slice['Low'].min(), df_slice['High'].max()
    p_buckets = np.linspace(p_min, p_max, bins)
    v_hist, _ = np.histogram(df_slice['Close'], bins=p_buckets, weights=df_slice['Volume'])
    poc = (p_buckets[np.argmax(v_hist)] + p_buckets[np.argmax(v_hist)+1]) / 2
    return poc, p_buckets, v_hist

# --- 3. 側邊欄設定 ---
st.sidebar.header("🕹️ 戰略核心設定")
stock_id = st.sidebar.text_input("輸入個股代號", value="2330")
display_days = st.sidebar.slider("觀察窗口 (天)", 60, 500, 200)
bins_val = st.sidebar.slider("籌碼掃描精度", 50, 200, 120)

raw_df, actual_ticker = load_stock_data_safe(stock_id)

if raw_df is not None:
    df_d = raw_df.copy()
    # 技術指標計算
    df_d.ta.sma(length=20, append=True)
    df_d.ta.rsi(length=14, append=True)
    df_d.ta.macd(append=True)
    df_d.ta.obv(append=True)
    df_d.ta.mfi(length=14, append=True)
    df_d['Net_Flow'] = (df_d['Close'].diff() * df_d['Volume'])
    
    df = df_d.tail(display_days).copy()
    curr = df.iloc[-1]
    price_now = float(curr['Close'])
    poc_price, p_buckets, v_hist = get_poc_data(df, bins_val)

    # 頂部戰力摘要
    st.markdown('<div class="summary-card">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([0.4, 0.4, 0.2])
    with c1:
        st.subheader(f"詹帥 AI 戰略監控：{actual_ticker}")
        st.write(f"現價 **{price_now:.2f}** | 重心位 **{poc_price:.2f}**")
    with c2:
        st.write(f"資金流向：**{'🔴 主力吸籌' if curr['Net_Flow'] > 0 else '🟢 主力派發'}**")
        st.write(f"防線：**{'🔥 多頭控盤' if price_now > curr['SMA_20'] else '❄️ 空頭盤整'}**")
    with c3:
        score = sum([30 if price_now > curr['SMA_20'] else 0, 20 if curr['RSI_14'] > 50 else 0, 50 if price_now > poc_price else 0])
        st.metric("戰力評分", f"{score}")
    st.markdown('</div>', unsafe_allow_html=True)

    tab_tech, tab_chip, tab_radar = st.tabs(["技術看板", "籌碼深度分析", "多空雷達診斷"])

    with tab_tech:
        # 6層子圖配置
        fig = make_subplots(rows=6, cols=1, shared_xaxes=True, vertical_spacing=0.015, 
                           row_heights=[0.35, 0.13, 0.13, 0.13, 0.13, 0.13])
        
        # 指標繪製
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], name="20MA", line=dict(color='orange', width=1.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI_14'], name="RSI", line=dict(color='#9467bd')), row=2, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df['MACDh_12_26_9'], name="MACD柱"), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MFI_14'], name="MFI", fill='tozeroy', line=dict(color='#17becf')), row=4, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['OBV'], name="OBV", line=dict(color='blue')), row=5, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df['Net_Flow'], name="資金流", marker_color=np.where(df['Net_Flow']>=0, '#d62728', '#2ca02c')), row=6, col=1)

        # 【核心優化】：日期數字化 + 全方位連動十字線
        for i in range(1, 7):
            fig.update_xaxes(
                tickformat="%Y-%m-%d", # 日期改為數字格式
                showspikes=True, 
                spikemode="across", 
                spikedash="dash", 
                spikecolor="#666666", 
                spikethickness=1,
                row=i, col=1
            )
            fig.update_yaxes(
                showspikes=True, 
                spikemode="toaxis", 
                spikedash="dash", 
                spikecolor="#666666", 
                row=i, col=1
            )
        
        fig.update_layout(
            template="plotly_white", 
            height=1100, 
            xaxis_rangeslider_visible=False, 
            hovermode='x unified', 
            hoverlabel=dict(bgcolor="rgba(255,255,255,0.9)", font_size=12),
            showlegend=False,
            margin=dict(l=50, r=50, t=30, b=30)
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab_chip:
        col_c1, col_c2 = st.columns([0.6, 0.4])
        with col_c1:
            fig_vp = go.Figure(go.Bar(y=(p_buckets[:-1] + p_buckets[1:]) / 2, x=v_hist, orientation='h', opacity=0.7))
            fig_vp.add_hline(y=price_now, line_color="red", annotation_text="現價", line_width=2)
            fig_vp.add_hline(y=poc_price, line_dash="dash", annotation_text="POC重心", line_color="blue")
            fig_vp.update_layout(title="Volume Profile 籌碼分佈", xaxis_title="成交量", height=600, template="plotly_white")
            st.plotly_chart(fig_vp, use_container_width=True)
        with col_c2:
            st.subheader("💡 籌碼深度報告")
            with st.container(border=True):
                dist_to_poc = ((price_now - poc_price) / poc_price) * 100
                st.markdown(f"📍 **重心分析：** 距離 POC **{dist_to_poc:.1f}%**")
                if price_now > poc_price: st.success("✅ 目前股價獲得籌碼支撐")
                else: st.warning("⚠️ 股價承受上方成本壓力")
                st.write(f"🔥 **MFI 現值：** {curr['MFI_14']:.1f}")

    with tab_radar:
        col_r1, col_r2 = st.columns([0.5, 0.5])
        with col_r1:
            radar_vals = [100 if price_now > curr['SMA_20'] else 20, curr['RSI_14'], curr['MFI_14'], 100 if curr['MACDh_12_26_9'] > 0 else 20, 100 if curr['OBV'] > df['OBV'].shift(5).iloc[-1] else 30, 100 if curr['Net_Flow'] > 0 else 30]
            fig_radar = go.Figure(go.Scatterpolar(r=radar_vals, theta=['20MA防守', 'RSI動能', 'MFI熱錢', 'MACD方向', 'OBV能量', '資金流向'], fill='toself'))
            fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=500, template="plotly_white")
            st.plotly_chart(fig_radar, use_container_width=True)
            
        with col_r2:
            st.subheader("📝 詹帥 AI 完整診斷（不縮減版）")
            with st.container(border=True):
                # 週期位階
                st.markdown('<p class="diag-section-title">📅 週期趨勢定位</p>', unsafe_allow_html=True)
                d_trend = "🔥 多頭" if price_now > curr['SMA_20'] else "❄️ 空頭"
                w_trend = "📈 強勢" if price_now > df_d['Close'].rolling(5).mean().iloc[-1] else "📉 轉弱"
                m_trend = "🧱 穩健" if price_now > df_d['Close'].rolling(20).mean().iloc[-1] else "⚠️ 警戒"
                st.write(f"日線：**{d_trend}** | 週線：**{w_trend}** | 月線：**{m_trend}**")
                
                # RSI 深度提示
                st.markdown('<p class="diag-section-title">🔍 技術動能深度解析</p>', unsafe_allow_html=True)
                rsi_v = curr['RSI_14']
                rsi_msg = "超買過熱，防備高檔獲利了結" if rsi_v > 70 else "多方掌控，具備推升動能" if rsi_v > 50 else "弱勢整理，反彈壓力大" if rsi_v > 30 else "嚴重超跌，尋找止跌訊號"
                st.markdown(f"<div class='indicator-box'><b>RSI 強度偵測 ({rsi_v:.1f})</b><br>戰略建議：{rsi_msg}</div>", unsafe_allow_html=True)
                
                # MACD 深度提示
                macd_h = curr['MACDh_12_26_9']
                m_prev = df['MACDh_12_26_9'].iloc[-2]
                macd_msg = "紅柱放大：多頭攻擊波段啟動" if macd_h > 0 and macd_h > m_prev else "綠柱縮減：跌勢初步止穩" if macd_h < 0 and macd_h > m_prev else "紅柱縮減：多頭動能耗盡，防回檔"
                st.markdown(f"<div class='indicator-box'><b>MACD 柱狀震盪 ({macd_h:.2f})</b><br>動態解讀：{macd_msg}</div>", unsafe_allow_html=True)
                
                # 資金流深度提示
                mfi_v = curr['MFI_14']
                obv_change = curr['OBV'] - df['OBV'].iloc[-5]
                st.markdown(f"<div class='indicator-box'><b>資金熱度 (MFI) 與能量 (OBV)</b><br>目前 MFI 為 {mfi_v:.1f}。OBV 表現：{'✅ 量價配合，波段有望延續' if obv_change > 0 else '❌ 價漲量不漲，留意虛紅'}。</div>", unsafe_allow_html=True)

                st.markdown('<p class="diag-section-title">📊 資金流量柱即時短評</p>', unsafe_allow_html=True)
                if curr['Net_Flow'] > 0: 
                    st.info("🔥 主力資金「淨流入」：市場買盤意願積極，多方勝出。")
                else: 
                    st.warning("⚠️ 主力資金「淨流出」：出現主動拋售賣壓，宜謹慎操作。")

                st.markdown("---")
                st.markdown("#### 🚩 詹帥戰略總結")
                if score >= 80: st.success("🎯 **【戰略特優】** 多項指標共振，具備強大攻擊能量。")
                elif score >= 50: st.info("⚖️ **【戰略中立】** 位階尚可，適合採取低吸戰術。")
                else: st.error("📉 **【戰略保守】** 破線且重心下移，建議保留現金。")

else:
    st.error("❌ 無法載入數據，請檢查代號。")
