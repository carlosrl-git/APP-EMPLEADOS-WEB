from fastapi.templating import Jinja2Templates
import os

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "..", "templates"))

def render_template(request, name, context, status_code=200):
    context["request"] = request
    return templates.TemplateResponse(name, context, status_code=status_code)
