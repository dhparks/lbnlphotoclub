# import login credentials. These are stored in a different file
# for security reasons
from credentials import *

# Specify the monthly meeting and how long the voting window is open
# please check the README.txt for information. IF this is improperly
# specified, voting will not work and the voting server may crash.
# NOTE: MEETING_TIME is the ***END*** of the meeting when voting opens.
MEETING_TIME     = 'Last Wednesday 12PM' # see README.txt for how to set this!!!!!
VOTING_TIME      = 5 # number of days to vote following meeting
TIEBREAKING_TIME = 1 # number of days after voting closes to break ties

# this specifies how many winners each month.
# this is a lower bound which admits ties
WINNERS = 4

# this is whether or not to download thumbnail images
# to serve as a local cache on the server
KEEP_LOCAL_COPY = False

# this is the voting message left on photos during
# vote backup
VOTE_MESSAGE = 'voting app backup'

# this is a list of the archive groups which hold completed contests
# from previous years. group 873396715 is the collection for "2013
# Monthly Photos". This list needs to be updated for future years, for
# example at the end of 2014 for "2014 Monthly Photos" etc. THIS
# VARIABLE IS CRITICAL FOR REPOPULATING THE DATABASE ON THE INITIAL RUN.
YEARLY_GROUPS = [873396715,]

# setting ADMIN to true allows the invocation of certain database
# management urls. In particular, when True, ADMIN allows votes
# for the current month to be backed up to zenfolio.
ADMIN = False

### server config. experts only! changing the debug-mode configuration
# requires a hard restart from the command line.
DEBUG = False