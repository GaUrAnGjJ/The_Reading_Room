import argparse
from urllib import parse
from ingestion.ingestion import run_pipeline
from transformation.transformation import transformation
from storage.db import main_db
from API.main import app
import uvicorn


def api():
    uvicorn.run(
        "API.main:app",
        # host="127.0.0.1",
        # port=8000,
        reload=True
    )

def main():
    parser = argparse.ArgumentParser(description="BDE Data Pipeline")

    parser.add_argument("--ingestion", action="store_true")
    parser.add_argument("--transformation", action="store_true")
    parser.add_argument("--db", action="store_true")
    parser.add_argument("--api", action="store_true")
    parser.add_argument("--all", action="store_true")

    args = parser.parse_args()

    if args.all:
        run_pipeline()
        transformation()
        main_db()
        app()
        api()
        return

    if args.ingestion:
        run_pipeline()

    if args.transformation:
        transformation()

    if args.db:
        main_db()
    
    if args.api:
        api()


if __name__ == "__main__":
    main()