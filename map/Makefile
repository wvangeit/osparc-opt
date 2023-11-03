clean:
	@rm -f params.json
test: clean
	pip install -qr requirements.txt
	DY_SIDECAR_PATH_INPUTS=test-inputs DY_SIDECAR_PATH_OUTPUTS=test-outputs \
		python main.py
