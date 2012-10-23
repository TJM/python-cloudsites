__author__ = "Tommy McNeely <tommy@lark-it.com>"
"""
Rackspace Cloud Sites Automation Library

    This attempts to provide a programatic interface to Rackspace Cloud Sites by parsing information
    and interactive with the control panel interface in lieu of an API.
"""

import mechanize
import re
import json

class CloudSitesError(Exception):
    """ Cloud Sites Error
    """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return(repr(self.value))

class Account(object):
    """ Rackspace Cloud Sites Account
            This is the starting point, first you must have an account with Rackspace to login to.
    """
    # Constants
    baseURL = 'https://manage.rackspacecloud.com'

    def __init__(self):
        """ INIT for CloudSites (what to put here?)
        """
        self.browser = mechanize.Browser()
        self.websiteList = { }
        self.databaseList = { }
        self.databaseDetail = { }
        self.cronList = { }
        self.clientList = None
        self.authenticated = False
        return

    def _isLoginPage(self, duringLogin = False):
        """ Determines if the current html page looks like a login page
        """
        for form in self.browser.forms():
            if (form.action.startswith(self.baseURL + '/Login.do')):
                self.authenticated = False
                return True
        return False

    def _openPath(self, path):
        """
            Open a page on Rackspace Cloud Sites, verify we didn't get "timed out"

            path - path to open
        """
        # First, attempt to figure out what "path" was, and construct a URL
        if path.startswith('http'):
            url = path
        elif path.startswith('/'):
            url = self.baseURL + path
        else: # assume they forgot the /
            url = self.baseURL + '/' + path
        # Actually Open the URL
        self.browser.open(url)
        # Attempt to determine if we have ended up at the Login Page
        if (self._isLoginPage()):
            raise CloudSitesError("ERROR: Session Timed Out or failed")
            # Perhaps we should "handle" this, like maybe logging in again?
            exit(1)
        return True

    def login(self,username, password):
        """ Login to the url, using the provided username and password

        Args:
            username
            password

        Returns: True or False
        """
        # Open the Login Page, and login
        b = self.browser
        b.open(self.baseURL + "/Login.do") # don't use _openPath() for this
        if (self._isLoginPage()):
            b.select_form(nr=0)
            b.form['username'] = username
            b.form['password'] = password
            resp = b.submit()
        else:
            raise CloudSitesError("Login Page Not Detected at Login")
            return False

        # OK, Login has been submitted, what do we have now?
        if (self._isLoginPage(True)):
            # Could check for "The username or password you entered is invalid."
            raise CloudSitesError("Login Failed")
            return False
        elif ( b.geturl() == (self.baseURL + '/Home.do') ):
            # May just need to be an empty "else" here?
            # Ugly Part - Parse the output to see if we are logged in or not
            html = resp.read()
            match = re.search(r'You are logged in as: \<strong\>(?P<username>\w+?)\</strong\>,\s+(?P<accountName>.+?) \(\#(?P<rsAccountID>\d+)\)', html)
            self.accountLogin = match.group(1)
            self.accountName = match.group(2)
            self.accountID = match.group(3)
            self.authenticated = True
            return True
        else:
            # Fail Gracefully? Maybe we were sent somewhere other than /Home.do?
            print "Potentially, that worked?"
            self.authenticated = True
            return True
        return

    def logout(self):
        """ Logout from Cloud Sites
            Probably would only call when exiting unless we needed to change accounts
        """
        b = self.browser
        b.open(self.baseURL + "/Logout.do") # don't use _openPath() for this
        # Reset all variables to the initial state (call __init__())
        self.__init__()
        return

    def _parseForJsVar(self,varName='listTableArgs'):
        """ Parse the HTML output of the current browser page for a specific
        JavaScript (JSON) variable. This is probably very specific to the way Rackspace
        formats their page.

        Args:
            varName = variable name to look for

        RETURN: json object representing the JSON parsed screen (or False)
        """
        html = self.browser.response().read()
        match = re.search(r'var\s+' + varName + r'\s*=\s*(?P<value>.*?);$',html, re.MULTILINE|re.DOTALL)
        if match:
            data = match.group(1).replace('\n','').replace(r'\"', '"').replace(r'\\"', r'\"')
            try:
                # Try loading the data using the json parser
                jsonData = json.loads(data)
            except:
                jsonData = False
                raise CloudSitesError('Error parsing JSON Data for var: ' + varName)
        else: # no match was found
            jsonData = False
            raise CloudSitesError('ERROR: The JS var: ' + varName + ' was not found or there was a matching issue.')
        return jsonData

    def _parseForJsVarPart(self,varName='tableData0'):
        """ Parse the HTML output of the *current* browser page for a specific
        JavaScript (JSON) variable. This is probably very specific to the way Rackspace
        formats their page. This will find a portion of the json object, usually tableData0.

        RETURN: json object representing the JSON parsed screen
        """
        html = self.browser.response().read()
        match = re.search(r'^\s*' + varName + ':\n*\"(?P<value>.*?)",$', html, re.MULTILINE|re.DOTALL)
        if match:
            data = match.group(1).replace('\n','').replace(r'\"', '"').replace(r'\\"', r'\"')
            try:
                # Try loading the data using the json parser
                jsonData = json.loads(data)
            except:
                jsonData = False
                raise CloudSitesError('Error parsing JSON Data for var: ' + varName)
        else: # no match was found
            jsonData = False
            raise CloudSitesError('ERROR: The JS var: ' + varName + ' was not found or there was a matching issue.')
        return jsonData

    def getClientList(self):
        """ Obtain a list of clients with the clientID and the management URL
        """
        if not self.authenticated:
            raise CloudSitesError("Please use login('username', 'password') method first")
        self._openPath('/ClientList.do')
        data = self._parseForJsVarPart('tableData0')
        # data['rows'] - list of clients
        # There is other information in tableData0, but all we want is the client rows for now
        self.clientList = data['rows']
        return data['rows']

    def displayClients(self):
        """ Display a Simple List of clients (for testing)
        """
        if not self.clientList:
            self.getClientList()
        data = self.clientList
        for client in iter(self.clientList):
            # client[2] is client ID
            # client[3] is a list containing ['Client Name', 'url']
            print 'ClientID: ' + client[2]
            print 'Client Company Name: ' + client[3][0]
            print 'URL: ' + self.baseURL + client[3][1]
            print
        return

### I should probably have a "Client" class here
###class Client(Account):

    def getWebsiteList(self,clientID):
        """ Get the websites configured for this client
        """
        if not self.authenticated:
            raise CloudSitesError("Please use login('username', 'password') method first")
        # maybe it would be better to find/click a link rather than constructing a URL?
        self._openPath('/ClientWebsiteList.do?accountID=' + clientID + '&pageTitle=ClientName')
        data = self._parseForJsVarPart('tableData0')
        # data['rows'] - list of clients
        # There is other information in tableData0, but all we want is the client rows for now
        self.websiteList[clientID] = data['rows']
        return data['rows']

    def displayWebsites(self,clientID):
        """ Display a Simple List of websites for a specific client (for testing)
        """
        if clientID not in self.websiteList: # Attempt to get it
            self.getWebsiteList(clientID)
        for website in iter(self.websiteList[clientID]):
            # website[0] is a list containing ['ClientID', '', '']
            # website[1] is "Full"
            # website[2] is a list containing ['domainName', 'url']
            # website[3] is "Site Name"
            print 'WebsiteID: ' + website[0][0]
            print 'Website Name: ' + website[3]
            print 'URL: ' + self.baseURL + website[2][1]
            print 'Domain Name: ' + website[2][0]
            print
        return

### I should probably have a "Website" class here
###class Website(Client)

    def getFeaturesForWebsite(self,clientID,websiteID):
        """ Get the Features configured on this website
            Features Include: databases, cronJobs, etc
        """
        if not self.authenticated:
            raise CloudSitesError("Please use login('username', 'password') method first")
        # maybe it would be better to find/click a link rather than constructing a URL?
        self._openPath('/WebsiteFeatures.do?accountID=' + clientID + '&siteID=' + websiteID+ '&pageTitle=WebsiteName')
        ##DOESNT WORK##data = self._parseForJsVar('listTableArgs')
        # data['tableData0'] -> databases
        # data['tableData1'] -> cron jobs
        dbList = self._parseForJsVarPart('tableData0')['rows']
        cronList = self._parseForJsVarPart('tableData1')['rows']

        self.databaseList[websiteID] = dbList
        self.cronList[websiteID] = cronList
        ###self.websiteList[clientID] = data['rows']
        return (dbList, cronList)

    def displayDatabases(self,clientID,websiteID):
        """ Display a Simple List of Databases for a specific website (for testing)
        """
        if clientID not in self.databaseList: # Attempt to get it
            self.getFeaturesForWebsite(clientID,websiteID)
        for db in iter(self.databaseList[websiteID]):
            # db[0] is a (checkbox)
            # db[1] is a number (index?)
            # db[2] is a list containing ['dbName', 'url']
            # db[3] is type (MySQL 5)
            print 'Database Name: ' + db[2][0]
            print 'Database Type: ' + db[3]
            print 'URL: ' + self.baseURL + db[2][1]
            print
        return

    def displayCronJobs(self,clientID,websiteID):
        """ Display a Simple List of cron jobs for a specific client (for testing)
        """
        if clientID not in self.cronList: # Attempt to get it
            self.getFeaturesForWebsite(clientID,websiteID)
        for job in iter(self.cronList[websiteID]):
            # job[0] is a list ['jobName', '', '']
            # job[1] is a number (index?)
            # job[2] is a list containing ['jobName', 'url']
            # job[3] is type (MySQL 5)
            print 'CronJob Name: ' + job[2][0]
            print 'URL: ' + self.baseURL + job[2][1]
            print
        return

    def getDatabaseDetail(self,websiteID,databaseName,serverID):
        """ Get the database details including server, users, etc
        """
        if not self.authenticated:
            raise CloudSitesError("Please use login('username', 'password') method first")
        # maybe it would be better to find/click a link rather than constructing a URL?
        self._openPath('/ViewDatabase.do?siteID=' + websiteID+ '&pageTitle=WebsiteName&databaseName='
                       + databaseName + '&serverId=' + serverID)
        # Things are about to get *ugly* 
        matches = re.search(r'<td class="itemName".*?>\s*(?P<itemName>[\w\s]*?)\s*</td>' +
	  r'.*?<td class="item".*?>\s*(?P<itemValue>[\w\s]*?)\s*</td>', html, re.MULTILINE|re.DOTALL)
        if matches:
            self.databaseDetail[databaseName] = { }
            for itemName, itemValue in matches:
                if (itemValue.find('<')>=0):
                    # Strip out the extra stuff we don't want
                    itemValue = re.search('(?:<.*?>)?(?P<value>[\w\d\-_\.\:\/]*)<', itemValue).group(1)
                self.databaseDetail[databaseName][itemName]=itemValue
        else:
            raise CloudSitesError("Error Parsing Database Details")
        self.databaseDetail[databaseName]['userList'] = self._parseForJsVarPart('tableData0')['rows']
        return self.databaseDetail[databaseName]

    def displayDatabaseDetail(self,databaseName):
        """ Display database detail for a specific database (for testing)
        """
        if databaseName not in self.databseDetail: # Attempt to get it
            #self.getDatabaseDetail(websiteID)
            raise CloudSitesError("ERROR: use getDatabseDetail() first")
        for itemName, itemValue in self.databaseDetail[databaseName].items():
            if (itemName != 'userList'):
                print itemName + ": " + itemValue
        print
        for user in iter(self.databaseDetail[databaseName]['userList']):
            # user[0] is a list ['userName', '', '']
            # user[1] is a number (index?)
            # user[2] is a list containing ['userName', 'url']
            print 'UserName: ' + user[2][0]
            print 'URL: ' + self.baseURL + user[2][1]
            print
        return
        
