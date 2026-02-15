"""Test _extract_chat_title — especially Gemini sidebar active-item detection."""
from bs4 import BeautifulSoup
from converter import _extract_chat_title

# Test 1: Gemini with active sidebar chat (aria-selected)
html1 = (
    '<html><head><title>Google Gemini</title></head><body>'
    '<aside>'
    '  <h1>Chats</h1>'
    '  <a href="/c/1">Codeforces Rating Plan</a>'
    '  <a href="/c/2" aria-selected="true" class="selected">'
    "    First Year Student's Academic Reset"
    '  </a>'
    '  <a href="/c/3">Python Decorators</a>'
    '</aside>'
    '<main><p>Chat content here</p></main>'
    '</body></html>'
)
t1 = _extract_chat_title(BeautifulSoup(html1, "html.parser"))
print(f"Test 1 (Gemini sidebar active): {t1!r}")
assert t1 == "First Year Student's Academic Reset", f"FAIL: {t1}"

# Test 2: Gemini with active class only (no aria-selected)
html2 = (
    '<html><head><title>Gemini</title></head><body>'
    '<nav>'
    '  <div class="item">Old Chat</div>'
    '  <div class="item active">Building a Stress Tester</div>'
    '</nav>'
    '<main><p>Content</p></main>'
    '</body></html>'
)
t2 = _extract_chat_title(BeautifulSoup(html2, "html.parser"))
print(f"Test 2 (class=active in nav):   {t2!r}")
assert t2 == "Building a Stress Tester", f"FAIL: {t2}"

# Test 3: <h1>Chats</h1> should NOT become the title
html3 = (
    '<html><head><title>Google Gemini</title></head><body>'
    '<h1>Chats</h1>'
    '<main><p>Content</p></main>'
    '</body></html>'
)
t3 = _extract_chat_title(BeautifulSoup(html3, "html.parser"))
print(f"Test 3 (h1=Chats skipped):      {t3!r}")
assert t3 is None, f"FAIL: {t3}"

# Test 4: ChatGPT title tag still works
html4 = '<html><head><title>Merge Sort Explanation - ChatGPT</title></head><body><main><p>x</p></main></body></html>'
t4 = _extract_chat_title(BeautifulSoup(html4, "html.parser"))
print(f"Test 4 (ChatGPT title tag):     {t4!r}")
assert t4 == "Merge Sort Explanation", f"FAIL: {t4}"

# Test 5: role=complementary with active item
html5 = (
    '<html><head><title>Gemini</title></head><body>'
    '<div role="complementary">'
    '  <a>Some Chat</a>'
    '  <a class="selected">My Important Chat</a>'
    '</div>'
    '<main><p>Content</p></main>'
    '</body></html>'
)
t5 = _extract_chat_title(BeautifulSoup(html5, "html.parser"))
print(f"Test 5 (role=complementary):    {t5!r}")
assert t5 == "My Important Chat", f"FAIL: {t5}"

# Test 6: data-message-author-role fallback
html6 = (
    '<html><head><title>Google Gemini</title></head><body>'
    '<main>'
    '  <div data-message-author-role="user"><p>How do I sort in C++?</p></div>'
    '  <div data-message-author-role="assistant"><p>Use std::sort</p></div>'
    '</main></body></html>'
)
t6 = _extract_chat_title(BeautifulSoup(html6, "html.parser"))
print(f"Test 6 (user msg fallback):     {t6!r}")
assert t6 == "How do I sort in C++", f"FAIL: {t6}"

print("\nALL TESTS PASSED")
