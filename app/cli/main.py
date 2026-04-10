from app.core.context import Context
from app.core.pipeline import QueryMindPipeline
import pandas as pd


def validate_column(input_col, columns):
    input_col = input_col.lower().strip().replace(" ", "_")
    if input_col not in columns:
        print("Invalid column: ", input_col)
        return None
    return input_col


def main():
    print("🧠 QueryMind CLI\n")

    # Step 1: File input
    file_path = input("📁 Enter file path: ")

    # Load once to show columns
    df = pd.read_csv(file_path)
    df.columns = [col.lower().strip().replace(" ", "_") for col in df.columns]

    print("\n📊 Detected Columns:")
    for col in df.columns:
        print(f"- {col}")

    # Step 2: Ask user for mapping
    print("\n🧠 Help me understand your data:")

    metric = validate_column(
        input("👉 Which column represents the main value (e.g. revenue, sales)? "),
        df.columns,
    )
    print(metric)
    dimension = validate_column(
        input("👉 Which column should we group by by default? "),
        df.columns,
    )
    print(dimension)
    time_col = validate_column(
        input("👉 Which column represents time? (optional) "),
        df.columns,
    )
    print(time_col)

    semantic_map = {
        "metric": metric,
        "dimension": dimension,
        "time": time_col if time_col else None,
    }

    pipeline = QueryMindPipeline(file_path, semantic_map)

    print("\n✅ Setup complete! Ask your questions.\n")

    while True:
        query = input(">> ")

        if query.lower() == "exit":
            break

        context = Context(query)
        result = pipeline.run(context)

        if result.get("error"):
            print("❌ Error:", result["error"])
        else:
            print("\n💡 Answer:")
            print(result.get("answer"))


if __name__ == "__main__":
    main()
