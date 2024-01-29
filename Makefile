.PHONY:	version setup push pypi test
export PYTHONPATH := $(shell pwd)/test:$(shell pwd):$(PYTHONPATH)

commit:
		git commit -am "Version $(shell cat VERSION)"
		git push
remote:
		git push cblabs main
build:
		bumpversion --allow-dirty build
patch:
		bumpversion --allow-dirty patch
minor:
		bumpversion --allow-dirty minor
major:
		bumpversion --allow-dirty major
setup:
		python setup.py sdist
push:
		$(eval REV_FILE := $(shell ls -tr dist/*.gz | tail -1))
		twine upload $(REV_FILE)
pypi: setup push
test:
		python -m pytest tests/test_1.py
