.PHONY:	version setup push pypi

version:
		bumpversion patch
setup:
		python setup.py sdist
push:
		$(eval REV_FILE := $(shell ls dist/*.gz | tail -1))
		twine upload $(REV_FILE)
pypi: setup push
