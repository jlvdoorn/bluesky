""" BlueSky Flight Plan Database plugin. This plugin can auto create a route 
based on a user input for point of departure and arrival using Flight Plan Database.
It then compares the points in this routes with the existing nav database in bluesky.
If the points are not already present, it will add them to the database."""

###################### TODO ####################
# Implement SID/STAR                           #
# Fix CheckDB?!                                #
# Add airways?                                 #
################################################


# Import the global bluesky objects. Uncomment the ones you need
from bluesky import core, stack, traf, settings, navdb, sim, scr, tools
import requests, json

### Initialization function of your plugin. Do not change the name of this
### function, as it is the way BlueSky recognises this file as a plugin.
def init_plugin():

    # Addtional initilisation code
    
    # Configuration parameters
    config = {
        # The name of your plugin
        'plugin_name':     'FPLDB',

        # The type of this plugin.
        'plugin_type':     'sim'    
        }

    # init_plugin() should always return the config dict.
    return config

class Route():  
    def __init__(self,acid: str,fromICAO: str = "EHAM",toICAO: str = "LFMN"):
        self.apiUrl = "https://api.flightplandatabase.com/"
        self.apiKey = "1328fIdYaRVo8Yx5nJiw3jtFB2O2L5sE0OVGX7Md"
        self.jsonFormat = "application/json"
        self.fplFormat = "application/vnd.fpd.export.v1.json+json"
        self.acid = acid
        self.fromICAO = fromICAO
        self.toICAO = toICAO

    def generate_fltplan(self):
        ## Generate flightplan
        genUrl = "https://api.flightplandatabase.com/auto/generate"
        data = {"fromICAO":self.fromICAO,"toICAO":self.toICAO}
        headers = {"Content-Type":self.jsonFormat,"Units":"AVIATION"}
        response = requests.post(genUrl, data=json.dumps(data), headers=headers, auth=(self.apiKey,' '))
        jR = response.json()

        self.id = jR["id"]
        self.fromName = jR["fromName"]
        self.toName = jR["toName"]
        self.flightNumber = jR["flightNumber"]
        self.distance = jR["distance"]
        self.maxAltitude = jR["maxAltitude"]
        self.waypoints = jR["waypoints"]
        self.notes = jR["notes"]
        self.encodedPolyline = jR["encodedPolyline"]

    def download_fltplan_data(self):
        ## Download flightplan data
        dataUrl = "https://api.flightplandatabase.com/plan/"
        data = {"id":int(self.id)}
        headers = {"Content-Type":self.fplFormat,"Units":"METRIC"}
        response = requests.get(dataUrl+str(self.id), data=json.dumps(data), headers=headers, auth=(self.apiKey,' '))
        jR = response.json()
        route = jR["route"]
        nodes = route["nodes"]

        ## Data processing
        nodeType = []
        nodeIdent = []
        nodeName = []
        nodeLat = []
        nodeLon = []
        nodeAlt = []
        nodeVia = []
        for node in nodes:
            nodeType.append(node["type"])
            nodeIdent.append(node["ident"])
            nodeName.append(node["name"])
            nodeLat.append(node["lat"])
            nodeLon.append(node["lon"])
            nodeAlt.append(node["alt"])
            nodeVia.append(node["via"])

        self.nodeType = nodeType
        self.nodeIdent = nodeIdent
        self.nodeName = nodeName
        self.nodeLat = nodeLat
        self.nodeLon = nodeLon
        self.nodeAlt = nodeAlt
        self.nodeVia = nodeVia
            
    def checkDB(self): # Checks navdb and adds points if they are missing
        for node in range(len(self.nodeIdent)):
            for wpt in navdb.wpid:
                if wpt == self.nodeIdent[node]:
                    # WPT is already in navdb
                    pass
                else:
                    # Add WPT to navdb based on wpt type
                    if self.nodeType[node] == 'VOR' or self.nodeType[node] == 'NDB' or self.nodeType[node] == 'ILS' or self.nodeType[node] == 'LOC' or self.nodeType[node] == 'GS' or self.nodeType[node] == 'OM' or self.nodeType[node] == 'MM' or self.nodeType[node] == 'IM' or self.nodeType[node] == 'DME' or self.nodeType[node] == 'TACAN' or self.nodeType[node] == 'FIX':
                        navdb.defwpt(self.nodeIdent[node],self.nodeLat[node],self.nodeLon[node],self.nodeType[node])
                    else:
                        pass

    def addToDB(self):
        for node in range(len(self.nodeIdent)):
            if self.nodeType[node] == 'VOR' or self.nodeType[node] == 'NDB' or self.nodeType[node] == 'ILS' or self.nodeType[node] == 'LOC' or self.nodeType[node] == 'GS' or self.nodeType[node] == 'OM' or self.nodeType[node] == 'MM' or self.nodeType[node] == 'IM' or self.nodeType[node] == 'DME' or self.nodeType[node] == 'TACAN' or self.nodeType[node] == 'FIX':
                navdb.defwpt(self.nodeIdent[node],self.nodeLat[node],self.nodeLon[node],self.nodeType[node])
            else:
                pass

    def addWPT(self): # Adds all waypoints to route
        for node in range(len(self.nodeIdent)):
            stack.stack("ORIG "+self.acid+" "+self.fromICAO)
            stack.stack("ADDWPT "+self.acid+" "+self.nodeIdent[node]+" "+str(self.nodeAlt[node]))
            stack.stack("DEST "+self.acid+" "+self.toICAO)

@stack.command(name='FPLR')
def createRoute(acid: str,fromICAO: str = "EHAM",toICAO: str = "LFMN"):
    ''''
    This command will create a route from a starting ICAO to arriving ICAO using flight plan database.
    Furthermore it will check if the route points are already in the nav database of bluesky and will add them if they are not.

    Arguments:
    - fromICAO: airport of departure in ICAO format
    - toICAO: airport of arrival in ICAO format
    '''
    r = Route(acid,fromICAO, toICAO)
    r.generate_fltplan()
    r.download_fltplan_data()
    #r.checkDB()
    r.addToDB()
    r.addWPT()
    stack.stack(acid+" lnav on")
    stack.stack(acid+" vnav on")