import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go  
from plotly.subplots import make_subplots
import numpy as np
import time
import requests
from streamlit_autorefresh import st_autorefresh  

# --- 0. 安全金鑰設定 (已修改為 Secrets 讀取) ---
# 在部署時，請在 Streamlit Cloud 後台 Secrets 設定這兩個欄位
try:
    TG_TOKEN = st.secrets["TG_TOKEN"]
    TG_CHAT_ID = st.secrets["TG_CHAT_ID"]
except:
    # 若本機測試時未設定 Secrets，則使用你原本提供的 ID (僅供測試)
    TG_TOKEN = "7608681850:AAGLPRCfK3N3mQ0ZHc4gER_sKQP9vp-fskM"
    TG_CHAT_ID = "7810557847"

# --- 1. 頁面基礎設定 ---
st.set_page_config(layout="wide", page_title="詹VICTOR帥 | AI 戰略終極版")

# 每 60 秒自動刷新頁面一次
st_autorefresh(interval=60 * 1000, key="data_refresh")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background: #ffffff; border: 1px solid #dee2e6; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stTabs [aria-selected="true"] { color: #007bff !important; font-weight: bold; border-bottom: 2px solid #007bff; }
    .summary-card { background-color: #ffffff; padding: 20px; border-radius: 15px; border-left: 8px solid #007bff; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px; }
    .info-label { color: #6c757d; font-size: 0.9rem; margin-bottom: 5px; }
    .diag-text { font-size: 1rem; line-height: 1.6; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ 詹VICTOR帥 | AI 戰術監控儀表板")

# --- 2. 初始化 Session State ---
if 'scan_results' not in st.session_state: st.session_state.scan_results = []
if 'last_scan_idx' not in st.session_state: st.session_state.last_scan_idx = 0
if 'is_scanning' not in st.session_state: st.session_state.is_scanning = False
if 'f_t' not in st.session_state: st.session_state.f_t = 0.0
if 'f_s' not in st.session_state: st.session_state.f_s = -100.0
if 'f_w' not in st.session_state: st.session_state.f_w = 0

# --- 3. 工具函數 ---
def send_telegram_msg(message):
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload = {"chat_id": TG_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        res = requests.post(url, json=payload, timeout=5)
        return res.status_code == 200
    except: return False

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

# --- 4. 側邊欄設定 ---
st.sidebar.header("🕹️ 戰略核心設定")
stock_id = st.sidebar.text_input("輸入個股代號", value="2330")
display_days = st.sidebar.slider("觀察窗口 (天)", 60, 500, 200)
bins_val = st.sidebar.slider("籌碼掃描精度", 50, 200, 120)

# (掃描清單保持不變，此處略過中間清單內容以節省長度，但部署時請確保你的原始清單都在)
scan_list = ["1101", "1102", "1103", "1104", "1108", "1109", "1110", "1201", "2330", "2609", "6147", "6155", "9945", "9958"] # ...以此類推

# --- 5. 主內容執行 ---
raw_df, actual_ticker = load_stock_data_safe(stock_id)

if raw_df is not None:
    df_d = raw_df.copy()
    df_d.ta.sma(length=5, append=True); df_d.ta.sma(length=20, append=True)
    df_d.ta.rsi(length=14, append=True); df_d.ta.macd(append=True); df_d.ta.obv(append=True)
    df_d.ta.mfi(length=14, append=True); df_d.ta.atr(length=14, append=True)
    df_d['Net_Flow'] = (df_d['Close'].diff() * df_d['Volume'])
    
    df = df_d.tail(display_days).copy()
    curr = df.iloc[-1]
    price_now = float(curr['Close'])
    poc_price, p_buckets, v_hist = get_poc_data(df, bins_val)

    st.markdown('<div class="summary-card">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([0.4, 0.4, 0.2])
    with c1:
        st.subheader(f"🤖 詹帥 AI 戰略監控：{actual_ticker}")
        st.write(f"現價 **{price_now:.2f}** | POC 重心位 **{poc_price:.2f}**")
    with c2:
        st.write(f"📊 資金動能：**{'🔴 主力吸籌' if curr['Net_Flow'] > 0 else '🟢 主力派發'}**")
        st.write(f"📈 趨勢防線：**{'🔥 多頭控盤' if price_now > curr['SMA_20'] else '❄️ 空頭盤整'}**")
    with c3:
        score = sum([30 if price_now > curr['SMA_20'] else 0, 20 if curr['RSI_14'] > 50 else 0, 50 if price_now > poc_price else 0])
        st.metric("戰力評分", f"{score}")
    st.markdown('</div>', unsafe_allow_html=True)

    tab_tech, tab_chip, tab_radar, tab_scan = st.tabs(["📈 技術看板", "📊 籌碼深度分析", "💠 多空雷達診斷", "🚀 選股雷達"])

    with tab_tech:
        fig = make_subplots(rows=6, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=[0.3, 0.12, 0.12, 0.12, 0.12, 0.12])
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], name="20MA", line=dict(color='orange')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI_14'], name="RSI", line=dict(color='#9467bd')), row=2, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df['MACDh_12_26_9'], name="MACD柱"), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MFI_14'], name="MFI", fill='tozeroy'), row=4, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['OBV'], name="OBV"), row=5, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df['Net_Flow'], name="資金流", marker_color=np.where(df['Net_Flow']>=0, '#d62728', '#2ca02c')), row=6, col=1)
        fig.update_layout(template="plotly_white", height=900, xaxis_rangeslider_visible=False, hovermode='x unified')
        st.plotly_chart(fig, use_container_width=True)

    with tab_chip:
        col_c1, col_c2 = st.columns([0.6, 0.4])
        with col_c1:
            fig_vp = go.Figure(go.Bar(y=(p_buckets[:-1] + p_buckets[1:]) / 2, x=v_hist, orientation='h', opacity=0.7, name="成交分布"))
            fig_vp.add_hline(y=price_now, line_color="red", annotation_text="現價", line_width=2)
            fig_vp.add_hline(y=poc_price, line_dash="dash", annotation_text="POC重心", line_color="blue")
            fig_vp.update_layout(title="Volume Profile 籌碼成本分佈", xaxis_title="成交量")
            st.plotly_chart(fig_vp, use_container_width=True)
        with col_c2:
            st.subheader("💡 籌碼戰略報告")
            with st.container(border=True):
                dist_to_poc = ((price_now - poc_price) / poc_price) * 100
                st.markdown(f"📍 **重心位分析：**\n目前股價距離 POC 重心約 **{dist_to_poc:.1f}%**。")
                if price_now > poc_price: st.success(f"✅ **多方佔優**：股價位於支撐區之上。")
                else: st.warning(f"⚠️ **空方佔優**：股價位於壓力區之下。")
                st.markdown(f"🔥 **資金活躍度 (MFI)：** {curr['MFI_14']:.1f}")
                obv_change = curr['OBV'] - df['OBV'].iloc[-5]
                st.markdown(f"📊 **能量趨勢 (OBV)：** {'✅ 價量齊揚' if obv_change > 0 else '❌ 能量背離'}")

    with tab_radar:
        col_r1, col_r2 = st.columns([0.5, 0.5])
        with col_r1:
            radar_vals = [100 if price_now > curr['SMA_20'] else 20, curr['RSI_14'], curr['MFI_14'], 100 if curr['MACDh_12_26_9'] > 0 else 20, 100 if curr['OBV'] > df['OBV'].shift(5).iloc[-1] else 30, 100 if curr['Net_Flow'] > 0 else 30]
            fig_radar = go.Figure(go.Scatterpolar(r=radar_vals, theta=['20MA防守', 'RSI動能', 'MFI熱錢', 'MACD方向', 'OBV能量', '資金流向'], fill='toself'))
            fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=False, title="核心戰力六角圖")
            st.plotly_chart(fig_radar, use_container_width=True)
        with col_r2:
            st.subheader("📝 詹帥 AI 綜合診斷")
            with st.container(border=True):
                st.write(f"📈 **趨勢診斷**：{'目前處於極強勢進攻格局' if price_now > curr['SMA_20'] and curr['MACDh_12_26_9'] > 0 else '趨勢偏多但動能稍減' if price_now > curr['SMA_20'] else '目前趨勢走弱'}")
                st.write(f"💪 **動能強度**：RSI 目前為 **{curr['RSI_14']:.1f}**。")
                st.markdown("---")
                if score >= 80: st.success("🎯 **【戰略特優】** 指標全面翻多。")
                elif score >= 50: st.info("秤⚖️ **【戰略中立】** 具備一定支撐。")
                else: st.error("📉 **【戰略保守】** 多項技術指標轉弱。")

    with tab_scan:
        st.subheader("🚀 詹帥 AI 自動選股雷達")
        c_sc1, c_sc2 = st.columns([0.8, 0.2])
        with c_sc1: lookback_val = st.slider("洗盤天數設定", 1, 180, 5)
        with c_sc2: 
            if st.button("🔴 啟動全掃描", use_container_width=True):
                st.session_state.scan_results, st.session_state.last_scan_idx = [], 0
                st.session_state.is_scanning = True
                st.rerun()

        if st.session_state.is_scanning:
            total = len(scan_list)
            idx = st.session_state.last_scan_idx
            batch_size = 15
            end_idx = min(idx + batch_size, total)
            st.progress(idx / total)
            for i in range(idx, end_idx):
                sid = scan_list[i]
                sdf, _ = load_stock_data_safe(sid)
                if sdf is not None and len(sdf) > 30:
                    sdf['Net_Flow'] = (sdf['Close'].diff() * sdf['Volume'])
                    vol_t = sdf['Volume'].iloc[-1]
                    s_val = (sdf['Net_Flow'].iloc[-1] / vol_t * 100) if vol_t != 0 else 0
                    avg_s_20 = (sdf['Net_Flow'] / sdf['Volume'] * 100).abs().tail(21).iloc[:-1].mean()
                    t_val = (abs(s_val) / avg_s_20) if avg_s_20 != 0 else 0
                    if sdf['Net_Flow'].iloc[-1] > 0:
                        count_w = 0
                        for v in reversed(sdf['Net_Flow'].iloc[:-1].values):
                            if v <= 0: count_w += 1
                            else: break
                        if count_w >= lookback_val:
                            flow_mini = sdf['Net_Flow'].tail(60).tolist()
                            st.session_state.scan_results.append({
                                "代號": sid, "現價": round(float(sdf['Close'].iloc[-1]), 2),
                                "今日流向": int(sdf['Net_Flow'].iloc[-1]), "資金流趨勢 (60D)": flow_mini,
                                "強度(S)": round(s_val), "強度比(T)": round(t_val, 2), "洗盤天數": int(count_w)
                            })
                st.session_state.last_scan_idx = i + 1
            if st.session_state.last_scan_idx >= total:
                st.session_state.is_scanning = False
                st.rerun()
            else: time.sleep(0.1); st.rerun()

        if st.session_state.scan_results:
            st.write("---")
            f1, f2, f3, f4 = st.columns([0.2, 0.2, 0.2, 0.4])
            with f1: t_f = st.number_input("強度比(T) ≧", value=float(st.session_state.f_t))
            with f2: s_f = st.number_input("強度(S) ≧", value=float(st.session_state.f_s))
            with f3: w_f = st.number_input("洗盤天數 ≧", value=int(st.session_state.f_w))
            st.session_state.f_t, st.session_state.f_s, st.session_state.f_w = t_f, s_f, w_f
            
            res_df = pd.DataFrame(st.session_state.scan_results).drop_duplicates(subset=['代號'])
            f_df = res_df[(res_df['強度比(T)'] >= t_f) & (res_df['強度(S)'] >= s_f) & (res_df['洗盤天數'] >= w_f)]
            
            with f4:
                st.write(" ")
                if st.button("📢 推播至 Telegram", use_container_width=True):
                    if not f_df.empty:
                        msg = f"🔥 *詹VICTOR帥 大戶進場通知* 🚩\n"
                        for _, row in f_df.iterrows(): msg += f"🔹 {row['代號']} | 現價:{row['現價']} | 力道:{row['強度比(T)']}\n"
                        send_telegram_msg(msg)
                        st.success("✅ 推播成功！")

            st.dataframe(
                f_df, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "資金流趨勢 (60D)": st.column_config.BarChartColumn("資金流趨勢 (60D)", y_min=res_df["資金流趨勢 (60D)"].apply(min).min(), y_max=res_df["資金流趨勢 (60D)"].apply(max).max())
                }
            )

else:
    st.error("❌ 無法讀取數據，請檢查個股代號是否正確。")