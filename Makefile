.PHONY: install
install:
	pip install -r requirements.txt

.PHONY: develop
develop:
	python setup.py develop

.PHONY: test
test:
	cd test; ./test_lint_examples.sh    
#	python -m unittest discover . --pattern '*test.py'

.PHONY: coverage
coverage:
	coverage run -m unittest discover --pattern '*test.py'

.PHONY: coverage-report
coverage-report:
	coverage report -m

.PHONY: publish
publish:
	python setup.py sdist upload -r pypi

.PHONY: publish-test
publish-test:
	python setup.py sdist upload -r https://testpypi.python.org/pypi

.PHONY: register
register:
	python setup.py register -r pypi

.PHONY: register-test
register-test:
	python setup.py register -r pypitest
