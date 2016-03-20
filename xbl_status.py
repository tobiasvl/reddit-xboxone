from HTMLParser import HTMLParser
from bs4 import BeautifulSoup
from flask import Flask
from datetime import datetime
import urllib
import praw
import re
from slackclient import SlackClient
from slacker import Slacker

## ===== USAGE ====
## In the wiki page you want to include the services table put this in:
## 
#  [](#/ServiceChecker/start)
#  
#  [](#/ServiceChecker/end)
##
## The content within the two 'links' will be replaced when the service is run.
## try it yourself at: <domain>/xbox/update-sidebar

## Change these settings:
settings = {
    'username': 'XbotOne',
    'password': '',
    'subreddit': 'XboxOne',
    'wiki_page': 'config/sidebar',
    'revision_message': 'BOT: XBL Status Update',
    'debug': False,
    # ==== DO NOT CHANGE THESE: ==== #
    'xbox_status_url': 'http://support.xbox.com/en-us/xbox-live-status', 
    'user_agent': '/r/xboxone Service Checker (by /u/tobiasvl)',
    'compare_start': '[](#/ServiceChecker/start)',
    'compare_end': '[](#/ServiceChecker/end)',
    'slack_token': '',
}

app = Flask(__name__)
app.config['DEBUG'] = settings['debug']

@app.route("/xbox/update-sidebar")
@app.route("/update-sidebar")
def parse():
    try:
        r = praw.Reddit(user_agent=settings['user_agent'], disable_update_check=True)
        r.config._ssl_url = None
        r.login(settings['username'], settings['password'])
    
        wikipage = r.get_wiki_page(settings['subreddit'], settings['wiki_page'])
        md = wikipage.content_md

        startIndex = md.find(settings['compare_start'])
        endIndex = md.find(settings['compare_end'])

        if startIndex != -1 and endIndex != -1:
            status = getXBLStatus()

            startMD = md[:startIndex + len(settings['compare_start']) + 1]
            endMD = md[endIndex:]

            table = """\r\n\r\n
Service | Status
---|---
Xbox Live Core Services | [""" + status['XboxLiveCoreServices'].title() + '](#/' + status['XboxLiveCoreServices'] + ' "' + status['XboxLiveCoreServices'].title() + """")
Purchase and Content Usage | [""" + status['PurchaseandContentUsage'].title() + '](#/' + status['PurchaseandContentUsage'] + ' "' + status['PurchaseandContentUsage'].title() + """")
Website | [""" + status['Website'].title() + '](#/' + status['Website'] + ' "' + status['Website'].title() +"""")
TV, Music and Video | [""" + status['TVMusicandVideo'].title() + '](#/' + status['TVMusicandVideo'] + ' "' + status['TVMusicandVideo'].title() + """")
Social and Gaming | [""" + status['SocialandGaming'].title() + '](#/' + status['SocialandGaming'] + ' "' + status['SocialandGaming'].title() + """")
\r\n\r\n
^(Last Updated: """ + datetime.now().strftime('%d-%b-%Y %H:%M:%S %Z') + """)
[**^(Status Page)**](""" + 'http://support.xbox.com/xbox-live-status' + ')\r\n\r\n'
            md = startMD + table + endMD

            # edit subreddit sidebar
            r.edit_wiki_page(settings['subreddit'], settings['wiki_page'], md, settings['revision_message'])

            # notify slack
            sc = Slacker(settings['slack_token'])
            # notice change
            f = open('/home/spug/xboxone.thespug.net/tmp/last_status', 'r')
            lines = [line.rstrip('\n') for line in f]
            f.close()

            for (line, service) in zip(lines, ('XboxLiveCoreServices', 'PurchaseandContentUsage', 'Website', 'TVMusicandVideo', 'SocialandGaming')):
                f2 = open('/home/spug/xboxone.thespug.net/tmp/debug', 'a')
                f2.write('{0}, {1}, {2}\n'.format(line, service, status[service]))
                f2.close()
                if line != status[service]:
                   sc.chat.post_message('#announcements', '{0} changed status from {1} to {2}'.format(service, line, status[service]), as_user=True)

            f = open('/home/spug/xboxone.thespug.net/tmp/last_status', 'w')
            for service in ('XboxLiveCoreServices', 'PurchaseandContentUsage', 'Website', 'TVMusicandVideo', 'SocialandGaming'):
                f.write(status[service] + '\n')

            f.close()

            return 'Success', 200
        else:
             return 'No Compare Container', 500
    except praw.errors.RateLimitExceeded:
        return 'Rate Limit', 500
    except praw.errors.InvalidUserPass:
        return 'Invalid User', 500
    except praw.errors.ModeratorRequired:
        return 'Not a Mod', 500
    return 'Unknown Failure', 500

@app.route('/')
def hello():
    """Return a friendly HTTP greeting."""
    return 'Hello World!'

@app.errorhandler(404)
def page_not_found(e):
    """Return a custom 404 error."""
    return 'Sorry, nothing at this URL.', 404

def getXBLStatus():
    soup = getHTMLSoup()
    results = dict()

    # Loop through all the LI elements in the core UL element
    # And get the status of each service
    for li in soup.find('ul', { 'class': 'core' }).find_all('li'):
        if li.has_key('id'):
            results[li.attrs['id']] = li.attrs['class'][1]
    return results

def getHTMLSoup():
    # Download the HTML source of the status page
    htmlDownloader = urllib.urlopen(settings['xbox_status_url'])
    htmlSource = htmlDownloader.read()
    htmlDownloader.close()
    return BeautifulSoup(htmlSource)

if __name__ == '__main__':
    app.run()
