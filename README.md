# 🧠 QueryMind
### *Ask in English. Get answers in data.*

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![LangChain](https://img.shields.io/badge/LangChain-Agents-1C3C3C?style=flat&logo=chainlink)](https://langchain.com)
[![Claude API](https://img.shields.io/badge/Claude-Sonnet-D97757?style=flat)](https://anthropic.com)
[![OracleDB](https://img.shields.io/badge/Oracle-DB-F80000?style=flat&logo=oracle&logoColor=white)](https://oracle.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

> **QueryMind** is an agentic AI system that transforms plain-English business questions into data-driven insights — autonomously. No SQL. No dashboards. No waiting. Just ask.

---

## 📸 Demo

```
User: "Which product category had the worst margin last quarter and why?"

QueryMind:
  ✅ Generating SQL query...
  ✅ Executing against Oracle DB...
  ✅ Detecting anomalies in results...
  ✅ Cross-referencing external market data...
  ✅ Generating narrative summary + chart...

→ "Electronics had the lowest margin at 12.4% (-8.2% vs prior quarter).
   Root cause: Component costs rose 23% in Q3 due to supply chain disruptions
   in Southeast Asia, compounded by a 14% drop in average selling price
   driven by competitor discounting..."
```

---

## ✨ Features

- **🗣️ Natural Language to SQL** — Converts any business question into optimized SQL, no technical knowledge required
- **🤖 Autonomous Agent Loop** — Multi-step reasoning: query → validate → enrich → narrate
- **🔍 Anomaly Detection** — Flags outliers and unexpected patterns automatically
- **🌐 External Context Enrichment** — Cross-references web data (market trends, news) to explain the *why* behind numbers
- **📊 Auto-generated Dashboards** — Produces visual charts alongside narrative summaries
- **🧩 Memory & Follow-up** — Maintains conversation context for multi-turn analysis sessions
- **🔒 Safe Execution** — Read-only DB access with query validation before execution

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        User Query                        │
│              "Which region underperformed Q3?"           │
└───────────────────────────┬─────────────────────────────┘
                            │
                    ┌───────▼────────┐
                    │  Query Planner │  ← Claude Sonnet
                    │    (Agent)     │    Understands intent
                    └───────┬────────┘    & breaks into steps
                            │
           ┌────────────────┼────────────────┐
           │                │                │
    ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐
    │  SQL Writer │  │  Validator  │  │  Enrichment │
    │    Tool     │  │    Tool     │  │    Agent    │
    └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
           │                │                │
    ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐
    │  Oracle DB  │  │  Anomaly    │  │  Web Search │
    │  Executor   │  │  Detector   │  │  (Context)  │
    └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
           │                │                │
           └────────────────┼────────────────┘
                            │
                    ┌───────▼────────┐
                    │    Narrator    │  ← Synthesizes findings
                    │    Agent       │    into insight report
                    └───────┬────────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
       ┌──────▼───┐  ┌──────▼───┐  ┌──────▼───┐
       │ Chart /  │  │Narrative │  │  Export  │
       │Dashboard │  │ Summary  │  │ PDF/CSV  │
       └──────────┘  └──────────┘  └──────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **LLM** | Claude Sonnet (Anthropic) |
| **Agent Framework** | LangChain Agents / LangGraph |
| **Database** | Oracle DB (cx_Oracle / oracledb) |
| **Data Processing** | Pandas, NumPy |
| **Anomaly Detection** | Isolation Forest (scikit-learn) |
| **Visualization** | Plotly, Matplotlib |
| **Web Enrichment** | SerpAPI / Tavily |
| **API Layer** | FastAPI |
| **Frontend** | Streamlit |
| **Orchestration** | LangGraph (state machine) |

---

### Prerequisites

- Python 3.11+
- Oracle DB instance (or use the mock DB for demo)
- Anthropic API Key
- (Optional) SerpAPI key for web enrichment

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/querymind.git
cd querymind

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your credentials
```

### Environment Variables

```env
# .env
ANTHROPIC_API_KEY=your_anthropic_api_key
ORACLE_USER=your_db_user
ORACLE_PASSWORD=your_db_password
ORACLE_DSN=your_db_host:1521/your_service_name
SERPAPI_KEY=your_serpapi_key          # optional: for web enrichment
```

### Run QueryMind

```bash
# Launch the Streamlit UI
streamlit run app/ui/dashboard.py

# Or run via CLI
python -m querymind.cli --query "Show me top 5 underperforming SKUs this month"

# Or start the API server
uvicorn app.api.main:app --reload
```

---

## 💬 Example Queries

```python
# Business Performance
"Which sales rep had the highest close rate last quarter?"
"Compare revenue by region for the past 3 months."

# Operational Intelligence
"Where are we losing the most customers in the funnel?"
"What's the average order fulfillment time by warehouse?"

# Anomaly Investigation
"Are there any unusual spikes in returns this week?"
"Flag any suppliers with delivery times over 2x the average."

# Strategic Insights
"Which product lines are growing fastest year-over-year?"
"Summarize the top 3 risks in our current inventory position."
```

---

## 📁 Project Structure

```
querymind/
├── app/
│   ├── agents/
│   │   ├── planner.py          # Query intent parsing
│   │   ├── sql_writer.py       # NL → SQL generation
│   │   ├── validator.py        # SQL safety + validation
│   │   ├── enrichment.py       # Web context agent
│   │   └── narrator.py         # Insight synthesis
│   ├── tools/
│   │   ├── db_executor.py      # OracleDB execution layer
│   │   ├── anomaly_detector.py # Statistical outlier detection
│   │   ├── chart_generator.py  # Plotly visualizations
│   │   └── web_search.py       # External data retrieval
│   ├── memory/
│   │   └── conversation.py     # Multi-turn context store
│   ├── api/
│   │   └── main.py             # FastAPI endpoints
│   └── ui/
│       └── dashboard.py        # Streamlit frontend
├── data/
│   └── mock_db/                # Demo data (no Oracle needed)
├── tests/
├── notebooks/
│   └── demo.ipynb              # Interactive walkthrough
├── .env.example
├── requirements.txt
└── README.md
```

---

## 🔬 How the Agent Works

QueryMind uses a **LangGraph state machine** with 5 autonomous steps:

```
1. PLAN    → Understand the business intent, identify required tables
2. WRITE   → Generate optimized SQL with schema awareness
3. EXECUTE → Run read-only query against Oracle DB
4. ENRICH  → Detect anomalies + fetch web context if needed
5. NARRATE → Synthesize all findings into a human-readable report
```

Each step is a separate agent node with its own prompt, tool access, and error recovery. If SQL execution fails, the **Validator** agent rewrites the query automatically.

---

## 📊 Sample Output

**Query:** *"What drove the revenue dip in the Northeast last month?"*

```
📉 INSIGHT REPORT — Northeast Revenue | March 2025
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FINDING: Revenue declined 18.3% MoM ($2.4M → $1.96M)

ROOT CAUSES IDENTIFIED:
  1. [HIGH] Apparel category: -34% — correlated with unseasonably
     warm weather (avg temp +8°F vs seasonal norm, NOAA data)
  2. [MED]  Top account ChainCo paused orders — net 30 payment
     terms renegotiation (flagged in CRM notes)
  3. [LOW]  3 field reps on medical leave — territory coverage gap

ANOMALIES:
  ⚠ Electronics sub-category bucked the trend (+12%) — investigate
    for replication opportunity in other regions

RECOMMENDATION:
  → Accelerate ChainCo contract resolution (est. $400K in held orders)
  → Reallocate Northeast inventory to warmer-climate regions

SQL EXECUTED: [View Query] | DATA ROWS ANALYZED: 14,847
CONFIDENCE: High | EXTERNAL SOURCES: 2
```

---

## 🗺️ Roadmap

- [x] Natural language to SQL translation
- [x] Oracle DB integration
- [x] Anomaly detection engine
- [x] Web enrichment agent
- [x] Streamlit UI
- [ ] Scheduled automated reports (cron + email)
- [ ] Slack bot integration
- [ ] Support for PostgreSQL, Snowflake, BigQuery
- [ ] Multi-agent debate for high-stakes decisions
- [ ] Fine-tuned SQL model on enterprise schemas

---

## 🤝 Contributing

Contributions are welcome! Please open an issue to discuss what you'd like to change.

```bash
# Development setup
pip install -r requirements-dev.txt
pre-commit install
pytest tests/
```

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 👤 Author

**[Your Name]**
- Backend Engineer turned AI/Data enthusiast
- 2 years in enterprise backend (Java, OracleDB)
- Building at the intersection of data, AI, and product

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0A66C2?style=flat&logo=linkedin)](https://linkedin.com/in/yourprofile)
[![GitHub](https://img.shields.io/badge/GitHub-Follow-181717?style=flat&logo=github)](https://github.com/yourusername)

---

<p align="center">
  <i>Built with ☕ and curiosity. QueryMind is a portfolio project demonstrating agentic AI, NL2SQL, and business intelligence automation.</i>
</p>
