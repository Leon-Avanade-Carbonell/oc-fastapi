.PHONY: run
run:
	uvicorn app.main:app --reload

.PHONY: install
install:
	pip install -r requirements.txt

.PHONY: help
help:
	@echo "Available commands:"
	@echo "  make run       - Run the FastAPI server with auto-reload"
	@echo "  make install   - Install dependencies from requirements.txt"
	@echo "  make help      - Show this help message"
