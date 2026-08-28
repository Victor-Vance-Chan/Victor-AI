import re

filepath = r"D:\IDE資料\0.股票系統\手機戰情室\victor.py"

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 替換 Strength_Ratio 計算為 T_Score
# 找到原本的 Strength_Ratio 計算區塊
old_rs_calc = """    # 大盤相對強度 (Strength Ratio)
    if idx_df is not None and not idx_df.empty:
        rs_raw = df_d['Close'] / idx_df['Close']
        df_d['Strength_Ratio'] = rs_raw.pct_change(periods=10) * 100
    else:
        df_d['Strength_Ratio'] = 0.0"""

new_t_calc = """    # 強度比(T) (T_Score) 與 RVOL
    flow_60_mean = df_d['Net_Flow'].abs().rolling(window=60, min_periods=1).mean()
    df_d['T_Score'] = (df_d['Net_Flow'] / (flow_60_mean + 1e-9)).fillna(0.0)
    df_d['RVOL'] = df_d['Volume'] / df_d['Volume'].rolling(20, min_periods=1).mean()"""

if old_rs_calc in content:
    content = content.replace(old_rs_calc, new_t_calc)

# 2. 修改 make_subplots (9 -> 10)
# old: [0.06, 0.28, 0.09, 0.12, 0.09, 0.09, 0.09, 0.09, 0.09]
# new: 10 rows. Total = 1.0. Let's make K-line 0.25, and RVOL 0.08.
old_subplots = "fig = make_subplots(rows=9, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=[0.06, 0.28, 0.09, 0.12, 0.09, 0.09, 0.09, 0.09, 0.09])"
new_subplots = "fig = make_subplots(rows=10, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=[0.06, 0.26, 0.08, 0.12, 0.08, 0.08, 0.08, 0.08, 0.08, 0.08])"

if old_subplots in content:
    content = content.replace(old_subplots, new_subplots)

# 3. Row shift for plotting traces & yaxes (Row 6~9 -> 7~10)
for i in range(9, 5, -1):
    content = content.replace(f"row={i}", f"row={i+1}")

# 4. 替換 plotting trace
old_rs_plot = """        # 第 5 層：強度比 (大盤相對強度)
        colors_rs = ['#DC2626' if x >= 0 else '#22C55E' for x in df['Strength_Ratio']]
        fig.add_trace(go.Bar(x=df.index, y=df['Strength_Ratio'], name="強度比", marker_color=colors_rs), row=5, col=1)"""

new_t_rvol_plot = """        # 第 5 層：強度比(T)
        colors_t = ['#EF4444' if t >= 2.5 else '#F87171' if t >= 1.5 else '#10B981' if t <= -2.5 else '#34D399' if t <= -1.5 else '#CBD5E1' for t in df['T_Score']]
        fig.add_trace(go.Bar(x=df.index, y=df['T_Score'], name="強度比(T)", marker_color=colors_t), row=5, col=1)
        
        # 第 6 層：RVOL 相對量能
        colors_rvol = ['#ff4d4d' if r >= 2.0 else '#ffb33b' if r >= 1.2 else '#a8dadc' for r in df['RVOL']]
        fig.add_trace(go.Bar(x=df.index, y=df['RVOL'], name="RVOL相對量能", marker_color=colors_rvol), row=6, col=1)"""

if old_rs_plot in content:
    content = content.replace(old_rs_plot, new_t_rvol_plot)

# 5. yaxes 調整
yaxes_rsi = "        fig.update_yaxes(title_text=\"RSI\", row=7, col=1)"
yaxes_rvol = """        fig.update_yaxes(title_text="RVOL", row=6, col=1)
        fig.update_yaxes(title_text="RSI", row=7, col=1)"""
if yaxes_rsi in content and "title_text=\"RVOL\"" not in content:
    content = content.replace(yaxes_rsi, yaxes_rvol)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("T_Score and RVOL Injection completed.")
