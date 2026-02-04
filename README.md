# 📝 AI Chat to Markdown Exporter

A robust Python automation tool that converts HTML chat logs (from ChatGPT, Gemini, Claude) into clean, formatted Markdown files. 

Designed for developers and students who want to archive their AI research into Knowledge Management Systems like **Obsidian** or **Notion**.

## 🚀 Key Features

* **🕵️‍♂️ Smart Watchdog:** Automatically detects when you save a chat file to your Downloads folder.
* **🧠 Context-Aware Parsing:** Extracts *specific* AI responses based on your search query—no need to save the whole conversation.
* **💻 Auto-Language Detection:** Intelligently detects code blocks (Python, C++, JS) and applies correct syntax highlighting.
* **📂 Obsidian Ready:** Automatically adds YAML Frontmatter (tags, date, source) to every file.
* **⚡ Dual Modes:** 1.  **Live Mode:** Runs in the background and watches for new files.
    2.  **Manual Mode:** Process existing HTML files from your hard drive.

## 🛠️ Installation

1.  Clone the repository:
    ```bash
    git clone [https://github.com/YOUR_USERNAME/AI-Chat-Exporter.git](https://github.com/YOUR_USERNAME/AI-Chat-Exporter.git)
    cd AI-Chat-Exporter
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3.  Configure your path:
    Open `watcher.py` and update the `DOWNLOADS_PATH` variable to your local Downloads folder.

## 📖 Usage

1.  Run the script:
    ```bash
    python watcher.py
    ```

2.  **Option 1: Live Mode**
    * Leave the script running.
    * Go to ChatGPT/Gemini and save the page as **"Webpage, Complete"** or **.html**.
    * The script will detect the file and ask for a "Search Phrase" (a unique keyword from your question).
    * The extracted answer appears in the `Exported_Notes` folder.

3.  **Option 2: Manual Mode**
    * Select Option 2 in the menu.
    * Select any previously saved HTML file.
    * Enter your search phrase to extract the specific response.

## 🤝 Contributing
Feel free to submit Pull Requests to support more AI platforms or improve the parsing logic!

## 📄 License
MIT License