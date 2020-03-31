import scrapy
import datetime
from bs4 import BeautifulSoup
import unicodedata
import uuid

class eventCrawler(scrapy.Spider):
    detailedTime = datetime.datetime.now()
    time = str(detailedTime.year) + "-" + str(detailedTime.month) + "-" + str(detailedTime.day)

    name = "eventures"
    tab = "exhibits"
    tag = {
        "academic":'["Academics","Education"]',
        "lectures":'["Seminar","Education","Academics"]',
        "sports":'["Recreational","Sports"]',
        "performing_arts":'["Music","Arts","Culture"]',
        "films":'["Education","Arts"]',
        "exhibits":'["Arts","Culture"]'
    }
    org = {
        "academic":"berkeleyAcademics",
        "lectures":"berkeleyLectures",
        "sports":"berkeleySports",
        "performing_arts":"berkeleyPerformingArts",
        "films":"berkeleyFilms",
        "exhibits":"berkeleyExhibition"
    }
        ## TODO: fix for exhibits, they tend to have many dates, in that case compare to the end date!!!
    
    start_urls = ["http://events.berkeley.edu/?view=summary&timeframe=week&date=2020-03-22&tab={}".format(tab),
    "http://events.berkeley.edu/?view=summary&timeframe=week&date=2020-03-15&tab={}".format(tab),
    "http://events.berkeley.edu/?view=summary&timeframe=week&date=2020-03-08&tab={}".format(tab),
    "http://events.berkeley.edu/?view=summary&timeframe=week&date=2020-03-01&tab={}".format(tab),
    "http://events.berkeley.edu/?view=summary&timeframe=week&date=2020-02-23&tab={}".format(tab),
    "http://events.berkeley.edu/?view=summary&timeframe=week&date=2020-02-16&tab={}".format(tab),
    "http://events.berkeley.edu/?view=summary&timeframe=week&date=2020-02-09&tab={}".format(tab),
    "http://events.berkeley.edu/?view=summary&timeframe=week&date=2020-02-02&tab={}".format(tab)]
    prefix = "https://events.berkeley.edu/"

    def parse(self, response):
        event = '//div[contains(@class, "event row")]/div' #only crawling div with event row classes
        eventInfo = response.xpath(event).getall()

        titleFormat = event+'/h3/a/text()' #per the website format
        eventTitles = response.xpath(titleFormat).getall()

        urlFormat = event+'/h3/a'
        urls = response.xpath(urlFormat).getall()
        eventUrls = []
        for u in urls:
            link = BeautifulSoup(u, features="lxml").a
            if (link != None):
                eventUrls.append(self.prefix + link.get('href'))
        #for u in eventUrls:
        #    print(u)
        assert(len(eventTitles)==len(eventUrls))

        spacetime = []
        for e in eventInfo:
            paragraph = BeautifulSoup(e, features="lxml").p
            if (paragraph != None):
                spacetime.append(paragraph.text)
        spacetime = list(filter((lambda s: '|' in s), spacetime)) #filtering and leave only the one with '|' since that's the website format

        assert(len(eventTitles)==len(spacetime)) #make sure each event title has a spacetime
        #for i in range(len(spacetime)):
        #    print(spacetime[i], eventTitles[i])

        eventTypes = []
        eventSpaces = []
        eventTimes = []
        for i in range(len(eventTitles)):
            typeSpaceTime = self.spacetimeParse(spacetime[i])
            eventTypes.append(typeSpaceTime[0])
            eventSpaces.append(typeSpaceTime[1])
            eventTimes.append(typeSpaceTime[2])
            startTime, endTime = typeSpaceTime[2][0], typeSpaceTime[2][1]

            yield  {
                'uuid':uuid.uuid1(),
                'Title':eventTitles[i],
                'Organization':self.org[self.tab],
                'Location':typeSpaceTime[1],
                'Description':typeSpaceTime[0] + " @ " + eventUrls[i],
                'Start time':startTime,
                'End time':endTime,
                'Published':1,
                'Public':1,
                'Tags':self.tag[self.tab],
                'Interested':'[]',
                'Favorites':'[]',
                'Creation date':"2020-01-01 12:00:00",
                'Last modified':"2020-01-01 12:00:00",
                'Has cover':0,
                'Capacity':0,
            }
        assert(len(eventTitles)==len(eventTypes)==len(eventSpaces)==len(eventTimes)==len(eventUrls))



    def spacetimeParse(self, s):
        #str format is the spacetime EVENT TYPE | DATE | TIME | SPACE
        one = s.find('|')
        assert(one != -1)
        eventType = s[0:one - 1]
        s = s[one + 2:]
        eventType = unicodedata.normalize("NFKD", eventType)

        two = s.find('|')
        assert(two != -1)
        date = s[0:two - 1]
        s = s[two + 2:]
        date = unicodedata.normalize("NFKD", date)
        if (date.find('–') != -1):
            date = date[0:date.find('–')]
        #Note that – is different from -, the prev is longer
        date = date.strip()
        # TODO: TO AVOID MULTI-DAY EVENT, NEED SMART PARSING
        date = date +" 2020"
        # TODO: CHANGE THE YEAR ADDING PROCEDURE

        three = s.find('|')
        try:
            #ghost events where a date is given, but not a time
            assert(three != -1)
            daytime = s[0:three - 1]
            daytime = unicodedata.normalize("NFKD", daytime)
            daytime = daytime.strip()
            space = s[three + 2:]
            space = unicodedata.normalize("NFKD", space)
        except AssertionError:
            # TODO: FIGURE OUT A DEFAULT WAY TO DEAL WITH GHOST EVENTS
            ## TODO: fix for exhibits, they tend to have many dates, in that case compare to the end date!!!
            daytime = "7 a.m.-7 p.m."
            space = s[two + 2:]
            space = unicodedata.normalize("NFKD", space)

        time = self.timeParse(date, daytime)
        return (eventType, space, time)

    def timeParse(self, date, daytime):
        format = '%B %d %Y'
        dateParsed = (datetime.datetime.strptime(date, format)).strftime("%Y-%m-%d %H:%M:%S")
        #We need to parse date from string to datetime first, then back to string for later concatenation
        dateParsed = dateParsed[0:dateParsed.find(' ')] #September 2 2019-->2019-09-02

        start = daytime[0:daytime.find('-')]
        if (start.find(':') == -1):
            #That means the website used abbreviation
            if (start.find(' ') == -1):
                #4-5:30 p.m.
                start = start+":00"
            else:
                #4 a.m --> 4:00 a.m
                start = start[0:start.find(' ')]+":00"+start[start.find(' '):]
        if (start.find('a') != -1):
            #4:00 a.m. --> 4:00AM
            start = start[0:start.find('a')-1]+"AM"
        elif (start.find('p') != -1):
            #4:00 p.m. --> 4:00PM
            start = start[0:start.find('p')-1]+"PM"
        else:
            #4:00 --> depends on the PM,AM status of end
            #There is no a.m., p.m. indicator
            if (daytime.find('a') != -1):
                #4:00-5:30 a.m. --> 4:00AM
                start = start + "AM"
            else:
                #4:00-5:30p.m. --> 4:00PM
                start = start + "PM"


        end = daytime[daytime.find('-')+1:]
        if (end.find(':') == -1):
            end = end[0:end.find(' ')]+":00"+end[end.find(' '):]
        if (end.find('a') != -1):
            #4:00 a.m. --> 4:00AM
            end = end[0:end.find('a')-1]+"AM"
        else:
            #4:00 p.m. --> 4:00PM
            end = end[0:end.find('p')-1]+"PM"

        format = '%Y-%m-%d %I:%M%p'
        start = dateParsed+" "+start
        start = datetime.datetime.strptime(start, format)+datetime.timedelta(hours=7)
        #Timedelta since the database uses UTC, and it is 7 hours ahead, so 9AM at UTC time is 2AM Berkeley Time

        end = dateParsed+" "+end
        end = datetime.datetime.strptime(end, format)+datetime.timedelta(hours=7)

        #print(start.strftime("%Y-%m-%d %H:%M:%S"))

        return (start,end)
        #print(start)
        #print(end)
