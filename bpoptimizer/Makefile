clean:
	@rm -rf tests/test-inputs
	@rm -rf tests/test-outputs
test: clean
	@mkdir -p tests/test-inputs/input_2/
	@mkdir -p tests/test-outputs/output_1/
	@pip install -qr requirements.txt
	@pytest
	#pytest -s --log-cli-level=INFO
shell-test: clean
	mkdir tests/test-inputs
	mkdir -p tests/test_outputs/output_1
	DY_SIDECAR_PATH_INPUTS='tests/test_inputs' DY_SIDECAR_PATH_OUTPUTS='tests/test_outputs' python main.py
