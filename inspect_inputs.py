from bs4 import BeautifulSoup

with open('gem_source_fetch.html', encoding='utf-8') as f:
    html = f.read()

import re
matches = [m.start() for m in re.finditer('window.param', html, re.IGNORECASE)]
print(f"Found {len(matches)} occurrences of 'window.param'")
for m in matches[:5]:
    print("Context:", html[max(0, m-200):min(len(html), m+400)].strip().replace('\n', ' '))
