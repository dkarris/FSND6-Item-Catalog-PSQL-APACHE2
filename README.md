# Udacity project N4 car datbase
## Project description:
This project contains catalog data about car manufactures and model they make.
The app consistst of two big parts:
### 1. DB populator/management - where user can make bulk data upload.
### 2. Catalog with Udacity project rubric

### DB populator:
The data is populated using public NHTSA database containig data about manufactures and model. Unfortunately, their public data has some gaps and errors such as dublicate ids and different data structures for certain fields, so some data cleansing is also built in to capture some inconsistencies. This prevents some records to be uploaded to database. At a later stage, after uploading manufactures you can upload models for selected manufactures. Model pic urls are retrieved using flickr api engine.
This leads to the following problems: 
- possible pics missmatch => since search is done using keywords/tags, it is up to user who uploaded pic to put correct tags => there are some errors.
- flickr api is really slow for free usage. So it is not recommended to upload too many models.

## Testing script for bulk upload:

it is recommended to select first page from NHTSA api - appox 86 records out of 100 will be uploaded.
When models will be uploaded I played with Tesla, Aston Martin and BMW - to retrieve model data and pics from flickr. Since it takes some time it is recommended to watch script execution in python flask console where run time info about the process is printed out. That scenario should suffice to examine script behaviour.

### Udacity project aligned with rubric specs

 -  functionaly with CRUD operations for manufactures and models - authorizing users based on OAUTH unique ids.
 - JSON API endpoints for database object access
 -  Front end interface developed with JS/jQuery functions.
 -  OAUTH implemented with 3 providers: Facebook, Google and GitHub
 User is uniquely identified not with email address as in Udacity example but with oauth provider unique id. Since in theory they may be the same - two char key is added to ensure uniqueness. This behaviour allows to have several users with the same email address - which is intentional behaviour for testing purposes.


Application has been tested in a standard udacity vagrant environment and has not been deployed to any hosting platforms.











