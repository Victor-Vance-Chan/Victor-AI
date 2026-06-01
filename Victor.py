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

# CSS 注入：強化手機端穩定性與 UI 質感
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; overflow-x: hidden; }
    [data-testid="stPlotlyChart"] { touch-action: pan-y !important; }
    .summary-card { background-color: #ffffff; padding: 20px; border-radius: 15px; border-left: 8px solid #007bff; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px; }
    .indicator-box { background: #ffffff; padding: 18px; border-radius: 10px; margin-bottom: 15px; border-left: 6px solid #007bff; line-height: 1.8; border: 1px solid #eaeaea; }
    .strategy-box { background: #ffffff; padding: 20px; border-radius: 12px; border: 2px solid #007bff; margin-top: 10px; box-shadow: 5px 5px 15px rgba(0,0,0,0.05); }
    .diag-section-title { font-weight: bold; color: #1f77b4; margin-top: 20px; margin-bottom: 12px; border-bottom: 2px solid #007bff; padding-bottom: 5px; font-size: 18px; }
    .calc-highlight { background: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 5px; }
    div.stButton > button:first-child { background-color: #007bff; color: white; border-radius: 10px; border: none; width: 100%; font-weight: bold; }
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

# --- 3. 頂部快速輸入區 ---
st.title("🛡️ 詹VICTOR帥 | AI 戰情室")
c_in1, c_in2, c_in3, c_in4 = st.columns([1, 1, 1, 1.5])
with c_in1: stock_id = st.text_input("📍 代號", value="2330")
with c_in2: cost_price = st.number_input("💰 成本價", value=0.0, format="%.2f")
with c_in3: hold_vol = st.number_input("股數 (股)", value=1000, step=1000)
with c_in4: display_days = st.select_slider("觀察天數", options=[60, 120, 200, 300, 500], value=120)

raw_df, actual_ticker = load_stock_data_safe(stock_id)

if raw_df is not None:
    df_d = raw_df.copy()
    
    # --- 升級：全面掛載量化雷達五大引擎核心指標 ---
    df_d.ta.sma(length=20, append=True)
    df_d.ta.rsi(length=14, append=True)
    df_d.ta.macd(append=True)
    df_d.ta.obv(append=True)
    df_d.ta.mfi(length=14, append=True)
    df_d.ta.bbands(length=20, std=2, append=True) # 新增布林通道引擎
    
    df_d['Net_Flow'] = (df_d['Close'].diff() * df_d['Volume']).fillna(0)
    df_d['Bias_20'] = ((df_d['Close'] - df_d['SMA_20']) / df_d['SMA_20']) * 100
    df_d['Vol_MA20'] = df_d['Volume'].rolling(20).mean()
    df_d['RVOL'] = (df_d['Volume'] / df_d['Vol_MA20']).fillna(1.0)
    df_d['Is_Vol_Dry'] = df_d['Volume'] < (df_d['Vol_MA20'] * 0.6) # 窒息量凹洞定義
    
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

    lock_config = {'displayModeBar': False, 'scrollZoom': False, 'staticPlot': False, 'doubleClick': False, 'responsive': True}

    # ==================== 📊 TAB 1: 技術看板 (已完全升級為雷達引擎規格) ====================
    with tab1:
        # 設定 6 個子圖軸：K線(含布林)、RVOL+凹洞標記、RSI、MACD、OBV/MFI、資金淨流
        fig = make_subplots(rows=6, cols=1, shared_xaxes=True, vertical_spacing=0.02, 
                            row_heights=[0.35, 0.12, 0.11, 0.11, 0.14, 0.17])
        
        # 1. 主圖：K線 + 20MA + 布林通道
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], name="20MA", line=dict(color='orange', width=2)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['BBU_20_2.0'], name="布林上軌", line=dict(color='rgba(173,216,230,0.7)', dash='dash')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['BBL_20_2.0'], name="布林下軌", line=dict(color='rgba(173,216,230,0.7)', dash='dash')), row=1, col=1)
        if cost_price > 0:
            fig.add_hline(y=cost_price, line_dash="dash", line_color="#333", annotation_text=f"成本:{cost_price}", row=1, col=1)
        
        # 2. 副圖二：RVOL 相對成交量 + 凹洞窒息量標記
        fig.add_trace(go.Bar(x=df.index, y=df['RVOL'], name="RVOL", marker_color='#9467bd', opacity=0.6), row=2, col=1)
        fig.add_hline(y=1.0, line_dash="dot", line_color="gray", row=2, col=1)
        # 標出符合窒息量（Is_Vol_Dry == True）的點
        dry_df = df[df['Is_Vol_Dry'] == True]
        if not dry_df.empty:
            fig.add_trace(go.Scatter(x=dry_df.index, y=dry_df['RVOL'], name="量縮凹洞", mode='markers', marker=dict(color='gold', size=8, symbol='circle')), row=2, col=1)
        
        # 3. 副圖三：RSI 攻擊力
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI_14'], name="RSI", line=dict(color='#2ca02c', width=1.5)), row=3, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="rgba(219, 68, 85, 0.5)", row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="rgba(15, 157, 88, 0.5)", row=3, col=1)
        
        # 4. 副圖四：MACD 趨勢柱狀體
        fig.add_trace(go.Bar(x=df.index, y=df['MACDh_12_26_9'], name="MACD柱"), row=4, col=1)
        
        # 5. 副圖五：OBV (能量潮) 與 MFI (資金動能指標)
        fig.add_trace(go.Scatter(x=df.index, y=df['MFI_14'], name="MFI", line=dict(color='#17becf', width=1.5)), row=5, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['OBV'], name="OBV", line=dict(color='#e377c2'), yaxis="y2"), row=5, col=1)
        
        # 6. 副圖六：資金淨流量 (Net Flow 柱狀圖)
        colors = ['#FF0000' if x >= 0 else '#00FF00' for x in df['Net_Flow']]
        fig.add_trace(go.Bar(x=df.index, y=df['Net_Flow'], name="資金流", marker_color=colors), row=6, col=1)
        
        # 板面美化配置與標籤修正
        fig.update_layout(
            height=1100, template="plotly_white", hovermode='x unified', 
            showlegend=False, xaxis_rangeslider_visible=False, 
            margin=dict(l=60, r=10, t=10, b=10)
        )
        
        # 設定各軸標題
        fig.update_yaxes(title_text="價格 / 布林", row=1, col=1)
        fig.update_yaxes(title_text="RVOL 量比", row=2, col=1)
        fig.update_yaxes(title_text="RSI(14)", row=3, col=1)
        fig.update_yaxes(title_text="MACD柱", row=4, col=1)
        fig.update_yaxes(title_text="MFI 動能", row=5, col=1)
        fig.update_yaxes(title_text="資金淨流", row=6, col=1)
        
        st.plotly_chart(fig, use_container_width=True, config=lock_config)

    # ==================== 💎 TAB 2: 籌碼深度分佈 (完整保留) ====================
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

    # ==================== 🎯 TAB 3: 深度實戰建議 (完整保留) ====================
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

    # ==================== ⚖️ TAB 4: 資金戰略與加減碼 (完整保留) ====================
    with tab4:
        st.markdown('<p class="diag-section-title">⚖️ 詹帥倉位調控模擬器</p>', unsafe_allow_html=True)
        col_calc1, col_calc2 = st.columns([0.4, 0.6])
        with col_calc1:
            st.subheader("🛠️ 戰略參數輸入")
            cur_avg_p = st.number_input("現有成本價", value=cost_price if cost_price > 0 else 30.0, format="%.2f", key="sim_cost")
            cur_qty = st.number_input("現有張數", value=int(hold_vol/1000), step=1, key="sim_qty")
            st.write("---")
            change_shares = st.number_input("變動張數 (張)", value=1, step=1, key="sim_change_q")
            change_price = st.number_input("變動執行價格", value=price_now, format="%.2f", key="sim_change_p")
            
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
