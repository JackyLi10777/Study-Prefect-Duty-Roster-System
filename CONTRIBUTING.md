# Contributing to Sing Yin Study Prefect Duty Roster System

## Safe Editing Practices

To avoid encoding and indentation issues that have historically caused regressions, please follow these guidelines:

### File Encoding

- **Always save files as UTF-8 without BOM.** This project uses UTF-8 encoding throughout.
- **Use Python or Node.js for editing files containing Chinese characters.** PowerShell Set-Content and Get-Content can silently corrupt UTF-8 files. Prefer:
  - [System.IO.File]::ReadAllText(path, [System.Text.Encoding]::UTF8) for reading
  - [System.IO.File]::WriteAllText(path, content, [System.Text.Encoding]::UTF8) for writing
- **Never use PowerShell heredocs (@''@) to pass Python code containing Chinese characters.** The terminal encoding (GBK on Chinese Windows) will corrupt non-ASCII bytes.

### Line Endings

- The project uses **CRLF (\r\n)** line endings on Windows. When using Node.js or Python to edit files, be aware that \n-only patterns will not match \r\n content.
- Use content.split('\n') and lines.join('\n') rather than binary string replacement when working with line-based structures.
- When using str.replace(), match the actual line endings: use \r\n for CRLF files.

### Safe String Replacement (Chinese Characters)

When replacing strings containing Chinese characters:

1. **Python (recommended):** Use Unicode escape sequences:
   `python
   zh_var = '\u9996\u5e2d\u5c0e\u5b78\u98a8\u7d00'  # 首席導學風紀
   text = text.replace(zh_var, 'New Value')
   `

2. **PowerShell:** Use Unicode code points:
   `powershell
    = [char]0x9996 + [char]0x5E2D + [char]0x5C0E  # partial
    = .Replace(, 'New Value')
   `

3. **Node.js:** Use s.readFileSync(path, 'utf8') and s.writeFileSync(path, content, 'utf8'). This handles UTF-8 reliably.

### Indentation

- The project uses **4 spaces** for Python indentation (no tabs).
- When editing pp.py, be especially careful with with tab_view: and similar context manager blocks. The indentation of these blocks relative to function definitions is critical.
- After editing, always run python -m py_compile app.py to check for syntax errors before running tests.

### Test Before Push

Always run the full test suite before committing:

`ash
python -m pytest tests/ -q
python -m py_compile app.py
`

The expected result is **36 passed**.
