# planwise-backend

# ToDo for this week

Assignments for CRUD:
Joe: Events (done mostly), Folders, Boards
Ivesa: Tags, Tasks
Brandon: Users, Notes

Basic Workflow:
1. create a service for adding removing updating and deleting your model

2. link it to its repository structure

3. fill in the functions to create read update and delete inside the functions folder. Make sure to add the @lambda_http_handler decorator to each function.

*note: you can copy the events example for most of these there just might need to be slight modifications. Here is a quick breakdown of the architecture.

API layer: everything that interacts directly with the frontend, primarily responsible for passing data from the https request down to the necessary services

Service Layer: The brain of the operation. Every query that is needed to be made will have an operation down here

Repository Layer: right now this is the most generic layer. if you need to call something to dynamo with a query, you should make a generic function to do so in repository.py. We probably won't need to go beyond generic functions and specify by datatype but I have made an inheritance structure just in case.


Errors: in utils there is an errors.py file that has custom errors for the application. For the most part you should try to raise errors that we know whats going on with or rather makes sense to get. If there is an unknown error raised the decorator will catch it. Again see events for details




# Queries
Here are the queries that we will need to get eventually:

Boards:
get boards for a user id at specific path
get boards for user id at current tree depth
create board for user id
update board for board id
update path of board for user
delete board for board id

Events:
create event for board id
update event for event id
delete event for event id
get events for a specific board
get events for a specific time range
get events for a specific board for a specific time range

Files:
create file for user id at specific path
update file for user id 
update path of file for user id
get files for current user at current tree depth

Tasks:
get tasks for specific board

Notes:
get notes for a user
get notes for a board