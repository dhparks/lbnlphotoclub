from __future__ import print_function
from imp import reload

import sys
sys.path.insert(0, '..')
from pyzenfolio import PyZenfolio
#from urllib.request import urlopen
import sqlite3
import os.path
import glob
import datetime
import calendar
import re
import voting_config as voting_config
import random
import time

class backend(object):
    """ Primary object which accepts commands from the server
    and executes them on the database, votingwindow, or zenfolio
    objects """

    def __init__(self, photo_path='static/photos'):
        """ Init"""

        self.z = zenfolio()
        self.w = VotingWindow()
        self.db = PhotoDatabase()

        self.photo_path = photo_path

        if self.db.recreated:
            self._repopulate_from_comments()

        self.cmds = {
            'winners': self._flask_winners,
            'voting': self._flask_voting,
            'castvotes': self._flask_cast_votes,
            'backup': self._flask_backup,
            'reset': self._flask_reset,
            'check': self._flask_check_votes,
            'tiebreaker': self._flask_tiebreaker,
            'delete': self._flask_delete}

    def _monthly_gallery(self, month, year, defer=False):

        """ Try to return photo information for a monthly gallery. If
        the gallery does not exist in the database, create it and
        download thumbnails from zenfolio """

        def _get_gallery(month, year):
            """ Find a gallery on zenfolio. Add its number to the db """
            gallery = self.db.find_gallery(month, year)
            if gallery == None:
                gallery = self.z.find_gallery(month, year)
                self.db.add_gallery(month, year, gallery)
            return gallery

        def _download(url, fn):
            """ download an image by url to a local file """
            print("downloading %s"%url)
            u = urlopen(url)
            local_file = open(self._join(fn), 'w')
            local_file.write(u.read())
            local_file.close()

        def _photo_to_dict(photo):
            """ turn a zenfolio photo object into something more useful """

            def _url(photo, size=None):
                """ Helper """
                if size is None:
                    return photo.OriginalUrl
                s = 'http://{p.UrlHost}{p.UrlCore}-{Size}.jpg?sn={p.Sequence}&tk={p.UrlToken}'
                return s.format(p=photo, Size=size)

            return {'downloadURL':_url(photo, 11),
                    'pageURL':photo.PageUrl,
                    'mailbox':photo.MailboxId, 'votes':0}

        def _db_tuple(p):
            """ Helper """
            time.sleep(.25)
            return (p,
                    zen_photos[p]['downloadURL'].split('?')[0],
                    zen_photos[p]['pageURL'],
                    len(self.z.get_comments(zen_photos[p]['mailbox'])),
                    zen_photos[p]['mailbox'])

        def _fn(photo):
            """ Hleper"""
            return '%s-%s-%s-%s.jpg'%(year, month, photo.Gallery, photo.Id)

        # compare the files in the local records to those in zenfolio.
        # local records are the db entries and the thumbnail files
        gallery = _get_gallery(month, year)
        zen_photos = {_fn(p):_photo_to_dict(p) for p in self.z.photo_gallery(gallery)}
        img_photos = [x.split('/')[-1] for x in glob.glob(self._join('%s-%s*.jpg'%(year, month)))]
        db_photos = {p['filename']:p for p in self.db.get_monthly_photos(month, year)}
        zpk = set(zen_photos.keys())
        dbk = set(db_photos.keys())

        # add photos to database if they are in zenfolio but not the database
        to_add = zpk-dbk
        self.db.add_new_photos([_db_tuple(t) for t in to_add], defer=defer)

        # download images if they are in zenfolio or the database but not the image folder
        if c.keeplocal:
            to_dl = to_add-set(img_photos)
            for p in to_dl:
                _download(zen_photos[p]['downloadURL'], p)

        # return a correctly-formed dictionary of results to _flaskWhatever
        # results should be formatted as self.get_monthly_photos are formatted
        tr = [db_photos[p] for p in zpk if p in dbk]
        if c.keeplocal:
            x['filename'] = self._join(x['filename'])
        return tr

    def _repopulate_from_comments(self):
        """
        First, get all the gallery numbers from zenfolio.
        Second, add them to the database
        Third, download photos for all of them.
        """

        galleries = self.z.find_all_galleries()
        self.db.add_galleries(galleries)
        for g in galleries:
            x = self._monthly_gallery(g[0], g[1], defer=False)
        self.db.database.commit()

    def _join(self, filename):
        """ Helper """
        return os.path.join(self.photo_path, filename)

    def _flask_winners(self, json):
        """ get the winners from the database; return in a template """
        c.reload()
        w = self.db.get_winners()

        # if voting is open, dont display the voting month's results
        try:
            #print(self.w.voting_year, self.db.months[self.w.voting_month])
            voting_key = (self.w.voting_year, self.db.months[self.w.voting_month])
            del w[voting_key]
        except:
            pass

        # if tiebreaking is open , dont display the results
        # for the most recent month
        try:
            mr = self.w.most_recent()
            if self.w.tiebreaking_open():
                tie_key = (mr.year, self.db.months[mr.month])
                del w[tie_key]
        except KeyError:
            pass

        def _path(d, key):
            if key == 'filename':
                return self._join(d[key])
            else:
                return d[key]

        # append the photopath to each photo object.
        # keys in photo: url, link, votes
        for key, photolist in w.items():
            w[key] = [{j:_path(p, j) for j in p.keys()} for p in photolist]

        # sort by month and year
        w2 = [(key[0], key[1], val) for key, val in w.items()]
        w2.sort(key=lambda x: (-1*x[0], -1*self.db.months.index(x[1])))

        return {'template':'winners.html', 'kwargs':{'winners':w2}}

    def _flask_delete(self, json):
        """ Delete a month from the database. Requires admin. """
        c.reload()
        if c.admin:
            now = datetime.datetime.today()
            month = self.db.months[now.month]
            year = now.year
            self.db.delete_month(month, year)
        return {'redirect':'/'}

    def _flask_voting(self, json):
        """ If voting is open, return the template for the voting page """
        c.reload()
        if self.w.voting_open():
            # serve the dynamic page for the current photos
            month, year = self.db.months[self.w.voting_month], self.w.voting_year
            photos = self._monthly_gallery(month, year)
            random.shuffle(photos)
            return {'template':'current.html',
                    'kwargs':{'photos':photos, 'month':month, 'year':year}}
        else:
            return {'redirect':'/winners'}

    def _flask_cast_votes(self, json):
        """
         add votes from json to database
         currently, I'm ignoring the user component of the json
         because user authentication is not implemented
        """
        c.reload()
        photos = [(p.split('/')[-1], ) for p in json['photos']]
        self.db.add_votes(photos)
        return {'result':'votes counted'}

    def _flask_backup(self, json):
        """ When the voting window has expired, backup votes to zenfolio by
        adding comments to photos. Once this operation has completed, there
        should be as many comments on each photo as there are votes for it in
        the database. In this way, _repopulate_from_comments will work for
        photo galleries which came into existence after the switch to this
        voting software
        """

        def _fn(photo):
            """ Helper """
            #return '%s-%s-%s-%s.jpg'%(year, month, photo.Gallery, photo.Id)
            return photo.OriginalUrl

        def _url(photo, size=11):
            """ Helper """
            s = 'http://{p.UrlHost}{p.UrlCore}-{Size}.jpg'
            return s.format(p=photo, Size=size)

        c.reload()

        # get the most recent voting period
        window = self.w.most_recent()
        year = window.year
        month = self.db.months[window.month]
        gallery = self.db.find_gallery(month, year)

        # compare the photos in the most recent voting to the photos in
        # the corresponding zenfolio gallery. only backup those photos
        # which exist in the gallery!
        d_photos = self.db.photos_for_backup(month, year)
        print(d_photos)
        z_photos = [_url(p) for p in self.z.photo_gallery(gallery)]
        print(z_photos)
        print("!!!")
        photos = [d for d in d_photos if d[0] in z_photos]

        # tell zenfolio to make some comments
        #added = [(self._join(a[0]), a[1]) for a in self.z.add_comments(photos)]
        added = [(a[0], a[1]) for a in self.z.add_comments(photos)]
        print(added)

        return {'template':'backup.html',
                'kwargs':{'year':year, 'month':month, 'added':added}}

    def _flask_reset(self, json):
        """ reset votes for the current month if admin is enabled """
        if c.admin:
            self.db.reset_votes()
            return {'redirect':'/'}
        else:
            msg = "insufficient permissions to reset votes"
            return {'template':'error.html', 'kwargs':{'error_msg':msg}}

    def _flask_check_votes(self, json):
        """ Check votes for the current month. Admin tool """
        c.reload()
        if self.w.voting_open():
            m, y = self.db.months[self.w.voting_month], self.w.voting_year
            self.db.check_votes(m, y)
        else:
            mr = self.w.most_recent()
            m, y = self.db.months[mr.month], mr.year
            self.db.check_votes(m, y)

        return {}

    def _flask_tiebreaker(self, json):
        """ Return the tiebreaker page """

        # get the winners of the most recent month
        if self.w.tiebreaking_open():
            mr = self.w.most_recent()
            month, year = mr.month, mr.year

            # return the winners to the correct template for tie-breaking
            photos = self.db.get_monthly_winners(self.db.months[month], year)

            def _path(d, key):
                """ Helper """
                if key == 'url' and c.keeplocal:
                    return self._join(d[key])
                else:
                    return d[key]

            photos2 = [{j:_path(photo, j) for j in photo.keys()} for photo in photos]

            return {'template':'tiebreaker.html',
                    'kwargs':{'winners':photos2, 'month':self.db.months[month], 'year':year}}

        else:
            return {'redirect':'/winners'}

class Config(object):

    """ holds reloadable configuration information """

    def __init__(self):
        """ Init """

        self.c = {
            'keeplocal':voting_config.KEEP_LOCAL_COPY,
            'admin':voting_config.ADMIN,
            'username':voting_config.USERNAME,
            'password':voting_config.PASSWORD,
            'meetingTime':voting_config.MEETING_TIME,
            'votingTime':voting_config.VOTING_TIME,
            'voteBody':voting_config.VOTE_MESSAGE,
            'yearlyGroups':voting_config.YEARLY_GROUPS,
            'winners':voting_config.WINNERS,
            'tiebreakingTime':voting_config.TIEBREAKING_TIME
        }

    def reload(self):
        """ Try to reload the configuration """

        try:
            reload(voting_config)
        except NameError as e:
            print(e.msg)

        self.c = {
            'keeplocal':voting_config.KEEP_LOCAL_COPY,
            'admin':voting_config.ADMIN,
            'username':voting_config.USERNAME,
            'password':voting_config.PASSWORD,
            'meetingTime':voting_config.MEETING_TIME,
            'votingTime':voting_config.VOTING_TIME,
            'voteBody':voting_config.VOTE_MESSAGE,
            'yearlyGroups':voting_config.YEARLY_GROUPS,
            'winners':voting_config.WINNERS,
            'tiebreakingTime':voting_config.TIEBREAKING_TIME
        }

    def __getattr__(self, name):
        """ Class method """
        return self.c[name]

class PhotoDatabase(object):

    """ Class to manage the database of photos and votes """

    def __init__(self, photo_path='static/photos'):

        # this is a lookup table for months
        self.months = (None, 'January', 'February', 'March', 'April', 'May',
                       'June', 'July', 'August', 'September', 'October',
                       'November', 'December')

        ###!!! DATABASE SCHEMA !!!###
        self.tables = (\
                ('photos', (('filename', 'text primary key'), ('thumburl','text'), ('photopage', 'text'), ('votes', 'integer'), ('mailbox', 'text'))), \
                ('votelog', (('month', 'text'), ('year', 'integer'), ('username', 'text'), ('userip', 'text'))), \
                ('galleries', (('month', 'text'), ('year', 'integer'), ('gallery', 'integer'))) \
                )

        print("db init")

        # set some variables based on input
        self.photo_path = photo_path

        # initial state of some variables
        self.voting_month = None
        self.voting_year = None

        # start the database
        self.recreated = None
        self.cursor = None
        self.database = None
        self._connect()

        # sql commands used in this class
        self.sql = {
            'add_gallery':"insert or ignore into galleries (month, year, gallery) values (?, ?, ?)",
            'add_votes':"update photos set votes = votes+1 where thumburl like ?",
            'add_photo':"insert or ignore into photos (filename, thumburl, photopage, votes, mailbox) values (?, ?, ?, ?, ?)",
            'delete_month1':"delete from galleries where month=? and year=?",
            'delete_month2':"delete from votelog where month=? and year=?",
            'delete_month3':"delete from photos where filename like ?",
            'find_gallery':"select gallery from galleries where month = ? and year = ?",
            'get_photos':"select * from photos where filename like ?",
            'get_winners':"select filename, thumburl, photopage, votes from photos where filename like ? and votes >= \
                           (select votes from photos where filename like ? order by votes desc limit 1 offset ?) \
                           order by votes desc",
            'for_backup':"select thumburl, mailbox, votes from photos where filename like ? and votes > 0 order by votes desc",
            'check_votes':'select filename, votes from photos where filename like ? order by votes',
            'check_sum':'select sum(votes) from photos where filename like ?',
            'getMonths':"select distinct year, month from galleries",
            'reset':"update photos set votes=0 where filename like ?"
            }

        # database shorthands
        self.x = lambda cmd, args: self.cursor.execute(self.sql[cmd], args)
        self.xm = lambda cmd, args: self.cursor.executemany(self.sql[cmd], args)
        self.xfo = lambda cmd, args: self.x(cmd, args).fetchone()
        self.xfa = lambda cmd, args: self.x(cmd, args).fetchall()

    def _connect(self, dbase="/home/lblphoto/lbnlphotoclub/photovotes.db", recreate=False):
        """ Connect to the database and make a cursor object.
        If the database does not exist, create it.
        Unless something has gone horribly wrong, there
        should never be a reason to set recreate=True

        database schema:
        2 tables
        1. first table has photo file names, zenfolio pages, number of votes
        2. second table logs which users have voted
        """

        print("connect")

        from os.path import isfile as isf
        from os.path import join

        #db = join(self.photo_path, dbase)
        db = dbase

        print("db")

        if recreate:
            import os
            try:
                os.remove(db)
            except OSError:
                pass

        print(db)
        print(isf(db))

        if isf(db):
            database = sqlite3.connect(db, check_same_thread=False)
            cursor = database.cursor()
            database.row_factory = sqlite3.Row

        self.recreated = False

        if not isf(db) or recreate:
            
            # create the database.
            database = sqlite3.connect(db, check_same_thread=False)
            cursor = database.cursor()
            database.row_factory = sqlite3.Row

            # make the database
            for table in self.tables:
                cmd = 'create table %s (%s)'%\
                      (table[0], ', '.join(['%s %s'%f for f in table[1]]))
                cursor.execute(cmd)

            self.recreated = True

        database.commit()
        self.database = database
        self.cursor = cursor

    def _fmt(self, month, year):
        """ Helper: format the month and year correctly for db queries"""
        try:
            month = self.months[int(month)]
        except (ValueError, IndexError):
            pass
        return '%s-%s'%(year, month)+'%'

    def add_gallery(self, month, year, gallery):
        """ Add a gallery to the database """
        self.add_galleries([(month, year, gallery), ])

    def add_galleries(self, galleries):
        """ Add galleries to the database. Galleries must be something like
        [(month1, year1, galid1), (month2, year2, galid2)...] """
        self.xm('add_gallery', galleries)
        self.database.commit()

    def add_new_photos(self, new_photos, defer=False):
        """ Add the photo and the original photo page
        to the tracking database """

        if len(new_photos) > 0:
            self.xm('add_photo', new_photos)
            if not defer:
                self.database.commit()

    def add_vote(self, thumburl):
        """ Add a vote to a photo """
        self.x('add_votes', ('%'+thumburl+'%',))

    def add_votes(self, photos):
        """ Increment the votes in the database """
        for x in photos:
            self.add_vote(x[0])
        self.database.commit()

    def check_votes(self, month, year):
        """ Administration tool """
        for x in self.xfa('check_votes', (self._fmt(month, year), )):
            print(x+"\n")

    def find_gallery(self, month, year):
        """ If a gallery for month and year is in the database,
        return its number """

        x = self.xfo('find_gallery', (month, year))
        if x != None:
            return x[0]
        else:
            return None

    def delete_month(self, month, year):
        """ Debugging: delete a month from the database. Photos, votes, etc. """
        self.x('delete_month1', (month, year))
        self.x('delete_month2', (month, year))
        self.x('delete_month3', (self._fmt(month, year), ))
        tmp = self.cursor.execute('select month, year from galleries').fetchall()
        j = [k for k in tmp]
        self.database.commit()

    def get_monthly_photos(self, month, year, order='random'):
        """ Query the database to get the photo information the month-year
        tuple hopefully provides a unique key for the set of entries. This
        obviously will not work in the case of a gallery which is not indexed
        by month-year.
        """

        photos = [photo for photo in self.xfa('get_photos', (self._fmt(month, year), ))]

        # return the results in the requested order
        if order == "random":
            random.shuffle(photos)
        if order == "byname":
            photos.sort(key=lambda x: x[0])
        if order == "byvotes":
            photos.sort(key=lambda x: (-x[2], x[0]))

        ni = 0 if c.keeplocal else 1

        tmp = [{'filename':p[0], 'url':p[ni], 'link':p[2], 'votes':p[3]} for p in photos]

        return tmp

    def get_monthly_winners(self, month, year):
        """ Helper: get monthly winners for a given month and year """
        fmt = self._fmt(month, year)
        tmp = self.xfa('get_winners', (fmt, fmt, c.winners-1))

        ni = 0 if c.keeplocal else 1

        winners = [{'url':p[ni], 'link':p[2], 'votes':p[3]} for p in tmp]
        if sum(w['votes'] for w in winners) == 0:
            return None
        else:
            return winners

    def get_winners(self, page=1):
        """ Get winning photos and votes for display on the winners
        page """

        def _get_old_galleries():
            """ query the database to get all the (year, month) pairs
            for which photos exist """

            q1 = "select distinct year, month from galleries"
            olds = self.cursor.execute(q1).fetchall()
            fmts = [(x[0], x[1], self.months.index(x[1])) for x in olds]
            fmts.sort(key=lambda x: x[2])
            return [(x[0], x[1]) for x in fmts]

        winners_dict = {}
        ogs = _get_old_galleries()
        #print ogs
        #
        ## clip the page number
        #max_page = len(ogs)/6
        #if page < 1:
        #    page = 1
        #if page > max_page:
        #    page = max_page
        #
        #l_bound = page*6
        #u_bound = min([(page+1)*6, len(ogs)])

        l_bound = 0
        u_bound = -1

        ogs = ogs[l_bound:u_bound]

        for og in ogs:
            winners = self.get_monthly_winners(og[1], og[0])
            if winners != None:
                winners_dict[og] = winners

        return winners_dict

    def photos_for_backup(self, month, year):
        """ Get the vote totals for doing zenfolio-comment backup """
        return [x for x in self.xfa('for_backup', (self._fmt(month, year), ))]

    def reset_votes(self):
        """ set the votes to 0 for the current month. for debugging. """
        now = datetime.datetime.today()
        self.x('reset', (self._fmt(now.month, now.year), ))
        self.database.commit()

class VotingWindow(object):
    """ Class which controls whether voting is open or not in accordance
    with the times specified in the configuration file """

    def __init__(self):
        """ Init """

        self.days = {'monday': 0, 'tuesday':1, 'wednesday':2, 'thursday':3,
                     'friday':4, 'saturday':5, 'sunday':6}
        self.orders = {'first':0, 'second':1, 'third':2, 'fourth':3,
                       'fifth':4, 'last':-1, '1st':0, '2nd':1, '3rd':2,
                       '4th':3, '5th':4, 'final':-1}

        # set up the regex for parsing the voting specification
        dls = '|'.join(self.days.keys())
        ols = '|'.join(self.orders.keys())
        self.fmt = r'(%s) (%s) ([0-9]*)(:?)([0-9]*?)(am|pm)'%(ols, dls)

        # these are requested by the voting server when it serves the landing
        self.voting_year = None
        self.voting_month = None

        # initial declarations
        self.hour = None
        self.period = None
        self.dayN = None
        self.dayStr = None
        self.minute = None

    def _find_day(self, l, n):
        """ Find the nth non-zero element of l. n can be negative """
        if n == -1:
            n = 0
            l.reverse()
        j = [x for x in l if x != 0]
        return j[n]

    def _make_window(self, year, month):
        """ Make the voting window out of datetime objects """

        cal = calendar.monthcalendar(year, month)
        day = self._find_day([x[self.dayN] for x in cal], self.period)

        window = {}
        window['vStart'] = datetime.datetime(year, month, day, self.hour, self.minute)
        window['vEnd'] = window['vStart']+datetime.timedelta(c.votingTime)
        window['tStart'] = window['vEnd']
        window['tEnd'] = window['tStart']+datetime.timedelta(c.tiebreakingTime)

        return window

    def _parse_time(self):
        """ Parse the meeting time using regex. Adjust for 12-hour clock. """

        # parse the meeting time using regex
        f = re.match(self.fmt, c.meetingTime.lower())
        self.period = self.orders[f.group(1)]
        self.dayStr = f.group(2)
        self.hour = int(f.group(3))
        try:
            self.minute = int(f.group(5))
        except ValueError:
            self.minute = 0

        # adjustments
        self.dayN = self.days[self.dayStr]
        if self.minute == None:
            self.minute = 0
        if 'p' in f.group(6) and self.hour < 12:
            self.hour = (self.hour+12)%24

    def most_recent(self):
        now = datetime.datetime.today()
        t = self.this_month()
        l = self.last_month()
        if now > t['vEnd']:
            return t['vStart']
        else:
            return l['vStart']

    def voting_open(self):
        """ Calculate the voting windows for this month
        and last month. see if we are currently within
        either. """

        def _check(w):
            """ Helper, check if voting is open"""
            if now > w['vStart'] and now < w['vEnd']:
                self.voting_year = w['vStart'].year
                self.voting_month = w['vStart'].month
                return True
            else:
                return False

        def _close():
            """ Helper, close the voting window"""
            self.voting_year = None
            self.voting_month = None
            return False

        c.reload()

        now = datetime.datetime.today()
        if _check(self.last_month()):
            return True
        if _check(self.this_month()):
            return True
        _close()

    def tiebreaking_open(self):
        """ determine if the tiebreaking time window is open. """
        c.reload()
        now = datetime.datetime.today()
        mr = self.most_recent()
        w = self._make_window(mr.year, mr.month)
        return now > w['tStart'] and now < w['tEnd']

    def _months_back(self, delta):
        """ Delta months back from present """
        self._parse_time()
        now = datetime.datetime.today()
        if now.month > delta:
            m, y = now.month-delta, now.year
        else:
            m, y = now.month-delta+12, now.year-1
        return self._make_window(y, m)

    def last_month(self):
        """ Last month """
        return self._months_back(1)

    def this_month(self):
        """ This month """
        return self._months_back(0)

class zenfolio(object):
    """ Class object which interacts with zenfolio through the pyzenfolio
    class and the zenfolio API. """

    def __init__(self):
        """ Init """
        self.vote = {'PosterName':c.username, 'PosterUrl':'',
                     'PosterEmail': '', 'Body':c.voteBody,
                     'IsPrivate': False, }

    def _auth(self):
        """ Perform zenfolio authorization """
        return PyZenfolio(auth={'username':c.username, 'password':c.password})

    def add_comments(self, photos):
        """ Add comments to the specified photos. This performs the
        redundant vote backup in case the database is lost"""

        def _add(photo):
            """ Helper; does the adding """
            filename, mailbox, local_votes = photo
            try:
                remote_votes = len(zen.LoadMessages(mailbox))
            except:
                remote_votes = 0

            diff = local_votes-remote_votes
            if diff > 0:
                for n in range(diff):
                    zen.AddMessage(mailbox, self.vote)

            return (filename, diff)

        zen = self._auth()
        zen.Authenticate()

        s = []
        for photo in photos:
            #try:
                s.append(_add(photo))
            #except:
            #    pass
        s.sort(key=lambda x: -x[1])
        return s

    def get_comments(self, mailbox):
        """ Get all the comments on a photo's mailbox.
        For vote counting """

        zen = self._auth()
        try:
            return zen.LoadMessages(mailbox)
        except:
            return []

    def find_gallery(self, month, year):
        """ Find the gallery for month, year at zenfolio """

        zen = self._auth()
        sets = zen.LoadPublicProfile().RecentPhotoSets
        year = str(year)
        for s in sets:
            ls = zen.LoadPhotoSet(s.Id)
            t = ls.Title
            if month in t and year in t:
                return s.Id
        return None

    def find_all_galleries(self):
        """ Knowing that galleries need to be of the form
        month year theme, get the numbers which identify
        the galleries on zenfolio """

        zen = self._auth()

        # regex stuff
        months = ['January', 'February', 'March', 'April', 'May', 'June',
                  'July', 'August', 'September', 'October', 'November',
                  'December']
        fmt = r'(%s) ([0-9]*) (.*)'%('|'.join(months))
        r = lambda s: re.match(fmt, s.Title)
        def _match(s):
            """ Regex helper """
            return r(s).group(1, 2)+(s.Id, )

        # find in yearlyGroups first, then RecentPhotoSets'
        ps1 = []
        for yg in c.yearlyGroups:
            ps1 += zen.LoadGroup(yg, recursive=True).Elements
        recent = zen.LoadPublicProfile().RecentPhotoSets
        ps2 = [zen.LoadPhotoSet(ps.Id) for ps in recent]

        sets = []
        for s in ps1:
            try:
                sets.append(_match(s))
            except:
                pass

        for s in ps2:
            try:
                sets.append(_match(s))
            except:
                pass

        # de-duplicate and sort
        sets = list(set(sets))
        sets.sort(key=lambda x: (x[1], months.index(x[0])))

        # get the month, year, and photoset id
        return sets

    def photo_gallery(self, gallery):
        """ Return all the photos in a gallery on zenfolio"""
        zen = self._auth()
        return [p for p in zen.LoadPhotoSet(gallery, with_photos=True).Photos]

c = Config()
