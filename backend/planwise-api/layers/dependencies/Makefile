build-DependenciesLayer:
	mkdir -p "$(ARTIFACTS_DIR)/python"
	cp -r python/shared "$(ARTIFACTS_DIR)/python/"
	pip install \
		--target "$(ARTIFACTS_DIR)/python/" \
		--upgrade \
		--platform manylinux2014_aarch64 \
		--only-binary=:all: \
		-r requirements.txt