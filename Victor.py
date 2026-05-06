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

# CSS 注入：強化手機端穩定性與 UI 質感 (完整保留)
st.markdown("""
    <style>
    /* 防止手機瀏覽器非必要的橫向滾動 */
    .main { background-color: #f8f9fa; overflow-x: hidden; }
    
    /* 強制禁止圖表容器內的觸控縮放，提升手機操作穩定性 */
    [data-testid="stPlotlyChart"] { touch-action: pan-y !important; }

    .summary-card { background-color: #ffffff; padding: 20px; border-radius: 15px; border-left: 8px solid #007bff; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px; }
    .indicator-box { background: #ffffff; padding: 18px; border-radius: 10px; margin-bottom: 15px; border-left: 6px solid #007bff; line-height: 1.8; border: 1px solid #eaeaea; }
    .strategy-box { background: #ffffff; padding: 20px; border-radius: 12px; border: 2px solid #007bff; margin-top: 10px; box-shadow: 5px 5px 15px rgba(0,0,0,0.05); }
    .diag-section-title { font-weight: bold; color: #1f77b4; margin-top: 20px; margin-bottom: 12px; border-bottom: 2px solid #007bff; padding-bottom: 5px; font-size: 18px; }
    
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { height: 45px; font-weight: 600; }
    
    .calc-highlight { background: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 5px; }
    
    /* 讓按鈕更醒目 */
    div.stButton > button:first-child {
        background-color: #007bff;
        color: white;
        border-radius: 10px;
        border: none;
        width: 100%;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 數據核心 ---
@st.cache_data(ttl=300)
def load_stock_data_safe(sid):
    for suffix in [".TW", ".TWO"]:
        try:
            full_sid = f"{sid}{suffix}"
            df = yf.download(full_sid, period="2y", interval="1d", auto_adjust=False, progress=False)
            if not df.empty:
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

# --- 3. 頂部快速輸入區 (已取消恢復鍵) ---
st.title("🛡️ 詹VICTOR帥 | AI 戰情室")
c_in1, c_in2, c_in3, c_in4 = st.columns([1, 1, 1, 1.5])
with c_in1: stock_id = st.text_input("📍 代號", value="2330")
with c_in2: cost_price = st.number_input("💰 成本價", value=0.0, format="%.2f")
with c_in3: hold_vol = st.number_input("股數 (股)", value=1000, step=1000)
with c_in4: display_days = st.select_slider("觀察天數", options=[60, 120, 200, 300, 500], value=120)

raw_df, actual_ticker = load_stock_data_safe(stock_id)

if raw_df is not None:
    df_d = raw_df.copy()
    df_d.ta.sma(length=20, append=True)
    df_d.ta.rsi(length=14, append=True)
    df_d.ta.macd(append=True)
    df_d.ta.obv(append=True)
    df_d.ta.mfi(length=14, append=True)
    df_d['Net_Flow'] = (df_d['Close'].diff() * df_d['Volume'])
    
    df = df_d.tail(display_days).copy()
    curr = df.iloc[-1]
    price_now = float(curr['Close'])
    poc_price, p_buckets, v_hist = get_poc_data(df, 120)

    unrealized_pnl = (price_now - cost_price) * hold_vol if cost_price > 0 else 0
    pnl_ratio = (unrealized_pnl / (cost_price * hold_vol)) * 100 if cost_price > 0 else 0

    st.markdown(f'''
        <div class="summary-card">
            <b>即時盤勢：{actual_ticker} | 現價：{price_now:.2f} | 籌碼重心：{poc_price:.2f}</b><br>
            <span style="color:{'#d9534f' if unrealized_pnl < 0 else '#5cb85c'}; font-size: 20px; font-weight: bold;">
                當前帳面損益：{unrealized_pnl:,.0f} ({pnl_ratio:.2f}%)
            </span>
        </div>
    ''', unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["📊 技術看板", "💎 籌碼深度分佈", "🎯 深度實戰建議", "⚖️ 資金戰略與加減碼"])

    # 配置：防止誤觸縮放，僅保留 Y 軸標籤
    lock_config = {
        'displayModeBar': False, 
        'scrollZoom': False, 
        'staticPlot': False, 
        'doubleClick': False,
        'responsive': True
    }

    with tab1:
        fig = make_subplots(rows=6, cols=1, shared_xaxes=True, vertical_spacing=0.03, 
                           row_heights=[0.35, 0.12, 0.12, 0.12, 0.12, 0.15])
        
        # 1. K線與SMA
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], name="20MA", line=dict(color='orange', width=2)), row=1, col=1)
        if cost_price > 0:
            fig.add_hline(y=cost_price, line_dash="dash", line_color="#333", annotation_text=f"成本:{cost_price}", row=1, col=1)
        
        # 2. RSI
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI_14'], name="RSI", line=dict(color='#9467bd')), row=2, col=1)
        
        # 3. MACD
        fig.add_trace(go.Bar(x=df.index, y=df['MACDh_12_26_9'], name="MACD"), row=3, col=1)
        
        # 4. MFI
        fig.add_trace(go.Scatter(x=df.index, y=df['MFI_14'], name="MFI", fill='tozeroy', line=dict(color='#17becf')), row=4, col=1)
        
        # 5. OBV
        fig.add_trace(go.Scatter(x=df.index, y=df['OBV'], name="OBV", line=dict(color='#e377c2', width=1.5)), row=5, col=1)
        
        # 6. 資金流
        colors = ['#FF0000' if x >= 0 else '#00FF00' for x in df['Net_Flow']]
        fig.add_trace(go.Bar(x=df.index, y=df['Net_Flow'], name="資金流", marker_color=colors), row=6, col=1)
        
        fig.update_layout(height=1000, template="plotly_white", hovermode='x unified', showlegend=False, xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10))
        
        fig.update_yaxes(title_text="價格", row=1, col=1)
        fig.update_yaxes(title_text="RSI", row=2, col=1)
        fig.update_yaxes(title_text="MACD", row=3, col=1)
        fig.update_yaxes(title_text="MFI", row=4, col=1)
        fig.update_yaxes(title_text="OBV能量", row=5, col=1)
        fig.update_yaxes(title_text="資金流", row=6, col=1)
        
        st.plotly_chart(fig, use_container_width=True, config=lock_config)

    with tab2:
        col_c1, col_c2 = st.columns([0.55, 0.45])
        with col_c1:
            fig_vp = go.Figure(go.Bar(y=(p_buckets[:-1] + p_buckets[1:]) / 2, x=v_hist, orientation='h', opacity=0.7))
            fig_vp.add_hline(y=price_now, line_color="red", line_width=2, annotation_text="現價")
            fig_vp.add_hline(y=poc_price, line_dash="dash", line_color="blue", annotation_text="POC重心")
            fig_vp.update_layout(height=600, hovermode='y unified', showlegend=False, margin=dict(l=5, r=5, t=10, b=10))
            st.plotly_chart(fig_vp, use_container_width=True, config=lock_config)
        with col_c2:
            st.markdown('<p class="diag-section-title">🕵️ 詹帥籌碼核心觀察</p>', unsafe_allow_html=True)
            st.markdown(f"<div class='indicator-box'><b>📍 籌碼重心 (POC) 解析</b><br>密集區在 {poc_price:.2f}。目前為{'「多頭優勢」' if price_now > poc_price else '「空頭反彈」'}。</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='indicator-box'><b>🔥 動能指標 (MFI)</b><br>數值 {curr['MFI_14']:.1f}。{'資金流入，籌碼穩定。' if curr['MFI_14'] > 50 else '資金流出，嚴防無量。'}</div>", unsafe_allow_html=True)

    with tab3:
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
            with st.container():
                st.markdown("**1. 現有部位實況**")
                cur_avg_p = st.number_input("現有成本價", value=cost_price if cost_price > 0 else 30.0, format="%.2f", key="sim_cost")
                cur_qty = st.number_input("現有張數", value=int(hold_vol/1000), step=1, key="sim_qty")
                
                now_cost_total = cur_avg_p * cur_qty * 1000
                now_market_total = price_now * cur_qty * 1000
                now_pnl_val = now_market_total - now_cost_total
                now_pnl_pct = (now_pnl_val / now_cost_total * 100) if now_cost_total > 0 else 0
                
                st.markdown(f"""<div class='calc-highlight'>當前盈虧：<span style='color:{'red' if now_pnl_val >=0 else 'green'}'>{now_pnl_val:,.0f} 元</span> ({now_pnl_pct:+.2f}%)</div>""", unsafe_allow_html=True)
                st.write("---")
                st.markdown("**2. 計畫變動 (加碼為正, 減碼為負)**")
                change_shares = st.number_input("變動張數 (張)", value=1, step=1, key="sim_change_q")
                change_price = st.number_input("變動執行價格", value=price_now, format="%.2f", key="sim_change_p")
                
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
            st.markdown("**💰 預期財務變動 (按現價計算)**")
            r1, r2 = st.columns(2)
            r1.metric("預期盈虧金額", f"{new_pnl_val:,.0f} 元", delta=f"{new_pnl_val - now_pnl_val:,.0f}")
            r2.metric("預期盈虧百分比", f"{new_pnl_pct:.2f}%", delta=f"{new_pnl_pct - now_pnl_pct:.2f}%")

            st.markdown('<p class="diag-section-title">⚠️ 加碼風險評鑑</p>', unsafe_allow_html=True)
            support_val = max(curr['SMA_20'], poc_price)
            if change_shares > 0:
                if change_price < support_val * 0.95:
                    risk_s, risk_c = "🔴 高風險 (危險攤平)", "red"
                elif change_price <= support_val * 1.03:
                    risk_s, risk_c = "🟢 低風險 (策略加碼)", "green"
                else:
                    risk_s, risk_c = "🟡 中風險 (追價加碼)", "orange"
                st.markdown(f"<div style='background:{risk_c}; color:white; padding:15px; border-radius:10px; text-align:center; font-weight:bold;'>評級：{risk_s}</div>", unsafe_allow_html=True)

            st.info(f"💡 **詹帥戰略提醒**：1. 保本點：股價需維持在 **{new_avg_price:.2f}** 以上。2. 最大曝險：若回測支撐位 **{support_val:.2f}**，損益將變動為 **{((support_val - new_avg_price) * total_qty_new * 1000):,.0f}** 元。")
else:
    st.error("❌ 數據載入失敗，請檢查代號是否正確。")
