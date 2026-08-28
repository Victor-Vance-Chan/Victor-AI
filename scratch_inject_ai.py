import re

src_file = r"D:\IDE資料\0.股票系統\AI戰情室\pages\1_tech_engine.py"
with open(src_file, "r", encoding="utf-8") as f:
    src_lines = f.readlines()

ai_logic = []
capture = False
for line in src_lines:
    if "col_ai, col_t1, col_t2, _ = st.columns" in line:
        capture = True
    if capture:
        if "st.plotly_chart(fig, use_container_width=True" in line:
            break
        # fix indentation (it was indented 12 spaces in 1_tech_engine, we need 8 spaces in victor)
        if line.startswith("            "):
            ai_logic.append(line[4:])
        elif line.startswith("        "):
            ai_logic.append(line[4:])
        else:
            ai_logic.append(line)

ai_logic_str = "".join(ai_logic)

tgt_file = r"D:\IDE資料\0.股票系統\手機戰情室\victor.py"
with open(tgt_file, "r", encoding="utf-8") as f:
    tgt_content = f.read()

# Replace the part in victor.py
# Find "        fig.update_layout(height=2500..." up to "st.plotly_chart(fig..."
import re
pattern = re.compile(r"(        fig\.update_layout\(height=2500.*?\n)(        st\.plotly_chart\(fig, use_container_width=True, config=lock_config\))", re.DOTALL)

def replacer(match):
    return match.group(1) + ai_logic_str + match.group(2)

new_content = pattern.sub(replacer, tgt_content)

with open(tgt_file, "w", encoding="utf-8") as f:
    f.write(new_content)
    
print("AI Logic injected successfully.")
