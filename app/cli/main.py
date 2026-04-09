from app.core.context import Context
from app.core.pipeline import QueryMindPipeline


def main():
    print("🧠 QueryMind CLI")
    print("Type 'exit' to quit\n")

    file_path = "data/samples/sales.csv"
    pipeline = QueryMindPipeline(file_path)

    while True:
        query = input(">> ")

        if query.lower() == "exit":
            break

        context = Context(query)
        result = pipeline.run(context)

        if result.get("error"):
            print("❌ Error:", result["error"])
        else:
            print("✅ Schema Loaded:")
            print(result["schema_description"])


if __name__ == "__main__":
    main()
