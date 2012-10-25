__author__ = "Tommy McNeely <tommy@lark-it.com>"
"""
Rackspace Cloud Sites Automation Library

    This attempts to provide a programatic interface to Rackspace Cloud Sites by parsing information
    and interactive with the control panel interface in lieu of an API.
"""

import mechanize
import re
import json
import urllib



########## CloudSitesCommon ##########
class CloudSitesCommon(object):
    """ Rackspace Cloud Sites Common Object
            This is for common methods used by all classes.
    """
    # Constants
    baseURL = 'https://manage.rackspacecloud.com'

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
        # Sanitize
        url = urllib.quote_plus(url,safe="%/:=&?~#+!$,;'@()*[]")
        # Actually Open the URL
        self.browser.open(url)
        # Attempt to determine if we have ended up at the Login Page
        if (self._isLoginPage()):
            raise CloudSitesError("ERROR: Session Timed Out or failed")
            # Perhaps we should "handle" this, like maybe logging in again?
            exit(1)
        return True

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


########## CloudSitesError CLASS ##########
class CloudSitesError(Exception):
    """ Cloud Sites Error
    """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return(repr(self.value))


########## Account ##########
class Account(CloudSitesCommon):
    """ Rackspace Cloud Sites Account
            This is the starting point, first you must have an account with Rackspace to login to.
    """

    def __init__(self):
        """ INIT for CloudSites (what to put here?)
        """
        self.browser = mechanize.Browser()
        self.clientList = { }
        self.authenticated = False
        return

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
            if match:
                self.accountLogin = match.group(1)
                self.accountName = match.group(2)
                self.accountID = match.group(3)
                self.authenticated = True
                return True
            else:
                print "Post Login Page Parsing Problem (error in program or site)"
                ## This is actually probably a successful login, but the above parsing failed
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

    def getClientList(self):
        """ Obtain a list of clients with the clientID and the management URL
        """
        # Ensure we are authenticated
        if not self.authenticated:
            raise CloudSitesError("Please use login('username', 'password') method first")
        self._openPath('/ClientList.do')
        data = self._parseForJsVarPart('tableData0')
        # data['rows'] - list of clients
        # There is other information in tableData0, but all we want is the client rows for now
        for client in iter(data['rows']):
            # client[2] is client ID
            # client[3] is a list containing ['Client Name', 'url']
            clientID = client[2]
            name = client[3][0]
            url = client[3][1]
            self.clientList[clientID] = Client(self,clientID,name,url)
        return self.clientList.keys()

    def displayClients(self):
        """ Display a Simple List of clients (for testing)
        """
        if not self.clientList:
            self.getClientList()
        for client in self.clientList.itervalues():
            # client[0] is client ID
            # client[1] is a Client object
            print 'ClientID: ' + client.clientID
            print 'Client Name: ' + client.name
            print 'URL: ' + self.baseURL + client.url
            print
        return

    def getClient(self,clientID):
        """ Obtain a specific client object with the clientID
        """
        clientID = str(clientID)
        return self.clientList.get(clientID)



########## Client ##########
class Client(CloudSitesCommon):
    """ Rackspace Cloud Sites Client
            This object belongs to an Account object
    """

    def __init__(self, account, clientID, name, url):
        """ INIT for Client object
                ARGS:
                    - account - link back to parent account object
                    - ClientID - represents clientID in URLs
                    - name - Company Name (arbitrary right now)
                    - URL - URL to bring up client details
        """
        self.account = account
        self.clientID = str(clientID)
        self.name = str(name)
        self.url = str(url)
        self.websites = { }
        self.browser = account.browser
        return
    
    def getWebsiteList(self):
        """ Get the websites configured for this client
        """

        url = self.url.replace('/ClientSettings.do', '/ClientWebsiteList.do', 1)
        self._openPath(url)
        # maybe it would be better to find/click a link rather than constructing a URL?
        #self._openPath('/ClientWebsiteList.do?accountID=' + self.clientID + '&pageTitle=ClientName')
        data = self._parseForJsVarPart('tableData0')
        # data['rows'] - list of clients
        # There is other information in tableData0, but all we want is the client rows for now
        for website in iter(data['rows']):
            # website[0] is a list containing ['WebsiteID', '', '']
            # website[1] is "Full"
            # website[2] is a list containing ['domainName', 'url']
            # website[3] is "Site Name"
            websiteID = website[0][0]
            domainName = website[2][0]
            url = website[2][1]
            name = website[3]
            self.websites[websiteID] = Website(self, websiteID, name, url, domainName)
        return self.websites.keys()

    def displayWebsites(self):
        """ Display a Simple List of websites for a specific client (for testing)
        """

        if not self.websites: # Attempt to get it
            self.getWebsiteList()
        for website in self.websites.itervalues():
            # website - Website object
            print 'WebsiteID: ' + website.websiteID
            print 'Website Name: ' + website.name
            print 'URL: ' + self.baseURL + website.url
            print 'Domain Name: ' + website.domainName
            print
        return

    def getWebsite(self,websiteID):
        """ Obtain a specific website object with the websiteID
        """
        websiteID = str(websiteID)
        return self.websites.get(websiteID)


########## Website ##########
class Website(CloudSitesCommon):
    """ Rackspace Cloud Sites Website
            This object belongs to a Client object
    """

    def __init__(self, client, websiteID, name, url, domainName):
        """ INIT for Client object
                ARGS:
                    - client - link back to parent client object
                    - websiteID - represents websiteID in URLs
                    - name - Website Name (used in URLs)
                    - url - URL to bring up website settings
                    - domainName - domain name for the website
        """
        self.client = client
        self.clientID = client.clientID
        self.websiteID = str(websiteID)
        self.name = str(name)
        self.url = str(url)
        self.domainName = str(domainName)
        self.databaseList = { }
        self.cronList = None
        self.browser = client.browser
        return

    def getFeatures(self):
        """ Get the Features configured on this website
            Features Include: databases, cronJobs, etc
        """

        url = self.url.replace('/WebsiteSettings.do', '/WebsiteFeatures.do', 1)
        self._openPath(url)
        # maybe it would be better to find/click a link rather than constructing a URL?
        #self._openPath('/WebsiteFeatures.do?accountID=' + self.clientID + '&siteID=' + self.websiteID+ '&pageTitle=websiteName')
        ##DOESNT WORK##
        #data = self._parseForJsVar('listTableArgs')
        # data['tableData0'] -> databases
        # data['tableData1'] -> cron jobs
        #### Fall back to parsing for individual parts
        databases = self._parseForJsVarPart('tableData0')['rows']
        cronList = self._parseForJsVarPart('tableData1')['rows']

        for db in databases:
            # db[0] is a (checkbox)
            # db[1] is a number (index?)
            # db[2] is a list containing ['dbName', 'url']
            # db[3] is type (MySQL 5)
            name = db[2][0]
            dbType = db[3]
            url = db[2][1]
            self.databaseList[name] = Database(self, name, dbType, url)

        self.cronList = cronList

        return (self.databaseList.keys(), cronList)

    def displayDatabases(self):
        """ Display a Simple List of Databases for a specific website (for testing)
        """

        if not self.databaseList: # Attempt to get it
            self.getFeatures()
        for db in self.databaseList.itervalues():
            # db[0] is a (checkbox)
            # db[1] is a number (index?)
            # db[2] is a list containing ['dbName', 'url']
            # db[3] is type (MySQL 5)
            print 'Database Name: ' + db.name
            print 'Database Type: ' + db.dbType
            print 'URL: ' + self.baseURL + db.url
            print
        return

    def getDatabase(self,databaseName):
        """ Obtain a specific database object with the databaseName
        """
        databaseName = str(databaseName)
        return self.databaseList.get(databaseName)

    def displayCronJobs(self):
        """ Display a Simple List of cron jobs for a specific client (for testing)
        """
        
        if not self.cronList: # Attempt to get it
            self.getFeatures()
        for job in iter(self.cronList):
            # job[0] is a list ['jobName', '', '']
            # job[1] is a number (index?)
            # job[2] is a list containing ['jobName', 'url']
            # job[3] is type (MySQL 5)
            print 'CronJob Name: ' + job[2][0]
            print 'URL: ' + self.baseURL + job[2][1]
            print
        return

########## Database ##########
class Database(CloudSitesCommon):
    """ Rackspace Cloud Sites Website
            This object belongs to a Website object
    """

    def __init__(self, website, name, dbType, url):
        """ INIT for Client object
                ARGS:
                    - website - link back to parent website object
                    - name - Database Name (unique)
                    - dbType - type of database
                    - URL - URL to bring up website details
        """
        self.website = website
        self.websiteID = website.websiteID
        self.name = str(name)
        self.dbType = str(dbType)
        self.url = str(url)
        self.detail = { }
        self.users = { }
        self.browser = website.browser
        return
    
    def getDetail(self):
        """ Get the database details including server, users, etc
        """

        self._openPath(self.url)
        self._parseDatabaseDetail(self.browser.response().read())
        return self.detail

    def _parseDatabaseDetail(self, html):
        """ Parse the database detail out of the html and store in self.detail
        """
        # Things are about to get *ugly*
        matches = re.findall(r'<td class="itemName".*?>\s*(?P<itemName>[\w\s]*?)\s*</td>' +
	  r'.*?<td class="item".*?>\s*(?P<itemValue>.*?)\s*<[^a]', html, re.MULTILINE|re.DOTALL)
        if matches:
            for itemName, itemValue in matches:
                if (itemValue.find('href=')>=0):
                    # Pull href value out of link code
                    itemValue = re.search(r'href="(?P<url>.*?)"', itemValue).group(1)
                self.detail[itemName]=itemValue
        else:
            raise CloudSitesError("Error Parsing Database Details")
        userData = self._parseForJsVarPart('tableData0')['rows']
        for user in iter(userData):
            # user[0] is a list ['userName', '', '']
            # user[1] is a number (index?)
            # user[2] is a list containing ['userName', 'url']
            userName = user[2][0]
            userUrl = user[2][1]
            self.users[userName] = userUrl        
        return

    def displayDetail(self):
        """ Display database detail for a specific database (for testing)
        """

        if not self.detail: # Attempt to get it
            self.getDetail()
        for itemName, itemValue in self.detail.items():
            if (itemName != 'userList'):
                print itemName + ": " + itemValue
        print
        for userName in self.users.keys():
            # user -> url
            print 'UserName: ' + userName
            print 'URL: ' + self.baseURL + self.users[userName]
            print
        return

    def createUser(self, username, password):
        """ Create a database user for this database
            ARGS:
                - username = Database Username (not including the customerid_ part) [a-z 0-9] (max 8 chars)
                - password = Password for Database User (min 8 chars, max 128 chars)
        """
        username = str(username)
        password = str(password)

        if len(username) > 8 or len(username) < 1:
            raise CloudSitesError("Username must be between 1 and 8 chars")
            return False

        if len(password) < 8 or len(password) > 128:
            raise CloudSitesError("Username must be between 1 and 8 chars")
            return False

        # We could do validation of the username/password, but it would be better to just let rackspace fail it for now

        # Open the Database Page and fill out the "DatabaseForm" (add user form)
        self._openPath(self.url)
        b = self.browser
        b.select_form(name='DatabaseForm')
        b.form['databaseUsername'] = username
        b.form['databasePassword'] = password
        b.form['databasePasswordConfirm'] = password
        r = b.submit()
        html = r.read()
        match = re.search(r'error has occurred',html)
        if match:
            raise CloudSitesError("Error adding user")
            return False
        self._parseDatabaseDetail(html)
        return True

    def _NYI_deleteUser(self, username):
        """ Delete a database user for this database
            ARGS:
                - username = Database Username (including the customerid_ part) [a-z 0-9] (max 8 chars)
        """
        username = str(username)

        if len(username) > 8 or len(username) < 1:
            raise CloudSitesError("Username must be between 1 and 8 chars")
            return False

        if username not in self.users:
            raise CloudSitesError("Username " + username + " not found")
            return False

        ### NOT YET IMPLEMENTED
        ### REASON: the "controls" (checkboxes) to delete users are created with javascript, which is not being processed here
        ### --- will have to fake it to make it work :P
        raise CloudSitesError("deleteUser is not yet implemented")


        # Open the Database Page and fill out the "DeleteUser" form (doesn't appear to have a name)
        b = self.browser
        self._openPath(self.url)
        for form in b.forms():
            if (form.action.startswith(self.baseURL + '/DeleteDatabaseUsers.do')):
                break
        ## FIXME: This is not right
        #b.form['usernames'][username].selected = True
        return False

    def changePassword(self, username, password):
        """ Change password for a database user for this database
            ARGS:
                - username = Database Username (not including the customerid_ part) [a-z 0-9] (max 8 chars)
                - password = New Password for Database User (min 8 chars, max 128 chars)
        """
        username = str(username)
        password = str(password)

        if username not in self.users:
            raise CloudSitesError("Username " + username + " not found")
            return False

        if len(password) < 8 or len(password) > 128:
            raise CloudSitesError("Username must be between 1 and 8 chars")
            return False
        
        # We could do validation of the password, but it would be better to just let rackspace fail it for now

        # Open the Database Page and fill out the "DatabaseForm"
        self._openPath(self.users[username])
        b = self.browser
        b.select_form(name='DatabaseForm')
        b.form['databasePassword'] = password
        b.form['databasePasswordConfirm'] = password
        r = b.submit()
        html = r.read()
        match = re.search(r'error has occurred',html)
        if match:
            raise CloudSitesError("Error adding user")
            return False
        self._parseDatabaseDetail(html)
        return True

