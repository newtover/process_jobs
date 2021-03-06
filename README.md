# README #

It is going to be a text-parsing application that would output the list of software products and tools a company is using
based on the job description.

## Input ##
 * List of keywords of products and tools that we are trying to identify
 * List of URLs with job descriptions

The processing script processes urls gradually. Theoretically there is no limit on the amount of urls to process.
An example url list with some comments is available (blank lines and lines starting with # are skipped on processing).

## Output ##
The code should output the following columns for each job description:
Job Description URL | Company Name | Tools (comma separated if more than one) | Website (optional)

If an error occurred on processing a url, the url and the error go to failed_urls.txt file (can be configured).

When a page contains a marker to a job description on another site (newton.newtonsoftware.com, boards.greenhouse.io, etc), the corresponding new url is written to the failed_urls.txt as well. 


## Example of the output ##
https://boards.greenhouse.io/embed/job_app?for=pantheon&token=135120&b=https://www.getpantheon.com/jobs | Pantheon | Drupal, Cassandra, Dropbox, Amazon S3, Amazon SWF, Docker, CircleCI, Redis,  | pantheon.io

## Some thoughts ##
The task can be split into several parts:
*  [x] downloading the job descriptions.
      At the first glance, most of the urls lead to the popular vacancy sites, but there are exceptions. Parallelizing the process of page fetching, we should be carefull       and balance the load on the sites for which we have multiple urls. Fortunatelly, the list of the vacancies sites should be rather small, other sites can be visited 
      simultaneously.
*  [x] extracting the job description from a page
      For simplicity, we can consider the whole text on the page. The only problem I see is that on some sites there is context advertizing of similar vacancies 
      which can list keywords as well, resulting in false positives. But these are the sites from the small list of vacancies sites, hence we can make specific parsers for      them. All other sites can be processed by a more general default parser.
*  [x] finding the terms within the job description
      I would split the text of the job description into n-grams and for each n-gram check if it is in the list of the searched terms. 
*  [x] Explore the provided urls
    at the first glance, most of the urls lead to the popular vacancy sites.

## How to run ##
The package can be installed with pip from the directory: `pip install .`.

The project contains a Vagrant configuration file, that is you can just vagrant up in the directory and a new virtual-box will be created. The prject is located in `/vagrant` directory within the virtual system.

If you prefer to develop run locally, there is also a requirements.txt site to configure the python3 environment.

The project as well contains a Makefile, so that you could see how the script is running. You can run `python3 -m jobs.scripts.extract_techs --help` to see the options.
