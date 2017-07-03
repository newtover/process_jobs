empty:
	#
main:
	python3 -m jobs.scripts.extract_products < job_urls.txt
test:
	python3 -m unittest discover jobs.tests

