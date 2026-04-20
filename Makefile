.PHONY: backend frontend test stack-up stack-restart stack-check stack-down

backend:
	cd backend && uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

test:
	cd backend && python -m pytest

stack-up:
	./.venv/bin/python scripts/dev_stack.py up

stack-restart:
	./.venv/bin/python scripts/dev_stack.py up --restart

stack-check:
	./.venv/bin/python scripts/dev_stack.py check

stack-down:
	./.venv/bin/python scripts/dev_stack.py down
