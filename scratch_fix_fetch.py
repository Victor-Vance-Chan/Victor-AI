file_path = r"D:\IDE資料\0.股票系統\手機戰情室\victor.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

import re

# We want to replace everything from "def fetch_shareholder_history(sid):"
# up to "@st.cache_data(ttl=300)"
pattern = re.compile(r"def fetch_shareholder_history\(sid\):.*?@st\.cache_data\(ttl=300\)", re.DOTALL)

replacement = """def fetch_shareholder_history(sid):
    cache_file = os.path.join(CACHE_DIR, f"shareholder_processed_{sid}.json")
    if os.path.exists(cache_file):
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(cache_file))
            if (datetime.now() - mtime).days < 7:
                df = pd.read_json(cache_file)
                if not df.empty:
                    return df
        except Exception:
            pass

    def parse_twsthr_html(html_text):
        try:
            import numpy as np
            dfs = pd.read_html(html_text)
            if len(dfs) >= 14:
                df_t9 = dfs[9].copy()
                df_t9 = df_t9.dropna(subset=[2])
                df_t9 = df_t9[df_t9[2] != "資料日期"]
                df_t9 = df_t9[df_t9[2] != "成交日"]

                df_t9_clean = pd.DataFrame()
                df_t9_clean["date"] = df_t9[2].astype(str)
                df_t9_clean["whale_1000"] = df_t9[13].astype(float)
                df_t9_clean["whale_100"] = df_t9[7].astype(float)
                df_t9_clean["total_people"] = df_t9[4].astype(int)

                df_t13_clean = pd.DataFrame()
                try:
                    df_t13 = dfs[13].copy()
                    df_t13 = df_t13.dropna(subset=[2])
                    df_t13 = df_t13[df_t13[2] != "資料日期"]
                    
                    df_t13_clean["date"] = df_t13[2].astype(str)
                    retail_cols = [3, 4, 5, 6, 7, 8, 9, 10]
                    df_t13_clean["retail_50"] = df_t13[retail_cols].astype(float).sum(axis=1)
                    df_t13_clean["retail_10"] = df_t13[[3, 4, 5]].astype(float).sum(axis=1)
                except Exception:
                    df_t13_clean["date"] = df_t9_clean["date"]
                    df_t13_clean["retail_50"] = np.nan
                    df_t13_clean["retail_10"] = np.nan

                df_merged = pd.merge(df_t9_clean, df_t13_clean, on="date", how="left")
                df_merged = df_merged.sort_values("date")
                df_merged["divergence"] = (df_merged["whale_1000"] - df_merged["retail_50"]).fillna(0.0)

                def format_date(d_str):
                    if len(d_str) == 8:
                        return f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:]}"
                    return d_str
                df_merged["date"] = df_merged["date"].apply(format_date)
                return df_merged
        except Exception:
            pass
        return pd.DataFrame()

    url_norway = f"https://norway.twsthr.info/StockHolders.aspx?stock={sid}"
    url_primary = f"https://twsthr.info/StockHolders.aspx?stock={sid}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        res = requests.get(url_norway, headers=headers, timeout=8)
        if res.status_code == 200:
            df_res = parse_twsthr_html(res.text)
            if not df_res.empty:
                try: df_res.to_json(cache_file, orient="records", force_ascii=False)
                except: pass
                return df_res
    except: pass

    try:
        res = requests.get(url_primary, headers=headers, timeout=8)
        if res.status_code == 200:
            df_res = parse_twsthr_html(res.text)
            if not df_res.empty:
                try: df_res.to_json(cache_file, orient="records", force_ascii=False)
                except: pass
                return df_res
    except: pass

    if os.path.exists(cache_file):
        try:
            df_cached = pd.read_json(cache_file)
            if not df_cached.empty:
                return df_cached
        except: pass
    return pd.DataFrame()

@st.cache_data(ttl=300)"""

new_content = pattern.sub(replacement, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(new_content)
print("fetch_shareholder_history fixed successfully.")
