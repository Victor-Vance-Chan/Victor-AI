import re

filepath = r"D:\IDE資料\0.股票系統\手機戰情室\victor.py"

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 注入 Chip_Concentration 計算邏輯
calc_injection = """    df_d['nf_QV_Score'] = (df_d['NF_Risk'] * 0.4) + (df_d['VPE_Risk'] * 0.4) + (df_d['Pos_Risk'] * 0.2)
    # ------------------------------
    
    # 籌碼集中度 (代理指標：20日淨流 / 20日總量)
    vol_20_sum = df_d['Volume'].rolling(window=20, min_periods=1).sum().replace(0, 1e-9)
    net_flow_20_sum = df_d['Net_Flow'].rolling(window=20, min_periods=1).sum()
    df_d['Chip_Concentration'] = (net_flow_20_sum / vol_20_sum) * 100
"""

if "df_d['Chip_Concentration']" not in content:
    content = content.replace("    df_d['nf_QV_Score'] = (df_d['NF_Risk'] * 0.4) + (df_d['VPE_Risk'] * 0.4) + (df_d['Pos_Risk'] * 0.2)\n    # ------------------------------", calc_injection)

# 2. 修改 make_subplots
old_subplots = "fig = make_subplots(rows=7, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=[0.08, 0.35, 0.13, 0.11, 0.11, 0.11, 0.11])"
new_subplots = "fig = make_subplots(rows=8, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=[0.08, 0.35, 0.1, 0.1, 0.1, 0.1, 0.09, 0.08])"
if old_subplots in content:
    content = content.replace(old_subplots, new_subplots)

# 3. 處理 add_trace (Row shift)
# Net_Flow is row=3. We need to insert Chip_Concentration at row=4.
# So existing row=4~7 must become row=5~8.
for i in range(7, 3, -1):
    content = content.replace(f"row={i}", f"row={i+1}")

# 4. 在 NetFlow trace 之後，插入 Chip_Concentration 的繪圖
netflow_trace = "        fig.add_trace(go.Bar(x=df.index, y=df['Net_Flow'], name=\"資金流\", marker_color=colors), row=3, col=1)"
chip_plot_injection = """        fig.add_trace(go.Bar(x=df.index, y=df['Net_Flow'], name="資金流", marker_color=colors), row=3, col=1)
        
        # 籌碼集中度 (面積圖)
        colors_chip = ['#1f77b4' if x >= 0 else '#d62728' for x in df['Chip_Concentration']]
        fig.add_trace(go.Scatter(x=df.index, y=df['Chip_Concentration'], name="集中度", fill='tozeroy', line=dict(color='rgba(255,255,255,0)')), row=4, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df['Chip_Concentration'], name="集中度柱狀", marker_color=colors_chip, showlegend=False), row=4, col=1)
        fig.add_hline(y=0, line_dash="solid", line_color="black", line_width=1, row=4, col=1)"""

if netflow_trace in content and "集中度" not in content:
    content = content.replace(netflow_trace, chip_plot_injection)

# 5. 更新 Y 軸標題
yaxes_3 = "        fig.update_yaxes(title_text=\"淨流\", row=3, col=1)"
yaxes_injection = """        fig.update_yaxes(title_text="淨流", row=3, col=1)
        fig.update_yaxes(title_text="集中度", row=4, col=1)"""
if yaxes_3 in content and "title_text=\"集中度\"" not in content:
    content = content.replace(yaxes_3, yaxes_injection)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Chip Concentration Injection completed.")
