file_path = r"D:\IDE資料\0.股票系統\手機戰情室\victor.py"
with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    new_lines.append(line)
    if "df = df_d.copy()" in line:
        new_lines.append("""
    # --- 技術指標全面預計算 (確保 17 層圖表不缺欄位) ---
    df['SMA_20'] = ta.sma(df['Close'], length=20)
    df['SMA_25'] = ta.sma(df['Close'], length=25)
    df['SMA_42'] = ta.sma(df['Close'], length=42)
    df['SMA_60'] = ta.sma(df['Close'], length=60)
    df['SMA_240'] = ta.sma(df['Close'], length=240)
    
    bbands = ta.bbands(df['Close'], length=20, std=2.0)
    if bbands is not None:
        df = pd.concat([df, bbands], axis=1)
        if 'BBP_20_2.0' in df.columns:
            df['BBP_EMA20'] = ta.ema(df['BBP_20_2.0'], length=20)
    else:
        df['BBU_20_2.0'], df['BBL_20_2.0'], df['BBP_20_2.0'], df['BBP_EMA20'] = np.nan, np.nan, np.nan, np.nan

    df['BIAS_25'] = ((df['Close'] - df['SMA_25']) / df['SMA_25']) * 100

    df['Typical_Price'] = (df['High'] + df['Low'] + df['Close']) / 3
    df['VWAP'] = (df['Typical_Price'] * df['Volume']).cumsum() / (df['Volume'].cumsum() + 1e-9)
    df['VWAP_BIAS'] = ((df['Close'] - df['VWAP']) / df['VWAP']) * 100

    max_vol_idx = df['Volume'].idxmax()
    df['AVWAP'] = np.nan
    if pd.notna(max_vol_idx):
        mask_a = df.index >= max_vol_idx
        if mask_a.any():
            vol_post = df.loc[mask_a, 'Volume']
            tp_post = df.loc[mask_a, 'Typical_Price']
            df.loc[mask_a, 'AVWAP'] = (tp_post * vol_post).cumsum() / (vol_post.cumsum() + 1e-9)

    df['RSI_14'] = ta.rsi(df['Close'], length=14)
    macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
    if macd is not None:
        df = pd.concat([df, macd], axis=1)
    df['MACD_raw'] = df['MACD_12_26_9'] if 'MACD_12_26_9' in df.columns else np.nan
    df['MACDh_raw'] = df['MACDh_12_26_9'] if 'MACDh_12_26_9' in df.columns else np.nan
    df['MACDs_raw'] = df['MACDs_12_26_9'] if 'MACDs_12_26_9' in df.columns else np.nan

    df['OBV'] = ta.obv(df['Close'], df['Volume'])
    df['MFI_14'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)

    df['RVOL'] = df['Volume'] / df['Volume'].rolling(20, min_periods=1).mean()
    df['Turnover'] = df['Close'] * df['Volume']
    df['Turnover_Chg'] = df['Turnover'].pct_change() * 100
    df['Turnover_Chg_EMA3'] = ta.ema(df['Turnover_Chg'], length=3).fillna(0)

    body_pct = (df['Close'] - df['Open']) / df['Close'].replace(0, 1e-9)
    df['VPE_Base'] = body_pct / (df['High'] - df['Low']).replace(0, 1e-9) * df['Close']
    df['Vol_Price_Efficiency'] = (df['VPE_Base'] * df['RVOL'] * 100).clip(-300, 300).fillna(0)

    vol_rank = df['Volume'].rolling(60).apply(lambda x: pd.Series(x).rank().iloc[-1] / len(x) * 100 if len(x)>0 else 50)
    df['Vol_Rank_Score'] = vol_rank.fillna(50)
""")

with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)
print("Injected indicators successfully.")
