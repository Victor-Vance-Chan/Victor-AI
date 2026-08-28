import re

filepath = r"D:\IDE資料\0.股票系統\手機戰情室\victor.py"

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 注入大盤下載函數
index_loader = """@st.cache_data(ttl=300)
def load_index_data():
    try:
        idx = yf.download("^TWII", period="2y", interval="1d", auto_adjust=False, progress=False)
        if isinstance(idx.columns, pd.MultiIndex):
            idx.columns = idx.columns.get_level_values(0)
        return idx
    except:
        return None

"""
if "def load_index_data" not in content:
    content = content.replace("@st.cache_data(ttl=300)\ndef load_stock_data_safe(sid):", index_loader + "@st.cache_data(ttl=300)\ndef load_stock_data_safe(sid):")

# 2. 注入資料獲取與指標計算
fetch_idx = """raw_df, actual_ticker = load_stock_data_safe(stock_id)
idx_df = load_index_data()"""
if "idx_df = load_index_data()" not in content:
    content = content.replace("raw_df, actual_ticker = load_stock_data_safe(stock_id)", fetch_idx)

calc_rs = """    # 大盤相對強度 (Strength Ratio)
    if idx_df is not None and not idx_df.empty:
        rs_raw = df_d['Close'] / idx_df['Close']
        df_d['Strength_Ratio'] = rs_raw.pct_change(periods=10) * 100
    else:
        df_d['Strength_Ratio'] = 0.0
"""
if "df_d['Strength_Ratio']" not in content:
    content = content.replace("    df = df_d.tail(display_days).copy()", calc_rs + "\n    df = df_d.tail(display_days).copy()")


# 3. 更新 make_subplots
# 注意：之前 victor.py 的 make_subplots 在多次修改後可能長不一樣，我們用正則找出它並替換
content = re.sub(
    r"fig\s*=\s*make_subplots\(rows=\d+,\s*cols=1,\s*shared_xaxes=True,\s*vertical_spacing=[0-9.]+,\s*row_heights=\[[0-9.,\s]+\]\)",
    "fig = make_subplots(rows=9, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=[0.06, 0.28, 0.09, 0.12, 0.09, 0.09, 0.09, 0.09, 0.09])",
    content
)

# 4. Row shift for plotting traces & yaxes (Row 5~8 -> 6~9)
for i in range(8, 4, -1):
    content = content.replace(f"row={i}", f"row={i+1}")

# 5. 在 RSI trace 之前注入強度比
rsi_trace = "        fig.add_trace(go.Scatter(x=df.index, y=df['RSI_14'], name=\"RSI\", line=dict(color='#9467bd')), row=6, col=1)"
rs_plot = """        # 第 5 層：強度比 (大盤相對強度)
        colors_rs = ['#DC2626' if x >= 0 else '#22C55E' for x in df['Strength_Ratio']]
        fig.add_trace(go.Bar(x=df.index, y=df['Strength_Ratio'], name="強度比", marker_color=colors_rs), row=5, col=1)
        fig.add_hline(y=0, line_dash="solid", line_color="black", line_width=1, row=5, col=1)
        
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI_14'], name="RSI", line=dict(color='#9467bd')), row=6, col=1)"""

if rsi_trace in content and "強度比" not in content:
    content = content.replace(rsi_trace, rs_plot)

# 6. 更新 y 軸標題
yaxes_rsi = "        fig.update_yaxes(title_text=\"RSI\", row=6, col=1)"
yaxes_rs = """        fig.update_yaxes(title_text="強度比", row=5, col=1)
        fig.update_yaxes(title_text="RSI", row=6, col=1)"""
if yaxes_rsi in content and "title_text=\"強度比\"" not in content:
    content = content.replace(yaxes_rsi, yaxes_rs)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Strength Ratio Injection completed.")
