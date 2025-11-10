build-DependenciesLayer:
	mkdir -p "$(ARTIFACTS_DIR)/python"
	cp -r python/shared "$(ARTIFACTS_DIR)/python/"
	pip install \
		--platform manylinux2014_x86_64 \
		--target "$(ARTIFACTS_DIR)/python/" \
		--implementation cp \
		--python-version 3.13 \
		--only-binary=:all: \
		--upgrade \
		-r requirements.txt