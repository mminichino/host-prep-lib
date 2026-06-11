.PHONY:	commit remote patch minor major pypi build publish test
export PYTHONPATH := $(CURDIR)/tests:$(CURDIR):$(PYTHONPATH)
export PROJECT_NAME := $(notdir $(CURDIR))
export PROJECT_VERSION := $(shell uv run hatch version)

commit:
		git commit -am "Version $(PROJECT_VERSION)"
		git push
remote:
		git push cblabs main
patch:
		bumpversion --allow-dirty patch
minor:
		bumpversion --allow-dirty minor
major:
		bumpversion --allow-dirty major
pypi:
		uv build
		uv publish
build:
		uv sync --all-groups
		hatch build
publish:
		uv publish
test:
		python -m pytest tests/test_1.py
release:
		gh release create -R "mminichino/$(PROJECT_NAME)" \
		-t $(PROJECT_VERSION) \
		-n $(PROJECT_VERSION) \
		$(PROJECT_VERSION) \
		"dist/pyhostprep-$(PROJECT_VERSION)-py3-none-any.whl" \
		"dist/pyhostprep-$(PROJECT_VERSION).tar.gz"
upload:
		gh release upload -R "mminichino/$(PROJECT_NAME)" $(PROJECT_VERSION) --clobber \
		"dist/pyhostprep-$(PROJECT_VERSION)-py3-none-any.whl" \
		"dist/pyhostprep-$(PROJECT_VERSION).tar.gz"
recall:
		gh release delete -R "mminichino/$(PROJECT_NAME)" $(PROJECT_VERSION) --cleanup-tag -y
