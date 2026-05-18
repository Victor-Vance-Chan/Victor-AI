import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go  
from plotly.subplots import make_subplots
import numpy as np
import time
import requests
import re
from streamlit_autorefresh import st_autorefresh  

# --- 0. Telegram 預設設定 ---
TG_TOKEN = "7608681850:AAGLPRCfK3N3mQ0ZHc4gER_sKQP9vp-fskM"
TG_CHAT_ID = "7810557847"

# --- 1. 頁面基礎設定 ---
st.set_page_config(layout="wide", page_title="詹VICTOR帥 | AI 戰略終極版")

st_autorefresh(interval=60 * 1000, key="data_refresh")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background: #ffffff; border: 1px solid #dee2e6; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stTabs [aria-selected="true"] { color: #007bff !important; font-weight: bold; border-bottom: 2px solid #007bff; }
    .summary-card { background-color: #ffffff; padding: 20px; border-radius: 15px; border-left: 8px solid #007bff; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px; }
    /* 側邊欄列表樣式 */
    .sb-item { display: flex; align-items: center; justify-content: space-between; margin-bottom: 5px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ 詹VICTOR帥 | AI 戰術戰情室")

# --- 2. 初始化 Session State ---
if 'scan_results' not in st.session_state: st.session_state.scan_results = []
if 'last_scan_idx' not in st.session_state: st.session_state.last_scan_idx = 0
if 'is_scanning' not in st.session_state: st.session_state.is_scanning = False
if 'watch_list' not in st.session_state: st.session_state.watch_list = ["2330", "2317"]
if 'target_sid' not in st.session_state: st.session_state.target_sid = "2330"

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
            ticker_obj = yf.Ticker(full_sid)
            df = ticker_obj.history(period="2y", interval="1d", auto_adjust=False)
            if not df.empty and len(df) > 30:
                info = ticker_obj.info
                shares = info.get('sharesOutstanding', 0)
                cap_billions = round((shares * 10) / 10**8, 2) if shares else 0
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                return df, full_sid, cap_billions
        except: continue
    return None, None, 0

def get_poc_data(df_slice, bins):
    p_min, p_max = df_slice['Low'].min(), df_slice['High'].max()
    p_buckets = np.linspace(p_min, p_max, bins)
    v_hist, _ = np.histogram(df_slice['Close'], bins=p_buckets, weights=df_slice['Volume'])
    poc = (p_buckets[np.argmax(v_hist)] + p_buckets[np.argmax(v_hist)+1]) / 2
    return poc, p_buckets, v_hist

# --- 4. 側邊欄設定 ---
st.sidebar.header("🕹️ 戰略核心設定")
manual_id = st.sidebar.text_input("搜尋個股代號", value=st.session_state.target_sid)
if manual_id != st.session_state.target_sid:
    st.session_state.target_sid = manual_id

st.sidebar.markdown("---")
st.sidebar.subheader("🎯 核心監控清單")

if st.sidebar.button("🚀 詹帥精選推播至 TG", use_container_width=True, type="primary"):
    if st.session_state.watch_list:
        with st.sidebar:
            with st.spinner("正在匯整戰報..."):
                msg = f"🔥 *詹VICTOR帥 核心監控報告* 🚩\n━━━━━━━━━━━━━━━\n"
                for sid in st.session_state.watch_list:
                    sdf, _, _ = load_stock_data_safe(sid)
                    if sdf is not None:
                        price = round(float(sdf['Close'].iloc[-1]), 2)
                        sdf['Net_Flow'] = (sdf['Close'].diff() * sdf['Volume']).fillna(0)
                        s_val = (sdf['Net_Flow'].iloc[-1] / sdf['Volume'].iloc[-1] * 100) if sdf['Volume'].iloc[-1] != 0 else 0
                        avg_s_20 = (sdf['Net_Flow'] / sdf['Volume'] * 100).abs().tail(21).iloc[:-1].mean()
                        t_val = round(abs(s_val) / avg_s_20, 2) if avg_s_20 != 0 else 0
                        msg += f"`{sid}`  現價:`{price}` 強度比:`{t_val}`\n"
                if send_telegram_msg(msg): st.success("✅ 推播成功！")
                else: st.error("❌ 推播失敗")
    else: st.sidebar.warning("清單是空的喔！")

for sid in st.session_state.watch_list:
    col_sid, col_del = st.sidebar.columns([0.75, 0.25])
    if col_sid.button(f"📊 {sid}", key=f"view_{sid}", use_container_width=True):
        st.session_state.target_sid = sid
        st.rerun()
    if col_del.button("❌", key=f"del_{sid}", use_container_width=True):
        st.session_state.watch_list.remove(sid)
        st.rerun()

if st.sidebar.button("🗑️ 全部清空"):
    st.session_state.watch_list = []
    st.rerun()

st.sidebar.markdown("---")
display_days = st.sidebar.slider("觀察窗口 (天)", 60, 500, 200)
bins_val = st.sidebar.slider("籌碼掃描精度", 50, 200, 120)

scan_list = [
    "1101", "1102", "1103", "1104", "1108", "1109", "1110", "1201", "1203", "1210", 
    "1213", "1215", "9802", "9902", "9904", "9905", "9906", "9907", "9908", "9910", 
    "9911", "9912", "9914", "9917", "9918", "9919", "9921", "9924", "9925", "9926", 
    "9927", "9928", "9929", "9930", "9931", "9933", "9934", "9935", "9937", "9938", 
    "9939", "9940", "9941", "9942", "9943", "9944", "9945", "9946", "9955", "9958"
]

# --- 5. 主內容執行 ---
raw_df, actual_ticker, current_cap = load_stock_data_safe(st.session_state.target_sid)

if raw_df is not None:
    df_d = raw_df.copy()
    df_d.ta.sma(length=5, append=True)
    df_d.ta.sma(length=20, append=True)
    df_d.ta.rsi(length=14, append=True)
    df_d.ta.macd(append=True)
    df_d.ta.obv(append=True)
    df_d.ta.mfi(length=14, append=True)
    df_d.ta.bbands(length=20, std=2, append=True) 
    
    df_d['Net_Flow'] = (df_d['Close'].diff() * df_d['Volume']).fillna(0)
    df_d['Bias_20'] = ((df_d['Close'] - df_d['SMA_20']) / df_d['SMA_20']) * 100
    df_d['Ref_20'] = df_d['Close'].shift(20)
    
    df = df_d.tail(display_days).copy()
    curr = df.iloc[-1]
    price_now = float(curr['Close'])
    poc_price, p_buckets, v_hist = get_poc_data(df, bins_val)

    st.markdown('<div class="summary-card">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([0.4, 0.4, 0.2])
    with c1:
        st.subheader(f"🤖 詹帥 AI 戰術監控：{actual_ticker}")
        st.write(f"現價 **{price_now:.2f}** | 股本 **{current_cap} 億** | POC 重心位 **{poc_price:.2f}**")
    with c2:
        st.write(f"📊 資金動能：**{'🔴 主力吸籌' if curr['Net_Flow'] > 0 else '🟢 主力派發'}**")
        st.write(f"📈 趨勢防線：**{'🔥 多頭控盤' if price_now > curr['SMA_20'] else '❄️ 空頭盤整'}**")
    with c3:
        score = sum([30 if price_now > curr['SMA_20'] else 0, 20 if curr['RSI_14'] > 50 else 0, 50 if price_now > poc_price else 0])
        st.metric("戰力評分", f"{score}")
    st.markdown('</div>', unsafe_allow_html=True)

    tab_tech, tab_chip, tab_radar, tab_scan, tab_import = st.tabs(["📈 技術看板", "📊 籌碼深度分析", "💠 多空雷達診斷", "🚀 選股雷達", "📥 批量匯入"])

    with tab_tech:
        fig = make_subplots(rows=6, cols=1, shared_xaxes=True, vertical_spacing=0.02, 
                            row_heights=[0.35, 0.13, 0.13, 0.13, 0.13, 0.13])
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], name="20MA", line=dict(color='orange', width=2)), row=1, col=1)
        
        if 'BBU_20_2.0' in df.columns and 'BBL_20_2.0' in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df['BBU_20_2.0'], name="布林上軌", line=dict(color='rgba(128, 128, 128, 0.5)', width=1.5, dash='dash')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['BBL_20_2.0'], name="布林下軌", line=dict(color='rgba(128, 128, 128, 0.5)', width=1.5, dash='dash')), row=1, col=1)
        
        if len(df) >= 20:
            target_date = df.index[-20]
            target_val = df['Close'].iloc[-20]
            fig.add_trace(go.Scatter(
                x=[target_date], y=[target_val],
                mode="markers+text",
                text=["🎯20MA扣抵點"],
                textposition="top center",
                marker=dict(color="purple", size=14, symbol="star", line=dict(width=2, color="white")),
                name="當日扣抵記號"
            ), row=1, col=1)

        colors = ['#d62728' if val >= 0 else '#2ca02c' for val in df['Net_Flow']]
        fig.add_trace(go.Bar(x=df.index, y=df['Net_Flow'], name="資金流向", marker_color=colors), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI_14'], name="RSI", line=dict(color='#9467bd')), row=3, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df['MACDh_12_26_9'], name="MACD柱"), row=4, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MFI_14'], name="MFI", fill='tozeroy', line=dict(color='#17becf')), row=5, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['OBV'], name="OBV", line=dict(color='#7f7f7f')), row=6, col=1)
        fig.update_layout(template="plotly_white", height=1000, xaxis_rangeslider_visible=False, hovermode='x unified')
        st.plotly_chart(fig, use_container_width=True)

    with tab_chip:
        col_c1, col_c2 = st.columns([0.6, 0.4])
        with col_c1:
            fig_vp = go.Figure(go.Bar(y=(p_buckets[:-1] + p_buckets[1:]) / 2, x=v_hist, orientation='h', opacity=0.7, name="成交分布", marker_color="#aec7e8"))
            fig_vp.add_hline(y=price_now, line_color="red", annotation_text="現價", line_width=2)
            fig_vp.add_hline(y=poc_price, line_dash="dash", annotation_text="POC重心", line_color="blue")
            fig_vp.update_layout(title="Volume Profile 籌碼成本分佈", xaxis_title="成交量", template="plotly_white")
            st.plotly_chart(fig_vp, use_container_width=True)
        with col_c2:
            st.subheader("💡 籌碼戰略報告")
            with st.container(border=True):
                dist_to_poc = ((price_now - poc_price) / poc_price) * 100
                st.markdown(f"📍 **重心位分析：**\n目前股價距離 POC 重心約 **{dist_to_poc:.1f}%**。")
                if price_now > poc_price: st.success("✅ **多方佔優**：股價位於支撐區之上。")
                else: st.warning("⚠️ **空方佔優**：股價位於壓力區之下。")
                st.write(f"🔥 **資金活躍度 (MFI)：** {curr['MFI_14']:.1f}")
                obv_change = curr['OBV'] - df['OBV'].iloc[-5]
                st.write(f"📊 **能量趨勢 (OBV)：** {'✅ 價量齊揚' if obv_change > 0 else '❌ 能量背離'}")

    with tab_radar:
        col_r1, col_r2 = st.columns([0.5, 0.5])
        with col_r1:
            radar_vals = [100 if price_now > curr['SMA_20'] else 20, curr['RSI_14'], curr['MFI_14'], 100 if curr['MACDh_12_26_9'] > 0 else 20, 100 if curr['OBV'] > df['OBV'].shift(5).iloc[-1] else 30, 100 if curr['Net_Flow'] > 0 else 30]
            fig_radar = go.Figure(go.Scatterpolar(r=radar_vals, theta=['20MA防守', 'RSI動能', 'MFI熱錢', 'MACD方向', 'OBV能量', '資金流向'], fill='toself', fillcolor='rgba(31, 119, 180, 0.5)'))
            fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=False, title="核心戰術六角圖")
            st.plotly_chart(fig_radar, use_container_width=True)
        with col_r2:
            st.subheader("📝 詹帥 AI 全方位戰術診斷")
            with st.container(border=True):
                st.write(f"📉 **20日乖離率 ({curr['Bias_20']:.2f}%)**")
                st.write(f"⚡ **RSI 動能 ({curr['RSI_14']:.1f})**")
                st.write(f"🚥 **MACD 趨勢 ({curr['MACDh_12_26_9']:.2f})**")
                st.write(f"💰 **資金流 (Net Flow: {int(curr['Net_Flow'])})**")
                st.markdown("---")
                if score >= 80: st.success("🎯 **【戰略特優】** 指標全面翻多。")
                elif score >= 50: st.info("⚖️ **【戰略中立】** 關鍵防線尚在。")
                else: st.error("📉 **【戰略保守】** 指標結構鬆動。")
            
            st.subheader("🔮 20MA 扣抵深度預測")
            with st.container(border=True):
                ref_20_val = curr['Ref_20']
                diff_pct = ((price_now - ref_20_val) / ref_20_val) * 100
                future_ref = df_d['Close'].iloc[-20:-15].mean() if len(df_d) >= 20 else ref_20_val
                
                st.write(f"📌 **當日扣抵值：** {ref_20_val:.2f} (與現價差：{diff_pct:+.2f}%)")
                
                if price_now > ref_20_val:
                    if future_ref < ref_20_val:
                        analysis_text = "現價成功壓制扣抵，且未來扣抵持續下沉！20MA上升動能深度極強，此處回踩將化為極佳暴風加碼點。"
                        st.success(analysis_text)
                    else:
                        analysis_text = "目前佔據扣低優勢，惟未來扣抵緩步攀升。短期多頭慣性仍在，預期走勢維持震盪盤堅，不宜過度追高。"
                        st.info(analysis_text)
                else:
                    if future_ref > ref_20_val:
                        analysis_text = "現價落入扣高危機，未來扣抵陡峭夾擊。均線下彎地心引力沉重，走勢恐加速探底，切勿盲目進場接刀。"
                        st.error(analysis_text)
                    else:
                        analysis_text = "雖現價低於扣抵，但未來扣抵即將扣低。均線下彎引力降溫，暗示走勢跌勢收斂，靜待止穩共振訊號。"
                        st.warning(analysis_text)

    with tab_scan:
        st.subheader("🚀 詹帥 AI 自動選股雷達")
        sc_col1, sc_col2 = st.columns([0.8, 0.2])
        with sc_col1: lookback_val = st.slider("洗盤天數設定", 1, 180, 5)
        with sc_col2: 
            if st.button("🔴 啟動全掃描", use_container_width=True):
                st.session_state.scan_results, st.session_state.last_scan_idx = [], 0
                st.session_state.is_scanning = True
                st.rerun()

        if st.session_state.is_scanning:
            total = len(scan_list); idx = st.session_state.last_scan_idx; batch_size = 15; end_idx = min(idx + batch_size, total)
            st.progress(idx / total); st.write(f"⏳ 掃描進度：{idx} / {total} ...")
            for i in range(idx, end_idx):
                sid = scan_list[i]
                sdf, _, scap = load_stock_data_safe(sid)
                if sdf is not None and len(sdf) > 60:
                    sdf.ta.sma(length=20, append=True)
                    sdf.ta.rsi(length=14, append=True)
                    sdf['Bias_20'] = ((sdf['Close'] - sdf['SMA_20']) / sdf['SMA_20']) * 100
                    sdf['Net_Flow'] = (sdf['Close'].diff() * sdf['Volume']).fillna(0)
                    vol_t = sdf['Volume'].iloc[-1]
                    s_val = (sdf['Net_Flow'].iloc[-1] / vol_t * 100) if vol_t != 0 else 0
                    avg_s_20 = (sdf['Net_Flow'] / sdf['Volume'] * 100).abs().tail(21).iloc[:-1].mean()
                    t_val = (abs(s_val) / avg_s_20) if avg_s_20 != 0 else 0
                    
                    sdf_slice = sdf.tail(display_days)
                    spoc, _, _ = get_poc_data(sdf_slice, bins_val)
                    s_close = float(sdf['Close'].iloc[-1])
                    poc_bias = ((s_close - spoc) / spoc) * 100
                    
                    if poc_bias >= 0 and poc_bias <= 3.0 and t_val >= 1.2:
                        status_tag = "⚡ 剛衝鋒"
                    elif abs(poc_bias) <= 1.0 and t_val < 1.2:
                        status_tag = "🛡️ 守成本"
                    elif poc_bias > 3.0:
                        status_tag = "🚀 鷹擊長空"
                    else:
                        status_tag = "⚠️ 潛水艇"
                    
                    if sdf['Net_Flow'].iloc[-1] > 0:
                        count_w = 0
                        for v in reversed(sdf['Net_Flow'].iloc[:-1].values):
                            if v <= 0: count_w += 1
                            else: break
                        if count_w >= lookback_val:
                            st.session_state.scan_results.append({
                                "代號": sid, "籌碼位階": status_tag, "股本(億)": scap, "現價": round(s_close, 2),
                                "60日資金流量柱": sdf['Net_Flow'].tail(60).tolist(), "RSI": round(float(sdf['RSI_14'].iloc[-1]), 1),
                                "20日乖離%": round(float(sdf['Bias_20'].iloc[-1]), 2),
                                "POC乖離%": round(poc_bias, 2),
                                "強度比(T)": round(t_val, 2), "強度(S)": round(s_val), "洗盤天數": int(count_w)
                            })
            st.session_state.last_scan_idx = i + 1
            if st.session_state.last_scan_idx >= total: st.session_state.is_scanning = False; st.rerun()
            else: time.sleep(0.1); st.rerun()

        if st.session_state.scan_results:
            st.write("---")
            f1, f2, f3, f4, f5 = st.columns([0.15, 0.15, 0.15, 0.15, 0.15])
            with f1: cap_f = st.number_input("股本(億) ≦", value=3000.0, step=10.0)
            with f2: t_f = st.number_input("強度比(T) ≧", value=0.0, step=0.1)
            with f3: bias_f = st.number_input("20日乖離 ≦", value=15.0, step=0.5)
            with f4: s_f = st.number_input("強度(S) ≧", value=-200.0, step=5.0)
            with f5: w_f = st.number_input("洗盤天數 ≧", value=0, step=1)
            
            f6, f7, f8 = st.columns([0.3, 0.3, 0.4])
            with f6: 
                poc_range = st.slider("POC乖離率篩選範圍 (%)", min_value=-200.0, max_value=200.0, value=(-200.0, 200.0), step=0.5)
            with f7:
                selected_tags = st.multiselect("過濾籌碼戰略位階", options=["⚡ 剛衝鋒", "🛡️ 守成本", "🚀 鷹擊長空", "⚠️ 潛水艇"], default=["⚡ 剛衝鋒", "🛡️ 守成本", "🚀 鷹擊長空", "⚠️ 潛水艇"])
            
            res_df = pd.DataFrame(st.session_state.scan_results).drop_duplicates(subset=['代號'])
            
            f_df = res_df[
                (res_df['股本(億)'] <= cap_f) & 
                (res_df['強度比(T)'] >= t_f) & 
                (res_df['20日乖離%'] <= bias_f) & 
                (res_df['POC乖離%'] >= poc_range[0]) & (res_df['POC乖離%'] <= poc_range[1]) & 
                (res_df['籌碼位階'].isin(selected_tags)) &
                (res_df['強度(S)'] >= s_f) & 
                (res_df['洗盤天數'] >= w_f)
            ]
            
            c_info = st.columns([0.5, 0.5])
            with c_info[0]: st.info(f"📊 **篩選戰報：** 符合條件 **{len(f_df)}** 檔 / 掃描總數 **{len(res_df)}** 檔。 ")
            with c_info[1]:
                if st.button("🚀 批量推播篩選結果至 TG", use_container_width=True, type="primary"):
                    if not f_df.empty:
                        msg = f"🚀 *詹VICTOR帥 | AI 選股雷達精選* \n━━━━━━━━━━━━━━━\n"
                        for _, row in f_df.iterrows():
                            msg += f"`{row['代號']} ` 現價:`{row['現價']}` 強度比:`{row['強度比(T']}%`\n"
                        if send_telegram_msg(msg): st.success("✅ 推播成功！")
                        else: st.error("❌ 推播失敗")
                    else: st.warning("目前無符合篩選條件的標的可推播")
            
            with f8:
                st.write(" ")
                if st.button("➕ 加入監控清單", use_container_width=True):
                    if not f_df.empty:
                        new_ids = f_df['代號'].tolist()
                        st.session_state.watch_list = list(dict.fromkeys(st.session_state.watch_list + new_ids))
                        st.success(f"✅ 已新增 {len(new_ids)} 檔標的"); time.sleep(1); st.rerun()
            
            st.dataframe(f_df, use_container_width=True, hide_index=True,
                column_config={
                    "60日資金流量柱": st.column_config.BarChartColumn("60日資金趨勢",
                        y_min=res_df["60日資金流量柱"].apply(min).min() if not res_df.empty else 0,
                        y_max=res_df["60日資金流量柱"].apply(max).max() if not res_df.empty else 1),
                    "RSI": st.column_config.NumberColumn("RSI位階", format="%.1f"),
                    "20日乖離%": st.column_config.NumberColumn("20日乖離", format="%.2f%%"),
                    "POC乖離%": st.column_config.NumberColumn("POC乖離", format="%.2f%%"),
                    "股本(億)": st.column_config.NumberColumn("股本(億)", format="%.1f 億")
                })

    with tab_import:
        st.subheader("📥 批量匯入個股代號")
        st.info("請在下方粘貼個股代號（支援換行、逗號或空白分隔）")
        input_data = st.text_area("代號輸入區", height=250, placeholder="在此貼上代號清單，例如：2330 2317 2454...")
        if st.button("✅ 執行匯入", type="primary", use_container_width=True):
            if input_data:
                extracted_ids = re.findall(r'\b\d{4,6}\b', input_data)
                if extracted_ids:
                    st.session_state.watch_list = list(dict.fromkeys(st.session_state.watch_list + extracted_ids))
                    st.success(f"🎊 匯入完成！偵測到 {len(extracted_ids)} 檔標的。"); time.sleep(1.5); st.rerun()
                else: st.error("❌ 找不到有效的數字代號。")
            else: text = st.warning("⚠️ 輸入框是空的喔！")
else:
    st.error("❌ 獲取失敗，請重新輸入代號。")
