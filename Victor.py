import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go  
from plotly.subplots import make_subplots
import numpy as np
from streamlit_autorefresh import st_autorefresh  

# --- 1. 頁面基礎設定 ---
st.set_page_config(layout="wide", page_title="詹VICTOR帥 | AI 深度交互實戰看板")
st_autorefresh(interval=60 * 1000, key="data_refresh")

bg_color = "#0F172A"
card_bg = "#1E293B"
text_color = "#F8FAFC"
border_color = "#334155"

# CSS 注入：強化手機端穩定性與 UI 質感
st.markdown(f"""
    <style>
    .main {{ background-color: {bg_color}; overflow-x: hidden; color: {text_color}; }}
    [data-testid="stPlotlyChart"] {{ touch-action: pan-y !important; }}
    .summary-card {{ background-color: {card_bg}; padding: 20px; border-radius: 15px; border-left: 8px solid #007bff; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px; color: {text_color}; }}
    .indicator-box {{ background: {card_bg}; padding: 18px; border-radius: 10px; margin-bottom: 15px; border-left: 6px solid #007bff; line-height: 1.8; border: 1px solid {border_color}; color: {text_color}; }}
    .strategy-box {{ background: {card_bg}; padding: 20px; border-radius: 12px; border: 2px solid #007bff; margin-top: 10px; box-shadow: 5px 5px 15px rgba(0,0,0,0.05); color: {text_color}; }}
    .diag-section-title {{ font-weight: bold; color: #1f77b4; margin-top: 20px; margin-bottom: 12px; border-bottom: 2px solid #007bff; padding-bottom: 5px; font-size: 18px; }}
    .calc-highlight {{ background: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 5px; color: #1E293B; }}
    div.stButton > button:first-child {{ background-color: #007bff; color: white; border-radius: 10px; border: none; width: 100%; font-weight: bold; }}
    
    </style>
    """, unsafe_allow_html=True)

# --- 2. 數據核心 ---
@st.cache_data(ttl=300)
def load_index_data():
    try:
        idx = yf.download("^TWII", period="2y", interval="1d", auto_adjust=False, progress=False)
        if isinstance(idx.columns, pd.MultiIndex):
            idx.columns = idx.columns.get_level_values(0)
        return idx
    except:
        return None

@st.cache_data(ttl=300)
def load_stock_data_safe(sid):
    for suffix in [".TW", ".TWO"]:
        try:
            full_sid = f"{sid}{suffix}"
            df = yf.download(full_sid, period="2y", interval="1d", auto_adjust=False, progress=False)
            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                
                df[['Open', 'High', 'Low', 'Close']] = df[['Open', 'High', 'Low', 'Close']].ffill()
                if 'Volume' in df.columns:
                    df['Volume'] = df['Volume'].fillna(0)
                    
                return df, full_sid
        except: continue
    return None, None

def get_poc_data(df_slice, bins):
    p_min, p_max = df_slice['Low'].min(), df_slice['High'].max()
    p_buckets = np.linspace(p_min, p_max, bins)
    v_hist, _ = np.histogram(df_slice['Close'], bins=p_buckets, weights=df_slice['Volume'])
    poc = (p_buckets[np.argmax(v_hist)] + p_buckets[np.argmax(v_hist)+1]) / 2
    return poc, p_buckets, v_hist

# --- 3. 頂部視覺與極致震撼標題 ---
header_bg = "linear-gradient(135deg, #020617 0%, #1e3a8a 100%)"
st.markdown(f"""
    <div style="
        background: {header_bg};
        padding: 30px 15px;
        border-radius: 20px;
        box-shadow: 0 15px 35px rgba(59, 130, 246, 0.4), inset 0 2px 5px rgba(255,255,255,0.2);
        margin-bottom: 25px;
        margin-top: 10px;
        text-align: center;
        border: 2px solid rgba(147, 197, 253, 0.2);
        position: relative;
        overflow: hidden;
    ">
        <div style="
            position: absolute; top: -50%; left: -50%; width: 200%; height: 200%;
            background: radial-gradient(circle, rgba(255,255,255,0.15) 0%, rgba(255,255,255,0) 60%);
            transform: rotate(30deg); pointer-events: none;
            animation: pulse 4s infinite alternate;
        "></div>
        <div class="main-header" style="
            position: relative;
            z-index: 10;
            margin: 0; 
            font-size: 34px; 
            font-weight: 900; 
            letter-spacing: 2px; 
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            flex-wrap: wrap;
        ">
            <span style="font-size: 40px;">🚀</span> 
            <span class="title-white" style="text-shadow: none;">詹VICTOR帥</span> 
            <span class="ai-badge" style="font-size: 18px; font-weight: 900; background: rgba(59,130,246,0.6); padding: 6px 14px; border-radius: 30px; border: 1px solid rgba(255,255,255,0.4); box-shadow: 0 0 10px rgba(0,0,0,0.5);">AI 戰情室</span>
        </div>
    </div>
    <style>
        .title-white {{ color: #FFFFFF !important; }}
        .ai-badge {{ color: #FDE047 !important; text-shadow: 0 0 5px rgba(253, 224, 71, 0.5); }}
        @keyframes pulse {{
            0% {{ transform: scale(1) rotate(30deg); opacity: 0.8; }}
            100% {{ transform: scale(1.1) rotate(30deg); opacity: 1; }}
        }}
    </style>
""", unsafe_allow_html=True)
c_in1, c_in4 = st.columns([1, 1.5])
with c_in1: stock_id = st.text_input("📍 代號", value="2330")
with c_in4: display_days = st.select_slider("觀察天數", options=[60, 120, 200, 300, 500], value=120)

cost_price = 0.0
hold_vol = 1000

raw_df, actual_ticker = load_stock_data_safe(stock_id)
idx_df = load_index_data()

if raw_df is not None:
    df_d = raw_df.copy()
    df_d.ta.sma(length=20, append=True)
    df_d.ta.rsi(length=14, append=True)
    df_d.ta.macd(append=True)
    df_d.ta.obv(append=True)
    df_d.ta.mfi(length=14, append=True)
    df_d['Net_Flow'] = (df_d['Close'].diff() * df_d['Volume'])
    
    # --- NF-QV 綜合風險指標計算 ---
    window_nf = 20
    nf_mean = df_d['Net_Flow'].rolling(window=window_nf, min_periods=1).mean()
    nf_std = df_d['Net_Flow'].rolling(window=window_nf, min_periods=1).std().replace(0, 1e-9)
    nf_z_score = (df_d['Net_Flow'] - nf_mean) / nf_std
    df_d['NF_Risk'] = np.where(nf_z_score > 0, 0, np.clip((abs(nf_z_score) / 2.0) * 100, 0, 100))
    
    vol_ma = df_d['Volume'].rolling(window=window_nf, min_periods=1).mean().replace(0, 1e-9)
    vol_ratio = df_d['Volume'] / vol_ma
    body_pct = (df_d['Close'] - df_d['Open']) / df_d['Close'].replace(0, 1e-9)
    df_d['VPE_Risk'] = 0.0
    mask_danger = (body_pct <= 0.005) & (vol_ratio > 1.0)
    df_d.loc[mask_danger, 'VPE_Risk'] = np.clip(((vol_ratio - 1) / 1.0) * 100, 0, 100)
    
    df_d['Pos_Risk'] = np.where(df_d.get('RSI_14', 50) < 70, 0, np.clip(((df_d.get('RSI_14', 50) - 70) / 15.0) * 100, 0, 100))
    df_d['nf_QV_Score'] = (df_d['NF_Risk'] * 0.4) + (df_d['VPE_Risk'] * 0.4) + (df_d['Pos_Risk'] * 0.2)
    # ------------------------------
    # ------------------------------
    
    # VPE_Base 與 籌碼集中度 (精準對齊 AI 戰情室)
    df_d['VPE_Base'] = (df_d['Close'] - df_d['Open']) / (df_d['High'] - df_d['Low'] + 1e-5)
    df_d['Chip_Concentration'] = (df_d['VPE_Base'] * df_d['Volume']).rolling(10).sum() / (df_d['Volume'].rolling(10).sum() + 1e-5) * 100

    
    # 強度比(T) (T_Score) 與 RVOL
    flow_60_mean = df_d['Net_Flow'].abs().rolling(window=60, min_periods=1).mean()
    df_d['T_Score'] = (df_d['Net_Flow'] / (flow_60_mean + 1e-9)).fillna(0.0)
    df_d['RVOL'] = df_d['Volume'] / df_d['Volume'].rolling(20, min_periods=1).mean()


    # --- 17層擴充運算 ---
    df_d.ta.macd(fast=12, slow=26, signal=9, append=True)
    df_d.ta.macd(fast=6, slow=10, signal=6, append=True)
    df_d['MACDh_raw'] = df_d['MACDh_12_26_9']
    df_d['MACD_raw'] = df_d['MACD_12_26_9']
    df_d['MACDs_raw'] = df_d['MACDs_12_26_9']
    
    df_d.ta.bbands(length=20, std=2, append=True)
    bbp_col = [c for c in df_d.columns if c.startswith('BBP_')][-1]
    df_d['BBP_EMA20'] = df_d[bbp_col].ewm(span=20, adjust=False).mean().fillna(0.5)
    
    df_d['Turnover_Value'] = df_d['Close'] * df_d['Volume']
    df_d['Turnover_Change_Rate'] = (df_d['Turnover_Value'].pct_change() * 100).clip(-300, 300).fillna(0)
    df_d['Turnover_Chg_EMA3'] = df_d['Turnover_Change_Rate'].ewm(span=3, adjust=False).mean()
    
    df_d['Vol_Rank_Score'] = (df_d['Volume'] / df_d['Volume'].rolling(120, min_periods=1).max() * 100).fillna(0)
    
    df_d['Typical_Price'] = (df_d['High'] + df_d['Low'] + df_d['Close']) / 3
    df_d['VWAP'] = (df_d['Typical_Price'] * df_d['Volume']).cumsum() / (df_d['Volume'].cumsum() + 1e-9)
    df_d['VWAP_BIAS'] = ((df_d['Close'] - df_d['VWAP']) / df_d['VWAP']) * 100
    
    df_d['BIAS_25'] = ((df_d['Close'] - df_d['Close'].rolling(25).mean()) / df_d['Close'].rolling(25).mean()) * 100
    df_d['Vol_Price_Efficiency'] = (df_d['VPE_Base'] * df_d['RVOL'] * 100).clip(-300, 300).fillna(0)
    

    df = df_d.tail(display_days).copy()
    curr = df.iloc[-1]
    price_now = float(curr['Close'])
    poc_price, p_buckets, v_hist = get_poc_data(df, 120)

    unrealized_pnl = (price_now - cost_price) * hold_vol if cost_price > 0 else 0
    pnl_ratio = (unrealized_pnl / (cost_price * hold_vol)) * 100 if cost_price > 0 else 0

    # 計算前一天收盤價與相關數據 (為了算漲幅與振幅)
    prev_close = df.iloc[-2]['Close'] if len(df) > 1 else curr['Open']
    change_pct = ((price_now - prev_close) / prev_close) * 100 if prev_close > 0 else 0
    amp_pct = ((curr['High'] - curr['Low']) / prev_close) * 100 if prev_close > 0 else 0
    
    if price_now > prev_close:
        close_color = "#DC2626"
        change_str = f"+{change_pct:.2f}%"
    elif price_now < prev_close:
        close_color = "#16A34A"
        change_str = f"{change_pct:.2f}%"
    else:
        close_color = "#334155"
        change_str = "0.00%"
        
    stock_name = ""
    try:
        import twstock
        clean_sid = str(stock_id).replace('.TWO', '').replace('.TW', '').strip()
        if clean_sid in twstock.codes:
            stock_name = twstock.codes[clean_sid].name
    except:
        pass
        
    display_title = f"{clean_sid} {stock_name}".strip()
    
    # 最新大單動向 (從 Net_Flow 推算)
    curr_netflow = curr['Net_Flow']
    if curr_netflow > 0:
        big_order_status = f"<span style='color:#DC2626; font-weight:bold;'>大單湧入 (淨流入 +{curr_netflow:,.0f})</span>"
    else:
        big_order_status = f"<span style='color:#16A34A; font-weight:bold;'>大單出場 (淨流出 {curr_netflow:,.0f})</span>"

    st.markdown(f"""<div style="display: flex; justify-content: space-between; align-items: center; background: #F8FAFC; padding: 12px 20px; border-radius: 8px; border: 1px solid #E2E8F0; margin-bottom: 15px; flex-wrap: wrap; gap: 10px;">
<div style="font-size: 16px; display: flex; align-items: baseline; flex-wrap: wrap;">
<span style="color: #64748B; margin-right: 5px;">現價</span>
<span style="color: {close_color}; font-size: 26px; font-weight: 900; margin-right: 15px; font-family: 'Consolas', monospace;">{price_now:.2f}</span>
<span style="color: {close_color}; font-size: 18px; font-weight: bold; margin-right: 25px;">({change_str})</span>
<span style="color: #64748B; margin-right: 5px;">開盤</span>
<span style="color: #334155; font-weight: bold; margin-right: 15px;">{curr['Open']:.2f}</span>
<span style="color: #64748B; margin-right: 5px;">最高</span>
<span style="color: #DC2626; font-weight: bold; margin-right: 15px;">{curr['High']:.2f}</span>
<span style="color: #64748B; margin-right: 5px;">最低</span>
<span style="color: #16A34A; font-weight: bold; margin-right: 20px;">{curr['Low']:.2f}</span>
<span style="color: #64748B; margin-right: 5px;">振幅</span>
<span style="color: #F59E0B; font-weight: bold; margin-right: 10px;">{amp_pct:.2f}%</span>
<span style="color: #475569; font-size: 24px; font-weight: 900; background: #F8FAFC; padding: 3px 15px; border-radius: 6px; border: 1px solid #CBD5E1; margin-left: 20px; letter-spacing: 1px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">{display_title}</span>
</div>
<div style="font-size: 16px; background: #FFFFFF; padding: 6px 15px; border-radius: 6px; border: 1px solid #CBD5E1; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
<span style="color: #475569; margin-right: 8px; font-weight: bold;">📊 最新大單動向:</span> {big_order_status}
</div>
</div>""", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["📊 技術看板", "💎 籌碼深度分佈", "🎯 深度實戰建議", "⚖️ 資金戰略與加減碼"])

    lock_config = {'displayModeBar': False, 'scrollZoom': False, 'staticPlot': False, 'doubleClick': False, 'responsive': True}

    with tab1:
        # 強制將 index 轉為字串，避免 Plotly 產生週末的空白 K 線
        df.index = df.index.strftime('%Y-%m-%d')
        fig = make_subplots(rows=17, cols=1, shared_xaxes=True, vertical_spacing=0.01, row_heights=[0.04, 0.12, 0.04, 0.06, 0.04, 0.04, 0.04, 0.06, 0.04, 0.05, 0.05, 0.04, 0.05, 0.04, 0.04, 0.04, 0.04])
        # 第 1 層：NF-QV 風險指標
        colors_nfqv = ['#DC2626' if val >= 80 else '#F59E0B' if val >= 60 else '#22C55E' for val in df['nf_QV_Score']]
        fig.add_trace(go.Bar(x=df.index, y=df['nf_QV_Score'], name="NF-QV風險", marker_color=colors_nfqv), row=1, col=1)
        fig.add_hline(y=80, line_dash="solid", line_color="#DC2626", line_width=1.5, row=1, col=1)
        fig.add_hline(y=60, line_dash="dash", line_color="#F59E0B", line_width=1.5, row=1, col=1)
        
        # 第 2 層主 K 線圖
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線", increasing_line_color='red', decreasing_line_color='black'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], name="20MA", line=dict(color='orange', width=2)), row=2, col=1)
        if cost_price > 0:
            fig.add_hline(y=cost_price, line_dash="dash", line_color="#333", annotation_text=f"成本:{cost_price}", row=2, col=1)
        
        # 指標加入左側顯示
        colors = ['#FF0000' if x >= 0 else '#00FF00' for x in df['Net_Flow']]
        fig.add_trace(go.Bar(x=df.index, y=df['Net_Flow'], name="資金流", marker_color=colors), row=3, col=1)
        
        # 籌碼集中度 (面積圖)
        colors_chip = ['#1f77b4' if x >= 0 else '#d62728' for x in df['Chip_Concentration']]
        fig.add_trace(go.Scatter(x=df.index, y=df['Chip_Concentration'], name="集中度", fill='tozeroy', line=dict(color='rgba(255,255,255,0)')), row=4, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df['Chip_Concentration'], name="集中度柱狀", marker_color=colors_chip, showlegend=False), row=4, col=1)
        fig.add_hline(y=0, line_dash="solid", line_color="black", line_width=1, row=4, col=1)
        # 第 5 層：強度比(T)
        colors_t = ['#EF4444' if t >= 2.5 else '#F87171' if t >= 1.5 else '#10B981' if t <= -2.5 else '#34D399' if t <= -1.5 else '#CBD5E1' for t in df['T_Score']]
        fig.add_trace(go.Bar(x=df.index, y=df['T_Score'], name="強度比(T)", marker_color=colors_t), row=5, col=1)
        
        # 第 6 層：RVOL 相對量能
        colors_rvol = ['#ff4d4d' if r >= 2.0 else '#ffb33b' if r >= 1.2 else '#a8dadc' for r in df['RVOL']]
        fig.add_trace(go.Bar(x=df.index, y=df['RVOL'], name="RVOL相對量能", marker_color=colors_rvol), row=6, col=1)
        
        # 加入強度比與RVOL的頸線
        fig.add_hline(y=1.5, line_dash="dash", line_color="#F87171", line_width=1.5, row=5, col=1)
        fig.add_hline(y=2.5, line_dash="solid", line_color="#EF4444", line_width=1.5, row=5, col=1)
        fig.add_hline(y=-1.5, line_dash="dash", line_color="#34D399", line_width=1.5, row=5, col=1)
        fig.add_hline(y=-2.5, line_dash="solid", line_color="#10B981", line_width=1.5, row=5, col=1)
        fig.add_hline(y=1.2, line_dash="dash", line_color="#ffb33b", line_width=2, row=6, col=1)
        fig.add_hline(y=2.0, line_dash="solid", line_color="#ff4d4d", line_width=2, row=6, col=1)
        fig.add_hline(y=0, line_dash="solid", line_color="black", line_width=1, row=5, col=1)
        
        # 第 7 層：成交值變化率
        colors_turnover_chg = ['rgba(239, 68, 68, 0.6)' if val >= 0 else 'rgba(34, 197, 94, 0.6)' for val in df['Turnover_Chg_EMA3']]
        fig.add_trace(go.Bar(x=df.index, y=df['Turnover_Chg_EMA3'], name="成交值變化率", marker_color=colors_turnover_chg), row=7, col=1)
        
        # 加入成交值變化率的頸線
        fig.add_hline(y=0, line_dash="dash", line_color="#475569", line_width=2, row=7, col=1)
        fig.add_hline(y=60, line_dash="solid", line_color="#EF4444", line_width=1.5, row=7, col=1)
        fig.add_hline(y=-20, line_dash="solid", line_color="#22C55E", line_width=1.5, row=7, col=1)
        
        # 第 8 層：成交量熱度分數
        vol_scaled = (df['Volume'] - df['Volume'].min()) / (df['Volume'].max() - df['Volume'].min()) * 100
        fig.add_trace(go.Bar(x=df.index, y=vol_scaled, name="成交量", marker_color='rgba(158, 202, 225, 0.5)'), row=8, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['Vol_Rank_Score'], name="熱度分數", line=dict(color='#EAB308', width=2)), row=8, col=1)
        
        # 第 9 層：量價效率指標
        colors_vpe = ['#EF4444' if val >= 0 else '#22C55E' for val in df['Vol_Price_Efficiency']]
        fig.add_trace(go.Bar(x=df.index, y=df['Vol_Price_Efficiency'], name="量價效率", marker_color=colors_vpe), row=9, col=1)
        
        # 加入量價效率的頸線
        fig.add_hline(y=0, line_dash="solid", line_color="#94A3B8", line_width=1, row=9, col=1)
        fig.add_hline(y=50, line_dash="dash", line_color="#EF4444", line_width=1, row=9, col=1)
        fig.add_hline(y=-50, line_dash="dash", line_color="#22C55E", line_width=1, row=9, col=1)
        
        # 第 10 層：MACD 快速
        colors_macd_fast = ['#e63946' if val >= 0 else '#2a9d8f' for val in df['MACDh_6_10_6']] if 'MACDh_6_10_6' in df.columns else ['#e63946'] * len(df)
        if 'MACDh_6_10_6' in df.columns:
            fig.add_trace(go.Bar(x=df.index, y=df['MACDh_6_10_6'], name="MACD快速柱", marker_color=colors_macd_fast), row=10, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MACD_6_10_6'], name="MACD快線", line=dict(color='#3B82F6', width=1)), row=10, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MACDs_6_10_6'], name="MACD慢線", line=dict(color='#F59E0B', width=1)), row=10, col=1)
        
        # 第 11 層：MACD 原始
        colors_macd_raw = ['#e63946' if val >= 0 else '#2a9d8f' for val in df['MACDh_raw']]
        fig.add_trace(go.Bar(x=df.index, y=df['MACDh_raw'], name="MACD原始柱", marker_color=colors_macd_raw), row=11, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD_raw'], name="MACD原快線", line=dict(color='#3B82F6', width=1)), row=11, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MACDs_raw'], name="MACD原慢線", line=dict(color='#F59E0B', width=1)), row=11, col=1)
        
        # 第 12 層：暫無大戶持股比 (因 yfinance 無法獲取，使用 OBV 替代顯示)
        fig.add_trace(go.Scatter(x=df.index, y=df['OBV'], name="大戶籌碼代理", fill='tozeroy', fillcolor='rgba(139, 92, 246, 0.2)', line=dict(color='#8B5CF6', width=2)), row=12, col=1)
        
        # 第 13 層：布林極限 %B (包含主線與均線以顯示黃金交叉)
        bbp_col = [c for c in df.columns if c.startswith('BBP_') and c != 'BBP_EMA20'][-1]
        fig.add_trace(go.Scatter(x=df.index, y=df[bbp_col], name="%B快線", line=dict(color='#ff0066', width=2)), row=13, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['BBP_EMA20'], name="%B慢線(均線)", line=dict(color='#ffd166', width=2)), row=13, col=1)
        
        # 第 14 層：RSI 動能
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI_14'], name="RSI", line=dict(color='#457b9d', width=2)), row=14, col=1)
        
        # 第 15 層：25日乖離線
        fig.add_trace(go.Scatter(x=df.index, y=df['BIAS_25'], name="25日乖離線", line=dict(color='#E11D48', width=2)), row=15, col=1)
        
        # 加入乖離率的頸線
        bias_std = df['BIAS_25'].std() if len(df) > 0 else 5
        upper_bound = bias_std * 1.5
        lower_bound = -bias_std * 1.5
        fig.add_hline(y=0, line_dash="dash", line_color="#94A3B8", line_width=1, row=15, col=1)
        fig.add_hline(y=upper_bound, line_dash="solid", line_color="#EF4444", line_width=1.5, row=15, col=1)
        fig.add_hline(y=lower_bound, line_dash="solid", line_color="#22C55E", line_width=1.5, row=15, col=1)
        
        # 第 16 層：MFI 熱錢流
        fig.add_trace(go.Scatter(x=df.index, y=df['MFI_14'], name="MFI", fill='tozeroy', fillcolor='rgba(23, 190, 207, 0.2)', line=dict(color='#17becf', width=2)), row=16, col=1)
        
        # 第 17 層：OBV 累積能量
        fig.add_trace(go.Scatter(x=df.index, y=df['OBV'], name="OBV", line=dict(color='#7f7f7f', width=2)), row=17, col=1)

        # 修正：調整 margin-l (左邊距) 從 10 增加到 50，避免名稱被遮擋
        fig.update_layout(height=3600, template="plotly_white", hovermode='x unified', showlegend=False, xaxis_rangeslider_visible=False, xaxis2_rangeslider_visible=False,
                          xaxis_type='category', margin=dict(l=50, r=10, t=10, b=10), dragmode=False)
        fig.update_xaxes(fixedrange=True)
        fig.update_yaxes(fixedrange=True)
        # 設定 y 軸標題顯示
        fig.update_yaxes(title_text="NF-QV", range=[0, 100], row=1, col=1)
        fig.update_yaxes(title_text="價格", row=2, col=1)
        fig.update_yaxes(title_text="淨流", row=3, col=1)
        fig.update_yaxes(title_text="集中度", row=4, col=1)
        fig.update_yaxes(title_text="強度(T)", row=5, col=1)
        fig.update_yaxes(title_text="RVOL", row=6, col=1)
        fig.update_yaxes(title_text="成交值變", row=7, col=1)
        fig.update_yaxes(title_text="熱度", row=8, col=1)
        fig.update_yaxes(title_text="量價效", row=9, col=1)
        fig.update_yaxes(title_text="快MACD", row=10, col=1)
        fig.update_yaxes(title_text="MACD", row=11, col=1)
        fig.update_yaxes(title_text="大戶代理", row=12, col=1)
        fig.update_yaxes(title_text="%B", row=13, col=1)
        fig.update_yaxes(title_text="RSI", row=14, col=1)
        fig.update_yaxes(title_text="乖離", row=15, col=1)
        fig.update_yaxes(title_text="MFI", row=16, col=1)
        fig.update_yaxes(title_text="OBV", row=17, col=1)
        
        st.plotly_chart(fig, use_container_width=True, config=lock_config)

    with tab2:
        col_c1, col_c2 = st.columns([0.55, 0.45])
        with col_c1:
            fig_vp = go.Figure(go.Bar(y=(p_buckets[:-1] + p_buckets[1:]) / 2, x=v_hist, orientation='h', opacity=0.7))
            fig_vp.add_hline(y=price_now, line_color="red", line_width=2, annotation_text="現價")
            fig_vp.add_hline(y=poc_price, line_dash="dash", line_color="blue", annotation_text="POC重心")
            fig_vp.update_layout(height=600, hovermode='y unified', showlegend=False, margin=dict(l=50, r=5, t=10, b=10))
            st.plotly_chart(fig_vp, use_container_width=True, config=lock_config)
        with col_c2:
            st.markdown('<p class="diag-section-title">🕵️ 詹帥籌碼核心觀察</p>', unsafe_allow_html=True)
            st.markdown(f"<div class='indicator-box'><b>📍 籌碼重心 (POC) 解析</b><br>密集區在 {poc_price:.2f}。目前為{'「多頭優勢」' if price_now > poc_price else '「空頭反彈」'}。</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='indicator-box'><b>🔥 動能指標 (MFI)</b><br>數值 {curr['MFI_14']:.1f}。{'資金流入，籌碼穩定。' if curr['MFI_14'] > 50 else '資金流出，嚴防無量。'}</div>", unsafe_allow_html=True)

    with tab3:
        # (此分頁內容與 21 項指標邏輯完整保留)
        col_r1, col_r2 = st.columns([0.45, 0.55])
        with col_r1:
            radar_vals = [100 if price_now > curr['SMA_20'] else 20, curr['RSI_14'], curr['MFI_14'], 100 if curr['MACDh_12_26_9'] > 0 else 20, 100 if curr['OBV'] > df['OBV'].iloc[-5] else 30, 100 if curr['Net_Flow'] > 0 else 30]
            fig_r = go.Figure(go.Scatterpolar(r=radar_vals, theta=['趨勢', 'RSI', 'MFI', 'MACD', 'OBV', '資金'], fill='toself'))
            fig_r.update_layout(height=400, showlegend=False, polar=dict(radialaxis=dict(visible=True, range=[0, 100]), angularaxis=dict(direction="clockwise")))
            st.plotly_chart(fig_r, use_container_width=True, config=lock_config)
        with col_r2:
            st.markdown('<p class="diag-section-title">🚀 詹帥動態實戰戰略艙</p>', unsafe_allow_html=True)
            support = max(curr['SMA_20'], poc_price)
            if cost_price == 0:
                cmd, detail, border_color = "請輸入成本價", "輸入後將提供專屬戰略。", "#007bff"
            elif pnl_ratio >= 15:
                cmd, detail, border_color = "【大幅獲利】啟動移動止盈", f"獲利已達 {pnl_ratio:.1f}%，建議守住 {price_now * 0.93:.2f} 讓利潤奔跑。", "#d9534f"
            elif 0 <= pnl_ratio < 15:
                cmd, detail, border_color = "【初步獲利】趨勢向上續抱", f"目前溫和獲利，不破支撐位 {support:.2f} 續抱，目標上看 {price_now * 1.1:.2f}。", "#f0ad4e"
            elif -5 <= pnl_ratio < 0:
                cmd, detail, border_color = "【微幅套牢】良性回檔觀察", f"套牢 {pnl_ratio:.1f}%，POC 重心 {poc_price:.2f} 附近具支撐，不破不砍。", "#5bc0de"
            else:
                cmd, detail, border_color = "【深度套牢】執行戰略撤退", f"虧損達 {pnl_ratio:.1f}%。若未站回 {support:.2f}，建議減碼 1/2 保護資金。", "#5cb85c"
            st.markdown(f"<div class='strategy-box' style='border-color: {border_color};'><span style='color:{border_color}; font-size:22px; font-weight:bold;'>指令：{cmd}</span><br><br>● <b>操作指令：</b>{detail}<br>● <b>關鍵支撐：</b><span style='color:green; font-weight:bold;'>{support:.2f}</span><br>● <b>預估壓力：</b><span style='color:red; font-weight:bold;'>{price_now * 1.08:.2f}</span></div>", unsafe_allow_html=True)
            st.markdown('<p class="diag-section-title">🔍 指標深度詳解 (21項評估核心)</p>', unsafe_allow_html=True)
            st.markdown(f"<div class='indicator-box'><b>RSI 攻擊力 ({curr['RSI_14']:.1f})</b><br>{'強勢格局，具過高潛力。' if curr['RSI_14']>60 else '盤整待變，等待放量。'}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='indicator-box'><b>MACD 趨勢 ({curr['MACDh_12_26_9']:.2f})</b><br>{'波段多方控盤中。' if curr['MACDh_12_26_9']>0 else '空方整理，動能收斂中。'}</div>", unsafe_allow_html=True)

    with tab4:
        st.markdown('<p class="diag-section-title">⚖️ 詹帥倉位調控模擬器</p>', unsafe_allow_html=True)
        col_calc1, col_calc2 = st.columns([0.4, 0.6])
        with col_calc1:
            st.subheader("🛠️ 戰略參數輸入")
            cur_avg_p = st.number_input("現有成本價", value=float(price_now), format="%.2f", key="sim_cost")
            cur_qty = st.number_input("現有張數", value=int(hold_vol/1000), step=1, key="sim_qty")
            st.write("---")
            change_shares = st.number_input("變動張數 (張)", value=1, step=1, key="sim_change_q")
            change_price = st.number_input("變動執行價格", value=float(price_now), format="%.2f", key="sim_change_p")
            
            # 保留：變動總價自動顯示
            change_total_amt = abs(change_shares) * change_price * 1000
            st.markdown(f"""<div class='calc-highlight' style='border-left: 5px solid #ff4b4b;'>🚀 變動總金額：<b>{change_total_amt:,.0f}</b> 元</div>""", unsafe_allow_html=True)
            
            total_qty_new = cur_qty + change_shares
            if total_qty_new > 0:
                new_avg_price = ((cur_avg_p * cur_qty) + (change_price * change_shares)) / total_qty_new
                new_cost_total = new_avg_price * total_qty_new * 1000
                new_market_total = price_now * total_qty_new * 1000
                new_pnl_val = new_market_total - new_cost_total
                new_pnl_pct = (new_pnl_val / new_cost_total * 100) if new_cost_total > 0 else 0
            else:
                new_avg_price, new_pnl_val, new_pnl_pct = 0, 0, 0

        with col_calc2:
            st.subheader("📊 模擬戰略結果")
            c1, c2, c3 = st.columns(3)
            c1.metric("模擬後新成本", f"{new_avg_price:.2f}")
            c2.metric("成本變動幅度", f"{((new_avg_price/cur_avg_p)-1)*100:+.2f}%" if cur_avg_p > 0 else "0%")
            c3.metric("總持股張數", f"{total_qty_new} 張")
            st.write("---")
            now_cost_total = cur_avg_p * cur_qty * 1000
            now_pnl_val = (price_now * cur_qty * 1000) - now_cost_total
            now_pnl_pct = (now_pnl_val / now_cost_total * 100) if now_cost_total > 0 else 0
            r1, r2 = st.columns(2)
            r1.metric("預期盈虧金額", f"{new_pnl_val:,.0f} 元", delta=f"{new_pnl_val - now_pnl_val:,.0f}")
            r2.metric("預期盈虧百分比", f"{new_pnl_pct:.2f}%", delta=f"{new_pnl_pct - now_pnl_pct:.2f}%")
            
            st.markdown('<p class="diag-section-title">⚠️ 加碼風險評鑑</p>', unsafe_allow_html=True)
            support_val = max(curr['SMA_20'], poc_price)
            if change_shares > 0:
                if change_price < support_val * 0.95: risk_s, risk_c = "🔴 高風險 (危險攤平)", "red"
                elif change_price <= support_val * 1.03: risk_s, risk_c = "🟢 低風險 (策略加碼)", "green"
                else: risk_s, risk_c = "🟡 中風險 (追價加碼)", "orange"
                st.markdown(f"<div style='background:{risk_c}; color:white; padding:15px; border-radius:10px; text-align:center; font-weight:bold;'>評級：{risk_s}</div>", unsafe_allow_html=True)
            st.info(f"💡 **詹帥戰略提醒**：1. 保本點：股價需維持在 **{new_avg_price:.2f}** 以上。2. 最大曝險：若回測支撐位 **{support_val:.2f}**，損益將變動為 **{((support_val - new_avg_price) * total_qty_new * 1000):,.0f}** 元。")
else:
    st.error("❌ 數據載入失敗，請檢查代號是否正確。")