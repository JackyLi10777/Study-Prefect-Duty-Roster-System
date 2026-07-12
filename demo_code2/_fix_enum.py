import pathlib
p = pathlib.Path(r'D:\code_v2\app\models\enums.py')
c = p.read_text('utf-8')
old = '    @property\n    def is_ahp(self) -> bool:\n        \"\"\"AHP can be assigned to the exclusive AHP duty post.\"\"\"\n        return self == Role.ASSISTANT_HEAD_PREFECT'
new = '    @property\n    def display(self) -> str:\n        \"\"\"Return display name (English).\"\"\"\n        return self.value\n\n    @property\n    def display_zh(self) -> str:\n        \"\"\"Return Chinese display name.\"\"\"\n        mapping = {\n            \"Head Study Prefect\": \"\u9996\u5e2d\u5b78\u7fd2\u98a8\u7d00\",\n            \"Assistant Head Study Prefect\": \"\u52a9\u7406\u9996\u5e2d\u5b78\u7fd2\u98a8\u7d00\",\n            \"Study Prefect\": \"\u5b78\u7fd2\u98a8\u7d00\",\n        }\n        return mapping.get(self.value, self.value)\n\n    @property\n    def is_ahp(self) -> bool:\n        \"\"\"AHP can be assigned to the exclusive AHP duty post.\"\"\"\n        return self == Role.ASSISTANT_HEAD_PREFECT'
if old in c:
    c = c.replace(old, new)
    p.write_text(c, 'utf-8')
    print('enums.py: display + display_zh added')
else:
    print('Pattern NOT FOUND')
