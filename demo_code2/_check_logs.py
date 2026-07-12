import pathlib, urllib.request, time

log = pathlib.Path(r"D:\code_v2\logs\app.log")
before = log.read_text("utf-8") if log.exists() else ""

try:
    r = urllib.request.urlopen("http://localhost:8080/", timeout=5)
    rid = r.headers.get("X-Request-ID", "N/A")
    print(f"Request: HTTP {r.status}, X-Request-ID: {rid[:30]}...")
except Exception as e:
    print(f"Request: {type(e).__name__}")

time.sleep(0.5)

after = log.read_text("utf-8")
new = [l for l in after.split("\n") if l.strip() and l not in before.split("\n")]
if new:
    print(f"\nNew log entries ({len(new)}):")
    for l in new:
        print(f"  {l[:150]}")
else:
    print("\nNo new entries - app may need restart")

print(f"\nLog location: {log}")
print(f"Log size: {log.stat().st_size} bytes")
