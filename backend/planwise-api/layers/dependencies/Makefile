build-DependenciesLayer:
	mkdir -p "$(ARTIFACTS_DIR)/python"
	pip install \
		--target "$(ARTIFACTS_DIR)/python/" \
		--platform manylinux2014_aarch64 \
		--implementation cp \
		--python-version 3.13 \
		--only-binary=:all: \
		--no-cache-dir \
		-r requirements.txt
	cp -r python/shared "$(ARTIFACTS_DIR)/python/"