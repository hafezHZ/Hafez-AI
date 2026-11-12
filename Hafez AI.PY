
import tkinter as tk
from tkinter import scrolledtext
import threading
import urllib.request
import urllib.parse
import json
import webbrowser
from html.parser import HTMLParser

# ---------------- SETTINGS ----------------

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL = "qwen2.5:3b"

SEARCH_URL = "https://lite.duckduckgo.com/lite/?q="

messages = [
    {
        "role": "system",
        "content": "You are Hafez AI, a friendly and helpful AI assistant. Answer in the language used by the user."
    }
]

# ---------------- WEB SEARCH ----------------

class SearchParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.results = []
        self.current_link = None
        self.current_text = ""
        self.current_snippet = ""
        self.reading_link = False
        self.reading_snippet = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get("class", "")

        if tag == "a" and (
            "result-link" in classes or "result__a" in classes
        ):
            self.current_link = attrs.get("href", "")
            self.current_text = ""
            self.reading_link = True

        if tag in ("td", "div") and (
            "result-snippet" in classes or "result__snippet" in classes
        ):
            self.current_snippet = ""
            self.reading_snippet = True

    def handle_data(self, data):
        if self.reading_link:
            self.current_text += data

        if self.reading_snippet:
            self.current_snippet += data

    def handle_endtag(self, tag):
        if tag == "a" and self.reading_link:
            if self.current_link and self.current_text.strip():
                self.results.append({
                    "title": self.current_text.strip(),
                    "url": self.current_link,
                    "snippet": ""
                })
            self.reading_link = False

        if tag in ("td", "div") and self.reading_snippet:
            if self.results:
                self.results[-1]["snippet"] = self.current_snippet.strip()
            self.reading_snippet = False


def search_web(query):
    url = SEARCH_URL + urllib.parse.quote(query)

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        html = response.read().decode("utf-8", errors="ignore")

    parser = SearchParser()
    parser.feed(html)

    return parser.results[:7]


# ---------------- CHAT WITH OLLAMA ----------------

def ask_ollama(user_text):
    messages.append({
        "role": "user",
        "content": user_text
    })

    data = json.dumps({
        "model": MODEL,
        "messages": messages,
        "stream": False
    }).encode("utf-8")

    request = urllib.request.Request(
        OLLAMA_URL,
        data=data,
        headers={"Content-Type": "application/json"}
    )

    with urllib.request.urlopen(request, timeout=180) as response:
        result = json.loads(response.read().decode("utf-8"))

    answer = result["message"]["content"]

    messages.append({
        "role": "assistant",
        "content": answer
    })

    return answer


# ---------------- GUI ----------------

root = tk.Tk()
root.title("Hafez AI")
root.geometry("950x700")
root.minsize(700, 500)
root.configure(bg="#eaf4ff")

BLUE = "#2878c8"
DARK_BLUE = "#15518c"
WHITE = "#ffffff"
TEXT_COLOR = "#172b4d"

# Header
header = tk.Frame(root, bg=BLUE, height=75)
header.pack(fill="x")
header.pack_propagate(False)

title = tk.Label(
    header,
    text="Hafez AI",
    font=("Segoe UI", 23, "bold"),
    bg=BLUE,
    fg=WHITE
)
title.pack(side="left", padx=25, pady=15)

subtitle = tk.Label(
    header,
    text="Your personal AI assistant",
    font=("Segoe UI", 10),
    bg=BLUE,
    fg=WHITE
)
subtitle.pack(side="right", padx=25)

# Chat area
chat_frame = tk.Frame(root, bg="#eaf4ff")
chat_frame.pack(fill="both", expand=True, padx=18, pady=15)

chat = scrolledtext.ScrolledText(
    chat_frame,
    wrap=tk.WORD,
    font=("Segoe UI", 11),
    bg=WHITE,
    fg=TEXT_COLOR,
    relief="flat",
    padx=15,
    pady=15,
    state="disabled"
)
chat.pack(fill="both", expand=True)

chat.tag_config("user", foreground=BLUE, font=("Segoe UI", 11, "bold"))
chat.tag_config("ai", foreground=DARK_BLUE, font=("Segoe UI", 11, "bold"))
chat.tag_config("link", foreground="#0878d1", underline=True)

def add_message(sender, text):
    chat.config(state="normal")

    if sender == "You":
        chat.insert(tk.END, "\nYou:\n", "user")
    else:
        chat.insert(tk.END, "\nHafez AI:\n", "ai")

    chat.insert(tk.END, text + "\n")
    chat.see(tk.END)
    chat.config(state="disabled")


def add_search_results(results):
    chat.config(state="normal")
    chat.insert(tk.END, "\nWeb Search Results:\n", "ai")

    if not results:
        chat.insert(tk.END, "No results found.\n")
    else:
        for index, result in enumerate(results):
            chat.insert(tk.END, f"\n{index + 1}. ")

            start = chat.index(tk.END)
            chat.insert(tk.END, result["title"], "link")
            end = chat.index(tk.END)

            tag = f"link_{index}_{start.replace('.', '_')}"

            chat.tag_add(tag, start, end)
            chat.tag_config(tag, foreground="#0878d1", underline=True)

            chat.tag_bind(
                tag,
                "<Button-1>",
                lambda event, url=result["url"]: webbrowser.open(url)
            )

            chat.insert(tk.END, "\n")

            if result["snippet"]:
                chat.insert(tk.END, result["snippet"] + "\n")

    chat.see(tk.END)
    chat.config(state="disabled")


def set_status(text):
    status_label.config(text=text)


# ---------------- SEND MESSAGE ----------------

def finish_reply(answer):
    add_message("Hafez AI", answer)
    set_status("Ready")


def send_message():
    text = message_entry.get().strip()

    if not text:
        return

    message_entry.delete(0, tk.END)
    add_message("You", text)
    set_status("Hafez AI is thinking...")

    def worker():
        try:
            answer = ask_ollama(text)
            root.after(0, lambda: finish_reply(answer))
        except Exception as error:
            root.after(
                0,
                lambda: set_status("Error: " + str(error))
            )

    threading.Thread(target=worker, daemon=True).start()


# ---------------- WEB SEARCH BUTTON ----------------

def web_search_message():
    query = message_entry.get().strip()

    if not query:
        return

    message_entry.delete(0, tk.END)
    add_message("You", "Search the web: " + query)
    set_status("Searching the web...")

    def worker():
        try:
            results = search_web(query)

            if not results:
                root.after(
                    0,
                    lambda: set_status("No search results found.")
                )
                return

            summary_text = "Summarize these search results in the user's language:\n"

            for item in results:
                summary_text += (
                    "\nTitle: " + item["title"] +
                    "\nURL: " + item["url"] +
                    "\nDescription: " + item["snippet"] + "\n"
                )

            answer = ask_ollama(summary_text)

            def finish():
                add_search_results(results)
                add_message("Hafez AI", answer)
                set_status("Ready")

            root.after(0, finish)

        except Exception as error:
            root.after(
                0,
                lambda: set_status("Search error: " + str(error))
            )

    threading.Thread(target=worker, daemon=True).start()


# ---------------- INPUT AREA ----------------

bottom = tk.Frame(root, bg="#eaf4ff")
bottom.pack(fill="x", padx=18, pady=(0, 10))

message_entry = tk.Entry(
    bottom,
    font=("Segoe UI", 12),
    relief="flat",
    bg=WHITE,
    fg=TEXT_COLOR
)
message_entry.pack(
    side="left",
    fill="x",
    expand=True,
    ipady=12,
    padx=(0, 8)
)

send_button = tk.Button(
    bottom,
    text="Send",
    font=("Segoe UI", 10, "bold"),
    bg=BLUE,
    fg=WHITE,
    activebackground=DARK_BLUE,
    activeforeground=WHITE,
    relief="flat",
    padx=20,
    command=send_message
)
send_button.pack(side="left", padx=4)

search_button = tk.Button(
    bottom,
    text="Web Search",
    font=("Segoe UI", 10, "bold"),
    bg=DARK_BLUE,
    fg=WHITE,
    activebackground=BLUE,
    activeforeground=WHITE,
    relief="flat",
    padx=15,
    command=web_search_message
)
search_button.pack(side="left", padx=4)

message_entry.bind("<Return>", lambda event: send_message())

# Status
status_label = tk.Label(
    root,
    text="Ready",
    font=("Segoe UI", 9),
    bg="#eaf4ff",
    fg="#52677f",
    anchor="w"
)
status_label.pack(fill="x", padx=20, pady=(0, 8))

add_message("Hafez AI", "Hello! I am Hafez AI. How can I help you today?")

root.mainloop()
