def log_step(context, step, data):
    context["logs"].append({"steps": step, "data": data})
