file_path = r"D:\IDE資料\0.股票系統\手機戰情室\victor.py"
with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
in_ui = False
for line in lines:
    if "curr = df.iloc[-1]" in line and "ma_20 =" in lines[lines.index(line)+2]:
        in_ui = True
    
    if in_ui:
        # The line currently has 4 or 8 spaces. We want it to be inside `with tab1:`, so it should have +4 spaces.
        # But wait, let's just add 4 spaces to any line that starts with spaces, up to the end of the UI block.
        if line.startswith("    "):
            new_lines.append("    " + line)
        else:
            new_lines.append("        " + line)
            
        if "st.markdown(\"<div style='margin-top: 30px;'></div>\"" in line:
            in_ui = False
    else:
        new_lines.append(line)

with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)
print("Indentation fixed.")
