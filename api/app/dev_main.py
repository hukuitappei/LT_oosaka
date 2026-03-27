from app.factory import create_app


app = create_app(include_analyze_router=True)
