.PHONY:	commit remote patch minor major pypi build publish test
export PYTHONPATH := $(shell pwd)/test:$(shell pwd):$(PYTHONPATH)
export PROJECT_NAME := $$(basename $$(pwd))
export PROJECT_VERSION := $(shell cat VERSION)

commit:
		git commit -am "Version $(shell cat VERSION)"
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
		poetry build
		poetry publish
build:
		poetry build
publish:
		poetry publish
test:
		python -m pytest tests/test_1.py
download:
		$(eval REV_FILE := $(shell ls -tr dist/*.whl | tail -1))
		cp $(REV_FILE) dist/pyhostprep-latest-py3-none-any.whl
		gh release create -R "mminichino/$(PROJECT_NAME)" \
		-t "Release $(PROJECT_VERSION)" \
		-n "Release $(PROJECT_VERSION)" \
		latest \
		dist/pyhostprep-latest-py3-none-any.whl
recall:
		gh release delete -R "mminichino/$(PROJECT_NAME)" latest --cleanup-tag -y
