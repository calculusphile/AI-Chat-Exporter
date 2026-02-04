# 📝 AI Chat to Markdown Exporter

A robust Python automation tool that converts HTML chat logs (from ChatGPT, Gemini, Claude) into clean, formatted Markdown files. 

Designed for developers and students who want to archive their AI research into Knowledge Management Systems like **Obsidian** or **Notion**.

## 🚀 Key Features

* **🕵️‍♂️ Smart Watchdog:** Automatically detects when you save a chat file to your Downloads folder.
* **🧠 Context-Aware Parsing:** Extracts *specific* AI responses based on your search query.
* **🔗 Session Merging:** Option to append multiple questions into a single "Master Note" (e.g., `Exam_Prep.md`) instead of creating scattered files.
* **💻 Deep Language Detection:** Uses proximity searching and syntax analysis to correctly identify languages (C++, Python, SQL) even if the HTML is messy.
* **📂 Obsidian Ready:** Automatically adds YAML Frontmatter (tags, date, source) to every entry.

## 📖 Usage

1.  Run the script:
    ```bash
    python watcher.py
    ```

2.  **Select Mode:**
    * The script will ask: *"Do you want to merge all notes into ONE file?"*
    * **Type a filename** (e.g., `Cpp_Notes.md`) to enable **Merge Mode**.
    * **Press Enter** to enable **Individual Mode** (one file per question).

3.  **Start Saving:**
    * Save any Gemini/ChatGPT page as `.html`.
    * The script detects it and asks for your **Search Phrase**.
    * **Pro Tip:** You can extract multiple different answers from the same file—just keep typing new phrases!

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

## 🤝 Contributing
Feel free to submit Pull Requests to support more AI platforms or improve the parsing logic!

## 📄 License
MIT License