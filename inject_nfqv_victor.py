import re

filepath = r"D:\IDE資料\0.股票系統\手機戰情室\victor.py"

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 注入 NF-QV 計算邏輯
calc_injection = """    df_d['Net_Flow'] = (df_d['Close'].diff() * df_d['Volume'])
    
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
    
    df_d['Pos_Risk'] = np.where(df_d['RSI_14'] < 70, 0, np.clip(((df_d['RSI_14'] - 70) / 15.0) * 100, 0, 100))
    df_d['nf_QV_Score'] = (df_d['NF_Risk'] * 0.4) + (df_d['VPE_Risk'] * 0.4) + (df_d['Pos_Risk'] * 0.2)
    # ------------------------------"""

if "df_d['Net_Flow'] = (df_d['Close'].diff() * df_d['Volume'])" in content and "nf_QV_Score" not in content:
    content = content.replace("    df_d['Net_Flow'] = (df_d['Close'].diff() * df_d['Volume'])", calc_injection)

# 2. 修改 make_subplots
old_subplots = "fig = make_subplots(rows=6, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.35, 0.12, 0.12, 0.12, 0.12, 0.15])"
new_subplots = "fig = make_subplots(rows=7, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=[0.08, 0.35, 0.11, 0.11, 0.11, 0.11, 0.13])"
if old_subplots in content:
    content = content.replace(old_subplots, new_subplots)

# 3. 處理 add_trace (Row shift)
# 我們必須先將現有的 add_trace row=1~6 改為 row=2~7, update_yaxes row=1~6 改為 row=2~7
# 為了避免重複替換 (例如把 6 變 7 又把 7 變 8)，從後面往前取代
for i in range(6, 0, -1):
    content = content.replace(f"row={i}", f"row={i+1}")

# 4. 在 Candlestick trace 前方，插入 NF-QV 的繪圖
candlestick_trace = "        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name=\"K線\"), row=2, col=1)"
nfqv_plot_injection = """        # 第 1 層：NF-QV 風險指標
        colors_nfqv = ['#DC2626' if val >= 80 else '#F59E0B' if val >= 60 else '#22C55E' for val in df['nf_QV_Score']]
        fig.add_trace(go.Bar(x=df.index, y=df['nf_QV_Score'], name="NF-QV風險", marker_color=colors_nfqv), row=1, col=1)
        fig.add_hline(y=80, line_dash="solid", line_color="#DC2626", line_width=1.5, row=1, col=1)
        fig.add_hline(y=60, line_dash="dash", line_color="#F59E0B", line_width=1.5, row=1, col=1)
        
        # 第 2 層主 K 線圖
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線"), row=2, col=1)"""

if candlestick_trace in content and "NF-QV風險" not in content:
    content = content.replace(candlestick_trace, nfqv_plot_injection)

# 5. 更新 Y 軸標題 (插入 row=1 的標題)
yaxes_1 = "        fig.update_yaxes(title_text=\"價格\", row=2, col=1)"
yaxes_injection = """        fig.update_yaxes(title_text="NF-QV", range=[0, 100], row=1, col=1)
        fig.update_yaxes(title_text="價格", row=2, col=1)"""
if yaxes_1 in content and "title_text=\"NF-QV\"" not in content:
    content = content.replace(yaxes_1, yaxes_injection)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Migration completed.")
