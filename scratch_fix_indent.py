file_path = r"D:\IDE資料\0.股票系統\手機戰情室\victor.py"
with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
in_tab1 = False

for line in lines:
    if line.startswith("    with tab1:"):
        in_tab1 = True
        new_lines.append(line)
        continue
        
    if in_tab1:
        # Stop indenting when we reach "    with tab2:"
        if line.startswith("    with tab2:"):
            in_tab1 = False
            new_lines.append(line)
            continue
            
        # Add 4 spaces if the line isn't empty and isn't already indented properly
        if line.strip() != "":
            if not line.startswith("        "):
                # Usually it has 4 spaces, so we add 4 more
                new_lines.append("    " + line)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    else:
        new_lines.append(line)

with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("Fixed indentation.")
