.PHONY: install test run generate-test api lint clean

install:
	pip install -r requirements.txt

test:
	PYTHONPATH=. python -m pytest tests/ -v

run:
	PYTHONPATH=. python app/cli.py data/sample/test_campus.mp4 -o data/output -v

generate-test:
	python scripts/generate_test_video.py --output data/sample/test_campus.mp4 --duration 10

api:
	PYTHONPATH=. uvicorn app.api.server:app --host 0.0.0.0 --port 8000 --reload

clean:
	rm -rf data/output/* data/uploads/* __pycache__ .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

docker-build:
	docker build -t campusnav-sentinel:latest .

docker-run:
	docker run -p 8000:8000 --gpus all campusnav-sentinel:latest
