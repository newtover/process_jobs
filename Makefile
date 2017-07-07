empty:
	#
main:
	python3 -m jobtechs.scripts.extract_techs < job_urls.txt
test:
	python3 setup.py test

