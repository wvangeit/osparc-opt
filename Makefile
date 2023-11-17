SHELL:=/bin/bash

all: 

daktest: map evaluator1 evaluator2 dakoptimizer

bptest: map evaluator1 evaluator2 bpoptimizer

iodirs: clean
	mkdir -p test-inputs
	mkdir -p test-outputs
	mkdir -p test-outputs/map
	mkdir -p test-outputs/eval1
	mkdir -p test-outputs/eval2
	mkdir -p test-outputs/opt
	mkdir -p test-inputs/map
	mkdir -p test-inputs/eval1
	mkdir -p test-inputs/eval2
	mkdir -p test-inputs/opt
	mkdir -p test-outputs/map/output_1
	mkdir -p test-outputs/map/output_2
	mkdir -p test-outputs/opt/output_1
	mkdir -p test-outputs/eval1/output_1
	mkdir -p test-outputs/eval2/output_1
	ln -rfs test-outputs/map/output_1 test-inputs/eval1/input_2
	ln -rfs test-outputs/map/output_1 test-inputs/eval2/input_2
	ln -rfs test-outputs/map/output_2 test-inputs/opt/input_2
	ln -rfs test-outputs/opt/output_1 test-inputs/map/input_2
	ln -rfs test-outputs/eval1/output_1 test-inputs/map/input_3
	ln -rfs test-outputs/eval2/output_1 test-inputs/map/input_4

dakoptimizer: iodirs
	cd dakoptimizer && \
	module load litis/dakota && \
	DY_SIDECAR_PATH_INPUTS=../test-inputs/opt \
	DY_SIDECAR_PATH_OUTPUTS=../test-outputs/opt \
	python main.py
bpoptimizer: iodirs
	cd bpoptimizer && \
	DY_SIDECAR_PATH_INPUTS=../test-inputs/opt \
	DY_SIDECAR_PATH_OUTPUTS=../test-outputs/opt \
	python main.py
evaluator1: iodirs
	cd evaluator && \
	DY_SIDECAR_PATH_INPUTS=../test-inputs/eval1 \
	DY_SIDECAR_PATH_OUTPUTS=../test-outputs/eval1 \
	python main.py
evaluator2: iodirs
	cd evaluator && \
	DY_SIDECAR_PATH_INPUTS=../test-inputs/eval2 \
	DY_SIDECAR_PATH_OUTPUTS=../test-outputs/eval2 \
	python main.py
map: iodirs
	cd map && \
	DY_SIDECAR_PATH_INPUTS=../test-inputs/map \
	DY_SIDECAR_PATH_OUTPUTS=../test-outputs/map \
	python main.py 

clean:
	rm -rf test-inputs
	rm -rf test-outputs
	rm -rf dakoptimizer/params.dak.in
	rm -rf dakoptimizer/params.dak.out
