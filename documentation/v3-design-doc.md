# Ok Server V3 Design Doc

## Goals

The goals of this rewrite are to payoff technical debt, move off App Engine, make ok more usable for course staff, and make future development easier (through documentation & testing)

It should be possible for other courses to use OK without much intervention after this rewrite. 

## Why is it called v3? 
v2 was used. Our models had a version of v2 and some API methods had a version of v2. 

## Why not just improve v1? 
It is certainly possible to address most of the issues with some changes to the v1 codebase. The problems with GAE & Datastore lock in would not be avoidable with this approach<sup>1</sup>. 
I felt that the changes would relatively major and it would be worth it to take our learnings from using Ok for three semesters and build it up stronger and better than it was before. 

[1] There exists a runtime for App Engine apps outside of GAE   [AppScale](http://appscale.com) -  I haven't used it. 

## Dates
- Target Release:
  -   1/15/16
- Courses that depend on that date:
  - CS61A (1000 students)
  - DATA 8 (170 students) 
- Fallback is to use the existing version off GAE but transitioning systems will be painful so there's a strong incentive to complete by that date.

## Status
- GitHub issue will track overall progress and TODOs 
- Currently: 
  - API will accept Submissions/Backups from ok-client
  - Models are written 
  - Login/Auth Handled

Major TODOs:
- Frontend 
- Documentation & Testing
- Infrastructure Design/Deploy

## v1 Issues
- Lack of email notifications
- Exports were inconsistent/slow
- Wasn't easy to generate analytics 
- Database migrations weren't easy
- GAE prevented long running tasks 
- Frontend was Slow 
 - Way too many DB reads for simple things
 - Needed large server + memcache inoreder to avoid timeouts on web requests
- Staff didn't have easy access to student progress
- Composition grading used massive amount of browser recourses
 - Syntax Highlighting/Diffing wasn't great 
- Models design (Submission vs Backup vs FinalSubmission) 
- App Engine gets expensive and we are locked into AppEngine & the datastore. 

## v1 Strengths 
- App Engine took care of scaling 
  - Especially DB scaling
- It works. Battle tested. 
- Easy to deploy
- 90% test coverage 



## Major Design Goals

### Documentation
  - It should be very clear how to develop for OK Server
  - Usage for staff should also be documented 
  - Markdown in repo -> Documentation Site. 
  - Will either use [FlatDoc](http://ricostacruz.com/flatdoc/) or [DocPress](http://docpress.github.io/). Leaning towards FlatDoc since no extra publishing is required and it'll just read markdown files on GitHub. 

### Code
  - Reduce scope of API to ok-client dependencies
    - Submission/Backup/Enrollment 
  - Use different database: Postgres 
    -  Motivation: native JSON type (JSONB) to handle ok messages.
    -  MySQL (Google Cloud SQL) was tempting (mostly because it was hosted - but the version Cloud SQL uses doesn't support JSON) 
  -  Server side rendering of pages. 
    -  Should speed up rendering.   
    -  Interface: List based instead of blocks. 
    -  Admin/Student Interface can share same base CSS (AdminLTE) 
      - [Student](https://almsaeedstudio.com/themes/AdminLTE/pages/layout/top-nav.html)
      - [Admin](https://almsaeedstudio.com/themes/AdminLTE/index2.html)

### Models
- Submissions & Backups
  - Now a clear distinction. All data lives on the backup. Submissions are mereley records of submissions. Will require minor changes to Ok-Client 
- FinalSubmission & Group remain the same. 
- Added Assignment ID Column to Scores, Messages, Comments (for easier querying) 

# Tech Stack 
It's still in Python & uses Flask. Choosing another language/stack might make it hard to find people to work on Ok. 

DB: Postgres 
Cache: Redis 

Core Libraries: Flask-SQLAlchemy (Models/ORM), Flask-RESTful (API)
Testing: PyTest
Linting: Flake8
Starter Template: [Flask-Foundation](https://jackstouffer.github.io/Flask-Foundation/)

Frontend: 
Bower for Package Management (retained from v1). 
Core CSS/JS Assets are compiled via Flask-Asset
Not using Angular since most of the app will be rendered on the server. This allows the API to be smaller and hopefully allow the pages to load faster. It will also help with accesibility.

AdminLTE for Admin/Student Views. 

## Infrastruture:
Fairly platform agnostic. Can be run on a single server or many. 

Current plan is to use a Kubernetes cluster to run the app. (DB, App, Caching servers). 
To be evaluated:
- The deploy process for updates to the app
- Scale out process of DB nodes (and underlying storage) 

The traditional approach would be have a load balancer and an auto-scaling cluster of app servers with a set of DB Primary/Secondary severs. I'm okay with this approach as well. 

Backups: Regular DB backups since it will be easier to cause data loss in the DB (since we would have raw SQL capabilites) 

Logging: 
- Host our own instance of [Sentry](http://getsentry.com) 
- Log to Google Cloud Logging
- ElasticSearch/Kibana/LogStash as well 

Data Analysis: 
- To allow quick data analysis for admins/authorized researchers we can use a Business Intelligence tool.
- Self Hosted [Metabase](http://www.metabase.com/) with direct access to the DB to allow for data dashboards/queries. ![Example of Metabase](http://www.metabase.com/docs/v0.13.2/images/AreaChart.png)
- The users table can be hidden for researchers to protect student privacy. 


(Optional) Vagrant VM for development. Current Dependcies for running locally: 
- Python/Virtualenv
- Make
- Postgres 
- Redis

## Testing
Travis CI & Coveralls coverage testing: 100% Goal. 

If we can figure out a way to batch load data from V1 to this DB that'd be great to see how this version performs under load. 

DB should be stress tested with 100 submission/sec. 











