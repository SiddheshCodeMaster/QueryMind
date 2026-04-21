from app.agents.llm_intepreter import LLMInterpreter

context = {
    "user_query": "Which location has highest revenue?",
    "schema": {
        "columns": [
            {"name": "location"},
            {"name": "payment_method"},
            {"name": "total_spent"},
        ]
    },
}

agent = LLMInterpreter()

result = agent.run(context)

print(result["intent"])
