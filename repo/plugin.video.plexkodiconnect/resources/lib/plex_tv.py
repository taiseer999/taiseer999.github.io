#!/usr/bin/env python
# -*- coding: utf-8 -*-
from logging import getLogger
import time
import threading
import xbmc

from .downloadutils import DownloadUtils as DU
from . import utils, app

###############################################################################
LOG = getLogger('PLEX.plex_tv')
###############################################################################


class HomeUser(utils.AttributeDict):
    """
    Turns an etree xml answer into an object with attributes
    Adds the additional properties:
        isProtected
        isAdmin
        isManaged
    """
    @property
    def isProtected(self):
        return self.protected == '1'

    @property
    def isAdmin(self):
        return self.admin == '1'

    @property
    def isManaged(self):
        return self.restricted == '1'


def switch_home_user(userid, pin, token, machine_identifier):
    """
    Retrieves Plex home token for a Plex home user. Returns None if this fails

    Input:
        userid          id of the Plex home user
        pin             PIN of the Plex home user, if protected
        token           token for plex.tv

    Output:
        usertoken       Might be empty strings if no token found
                        for the machine_identifier that was chosen
    """
    LOG.info('Switching to user %s', userid)
    url = 'https://plex.tv/api/home/users/%s/switch' % userid
    if pin:
        url += '?pin=%s' % pin
    xml = DU().downloadUrl(url,
                           authenticate=False,
                           action_type="POST",
                           headerOptions={'X-Plex-Token': token})
    try:
        xml.attrib
    except AttributeError:
        LOG.error('Switch HomeUser change failed')
        return

    username = xml.get('title', '')
    token = xml.get('authenticationToken', '')

    # Get final token to the PMS we've chosen
    url = 'https://plex.tv/api/resources?includeHttps=1'
    xml = DU().downloadUrl(url,
                           authenticate=False,
                           headerOptions={'X-Plex-Token': token})
    try:
        xml.attrib
    except AttributeError:
        LOG.error('Answer from plex.tv not as excepted')
        # Set to empty iterable list for loop
        xml = []

    LOG.debug('Our machine_identifier is %s', machine_identifier)
    for device in xml:
        identifier = device.attrib.get('clientIdentifier')
        LOG.debug('Found the Plex clientIdentifier: %s', identifier)
        if identifier == machine_identifier:
            token = device.attrib.get('accessToken')
            break
    else:
        LOG.info('No tokens found for your server! Using empty string')
        token = ''
    LOG.info('Plex.tv switch HomeUser change successfull for user %s',
             username)
    return token


def plex_home_users(token):
    """
    Returns a list of HomeUser elements from plex.tv
    """
    xml = DU().downloadUrl('https://plex.tv/api/home/users/',
                           authenticate=False,
                           headerOptions={'X-Plex-Token': token})
    users = []
    try:
        xml.attrib
    except AttributeError:
        LOG.error('Download of Plex home users failed.')
        # Plex.tv did not provide us a valid list of Plex users, sorry.
        utils.messageDialog(utils.lang(29999), utils.lang(33011))
    else:
        for user in xml:
            users.append(HomeUser(user.attrib))
    return users


class PinLogin(object):
    """
    Signs user in to plex.tv
    """
    INIT = 'https://plex.tv/pins.xml'
    POLL = 'https://plex.tv/pins/{0}.xml'
    ACCOUNT = 'https://plex.tv/users/account'
    POLL_INTERVAL = 1

    def __init__(self, callback=None):
        self._callback = callback
        self.id = None
        self.pin = None
        self.token = None
        self.finished = False
        self._abort = False
        self.expired = False
        self.xml = None
        self._init()

    def _init(self):
        xml = DU().downloadUrl(self.INIT,
                               authenticate=False,
                               action_type="POST")
        try:
            xml.attrib
        except AttributeError:
            LOG.error("Error, no PIN from plex.tv provided")
            raise RuntimeError
        self.pin = xml.find('code').text
        self.id = xml.find('id').text
        LOG.debug('Successfully retrieved code and id from plex.tv')

    def _poll(self):
        LOG.debug('Start polling plex.tv for token')
        start = time.time()
        while (not self._abort and
               time.time() - start < 300 and
               not app.APP.stop_pkc):
            xml = DU().downloadUrl(self.POLL.format(self.id),
                                   authenticate=False)
            try:
                token = xml.find('auth_token').text
            except AttributeError:
                app.APP.monitor.waitForAbort(self.POLL_INTERVAL)
                continue
            if token:
                self.token = token
                break
            app.APP.monitor.waitForAbort(self.POLL_INTERVAL)
        if self._callback:
            self._callback(self.token, self.xml)
        if self.token:
            # Use temp token to get the final plex credentials
            self.xml = DU().downloadUrl(self.ACCOUNT,
                                        authenticate=False,
                                        parameters={'X-Plex-Token': self.token})
        self.finished = True
        LOG.debug('Polling done')

    def start_token_poll(self):
        t = threading.Thread(target=self._poll, name='PIN-LOGIN:Token-Poll')
        t.start()
        return t

    def wait_for_token(self):
        t = self.start_token_poll()
        t.join()
        return self.token

    def abort(self):
        self._abort = True


def sign_in_with_pin():
    """
    Prompts user to sign in by visiting https://plex.tv/pin

    Writes to Kodi settings file and returns the HomeUser or None
    """
    LOG.info('Showing plex.tv sign in window')
    # Fix for:
    #   DEBUG: Activating window ID: 13000
    #   INFO: Activate of window '13000' refused because there are active modal dialogs
    #   DEBUG: Activating window ID: 13000
    xbmc.executebuiltin("Dialog.Close(all, true)")
    from .windows import background
    bkgrd = background.BackgroundWindow.create(function=_sign_in_with_pin)
    bkgrd.modal()
    xml = bkgrd.result
    del bkgrd

    if xml is None:
        return
    user = HomeUser(xml.attrib)
    utils.settings('myplexlogin', 'true')
    utils.settings('plex_status', value=utils.lang(39227))
    utils.settings('plexLogin', user.title)
    utils.settings('plexid', user.id)
    utils.settings('plexToken', user.authToken)
    return user


def _sign_in_with_pin():
    """
    Returns the user xml answer from plex.tv or None if unsuccessful
    """
    from .windows import signin, background

    background.setSplash(False)
    back = signin.Background.create()

    try:
        while True:
            pin_login_window = signin.PinLoginWindow.create()
            try:
                try:
                    pinlogin = PinLogin()
                except RuntimeError:
                    # Could not sign in to plex.tv Try again later
                    utils.messageDialog(utils.lang(29999), utils.lang(39305))
                    return
                pin_login_window.setPin(pinlogin.pin)
                pinlogin.start_token_poll()
                while not pinlogin.finished:
                    if pin_login_window.abort:
                        LOG.debug('Pin login aborted')
                        pinlogin.abort()
                        return
                    app.APP.monitor.waitForAbort(0.1)
                if not pinlogin.expired:
                    if pinlogin.xml is not None:
                        pin_login_window.setLinking()
                    return pinlogin.xml
            finally:
                pin_login_window.doClose()
                del pin_login_window
            if pinlogin.expired:
                LOG.debug('Pin expired')
                expired_window = signin.ExpiredWindow.open()
                try:
                    if not expired_window.refresh:
                        LOG.debug('Pin refresh aborted')
                        return
                finally:
                    del expired_window
    finally:
        back.doClose()
        del back


def get_pin():
    """
    For plex.tv sign-in: returns 4-digit code and identifier as 2 str
    """
    code = None
    identifier = None
    # Download
    xml = DU().downloadUrl('https://plex.tv/pins.xml',
                           authenticate=False,
                           action_type="POST")
    try:
        xml.attrib
    except AttributeError:
        LOG.error("Error, no PIN from plex.tv provided")
        return None, None
    code = xml.find('code').text
    identifier = xml.find('id').text
    LOG.info('Successfully retrieved code and id from plex.tv')
    return code, identifier


def check_pin(identifier):
    """
    Checks with plex.tv whether user entered the correct PIN on plex.tv/pin

    Returns None if not yet done so, or the XML response file as etree
    """
    # Try to get a temporary token
    xml = DU().downloadUrl('https://plex.tv/pins/%s.xml' % identifier,
                           authenticate=False)
    try:
        temp_token = xml.find('auth_token').text
    except AttributeError:
        LOG.error("Could not find token in plex.tv answer")
        return
    if not temp_token:
        return
    # Use temp token to get the final plex credentials
    xml = DU().downloadUrl('https://plex.tv/users/account',
                           authenticate=False,
                           parameters={'X-Plex-Token': temp_token})
    return xml
