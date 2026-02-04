import os
import datetime
from bs4 import BeautifulSoup
from markdownify import markdownify as md
import re # <--- MAKE SURE TO ADD THIS IMPORT AT THE TOP OF THE FILE

def load_html(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()

# --- HELPER: METADATA GENERATOR ---
# --- IMPROVED METADATA GENERATOR ---
def generate_frontmatter(title, content, url="Local File"):
    date_str = datetime.date.today().strftime("%Y-%m-%d")
    
    # Base tag
    tags = ["ai-chat"]
    content_lower = content.lower()
    
    # 1. Stricter Python Check
    # Only tag python if we see "def ", "import ", or "```python"
    if "```python" in content_lower or "def " in content_lower or "import " in content_lower:
        tags.append("python")

    # 2. Stricter C++ Check
    # Check for includes, std::, or code blocks
    if "```cpp" in content_lower or "```c++" in content_lower or "#include" in content_lower or "std::" in content_lower:
        tags.append("cpp")

    # 3. JavaScript
    if "```javascript" in content_lower or "```js" in content_lower or "console.log" in content_lower:
        tags.append("javascript")

    # 4. Remove duplicates just in case
    tags = list(set(tags))
    
    tag_str = ", ".join(tags)
    
    return f"""---
title: "{title}"
date: {date_str}
tags: [{tag_str}]
source: "{url}"
---

"""

# --- LANGUAGE DETECTOR ---
# --- UPGRADED LANGUAGE DETECTOR ---
# --- UPGRADED LANGUAGE DETECTOR (PRIORITY: LABEL > CONTENT) ---
def get_code_language(el):
    """
    1. Checks HTML classes.
    2. Proximity Search: Finds the closest text ABOVE the block (ignoring nesting).
    3. Syntax Analysis: Checks for C++ specific patterns in the code.
    """
    # 1. HTML Class Check
    el_classes = el.get("class", []) or []
    parent_classes = el.parent.get("class", []) if el.parent else []
    for c in el_classes + parent_classes:
        if c.startswith("language-"): return c.replace("language-", "")

    # 2. PROXIMITY CHECK (The Fix)
    # Instead of siblings, we search the entire document backwards from this element
    # to find the closest header or paragraph.
    search_limit = 3  # Look at the last 3 elements found
    found_elements = el.parent.find_all_previous(['p', 'div', 'h3', 'h4', 'li'], limit=search_limit)
    
    for prev in found_elements:
        text = prev.get_text(strip=True).lower()
        
        # If the text is huge (like a whole paragraph), check the LAST sentence
        if len(text) > 100:
            text = text[-50:] # Only look at the end
            
        # Explicit Labels
        if "c++" in text or "cpp" in text: return "cpp"
        if "python" in text: return "python"
        if "javascript" in text or "js code" in text: return "javascript"
        if "java" in text and "script" not in text: return "java"
        if "sql" in text: return "sql"
        if "bash" in text: return "bash"

    # 3. CONTENT CHECK (Syntax Analysis)
    code_content = el.get_text()
    
    # C++ Specifics
    if "#include" in code_content or "std::" in code_content: return "cpp"
    if "cout" in code_content and "<<" in code_content: return "cpp"
    
    # Regex for C-style functions: "int add(int a) {"
    # We use re.DOTALL to handle newlines correctly
    if re.search(r'\b(int|void|double|float|bool|char)\s+\w+\s*\(.*?\)\s*\{', code_content, re.DOTALL):
        return "cpp"
        
    # Python Specifics
    if "def " in code_content and ":" in code_content: return "python"
    if "import " in code_content and "from " in code_content: return "python"

    return "" # No guess

# --- MAIN LOGIC ---
def extract_response(file_path, search_phrase):
    raw_html = load_html(file_path)
    soup = BeautifulSoup(raw_html, "html.parser")

    # 1. Find User Question
    user_msg_node = soup.find(string=lambda text: text and search_phrase.lower() in text.lower())
    if not user_msg_node:
        return None, "❌ Phrase not found."

    # 2. Find Container
    container = user_msg_node.parent
    while container.name not in ['div', 'li', 'article'] and container.parent:
        container = container.parent

    # 3. Find AI Response
    ai_response_node = None
    for sibling in container.find_all_next("div"):
        if sibling == container: continue
        if len(sibling.get_text(strip=True)) > 20:
            ai_response_node = sibling
            break
    
    if not ai_response_node:
        return None, "⚠️ Found question, but couldn't isolate answer."

    # 4. Cleanup
    for tag in ai_response_node(['button', 'svg', 'img']):
        tag.decompose()

    # 5. Convert (RETURN RAW MARKDOWN ONLY)
    markdown_text = md(
        str(ai_response_node), 
        heading_style="ATX", 
        code_language_callback=get_code_language
    )
    
    # REMOVED: generate_frontmatter call here. We do it in save_to_file now.
    return markdown_text, "✅ Success"

# --- SMART SAVE FUNCTION ---
def save_to_file(content, filename, title_for_header, mode="w"):
    os.makedirs("Exported_Notes", exist_ok=True)
    full_path = os.path.join("Exported_Notes", filename)
    
    # Check if file is new (doesn't exist) or we are overwriting
    is_new_file = not os.path.exists(full_path) or mode == "w"
    
    with open(full_path, mode, encoding="utf-8") as f:
        if is_new_file:
            # Case 1: New File -> Add YAML Frontmatter at the very top
            header = generate_frontmatter(title_for_header, content)
            # Add the actual header title too
            f.write(header + f"# {title_for_header}\n\n" + content)
        else:
            # Case 2: Appending -> Just add a separator and the new Question Title
            f.write(f"\n\n---\n\n# {title_for_header}\n\n" + content)
        
    return full_path