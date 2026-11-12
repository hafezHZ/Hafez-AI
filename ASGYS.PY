
import json
import threading
import tkinter as tk
from html.parser import HTMLParser
from urllib.parse import quote_plus, urlparse, parse_qs
import urllib.request
import urllib.error

# AI SETTINGS
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL = "qwen2.5:3b"

# WEB SEARCH
SEARCH_URL = "https://lite.duckduckgo.com/lite/?q="

root = tk.Tk()
root.title("Hafez AI")
root.geometry("1050x720")
root.minsize(800, 600)
root.configure(bg="#F3F7FC")

BLUE = "#3978E8"
DARK_BLUE = "#245CC2"
TEXT = "#1E293B"
MUTED = "#718096"
WHITE = "#FFFFFF"

conversation = []

# HEADER
header = tk.Frame(root, bg=WHITE, height=76)
header.pack(fill="x")
header.pack_propagate(False)

title = tk.Label(
    header,
    text="Hafez AI",
    font=("Segoe UI", 22, "bold"),
    fg=BLUE,
    bg=WHITE
)
title.pack(side="left", padx=28, pady=16)

subtitle = tk.Label(
    header,
    text="YOUR PERSONAL AI ASSISTANT",
    font=("Segoe UI", 9, "bold"),
    fg=MUTED,
    bg=WHITE
)
subtitle.pack(side="right", padx=28)

# MAIN AREA
main = tk.Frame(root, bg="#F3F7FC")
main.pack(fill="both", expand=True, padx=28, pady=22)

welcome = tk.Label(
    main,
    text="Hello! I'm Hafez AI. How can I help you today?",
    font=("Segoe UI", 15, "bold"),
    fg=TEXT,
    bg="#F3F7FC"
)
welcome.pack(anchor="w", pady=(0, 14))

# CHAT AREA
chat_frame = tk.Frame(
    main,
    bg=WHITE,
    highlightthickness=1,
    highlightbackground="#DCE6F3"
)
chat_frame.pack(fill="both", expand=True)

scrollbar = tk.Scrollbar(chat_frame)
scrollbar.pack(side="right", fill="y")

chat = tk.Text(
    chat_frame,
    wrap="word",
    font=("Segoe UI", 11),
    bg=WHITE,
    fg=TEXT,
    padx=20,
    pady=18,
    relief="flat",
    state="disabled",
    yscrollcommand=scrollbar.set
)
chat.pack(fill="both", expand=True)
scrollbar.config(command=chat.yview)

chat.tag_configure(
    "user",
    foreground=BLUE,
    font=("Segoe UI", 11, "bold")
)

chat.tag_configure(
    "assistant",
    foreground=TEXT,
    font=("Segoe UI", 11, "bold")
)

chat.tag_configure(
    "body",
    foreground=TEXT,
    font=("Segoe UI", 11)
)

chat.tag_configure(
    "error",
    foreground="#C0392B",
    font=("Segoe UI", 10)
)

# ADD MESSAGE
def add_message(sender, message, tag):
    chat.config(state="normal")
    chat.insert("end", sender + "\n", tag)
    chat.insert(
        "end",
        message + "\n\n",
        "body" if tag != "error" else "error"
    )
    chat.config(state="disabled")
    chat.see("end")


# CONNECT TO OLLAMA
def ask_ollama(messages):
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are Hafez AI, a helpful and friendly personal "
                    "AI assistant. Reply in the same language as the user. "
                    "Keep answers clear and useful."
                )
            }
        ] + messages,
        "stream": False
    }

    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(
            request, timeout=180
        ) as response:
            data = json.loads(
                response.read().decode("utf-8")
            )

    except urllib.error.HTTPError as error:
        details = error.read().decode(
            "utf-8", errors="replace"
        )
        raise RuntimeError("Ollama error: " + details)

    except urllib.error.URLError:
        raise RuntimeError(
            "Ollama is not running. Please start Ollama."
        )

    answer = data.get(
        "message", {}
    ).get("content", "").strip()

    if not answer:
        raise RuntimeError("Hafez AI returned an empty response.")

    return answer


# PARSE WEB SEARCH RESULTS

class SearchParser(HTMLParser):

    def __init__(self):
        super().__init__()
        self.results = []
        self.current = None
        self.mode = None
        self.end_tag = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get("class", "").split()

        if tag == "a" and (
            "result-link" in classes
            or "result__a" in classes
        ):
            self.current = {
                "title": "",
                "url": attrs.get("href", ""),
                "snippet": ""
            }
            self.results.append(self.current)
            self.mode = "title"
            self.end_tag = "a"

        elif (
            "result-snippet" in classes
            or "result__snippet" in classes
        ):
            if self.results:
                self.current = self.results[-1]
                self.mode = "snippet"
                self.end_tag = tag

    def handle_endtag(self, tag):
        if self.mode and tag == self.end_tag:
            self.mode = None
            self.end_tag = None
            self.current = None

    def handle_data(self, data):
        if self.mode and self.current:
            self.current[self.mode] += data

def search_web(query):
    url = SEARCH_URL + quote_plus(query)

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    with urllib.request.urlopen(
        request, timeout=25
    ) as response:
        page = response.read().decode(
            "utf-8", errors="replace"
        )

    parser = SearchParser()
    parser.feed(page)

    results = []

    for item in parser.results:
        title = item["title"].strip()
        link = item["url"].strip()
        snippet = item["snippet"].strip()

        if not title or not link:
            continue

        # Decode DuckDuckGo redirect links
        parsed = urlparse(link)
        query_values = parse_qs(parsed.query)

        if "uddg" in query_values:
            link = query_values["uddg"][0]

        results.append({
            "title": title,
            "url": link,
            "snippet": snippet
        })

    if not results:
        raise RuntimeError(
            "No search results found. Try another search."
        )

    return results[:6]


# FORMAT SEARCH RESULTS
def format_results(results):
    text = ""

    for number, item in enumerate(results, 1):
        text += (
            str(number) + ". " + item["title"] + "\n"
            + item["url"] + "\n"
            + item["snippet"] + "\n\n"
        )

    return text


# NORMAL CHAT
def finish_reply(answer, success):
    send_button.config(state="normal", text="Send")
    search_button.config(state="normal")
    entry.config(state="normal")
    entry.focus_set()

    if success:
        conversation.append({
            "role": "assistant",
            "content": answer
        })

        add_message("Hafez AI", answer, "assistant")
        status.config(
            text="Connected to Qwen 2.5 3B",
            fg="#21865B"
        )

    else:
        if conversation and conversation[-1]["role"] == "user":
            conversation.pop()

        add_message("Error", answer, "error")
        status.config(
            text="Connection problem",
            fg="#C0392B"
        )


def send_message(event=None):
    message = entry.get().strip()

    if not message:
        return

    entry.delete(0, "end")

    conversation.append({
        "role": "user",
        "content": message
    })

    add_message("You", message, "user")

    send_button.config(state="disabled", text="Sending...")
    search_button.config(state="disabled")
    entry.config(state="disabled")
    status.config(text="Hafez AI is thinking...", fg=BLUE)

    def work():
        try:
            answer = ask_ollama(conversation.copy())

            root.after(
                0,
                lambda: finish_reply(answer, True)
            )

        except Exception as error:
            error_message = str(error)

            root.after(
                0,
                lambda msg=error_message: finish_reply(
                    msg, False
                )
            )

    threading.Thread(target=work, daemon=True).start()


# WEB SEARCH BUTTON ACTION
def web_search_message():
    query = entry.get().strip()

    if not query:
        status.config(
            text="Write something to search first.",
            fg="#C0392B"
        )
        return

    entry.delete(0, "end")

    conversation.append({
        "role": "user",
        "content": query
    })

    add_message("You (Web Search)", query, "user")

    send_button.config(state="disabled")
    search_button.config(state="disabled", text="Searching...")
    entry.config(state="disabled")

    status.config(
        text="Searching the web...",
        fg=BLUE
    )

    def work():
        try:
            results = search_web(query)

            search_context = format_results(results)

            prompt = (
                "Answer the user's question using these web search results. "
                "Reply in the user's language. "
                "Explain that search results may need verification. "
                "Do not invent facts that are not supported by the results. "
                "Include the relevant source URLs in your answer.\n\n"
                "USER QUESTION:\n"
                + query
                + "\n\nWEB SEARCH RESULTS:\n"
                + search_context
            )

            answer = ask_ollama([
                {
                    "role": "user",
                    "content": prompt
                }
            ])

            root.after(
                0,
                lambda: finish_web_search(
                    answer, results, True
                )
            )

        except Exception as error:
            error_message = str(error)

            root.after(
                0,
                lambda msg=error_message: finish_web_search(
                    msg, [], False
                )
            )

    threading.Thread(target=work, daemon=True).start()


# FINISH WEB SEARCH
def finish_web_search(answer, results, success):
    send_button.config(state="normal", text="Send")
    search_button.config(state="normal", text="Web Search")
    entry.config(state="normal")
    entry.focus_set()

    if success:
        conversation.append({
            "role": "assistant",
            "content": answer
        })

        add_message(
            "Web Search Results",
            format_results(results),
            "assistant"
        )

        add_message(
            "Hafez AI - Summary",
            answer,
            "assistant"
        )

        status.config(
            text="Web Search completed",
            fg="#21865B"
        )

    else:
        if conversation and conversation[-1]["role"] == "user":
            conversation.pop()

        add_message("Search Error", answer, "error")

        status.config(
            text="Search problem",
            fg="#C0392B"
        )


# MESSAGE INPUT
composer = tk.Frame(main, bg="#F3F7FC")
composer.pack(fill="x", pady=(16, 0))

entry = tk.Entry(
    composer,
    font=("Segoe UI", 12),
    bg=WHITE,
    fg=TEXT,
    relief="flat",
    highlightthickness=1,
    highlightbackground="#DCE6F3",
    highlightcolor=BLUE
)

entry.pack(
    side="left",
    fill="x",
    expand=True,
    ipady=15,
    padx=(0, 10)
)

entry.bind("<Return>", send_message)


# SEND BUTTON
send_button = tk.Button(
    composer,
    text="Send",
    command=send_message,
    font=("Segoe UI", 10, "bold"),
    bg=BLUE,
    fg=WHITE,
    activebackground=DARK_BLUE,
    activeforeground=WHITE,
    relief="flat",
    cursor="hand2",
    padx=18,
    pady=12
)
send_button.pack(side="right", padx=(5, 0))


# WEB SEARCH BUTTON
search_button = tk.Button(
    composer,
    text="Web Search",
    command=web_search_message,
    font=("Segoe UI", 10, "bold"),
    bg="#21865B",
    fg=WHITE,
    activebackground="#176B47",
    activeforeground=WHITE,
    relief="flat",
    cursor="hand2",
    padx=16,
    pady=12
)
search_button.pack(side="right")


# STATUS
status = tk.Label(
    main,
    text="Ready - Local AI",
    font=("Segoe UI", 9),
    fg=MUTED,
    bg="#F3F7FC"
)
status.pack(anchor="e", pady=(8, 0))


# WELCOME MESSAGE
add_message(
    "Hafez AI",
    "Welcome! I am powered by Qwen 2.5 3B. "
    "Use Web Search to search the internet.",
    "assistant"
)

entry.focus_set()

root.mainloop()
