# BlueSky - The Open Air Traffic Simulator

This is just a fork of the original BlueSky repo used for the addition of the FlightPlanDatabase plug-in.
For more info see the original [bluesky repo](https://github.com/TUDelft-CNS-ATM/bluesky)

## Flight Plan Database
https://flightplandatabase.com/dev/api

## Requirements
```pip install requests```

## Idea
- Functions to communicate with Flight Plan Database
- Make scenario that uses this function (to auto create flightplan)
- Check whether nav points are already in bluesky database
    If not -> Add them as custom waypoints or only flight specific points

## Working
- ```fpldb_plug.py``` is the main program. This needs to be copied into the bluesky plugins folder
- In bluesky you need to enable the plugin by calling ```plugins load fpldb ```
- In bluesky the command needed is ```fplr```
- There is also an example scenario file that automatically loads the plugin file ```fpldb_scn.scn```

## Acknowledgements
This plugin is build for the use together with [bluesky](https://github.com/TUDelft-CNS-ATM/bluesky) built by the TU Delft Air Traffic Management department.

## Status
Work in Progress - Testing Version 1.0
