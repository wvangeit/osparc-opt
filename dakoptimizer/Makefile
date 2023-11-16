SHELL:=/bin/bash

test: clean
	module load litis/dakota && \
	python main.py
clean:
	rm -rf objs.json params.json
