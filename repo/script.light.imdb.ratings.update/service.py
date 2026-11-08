# -*- coding: utf-8 -*-

#############################
# Light IMDb Ratings Update #
# by axlt2002               #
#############################

import xbmc, xbmcaddon, xbmcvfs, xbmcgui
import time, _strptime
import datetime
from support.common import *
from core.database import update_database
from update import StartUpdate

if not xbmcvfs.exists( addonProfile ): xbmcvfs.mkdir( addonProfile )

WeekDay = addonSettings.getSetting( "WeekDay" )
DayTime = addonSettings.getSetting( "DayTime" )
ScheduleType = addonSettings.getSetting( "ScheduleType" )
IncludeTop250 = addonSettings.getSetting( "IncludeTop250" )

def UpdateSchedule():
    if ScheduleType == '0':
        day_difference = datetime.date.today().weekday() - int(WeekDay)
        if day_difference < 0:
            day_difference = -day_difference
        elif day_difference > 0:
            day_difference = 7-day_difference
        elif day_difference == 0 and time.strftime("%H:%M:%S") >= DayTime:
            day_difference = day_difference+7
        nextrun = datetime.datetime.now() + datetime.timedelta( days = day_difference )
    else:
        if time.strftime("%H:%M:%S") >= DayTime:
            nextrun = datetime.datetime.now() + datetime.timedelta( days = 1 )
        else:
            nextrun = datetime.datetime.now() + datetime.timedelta( days = 0 )
    nextruntime = DayTime
    addonSettings.setSetting( "ScheduledWeekDay", nextrun.strftime("%Y-%m-%d") )
    statusLog( "Next scheduled update: " + nextrun.strftime("%Y-%m-%d") + " at " + str( nextruntime ))
    xbmc.sleep(2000)

def AutoStart():
    addonSettings.setSetting( "PerformingUpdate", "false" )
    addonSettings.setSetting( "LogDialog", "false" )
    addonSettings.setSetting( "UpdatingDatabase", "false" )
    start_StatusLog()
    if UpdateDatabaseStartup == "true":
        update_database()
    monitor = xbmc.Monitor()
    while not monitor.abortRequested():
        monitor.waitForAbort(5)

        global IncludeTop250
        newIncludeTop250 = addonSettings.getSetting( "IncludeTop250" )
        if newIncludeTop250 != IncludeTop250:
            statusLog("Include Top 250 for movies set to " + newIncludeTop250)
            if newIncludeTop250 == "true":
                update_database()
        IncludeTop250 = newIncludeTop250

        if addonSettings.getSetting( "ScheduleEnabled" ) == "true":
            global WeekDay
            global DayTime
            global ScheduleType
            newWeekDay = addonSettings.getSetting( "WeekDay" )
            newScheduledTime = addonSettings.getSetting( "DayTime" )
            newScheduleType = addonSettings.getSetting( "ScheduleType" )
            if ( WeekDay != newWeekDay ) or ( DayTime != newScheduledTime ) or ( addonSettings.getSetting( "ScheduledWeekDay" ) == "2000-01-01") or ( newScheduleType != ScheduleType ):
                WeekDay = newWeekDay
                DayTime = newScheduledTime
                ScheduleType = newScheduleType
                UpdateSchedule()
            try:
                ScheduledDay = datetime.datetime.strptime( addonSettings.getSetting( "ScheduledWeekDay" ), "%Y-%m-%d" )
            except TypeError:
                ScheduledDay = datetime.datetime(*(time.strptime( addonSettings.getSetting( "ScheduledWeekDay" ), "%Y-%m-%d" )[0:6]))
            if ( datetime.datetime.now() >= ScheduledDay ):
                if ( time.strftime("%H:%M:%S") >= addonSettings.getSetting( "DayTime" ) ):
                    StartUpdate()
                    UpdateSchedule()

if (__name__ == "__main__"):
    AutoStart()