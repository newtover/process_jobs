# README #

It is going to be a text-parsing application that would output the list of software products and tools a company is using
based on the job description.

## Input ##
 * List of keywords of products and tools that we are trying to identify
 * List of URLs with job descriptions

## Output ##
The code should output the following columns for each job description:
Job Description URL | Company Name | Tools (comma separated if more than one) | Website (optional)

## Example of the output ##
https://boards.greenhouse.io/embed/job_app?for=pantheon&token=135120&b=https://www.getpantheon.com/jobs | Pantheon | Drupal, Cassandra, Dropbox, Amazon S3, Amazon SWF, Docker, CircleCI, Redis,  | pantheon.io