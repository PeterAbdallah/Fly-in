PYTHON = python3
PIP = $(PYTHON) -m pip
MAIN = src/main.py
REQUIREMENTS = requirements.txt

.PHONY: install run debug clean lint lint-strict

install:
	$(PIP) install -r $(REQUIREMENTS)

run:
	$(PYTHON) $(MAIN)

debug:
	$(PYTHON) -m pdb $(MAIN)

clean:
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf .mypy_cache .pytest_cache .coverage

lint:
	flake8 .
	mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	flake8 .
	mypy . --strict