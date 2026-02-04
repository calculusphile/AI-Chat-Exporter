import os
import datetime  # <--- NEW IMPORT
from bs4 import BeautifulSoup
from markdownify import markdownify as md

def load_html(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()

# --- NEW FUNCTION: METADATA GENERATOR ---
def generate_frontmatter(title, content, url="Local File"):
    """
    Creates a YAML block for Obsidian/Notion compatibility.
    """
    date_str = datetime.date.today().strftime("%Y-%m-%d")
    
    # Simple auto-tagging logic based on keywords
    tags = ["ai-chat"]
    content_lower = content.lower()
    
    if "python" in content_lower or "def " in content_lower: tags.append("python")
    if "javascript" in content_lower or "function " in content_lower: tags.append("javascript")
    if "c++" in content_lower or "std::" in content_lower: tags.append("cpp")
    if "sql" in content_lower: tags.append("database")
    if "html" in content_lower: tags.append("web-dev")
    
    tag_str = ", ".join(tags)
    
    # The --- block is standard YAML syntax used by Obsidian/Jekyll
    frontmatter = f"""---
title: "{title}"
date: {date_str}
tags: [{tag_str}]
source: "{url}"
---

"""
    return frontmatter + content

# --- LANGUAGE DETECTOR (From previous step) ---
def get_code_language(el):
    """
    Tries to find the language for syntax highlighting.
    """
    el_classes = el.get("class", []) or []
    parent_classes = el.parent.get("class", []) if el.parent else []
    
    # Strategy A: Check for classes
    all_classes = el_classes + parent_classes
    for c in all_classes:
        if c.startswith("language-"): return c.replace("language-", "")
        if c.startswith("lang-"): return c.replace("lang-", "")

    # Strategy B: Check Header text
    found_lang = ""
    if el.parent and el.parent.name == 'pre':
        prev_node = el.parent.find_previous_sibling()
        if prev_node:
            text = prev_node.get_text(strip=True).lower()
            clean_text = text.replace("copy code", "").replace("copy", "").strip()
            
            valid_langs = ["python", "cpp", "c++", "java", "javascript", "js", "html", "css", "sql", "bash", "json"]
            
            if clean_text in valid_langs:
                found_lang = clean_text
            elif any(lang in clean_text for lang in valid_langs) and len(clean_text) < 15:
                for lang in valid_langs:
                    if lang in clean_text:
                        found_lang = lang
                        break

    if found_lang:
        if found_lang == "c++": return "cpp"
        if found_lang == "js": return "javascript"
        return found_lang

    return "python" # Default fallback

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

    # 5. Convert
    markdown_text = md(
        str(ai_response_node), 
        heading_style="ATX", 
        code_language_callback=get_code_language
    )
    
    # --- NEW STEP: Add the Metadata Header ---
    final_output = generate_frontmatter(search_phrase, markdown_text)
    
    return final_output, "✅ Success"

def save_to_file(content, filename):
    os.makedirs("Exported_Notes", exist_ok=True)
    full_path = os.path.join("Exported_Notes", filename)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
    return full_path