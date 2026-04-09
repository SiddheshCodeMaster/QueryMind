class Context(dict):
    def __init__(self, user_query: str):
        super().__init__()
        self["user_query"] = user_query
        self["schema"] = None
        self["schema_desription"] = None
        self["intent"] = None
        self["sql_query"] = None
        self["validated_sql"] = None
        self["data"] = None
        self["analysis"] = None
        self["insight"] = None
        self["error"] = None
        self["logs"] = None
