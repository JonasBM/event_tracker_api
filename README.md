# eventtracker_api

## Event Tracker for municipal audit body
A Backend python project, using django and django rest framework to build the api, connected with a postgresql database.

See the frontend project ([event_tracker_react](https://github.com/JonasBM/eventtracker_react))

## Running the docker

### Building
Use the Dockerfile to build the image.

### Ports
Expose the port 8000.

### Volumes
| Container volume | optional | description |
|:--|:-:|:--|
/static | no | You need map this folder to a webserver, to serve the static files.<br />On the start of the container, it will verify if the static folder is empty, and if so, will collect the static files.
/code | yes | The python code of the project.<br />This folder can be mapped if you want to change the code on the fly, without rebuilding the docker.

### Enviroment
| Enviroment | default | optional | description |
:--|:--|:-:|:--|
SECRET_KEY | secretkeyissecret | yes (at your on risk) | secret key for your django project. Please change this!
ALLOWED_HOSTS | * | yes (at your on risk) | allowed urls to your backend
DEBUG | 1 | yes (please change in production) | 0 => debug off, 1 => debug on
DJANGO_MANAGEPY_MIGRATE | off | yes | change to on with you want to make a migrate on the start of the container
PG_DB_HOST | changeme | no | Host of your database (postgresql), without port
PG_DB_PORT | 5432 | yes | Port for your database 
PG_DB_USER | changeme | no | Name of the user to access the database
PG_DB_PASSWORD password | changeme | no | password to access the database
PG_DB_NAME event_tracker | changeme | no | Name of the database
CORS_ALLOWED_ORIGINS |  | no | Endpoint of your frontend. To allow communication between diferent domains or subdomains.<br /> Can be multiple addresses separated with a comma (https://domainone.com,https://domaintwo.com)
