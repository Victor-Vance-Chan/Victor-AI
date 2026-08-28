import re

src_file = r"D:\IDE資料\0.股票系統\AI戰情室\pages\1_tech_engine.py"
with open(src_file, "r", encoding="utf-8") as f:
    src_lines = f.readlines()

ui_block = []
capture = False
for i, line in enumerate(src_lines):
    if "curr = df.iloc[-1]" in line and "ma_20 =" in src_lines[i+2]:
        capture = True
    
    if capture:
        if "st.markdown(\"<div style='margin-top: 30px;'></div>\"" in line:
            ui_block.append(line)
            break
        # fix indentation
        if line.startswith("    "):
            ui_block.append("    " + line)
        else:
            ui_block.append("        " + line)

ui_block_str = "".join(ui_block)

tgt_file = r"D:\IDE資料\0.股票系統\手機戰情室\victor.py"
with open(tgt_file, "r", encoding="utf-8") as f:
    tgt_lines = f.readlines()

new_lines = []
for line in tgt_lines:
    new_lines.append(line)
    if line.startswith("    with tab1:"):
        new_lines.append(ui_block_str)

with open(tgt_file, "w", encoding="utf-8") as f:
    f.writelines(new_lines)
    
print("UI cards injected successfully.")
