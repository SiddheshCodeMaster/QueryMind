class Context(dict):
    def __init__(self, user_query):
        super().__init__()

        self["user_query"] = user_query
        self["intent"] = None
        self["analysis"] = None
        self["answer"] = None
        self["error"] = None
        self["logs"] = []
