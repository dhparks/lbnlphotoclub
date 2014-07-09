1. Purpose
The purpose of this project is to provide an anonymous voting system to the LBNL photoclub for its monthly contests. The software provided here runs a webserver which interacts with a database to record votes on photos in the monthly contest. When no voting window is currently open, the webserver displays a list of past winners.

2. Setup
This project is written entirely in Python and SQL, with minimal depence on external libraries. The only strictly required dependecy is the flask WSGI module which runs the webserver. Flask can be downloaded from:

http://flask.pocoo.org/

or installed by following the directions at the above link. All other components used by this software are included in the standard library of python 2.7. This project has not been tested with python 3, but almost certainly it is not compatible. The voting application also uses the python-zenfolio api through the pyzenfolio module, which is included with this software and does not have to be installed separately.

No installation of this software is required. Instead, it must be run in some sort of persistent mode during, at the very least, the entirety of the voting window. On my computer, I do this by opening a detachable terminal screen and invoking

"python voting_server.py"

and then logging out. It may also be possible to run the application as a daemon. The first time the software is run, it will attempt to populate the newly-created voting database by querying zenfolio for old monthly contests, treating the number of comments as the number of votes.

3. Ports and firewall
As provided, this software listens to port :6005 for incoming connections. This port should be opened to TCP/UDP traffic on the machine hosting the server.

4. Configuration
Configuration options are found in voting_config.py. In general, it should not be necessary to change the options in this file. I anticipate that the options most likely to be changed are the following:

i. MEETING_TIME: This variable specifies the date and time when the monthly meeting ENDS. As of the writing of this readme, the monthly meeting is held on the final Wednesday of each month at 12PM. The time specification is therefore "Final Wednesday 12PM". If the meeting were changed to the 2nd Monday at 11AM, the time specification would become "Second Monday 11AM" or "2nd Monday 11AM". The following keywords are supported in the date specification: first, 1st, second, 2nd, third, 3rd, fourth, 4th, final, last, Monday, Tuesday, Wednesay, Thursday, Friday, Saturday, Sunday, AM, PM. Times should always be given in the format HH(:MM)[P/A]M; the :MM specifier is optional, but one of either AM or PM is required. Times in 24-hour format (eg, 18:00 = 6:00PM) are not allowed.

ii. VOTING_TIME: this should be an integer with the number of days voting is allowed. Voting opens at MEETING_TIME and lasts VOTING_TIME days. Floating point values to reflect partial days probably work but I have only tested with integers.

iii. WINNERS: how many winners each month for Today at Berkeley Lab. It is possible for there to be more than this number of winners when there is a tie in the voting, so WINNERS must be understood as a lower bound. For example, if WINNERS = 3 and the top-voted photos have votes 10, 9, 8, 8, 8, 7, there will actually be 5 winners due to the 3-way tie at 8 votes.

iv. USERNAME/PASSWORD: these are the login credentials for the photo club account on zenfolio.

5. Operation
Once running in a peristent mode, the voting server should mostly run itself. Even changes in the configuration file (for example, a change of meeting time) will be reflected without restarting the application as the webserver checks for a change in configuration each time a new session is served.

When the voting window defined by MEETING_TIME and VOTING_WINDOW is open, votes are submitted by navigating to /voting, clicking on the photos, and pressing the submit button. Currently, I make no attempt to authenticate the votes, although in the future it may be possible to check the submitter IP address. In the absence of any evidence of cheating, however, this seems like overkill.

When the voting window closes, winners can be seen at /winners automatically, with a link to the corresponding photo page at zenfolio.

6. Backing up votes to zenfolio
This voting project currently uses the old voting mechanism (comments left on each photo in the club's zenfolio account) to backup the votes recorded through this new mechanism. This allows the server to be moved to a different computer or recreated ab initio as all information is eventually stored at zenfolio. However, backing up the votes currently requires a minor manual intervention from the server administrator. After the voting window closes, the server administator must alter the config file to set

ADMIN = True

and then direct a webbrowser to server:port/backup, which tells the server to backup the votes to zenfolio as comments.
