# 🧠 QueryMind

**Ask questions about your data in plain English. No SQL. No code. Just a terminal.**

QueryMind is a CLI data analyst that lets you load a CSV or Excel file and query it conversationally — right in your terminal.

```
>> top 5 regions by sales
>> which month had the highest profit?
>> average spend by payment method in ascending order
>> show sales in sheet Orders by customer segment
```

---

## Install

```bash
pip install querymind-cli
```

**Requirements:**
- Python 3.10+
- [Ollama](https://ollama.ai) (optional — enables LLM fallback for complex queries)

If you want LLM support, install Ollama and pull the model:
```bash
ollama pull phi
```

---

## Quickstart

```bash
querymind
```

You'll be prompted to:
1. Enter a CSV or Excel file path
2. Select sheets (Excel only)
3. Map your metric and dimension columns
4. Start asking questions

---

## What it can do

| Query | What happens |
|---|---|
| `top 5 products by revenue` | Ranked bar chart in terminal |
| `which region had lowest sales` | Ascending comparison with insight |
| `average profit by category` | Mean aggregation per group |
| `sales trend over time monthly` | Monthly groupby on datetime column |
| `show sales in sheet Orders by region` | Sheet-scoped query |
| `which manager had the most sales` | Cross-sheet join (Orders + Users) |
| `sales by region in ascending order` | Explicit sort order |

---

## Supported file formats

| Format | Extension |
|---|---|
| CSV | `.csv`, `.tsv` |
| Excel | `.xlsx`, `.xls`, `.xlsm` |

Auto-detects: encoding (UTF-8 BOM, latin-1), delimiter (comma, semicolon, tab, pipe), packed integer dates (DDMMYYYY, YYYYMMDD).

---

## How it works

```
Your query
    ↓
InputGuard       — blocks gibberish and sensitive input
    ↓
InterpreterAgent — rule-based intent extraction (fast, no LLM needed)
    ↓
LLMInterpreter   — Ollama fallback for complex queries (optional)
    ↓
JoinResolver     — auto-detects and performs cross-sheet joins
    ↓
Analyzer         — pandas groupby / aggregation
    ↓
InsightGenerator — formats result + ASCII bar chart
```

---

## What's New in v0.2.2

- **`/export`** — save the last query result to CSV or Excel
  - `/export` → auto-named timestamped CSV
  - `/export myfile.csv` or `/export myfile.xlsx` → custom name and format
  - The original query is embedded in the exported file (comment lines in CSV, header cells in Excel)
- All files saved to `~/querymind_sessions/`

## What's New in v0.2.0

- **`/profile`** — instant dataset profile: row count, column types, null %, unique counts, min/avg/max stats per column. For Excel files shows overall summary + per-sheet breakdown.
- **`/history`** — shows your last 5 queries inline in the TUI with the path to the full log
- **Persistent session history** — every query saved to `~/querymind_sessions/querymind_history.md` across all sessions forever
- **Sort order fix** — `"lowest sales in descending order"` now correctly highlights the minimum while sorting high→low
- **Integer display fix** — IDs like `customer_id` no longer show as `553.0`

---

## Session History

Every query and answer is automatically saved to:
```
~/querymind_sessions/querymind_history.md
```

This is a single persistent Markdown file — all sessions across all datasets append to it. Open it in any editor or view it on GitHub.

Inside the TUI, type `/history` to see your last 5 queries and the file path.

---

## Beta

QueryMind is in active development. If something breaks or a query gives a wrong answer, please [open an issue](https://github.com/SiddheshCodeMaster/QueryMind/issues) with:
- Your query
- The column names in your file (no need to share actual data)
- The output you got

This feedback directly shapes what gets fixed next.

---

## License

MIT