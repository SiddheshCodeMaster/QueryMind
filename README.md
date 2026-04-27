# 🧠 QueryMind

QueryMind is a terminal-based AI Data Analyst that allows users to interact with their data using natural language.

It combines rule-based logic and local LLMs to deliver fast, intelligent, and human-readable insights directly from your dataset.

---

## 🚀 Features

* 📊 Query CSV data using natural language
* 🧠 Hybrid intelligence (rule-based + LLM)
* ⚡ Fast responses with LLM fallback
* 💡 Insight generation (not just raw outputs)
* 🖥️ Interactive terminal UI (Textual)
* 🔒 Input validation and safety checks

---

## 🏗️ Architecture

User Input → Pipeline → Interpreter → Analyzer → Insight Generator → Output

* Interpreter: Converts query → structured intent
* Analyzer: Performs data operations (pandas)
* Insight Generator: Produces human-readable insights
* LLM: Enhances understanding and explanations

---

## 🧰 Tech Stack

* Python
* Pandas
* Textual (TUI)
* Ollama (local LLM runtime)

---

## 📦 Installation

1. Clone the repository

```bash
git clone <your-repo-url>
cd QueryMind
```

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Install and run Ollama

Download: https://ollama.com

```bash
ollama run phi
```

---

## ▶️ Usage

Run the application:

```bash
python -m app.cli.main
```

Steps:

1. Provide dataset path
2. Map key columns (metric, dimension)
3. Ask questions in natural language

---

## 💬 Example Queries

* Which payment method has highest total spent?
* Top 5 products by revenue
* Average spending by location
* Where did we earn the most money?

---

## 🧠 How It Works

QueryMind uses a hybrid approach:

* Rule-based system for fast interpretation
* LLM (via Ollama) for complex queries and insights

---

## ⚠️ Notes

* Ensure Ollama is running before using LLM features
* Works best with clean and structured datasets
* Large datasets may take longer to process

---

## 🔮 Future Work

* Data visualizations
* Multi-agent architecture
* Database integrations (SQL/NoSQL)
* Conversational memory

---

## 👨‍💻 Author

Built as an advanced data + AI systems project.

---

## ⭐ If you like this project

Give it a star and share it 🚀
