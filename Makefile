empty:
	#
main:
	python3 -m jobtechs.scripts.extract_techs < job_urls.txt
test:
	python3 -m unittest discover jobtechs.tests

