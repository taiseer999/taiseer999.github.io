from __future__ import absolute_import

from lib import util
from . import kodigui


class OptionsDialog(kodigui.BaseDialog):
    xmlFile = 'script-plex-options_dialog.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    GROUP_ID = 100
    BUTTON_IDS = (1001, 1002, 1003)

    def __init__(self, *args, **kwargs):
        kodigui.BaseDialog.__init__(self, *args, **kwargs)
        self.header = kwargs.get('header')
        self.info = kwargs.get('info')
        self.button0 = kwargs.get('button0')
        self.button1 = kwargs.get('button1')
        self.button2 = kwargs.get('button2')
        self.actionCallback = kwargs.get('action_callback')
        self.buttonChoice = None

    def onFirstInit(self):
        self.setProperty('header', self.header)
        self.setProperty('info', self.info)

        if self.button2:
            self.setProperty('button.2', self.button2)

        if self.button1:
            self.setProperty('button.1', self.button1)

        if self.button0:
            self.setProperty('button.0', self.button0)

        self.setBoolProperty('initialized', True)
        util.MONITOR.waitForAbort(0.1)
        self.setFocusId(self.BUTTON_IDS[0])

    def onAction(self, action):
        controlID = self.getFocusId()
        actionID = action.getId()

        if self.actionCallback:
            res = self.actionCallback(self, actionID, controlID)
            if res:
                return

        kodigui.BaseDialog.onAction(self, action)

    def onClick(self, controlID):
        if controlID in self.BUTTON_IDS:
            self.buttonChoice = self.BUTTON_IDS.index(controlID)
            self.doClose()


def show(header, info, button0=None, button1=None, button2=None, action_callback=None, dialog_props=None):
    w = OptionsDialog.open(header=header, info=info, button0=button0, button1=button1, button2=button2,
                           action_callback=action_callback, dialog_props=dialog_props)
    choice = w.buttonChoice
    del w
    util.garbageCollect()
    return choice
