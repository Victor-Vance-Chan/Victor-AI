file_path = r"D:\IDE資料\0.股票系統\手機戰情室\victor.py"
with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# First, revert the previous bad fix. We know the previous fix prepended "    " to lines NOT starting with 8 spaces.
# It's easier to just regenerate victor.py using the scratch_build.py, but modifying scratch_build.py to indent fig_str properly.

import os
src_file = r"D:\IDE資料\0.股票系統\AI戰情室\pages\1_tech_engine.py"
with open(src_file, "r", encoding="utf-8") as f:
    src_lines = f.readlines()

# Extract the 17 layer fig plotting block
fig_block = []
in_fig = False
for line in src_lines:
    if "specs = [[{}]] * 17" in line:
        in_fig = True
    if in_fig:
        # Add 4 spaces to every line
        if line.strip() != "":
            fig_block.append("    " + line)
        else:
            fig_block.append(line)
        if "fig.update_layout(" in line:
            in_fig = False
            break

# Now read the existing victor.py and replace the tab1 block
new_lines = []
in_tab1 = False
in_tab2 = False
for line in lines:
    if line.startswith("    with tab1:"):
        in_tab1 = True
        new_lines.append(line)
        new_lines.extend(fig_block)
        new_lines.append("\n        st.plotly_chart(fig, use_container_width=True, config=lock_config)\n\n")
        continue
    
    if in_tab1:
        if line.startswith("    with tab2:"):
            in_tab1 = False
            in_tab2 = True
            new_lines.append(line)
        continue
        
    if not in_tab1:
        new_lines.append(line)

with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)
    
print("Fixed indentation completely.")
