import pathlib, re

pages = {
    "dashboard": r"D:\code_v2\app\pages\dashboard.py",
    "roster": r"D:\code_v2\app\pages\roster.py", 
    "prefects": r"D:\code_v2\app\pages\prefects.py",
    "audit": r"D:\code_v2\app\pages\audit.py",
    "leave": r"D:\code_v2\app\pages\leave.py",
}
design = r"D:\code_v2\app\main.py"
sidebar = r"D:\code_v2\app\components\sidebar.py"

print("=== PASS 1: i18n & Dark Mode Diagnosis ===\n")

for name, fp in {**pages, "main (design)": design, "sidebar": sidebar}.items():
    c = pathlib.Path(fp).read_text("utf-8")
    # Count _t() usage
    t_count = c.count("_t(")
    # Count hardcoded English strings (simple heuristic)
    # Find string literals that look like English UI labels
    english_labels = re.findall(r'"([A-Z][a-z]+(?:\s[A-Z][a-z]+){1,5})"', c)
    # Filter out Python keywords and common technical terms
    excluded = {"True","False","None","Prefect","Roster","Weekday","Monday","Tuesday",
                "Wednesday","Thursday","Friday","Saturday","Sunday","January","February",
                "March","April","May","June","July","August","September","October",
                "November","December","Chinese","English","Unknown","Name","Form","Class",
                "Role","Day","Room","Slot","Yes","No","Backup","Restore","System","Import",
                "Export","Generate","Leave","Active","NKJV","Light","Dark","Theme","PDF",
                "CSV","JSON","HTML","F.3","F.4","F.5","AHPs","STUDY_PREFECT",
                "ASSISTANT_HEAD_PREFECT","HEAD_STUDY_PREFECT","ROOM_302","ROOM_303",
                "ROOM_202","Noto Sans TC","PingFang TC","Microsoft JhengHei UI",
                "Segoe UI","Helvetica Neue","Times New Roman","HyperOS","KPI"}
    english_labels = [l for l in english_labels if l not in excluded and len(l) > 8]
    # Count dark: classes
    dark_count = c.count("dark:")
    
    print(f"  {name}: {t_count} _t() calls, {len(english_labels)} hardcoded EN labels, {dark_count} dark: classes")
    if english_labels:
        print(f"    EN labels: {english_labels[:6]}...")
