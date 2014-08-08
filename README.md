# Code for America - Cary Django Site
Proof of concept for a Town of Cary [django](https://www.djangoproject.com/) 
site/application. At the moment, a single application is included that 
parses and displays geospatial data for building permits issued by the town.

## Permit Map Application
This application takes [KML](https://developers.google.com/kml/) permit data 
issued by the towns of Cary and Apex and imports them into a 
[GeoDjango](http://geodjango.org/) application, which allows for native storage
of geometric objects and provides query tools for calculating region overlap, 
containment, etc. The app django exposes a simple API that supports such 
operations as:

- Rendering all permits into [GeoJSON](http://geojson.org/), suitable for 
  overlay on a map.
- Full-text search of the permit data.
- Retreving all permits that are present at a specific latitude/longitude.

A rudimentary web interface is also included to allow exercising these APIs. 
The web interface leverages [AngularJs](https://angularjs.org/) and is 
currently only comfortable for usage on the desktop. It is provided for 
demonstration purposes only and could be vastly improved.

## Architecture
The permit application is broken up into several pieces, with each part 
responsible for a different role. Each chunk, along with its major code entry
point are described below:

1. **Django Site**: Django encourages breaking up web apps into *sites* and 
   *applications*. The top level *site* in this repo is 'cfac'. The main 
   entry points are `cfac/settings.py` and `cfac/urls.py`. Other 
   than establishing basic functionality like database connections and 
   backend caches, the cfac site forwards to the permit\_map app.
2. **Django App**: The permit\_map application contains all of the logic for 
   importing, querying, and searching the permit data. Main entry points 
   here are in `permit_map/urls.py` and `permit_map/models.py`. The 
   permit\_map application also contains a single URL route (/) that renders
   the primary view: `permit_map/templates/permit_map/index.html`.
3. **AngularJS App**: The front-end is rendered using AngularJS. Angular is 
   invoked by the index.html template and control then shifts to a set of 
   statically served JavaScript and HTML files. All of the front-end code 
   comes from a CDN or is stored in `permit_map/static/permit_map/*`. The 
   main entry points are `js/app.js`, `js/controller.js`, and 
   `templates/render.html`.

## Contributing
Pulling down the source code and analyzing the various objects within the 
django shell is one of the fastest ways to understand how the applicaiton 
works. There are two ways of getting a working application: local development
and deploying to [RedHat OpenShift](https://www.openshift.com/). Local 
development is preferred.

Note that it is probably best to clone this repository within it's own 
sandbox. It makes both local and OpenShift development much easier. One 
possible directory structure is:

```
code-for-cary/				# your sandbox directory
|-- cfa-cary-django-site		# this repository
`-- open-shift				# open-shift staging
```

### Local Development
For a local deployment, you will first need a PostGIS 2.1 database. There are 
many ways to install PostGIS. Here's an example for Ubuntu that installs from
the ubuntugis-unstable PPA. These two commands will pull down postgres and 
postgis.

```
# sudo apt-add-repository ppa:ubuntugis/ubuntugis-unstable
# sudo apt-get install postgresql-9.1-postgis-2.1
```

After installing Postgres, we need to add a user and database. We do so by 
switching to the postgres user and running the createdb and createuser 
commands. Finally, we grant rights to our new user. Again, examples assume
Ubuntu:

```
# sudo su - postgresql
postgres# createdb cfac
postgres# createuser -P
  role: cfac
  password: cfac
  n
  n
  n
postgres# psql -c "GRANT ALL PRIVILEGES ON DATABASE cfac TO cfac;"
postgres# psql -f /home/matt/code-for-cary/cfa-cary-django-site/permit_map/init.sql cfac
```

We're now ready to install the necessary python requirements. From within the 
sandbox directory we created ealier (e.g. 'code-for-cary', the directory above
this repo), create a new Python virtualenv:

```
# virtualenv --no-site-packages env
# source env/bin/activate
```

We now have a sandbox Python environment to house our django applicaiton. 
Install all our dependencies:

```
(env)# cd cfa-cary-django-site
(env)# pip install -r requirements.txt
```

Resolve any compile errors that occur by using Google. Usually it's due to a 
missing C library or development package and is easy enough to resolve. Once 
all the requirements are in place, we activate django in our database and 
import our KML files:

```
python manage.py syncdb
python manage.py migrate permit_map 
python import_permits.py kml/*.kml
```

Finally we can start up the django development server:

```
python manage.py runserver 0.0.0.0:8080
```

### OpenShift Deployment
The application is also configured to be deployed onto RedHat's OpenShift 
platform. Follow the [instructions](https://www.openshift.com/get-started) on
RedHat's website to get started with the command line tools. Once you're to the
point where you're conneccted to OpenShift and ready to deploy the application,
execute the following from your OpenShift staging directory (see recommended 
layout in prior section):

```
rhc app create -a cfac -t python-2.7
rhc cartridge add postgresql-9.2 --app cfac
cd cfac
git remote add upstream -m master https://github.com/mattkendall/cfa-cary-django-site.git
git pull -s recursive -X theirs upstream master
git push
```

These commands create a new gear with python and postgres, pull this 
repository into your OpenShift application's repository, and then push the
changes, which deploys and starts the gear.
