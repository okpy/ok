# How to contribute to OK

Installation
--------------
See `README.md`

Filing Issues
----------------
Please include instructions on how to reproduce the error you are seeing.

Documentation
----------------
Changes that improve the documentation are welcomed!

Style Guide
----------------
Refer to [The Elements of Python Style](https://github.com/amontalenti/elements-of-python-style)

The `make lint` command will check for common style issues.

Branch Name Convention
--------------------
To add features to ok, please do the following:

- Follow the Installation instructions in order to install the ok server.
- Name your branch according to our convention of &lt;category&gt;/&lt;GithubUsername&gt;/&lt;branch name&gt;
  * Category is one of the following things:
    - 'enhancement': This is a new feature that is being added to ok.
    - 'bug': This is when the purpose of the branch is to fix a bug in the current codebase.
    - 'cleanup': This is when technical debt is being reduced (e.g. adding tests, improving code style, etc)
  * GithubUsername is the username of one person who is the point of contact for the branch. The point of contact should be the first person that will field questions about the branch- there might be many other people working on it.
  * branch name: A descriptive name for the branch

Submitting Changes
----------------------
- Make a pull request, which will get code-reviewed and merged.
- Your pull request should include tests for the features developed.

Additional Resources
------------------------
* [General GitHub documentation](https://help.github.com/)
* [GitHub pull request documentation](https://help.github.com/send-pull-requests/)
