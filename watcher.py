import time
import os
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from converter import extract_response, save_to_file

# --- CONFIGURATION ---
DOWNLOADS_PATH = r"C:\Users\Asus\Downloads" # Update this if needed

# Global variable to store the merge filename (if selected)
MERGE_TARGET = None

def process_file(file_path):
    print(f"\n📄 Opened file: {os.path.basename(file_path)}")
    
    if not os.path.exists(file_path):
        print("❌ Error: File not found.")
        return

    while True:
        print("\n------------------------------------------------")
        phrase = input("👉 Enter phrase to extract (or ENTER to finish): ")
        
        if not phrase.strip():
            print("✅ Finished processing this file.")
            break
            
        print(f"   🔍 Hunting for '{phrase}'...")
        md_content, status = extract_response(file_path, phrase)
        
        if "Success" in status:
            if MERGE_TARGET:
                # Pass 'phrase' as the title argument
                saved_path = save_to_file(md_content, MERGE_TARGET, phrase, mode="a")
                print(f"   📎 Appended to: {MERGE_TARGET}")
            else:
                filename = phrase.replace(" ", "_").strip()[:30] + ".md"
                # Pass 'phrase' here too
                saved_path = save_to_file(md_content, filename, phrase, mode="w")
                print(f"   🎉 Saved new file: {filename}")
        else:
            print(f"   {status}")

class NewFileHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.src_path.endswith(".html") or event.src_path.endswith(".htm"):
            print(f"\n👀 Detected new file: {os.path.basename(event.src_path)}")
            time.sleep(1)
            process_file(event.src_path)
            print("Listening for new files...")

def main():
    global MERGE_TARGET
    
    print("==========================================")
    print("   AI CHAT TO MARKDOWN - v2.0")
    print("==========================================")
    
    # --- ASK FOR MERGE PREFERENCE ---
    print("Do you want to merge all notes into ONE file?")
    merge_choice = input("Enter filename (e.g. 'MyNotes.md') or press ENTER for separate files: ").strip()
    
    if merge_choice:
        if not merge_choice.endswith(".md"): merge_choice += ".md"
        MERGE_TARGET = merge_choice
        print(f"🔄 MERGE MODE ACTIVE: All notes will go into '{MERGE_TARGET}'")
    else:
        print("📂 INDIVIDUAL MODE: Each question will be a separate file.")
        
    print("\n1. 🔴 Live Watch Mode")
    print("2. 📂 Manual Mode")
    
    choice = input("\nEnter choice (1 or 2): ").strip()

    if choice == "1":
        event_handler = NewFileHandler()
        observer = Observer()
        observer.schedule(event_handler, path=DOWNLOADS_PATH, recursive=False)
        print(f"\n🚀 Watchdog running on: {DOWNLOADS_PATH}")
        observer.start()
        try:
            while True: time.sleep(1)
        except KeyboardInterrupt: observer.stop()
        observer.join()

    elif choice == "2":
        filename = input("Enter HTML filename (in Downloads): ").strip()
        full_path = os.path.join(DOWNLOADS_PATH, filename)
        process_file(full_path)

if __name__ == "__main__":
    main()