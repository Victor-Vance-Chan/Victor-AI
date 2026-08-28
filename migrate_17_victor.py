import re

filepath = r"D:\IDE資料\0.股票系統\手機戰情室\victor.py"

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 注入更多的計算 (在 df = df_d.tail... 之前)
extra_calcs = """
    # --- 17層擴充運算 ---
    df_d.ta.macd(fast=12, slow=26, signal=9, append=True)
    df_d.ta.macd(fast=6, slow=10, signal=6, append=True)
    df_d['MACDh_raw'] = df_d['MACDh_12_26_9']
    df_d['MACD_raw'] = df_d['MACD_12_26_9']
    df_d['MACDs_raw'] = df_d['MACDs_12_26_9']
    
    df_d.ta.bbands(length=20, std=2, append=True)
    df_d['BBP_EMA20'] = df_d['BBP_20_2.0'].ewm(span=20, adjust=False).mean().fillna(0.5)
    
    df_d['Turnover_Value'] = df_d['Close'] * df_d['Volume']
    df_d['Turnover_Change_Rate'] = (df_d['Turnover_Value'].pct_change() * 100).clip(-300, 300).fillna(0)
    df_d['Turnover_Chg_EMA3'] = df_d['Turnover_Change_Rate'].ewm(span=3, adjust=False).mean()
    
    df_d['Vol_Rank_Score'] = (df_d['Volume'] / df_d['Volume'].rolling(120, min_periods=1).max() * 100).fillna(0)
    
    df_d['Typical_Price'] = (df_d['High'] + df_d['Low'] + df_d['Close']) / 3
    df_d['VWAP'] = (df_d['Typical_Price'] * df_d['Volume']).cumsum() / (df_d['Volume'].cumsum() + 1e-9)
    df_d['VWAP_BIAS'] = ((df_d['Close'] - df_d['VWAP']) / df_d['VWAP']) * 100
    
    df_d['BIAS_25'] = ((df_d['Close'] - df_d['Close'].rolling(25).mean()) / df_d['Close'].rolling(25).mean()) * 100
    df_d['Vol_Price_Efficiency'] = df_d['Turnover_Change_Rate']
"""

if "# --- 17層擴充運算 ---" not in content:
    content = content.replace("    df = df_d.tail(display_days).copy()", extra_calcs + "\n    df = df_d.tail(display_days).copy()")

# 2. 修改 make_subplots
# old: fig = make_subplots(rows=10, ...)
# new: 17 rows
old_subplots = "fig = make_subplots(rows=10, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=[0.06, 0.26, 0.08, 0.12, 0.08, 0.08, 0.08, 0.08, 0.08, 0.08])"
new_subplots = "fig = make_subplots(rows=17, cols=1, shared_xaxes=True, vertical_spacing=0.01, row_heights=[0.04, 0.24, 0.04, 0.06, 0.04, 0.04, 0.04, 0.06, 0.04, 0.05, 0.05, 0.04, 0.05, 0.04, 0.04, 0.04, 0.04])"

# fallback regex if it doesn't match string exactly
import re
content = re.sub(
    r"fig\s*=\s*make_subplots\(rows=\d+,\s*cols=1,\s*shared_xaxes=True,\s*vertical_spacing=[0-9.]+,\s*row_heights=\[[0-9.,\s]+\]\)",
    new_subplots,
    content
)

# 3. 替換繪圖區塊
# Find where row=7 starts (which is currently RSI) and replace everything down to just before fig.update_layout
start_marker = "        fig.add_trace(go.Scatter(x=df.index, y=df['RSI_14'], name=\"RSI\", line=dict(color='#9467bd')), row=7, col=1)"
end_marker = "        # 修正：調整 margin-l (左邊距) 從 10 增加到 50，避免名稱被遮擋"

new_traces = """        # 第 7 層：成交值變化率
        colors_turnover_chg = ['rgba(239, 68, 68, 0.6)' if val >= 0 else 'rgba(34, 197, 94, 0.6)' for val in df['Turnover_Chg_EMA3']]
        fig.add_trace(go.Bar(x=df.index, y=df['Turnover_Chg_EMA3'], name="成交值變化率", marker_color=colors_turnover_chg), row=7, col=1)
        
        # 第 8 層：成交量熱度分數
        vol_scaled = (df['Volume'] - df['Volume'].min()) / (df['Volume'].max() - df['Volume'].min()) * 100
        fig.add_trace(go.Bar(x=df.index, y=vol_scaled, name="成交量", marker_color='rgba(158, 202, 225, 0.5)'), row=8, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['Vol_Rank_Score'], name="熱度分數", line=dict(color='#EAB308', width=2)), row=8, col=1)
        
        # 第 9 層：量價效率指標
        colors_vpe = ['#EF4444' if val >= 0 else '#22C55E' for val in df['Vol_Price_Efficiency']]
        fig.add_trace(go.Bar(x=df.index, y=df['Vol_Price_Efficiency'], name="量價效率", marker_color=colors_vpe), row=9, col=1)
        
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
        fig.add_trace(go.Scatter(x=df.index, y=df['OBV'], name="大戶籌碼代理", line=dict(color='#8B5CF6', width=2)), row=12, col=1)
        
        # 第 13 層：布林極限 %B
        fig.add_trace(go.Scatter(x=df.index, y=df['BBP_20_2.0'], name="%B主線", line=dict(color='#9467bd', width=2)), row=13, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['BBP_EMA20'], name="%B平滑線", line=dict(color='#ffd166', width=2)), row=13, col=1)
        
        # 第 14 層：RSI 動能
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI_14'], name="RSI", line=dict(color='#457b9d', width=2)), row=14, col=1)
        
        # 第 15 層：VWAP 乖離率與 25日乖離線
        fig.add_trace(go.Scatter(x=df.index, y=df['BIAS_25'], name="25日乖離", line=dict(color='#E11D48', width=2)), row=15, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['VWAP_BIAS'], name="VWAP乖離", line=dict(color='#06B6D4', width=2, dash='dot')), row=15, col=1)
        
        # 第 16 層：MFI 熱錢流
        fig.add_trace(go.Scatter(x=df.index, y=df['MFI_14'], name="MFI", fill='tozeroy', fillcolor='rgba(23, 190, 207, 0.2)', line=dict(color='#17becf', width=2)), row=16, col=1)
        
        # 第 17 層：OBV 累積能量
        fig.add_trace(go.Scatter(x=df.index, y=df['OBV'], name="OBV", line=dict(color='#7f7f7f', width=2)), row=17, col=1)
"""

if start_marker in content and "第 17 層" not in content:
    idx_start = content.find(start_marker)
    idx_end = content.find(end_marker)
    content = content[:idx_start] + new_traces + "\n" + content[idx_end:]

# 4. 更新 y 軸標題 (17層)
# Replace all lines from `fig.update_yaxes(title_text="價格", row=2, col=1)` to `st.plotly_chart(fig, ...)`
yaxes_start = "        fig.update_yaxes(title_text=\"價格\", row=2, col=1)"
yaxes_end = "        st.plotly_chart(fig, use_container_width=True, config=lock_config)"

new_yaxes = """        fig.update_yaxes(title_text="價格", row=2, col=1)
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
        
"""

if yaxes_start in content:
    idx_start2 = content.find(yaxes_start)
    idx_end2 = content.find(yaxes_end)
    content = content[:idx_start2] + new_yaxes + content[idx_end2:]

# update height from 1000 to 1800 for 17 layers
content = content.replace("height=1000", "height=1800")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("17-layer migration injection completed.")
