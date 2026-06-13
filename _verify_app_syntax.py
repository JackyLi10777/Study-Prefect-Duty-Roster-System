import ast
import sys
try:
    with open('app.py', 'r', encoding='utf-8') as f:
        src = f.read()
    ast.parse(src)
    print('✅ Syntax OK (ast.parse success) - no SyntaxError')
    sys.exit(0)
except SyntaxError as se:
    print(f'❌ SyntaxError line {se.lineno}: {se.msg}')
    print('Near:', se.text)
    sys.exit(1)
except Exception as ex:
    print('❌ Other error:', type(ex).__name__, str(ex)[:200])
    sys.exit(2)
