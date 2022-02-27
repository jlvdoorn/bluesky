""" BlueSky Flight Plan Database plugin. This plugin can auto create a route 
based on a user input for point of departure and arrival using Flight Plan Database.
It then compares the points in this routes with the existing nav database in bluesky.
If the points are not already present, it will add them to the database."""

###################### TODO ###########################
# Implement SID/STAR                                  #
# Add auto return flight after time interval - Option #
#######################################################


# Import the global bluesky objects. Uncomment the ones you need
from bluesky import core, stack, traf, settings, navdb, sim, scr, tools
import requests, json
import numpy as np
import os, time

### Initialization function of your plugin. Do not change the name of this
### function, as it is the way BlueSky recognises this file as a plugin.
def init_plugin():
    """
    An initiation function of the plugin. 
    This function is called when the plugin is loaded.
    It gives defines the type and the name of the plugin.
    """

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
        """
        The init function of the class Route. This function is called when a new route 
        is created using this class. It sets parameters as the:
        - apiUrl and apiKey
        - acid
        - fromICAO
        - toICAO

        Parameters
        ----------
        acid : str
        fromICAO : str, optional
            The origin of the aircraft. Default: EHAM
        toICAO : str, optional
            The destination of the aircraft. Default: LFMN
        """
        self.apiUrl = "https://api.flightplandatabase.com/"
        self.apiKey = "1328fIdYaRVo8Yx5nJiw3jtFB2O2L5sE0OVGX7Md"
        self.jsonFormat = "application/json"
        self.fplFormat = "application/vnd.fpd.export.v1.json+json"
        self.acid = acid
        self.fromICAO = fromICAO
        self.toICAO = toICAO

    def generate_fltplan(self):
        """
        This function creates a flight plan with the use of FlightPlanDatabase.
        The aircraft id, origin and destination are used that are defined when calling the FPLR command.
        """

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
        """
        This function downloads the data of the flightplan created. It then implements this data into the object itself.
        """

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
            
    def checkDB(self):
        """
        This function checks the navdb of BlueSky. If any of the points in the downloaded flightplan
        is not yet in the navdb, then it adds them to the navdb for this user sessions. 
        """

        for node in range(len(self.nodeIdent)):
            if self.nodeIdent[node] in navdb.wpid:
                # WPT is already in navdb
                pass
            else:
                # Add WPT to navdb for this user session based on wpt type
                if self.nodeType[node] == 'VOR' or self.nodeType[node] == 'NDB' or self.nodeType[node] == 'ILS' or self.nodeType[node] == 'LOC' or self.nodeType[node] == 'GS' or self.nodeType[node] == 'OM' or self.nodeType[node] == 'MM' or self.nodeType[node] == 'IM' or self.nodeType[node] == 'DME' or self.nodeType[node] == 'TACAN' or self.nodeType[node] == 'FIX':
                    navdb.defwpt(self.nodeIdent[node],self.nodeLat[node],self.nodeLon[node],self.nodeType[node])
                else:
                    pass

    def addAllWPTToDB(self):
        """
        This function adds all the points of the downloaded flightplan to the current user database.
        The database is used only for the current simulation, so the points are removed after the simulation ends.
        """

        for node in range(len(self.nodeIdent)):
            if self.nodeType[node] == 'VOR' or self.nodeType[node] == 'NDB' or self.nodeType[node] == 'ILS' or self.nodeType[node] == 'LOC' or self.nodeType[node] == 'GS' or self.nodeType[node] == 'OM' or self.nodeType[node] == 'MM' or self.nodeType[node] == 'IM' or self.nodeType[node] == 'DME' or self.nodeType[node] == 'TACAN' or self.nodeType[node] == 'FIX':
                navdb.defwpt(self.nodeIdent[node],self.nodeLat[node],self.nodeLon[node],self.nodeType[node])
            else:
                pass

    def setOrig(self):
        """
        This function sets the origin of the route
        """

        stack.stack("ORIG "+self.acid+" "+self.fromICAO)

    def addEHAMSid(self):
        """
        This function automatically adds a random SID if the plane departs from EHAM (Schiphol)
        """

        SIDs = []
        keySID = 'SID-'
        for fname in os.listdir('scenario/eham'):
            if keySID in fname:
                sidFName = fname
                SIDs.append('eham/'+fname)

        rndmSID = SIDs[np.random.randint(0,len(SIDs))]
        if self.fromICAO == "EHAM":
            stack.stack("pcall "+rndmSID+" "+self.acid+" abs")

        
    def addWPTToRoute(self):
        """
        This function adds all the points in the downloaded flightplan to the current route of an aircraft. 
        The route then ceated is a 3D trajectory.
        """

        for node in range(len(self.nodeIdent)):    
            if self.nodeType == 'VOR' or self.nodeType[node] == 'NDB' or self.nodeType[node] == 'ILS' or self.nodeType[node] == 'LOC' or self.nodeType[node] == 'GS' or self.nodeType[node] == 'OM' or self.nodeType[node] == 'MM' or self.nodeType[node] == 'IM' or self.nodeType[node] == 'DME' or self.nodeType[node] == 'TACAN' or self.nodeType[node] == 'FIX':      
                stack.stack(self.acid+" ADDWPT "+self.nodeIdent[node]+" "+str(self.nodeAlt[node]))

    def addEHAMStar(self):
        """
        This function automatically adds a random STAR if the plane arrives at EHAM (Schiphol)
        """

        STARs = []
        keySTAR = 'STAR-'
        for fname in os.listdir('scenario/eham/'):
            if keySTAR in fname:
                STARs.append('eham/'+fname)

        rndmSTAR = STARs[np.random.randint(0,len(STARs))]
        if self.toICAO == "EHAM":
            stack.stack("pcall "+rndmSTAR+" "+self.acid+" abs")

    def setDest(self):
        """
        This function sets the destination of the route
        """

        stack.stack("DEST "+self.acid+" "+self.toICAO)       
        
    def removeAtDest(self):
        """
        This function removes a flight when it reaches its destination.
        """

        stack.stack(self.acid+" AT "+self.toICAO+" DO DEL "+self.acid) 

    def createReturn(self):
        """
        This function will have an aircraft hold at its destination for 1 hour and 
        then create a return route back to the origin.

        WARNING
        -------
        CURRENTLY BLUESKY DOES NOT RECOGNIZE 'delay' AS A VALID STACK COMMAND TO DO 'at' A CERTAIN POINT - WORK IN PROGRESS
        """

        returnCMD = "DELAY 01:00:00.00, fplr "+self.acid+" "+self.toICAO+" "+self.fromICAO
        stack.stack(self.acid+" AT "+self.toICAO+" DO STACK "+returnCMD)

@stack.command(name='FPLR')
def createRoute(acid: str,fromICAO: str = "EHAM",toICAO: str = "LFMN"):
    """
    This command will create a route from a starting ICAO to arriving ICAO using flight plan database.
    Furthermore it will check if the route points are already in the navdb of bluesky and will add them if they are not.

    Parameters
    ----------
    fromICAO: str
        airport of departure in ICAO format
    toICAO: str
        airport of arrival in ICAO format
    """

    stack.stack("pause")
    r = Route(acid,fromICAO, toICAO)
    r.generate_fltplan()
    r.download_fltplan_data()
    r.checkDB()
    r.setOrig()
    r.addEHAMSid()
    r.addWPTToRoute()
    r.addEHAMStar()
    r.setDest()
    r.removeAtDest() # or r.createReturn()
    stack.stack(acid+" lnav on")
    stack.stack(acid+" vnav on")
    stack.stack("op")