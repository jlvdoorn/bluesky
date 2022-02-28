""" BlueSky Flight Plan Database plugin. This plugin can auto create a route 
based on a user input for point of departure and arrival using Flight Plan Database.
It then compares the points in this routes with the existing nav database in bluesky.
If the points are not already present, it will add them to the database."""

###################### TODO #################################
# Implement SID/STAR Runway selection                       #
# Add auto return flight - NOT POSSIBLE (INVALID STACK CMD) #
#############################################################


# Import the global bluesky objects. Uncomment the ones you need
from bluesky import core, stack, traf, settings, navdb, sim, scr, tools
from bluesky.tools import calculator
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

    def calcDirOut(self):
        """
        This function calculates the direction from the origin to the first wpt.
        """

        lata = self.nodeLat[0]
        lona = self.nodeLon[0]
        latb = self.nodeLat[1]
        lonb = self.nodeLon[1]
        dirOut = calculator.qdr(lata,lona,latb,lonb) # Degrees
        if dirOut < 0:
            dirOut = dirOut + 360       
        return dirOut  
    
    def calcDirIn(self):
        """
        This function calculates the direction from the last wpt to the destination.
        """

        lata = self.nodeLat[-2]
        lona = self.nodeLon[-2]
        latb = self.nodeLat[-1]
        lonb = self.nodeLon[-1]
        dirIn = calculator.qdr(lata,lona,latb,lonb) # Degrees
        if dirIn < 0:
            dirIn = dirIn + 360
        return dirIn

    def findEHAMSid(self):
        """
        This function finds and lists all the SIDs for EHAM.
        """

        sidAndik = []; keyAndik = 'ANDIK'
        sidArnem = []; keyArnem = 'ARNEM'
        sidBergi = []; keyBergi = 'BERGI'
        sidGorlo = []; keyGorlo = 'GORLO'
        sidKudad = []; keyKudad = 'KUDAD'
        sidLopik = []; keyLopik = 'LOPIK'
        sidRendi = []; keyRendi = 'RENDI'
        sidValko = []; keyValko = 'VALKO'
        sidBetus = []; keyBetus = 'BETUS'
        sidDenag = []; keyDenag = 'DENAG'
        sidEdupo = []; keyEdupo = 'EDUPO'
        sidElpat = []; keyElpat = 'ELPAT'
        sidLaras = []; keyLaras = 'LARAS'
        sidRoven = []; keyRoven = 'ROVEN'
        sidTorga = []; keyTorga = 'TORGA'
        sidWispa = []; keyWispa = 'WISPA'
        sidLekko = []; keyLekko = 'LEKKO'
        sidSpijk = []; keySpijk = 'SPIJKERBOOR'
        sidIvlut = []; keyIvlut = 'IVLUT'
        sidNopsu = []; keyNopsu = 'NOPSU'
        sidNyker = []; keyNyker = 'NYKER'
        sidOgina = []; keyOgina = 'OGINA'
        sidWoody = []; keyWoody = 'WOODY'

        for fname in os.listdir('scenario/eham'):
            if keyAndik in fname: sidAndik.append('eham/'+fname)
            elif keyArnem in fname: sidArnem.append('eham/'+fname)
            elif keyBergi in fname: sidBergi.append('eham/'+fname)
            elif keyGorlo in fname: sidGorlo.append('eham/'+fname)
            elif keyKudad in fname: sidKudad.append('eham/'+fname)
            elif keyLopik in fname: sidLopik.append('eham/'+fname)
            elif keyRendi in fname: sidRendi.append('eham/'+fname)
            elif keyValko in fname: sidValko.append('eham/'+fname)
            elif keyBetus in fname: sidBetus.append('eham/'+fname)
            elif keyDenag in fname: sidDenag.append('eham/'+fname)
            elif keyEdupo in fname: sidEdupo.append('eham/'+fname)
            elif keyElpat in fname: sidElpat.append('eham/'+fname)
            elif keyLaras in fname: sidLaras.append('eham/'+fname)
            elif keyRoven in fname: sidRoven.append('eham/'+fname)
            elif keyTorga in fname: sidTorga.append('eham/'+fname)
            elif keyWispa in fname: sidWispa.append('eham/'+fname)
            elif keyLekko in fname: sidLekko.append('eham/'+fname)
            elif keySpijk in fname: sidSpijk.append('eham/'+fname)
            elif keyIvlut in fname: sidIvlut.append('eham/'+fname)
            elif keyNopsu in fname: sidNopsu.append('eham/'+fname)
            elif keyNyker in fname: sidNyker.append('eham/'+fname)
            elif keyOgina in fname: sidOgina.append('eham/'+fname)
            elif keyWoody in fname: sidWoody.append('eham/'+fname)

        self.sidAndik = sidAndik; self.sidArnem = sidArnem; self.sidBergi = sidBergi; self.sidGorlo = sidGorlo; self.sidKudad = sidKudad
        self.sidLopik = sidLopik; self.sidRendi = sidRendi; self.sidValko = sidValko; self.sidBetus = sidBetus; self.sidDenag = sidDenag
        self.sidEdupo = sidEdupo; self.sidElpat = sidElpat; self.sidLaras = sidLaras; self.sidRoven = sidRoven; self.sidTorga = sidTorga
        self.sidWispa = sidWispa; self.sidLekko = sidLekko; self.sidSpijk = sidSpijk; self.sidIvlut = sidIvlut; self.sidNopsu = sidNopsu
        self.sidNyker = sidNyker; self.sidOgina = sidOgina; self.sidWoody = sidWoody
    
    def findEHAMStar(self):
        """
        This function finds and lists al the STARS for EHAM.
        """
        starDenut = []; keyDenut = 'DENUT'
        starEelde1A = []; keyEelde1A = 'EELDE-1A'
        starEelde1B = []; keyEelde1B = 'EELDE-1B'
        starHelen = []; keyHelen = 'HELEN'
        starLamso = []; keyLamso = 'LAMSO'
        starMolix = []; keyMolix = 'MOLIX'
        starNorku2A = []; keyNorku2A = 'NORKU-2A'
        starNorku2B = []; keyNorku2B = 'NORKU-2B'
        starPeser = []; keyPeser = 'PESER'
        starPutty = []; keyPutty = 'PUTTY'
        starRedfa = []; keyRedfa = 'REDFA'
        starRekken2A = []; keyRekken2A = 'REKKEN-2A'
        starRekken2B = []; keyRekken2B = 'REKKEN-2B'
        starToppa = []; keyToppa = 'TOPPA'

        for fname in os.listdir('scenario/eham'):
            if keyDenut in fname: starDenut.append('eham/'+fname)
            elif keyEelde1A in fname: starEelde1A.append('eham/'+fname)
            elif keyEelde1B in fname: starEelde1B.append('eham/'+fname)
            elif keyHelen in fname: starHelen.append('eham/'+fname)
            elif keyLamso in fname: starLamso.append('eham/'+fname)
            elif keyMolix in fname: starMolix.append('eham/'+fname)
            elif keyNorku2A in fname: starNorku2A.append('eham/'+fname)
            elif keyNorku2B in fname: starNorku2B.append('eham/'+fname)
            elif keyPeser in fname: starPeser.append('eham/'+fname)
            elif keyPutty in fname: starPutty.append('eham/'+fname)
            elif keyRedfa in fname: starRedfa.append('eham/'+fname)
            elif keyRekken2A in fname: starRekken2A.append('eham/'+fname)
            elif keyRekken2B in fname: starRekken2B.append('eham/'+fname)
            elif keyToppa in fname: starToppa.append('eham/'+fname)

        self.starDenut = starDenut; self.starEelde1A = starEelde1A; self.starEelde1B = starEelde1B; self.starHelen = starHelen; self.starLamso = starLamso
        self.starMolix = starMolix; self.starNorku2A = starNorku2A; self.starNorku2B = starNorku2B; self.starPeser = starPeser; self.starPutty = starPutty
        self.starRedfa = starRedfa; self.starRekken2A = starRekken2A; self.starRekken2B = starRekken2B; self.keyToppa = starToppa

    def checkDB(self):
        """
        This function checks the navdb of BlueSky. If any of the points in the downloaded flightplan
        is not yet in the navdb, then it adds them to the navdb for this user session. 
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
        This function adds all the points of the downloaded flightplan to the database.
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
        This function automatically adds a SID if the plane departs from EHAM (Schiphol).
        The chosen SID depends on the direction of the first waypoint (see calcDirOut()). 
        """

        self.findEHAMSid()

        dirOut = self.calcDirOut()
        if dirOut >= 16.5 and dirOut < 26.5:
            SIDs = self.sidNopsu
        elif dirOut >= 26.5 and dirOut < 32.5:
            SIDs = self.sidBetus
        elif dirOut >= 32.5 and dirOut < 38.5:
            SIDs = self.sidAndik
        elif dirOut >= 38.5 and dirOut < 70.5:
            SIDs = self.sidTorga
        elif dirOut >= 70.5 and dirOut < 99:
            SIDs = self.sidNyker
        elif dirOut >= 99 and dirOut < 101:
            SIDs = self.sidIvlut
        elif dirOut >= 101 and dirOut < 102.5:
            SIDs = self.sidElpat
        elif dirOut >= 102.5 and dirOut < 107.5:
            SIDs = self.sidArnem
        elif dirOut >= 107.5 and dirOut < 113.5:
            SIDs = self.sidRendi
        elif dirOut >= 113.5 and dirOut < 126.5:
            SIDs = self.sidEdupo
        elif dirOut >= 126.5 and dirOut < 142:
            SIDs = self.sidOgina   
        elif dirOut >= 142 and dirOut < 146.5:
            SIDs = self.sidRoven  
        elif dirOut >= 146.5 and dirOut < 162.5:
            SIDs = self.sidLopik  
        elif dirOut >= 162.5 and dirOut < 180.5:
            SIDs = self.sidLekko  
        elif dirOut >= 180.5 and dirOut < 186:
            SIDs = self.sidLaras
        elif dirOut >= 186 and dirOut < 191:
            SIDs = self.sidKudad  
        elif dirOut >= 191 and dirOut < 219:
            SIDs = self.sidWoody  
        elif dirOut >= 219 and dirOut < 245.5:
            SIDs = self.sidValko  
        elif dirOut >= 245.5 and dirOut < 258.5:
            SIDs = self.sidDenag 
        elif dirOut >= 258.5 and dirOut < 298.5:
            SIDs = self.sidGorlo
        elif dirOut >= 298.5 and dirOut < 327.5:
            SIDs = self.sidWispa  
        elif dirOut >= 327.5 and dirOut < 350:
            SIDs = self.sidBergi  
        elif dirOut >= 350 or dirOut < 16.5:
            SIDs = self.sidSpijk    

        rndmSID = SIDs[np.random.randint(0,len(SIDs))]
        stack.stack("pcall eham/deffix.scn")
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
        The chosen STAR depends on the direction of the last waypoint (see calcDirIn()).
        """

        self.findEHAMStar()

        dirIn = self.calcDirIn()
        if dirIn >= 13 and dirIn < 19.5:
            STARs = self.starPutty
        elif dirIn >= 19.5 and dirIn < 28:
            STARs = self.starHelen
        elif dirIn >= 28 and dirIn < 55.5:
            STARs = self.starDenut
        elif dirIn >= 55.5 and dirIn < 94.5:
            STARs = self.starRedfa
        elif dirIn >= 94.5 and dirIn < 111.5:
            STARs = self.starLamso
        elif dirIn >= 111.5 and dirIn < 129:
            STARs = self.starMolix
        elif dirIn >= 129 and dirIn < 188:
            STARs = self.starToppa
        elif dirIn >= 188 and dirIn < 252:
            STARs = np.concatenate((self.starEelde1A, self.starEelde1B))
        elif dirIn >= 252 and dirIn < 274:
            STARs = np.concatenate((self.starNorku2A, self.starNorku2B))
        elif dirIn >= 274 and dirIn < 324:
            STARs = np.concatenate((self.starRekken2A, self.starRekken2B))
        elif dirIn >= 324 or dirIn < 13:
            STARs = self.starPeser

        rndmSTAR = STARs[np.random.randint(0,len(STARs))]
        stack.stack("pcall eham/deffix.scn")
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
    acid: str
        callsign of the aircraft to create a route for (ex: KL575)
    fromICAO: str
        airport of departure in ICAO format
    toICAO: str
        airport of arrival in ICAO format
    """

    stack.stack("pause")
    r = Route(acid,fromICAO, toICAO); acid = acid.upper();  print('                                                  ')
    r.generate_fltplan();                                   print(acid+': Generated FPL')
    r.download_fltplan_data();                              print(acid+': Downloaded FPL')
    r.checkDB();                                            print(acid+': Checked DB')
    r.setOrig();                                            print(acid+': Origin Set')
    if fromICAO == "EHAM": r.addEHAMSid();                  print(acid+': SID Selected')
    r.addWPTToRoute();                                      print(acid+': Waypoints added to route')
    if toICAO == "EHAM": r.addEHAMStar();                   print(acid+': STAR Selected')
    r.setDest();                                            print(acid+': Destination Set')
    r.removeAtDest();                                       print('Flight '+acid+' will be deleted upon arrival')
    stack.stack(acid+" lnav on");                           print('                                                  ')
    stack.stack(acid+" vnav on")
    stack.stack("op")