import time
import os
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from converter import extract_response, save_to_file

# --- CONFIGURATION ---
# UPDATE THIS PATH to your actual Downloads folder!
DOWNLOADS_PATH = r"C:\Users\Asus\Downloads" 

# --- CORE PROCESSING FUNCTION ---
def process_file(file_path):
    """
    Shared logic to handle the user interaction for a specific file.
    """
    print(f"\n📄 Selected file: {os.path.basename(file_path)}")
    
    # Check if file actually exists
    if not os.path.exists(file_path):
        print("❌ Error: File not found.")
        return

    phrase = input("👉 Enter a unique phrase from the QUESTION you want to extract: ")
    
    if phrase.strip():
        print("Processing...")
        md_content, status = extract_response(file_path, phrase)
        
        if "Success" in status:
            filename = phrase.replace(" ", "_").strip()[:30] + ".md"
            saved_path = save_to_file(md_content, filename)
            print(f"🎉 Saved to: {saved_path}")
        else:
            print(status)
    print("------------------------------------------------")


# --- WATCHER CLASS ---
class NewFileHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.src_path.endswith(".html") or event.src_path.endswith(".htm"):
            print(f"\n👀 Detected new file: {os.path.basename(event.src_path)}")
            time.sleep(1) # Wait for write to finish
            process_file(event.src_path)
            print("Listening for new files...")


# --- MAIN MENU ---
def main():
    print("==========================================")
    print("   AI CHAT TO MARKDOWN CONVERTER v1.0")
    print("==========================================")
    print("1. 🔴 Live Watch Mode (Wait for new downloads)")
    print("2. 📂 Manual Mode (Select existing file)")
    
    choice = input("\nEnter your choice (1 or 2): ").strip()

    if choice == "1":
        # --- START WATCHER ---
        event_handler = NewFileHandler()
        observer = Observer()
        observer.schedule(event_handler, path=DOWNLOADS_PATH, recursive=False)
        
        print(f"\n🚀 Watchdog is running! Monitoring: {DOWNLOADS_PATH}")
        print("Save a chat as .html to trigger the script.")
        
        observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

    elif choice == "2":
        # --- MANUAL MODE ---
        print(f"\nTarget Folder: {DOWNLOADS_PATH}")
        filename = input("Enter the filename (e.g., 'Chat.html'): ").strip()
        
        # We assume the file is in the Downloads folder unless they give a full path
        if os.path.isabs(filename):
            full_path = filename
        else:
            full_path = os.path.join(DOWNLOADS_PATH, filename)
            
        process_file(full_path)

    else:
        print("Invalid choice. Exiting.")

if __name__ == "__main__":
    main()