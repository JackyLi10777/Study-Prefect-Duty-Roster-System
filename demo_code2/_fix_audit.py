import pathlib
p = pathlib.Path(r"D:\code_v2\app\pages\audit.py")
c = p.read_text("utf-8")
old = '"Track system actions: roster generation, leave adjustment, data imports."'
new = '_t("\u8ffd\u8e64\u7cfb\u7d71\u64cd\u4f5c\uff1a\u503c\u73ed\u8868\u751f\u6210\u3001\u8acb\u5047\u8abf\u6574\u3001\u6578\u64da\u532f\u5165\u3002", "Track system actions: roster generation, leave adjustment, data imports.")'
c = c.replace(old, new)
old2 = '"No audit records yet"'
new2 = '_t("\u66ab\u7121\u5be9\u8a08\u8a18\u9304", "No audit records yet")'
c = c.replace(old2, new2)
old3 = '"Records appear automatically after roster generation, leave adjustments, etc."'
new3 = '_t("\u503c\u73ed\u8868\u751f\u6210\u3001\u8acb\u5047\u8abf\u6574\u7b49\u64cd\u4f5c\u5f8c\u8a18\u9304\u6703\u81ea\u52d5\u51fa\u73fe\u3002", "Records appear automatically after roster generation, leave adjustments, etc.")'
c = c.replace(old3, new3)
p.write_text(c, "utf-8")
print("Audit log i18n done")
