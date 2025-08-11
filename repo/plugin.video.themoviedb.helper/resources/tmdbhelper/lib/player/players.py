import re
from xbmcgui import Dialog
from xbmcaddon import Addon as KodiAddon
from jurialmunkey.window import get_property
from tmdbhelper.lib.addon.plugin import ADDONPATH, PLUGINPATH, format_folderpath, get_localized, get_setting, executebuiltin
from jurialmunkey.parser import try_int, boolean
from tmdbhelper.lib.addon.consts import PLAYERS_PRIORITY, PLAYERS_CHOSEN_DEFAULTS_FILENAME
from tmdbhelper.lib.api.kodi.rpc import get_directory, KodiLibrary
from tmdbhelper.lib.player.inputter import KeyboardInputter
from tmdbhelper.lib.player.actions.resolver import ResolverPlayerSelect
from tmdbhelper.lib.addon.logger import kodi_log
from tmdbhelper.lib.addon.thread import SafeThread
from tmdbhelper.lib.player.phacks.phacks import PlayerHacks
from jurialmunkey.ftools import cached_property


class PlayerMethods():
    def string_format_map(self, fmt):
        return fmt.format_map(self.item)  # NOTE: .format(**d) works in Py3.5 but not Py3.7+ so use format_map(d) instead

    def set_external_ids(self, required=True):
        if required and self.details:
            self.thread_external_ids.join()
            self.details.set_details(details=self.external_ids, reverse=True)
        return self.set_detailed_item()

    def get_local_item(self):
        if not get_setting('default_player_kodi', 'int'):
            return []
        file = self.get_local_movie() if self.tmdb_type == 'movie' else self.get_local_episode()
        if not file:
            return []
        return [{
            'name': f'{get_localized(32061)} Kodi',
            'is_folder': False,
            'is_local': True,
            'is_resolvable': "true",
            'make_playlist': "true",
            'plugin_name': 'xbmc.core',
            'plugin_icon': f'{ADDONPATH}/resources/icons/other/kodi.png',
            'actions': file}]

    def get_local_movie(self):
        k_db = KodiLibrary(dbtype='movie')
        dbid = k_db.get_info(
            'dbid', fuzzy_match=False,
            tmdb_id=self.item.get('tmdb'),
            imdb_id=self.item.get('imdb'))
        if not dbid:
            return
        if self.details:  # Add dbid to details to update our local progress.
            self.details.infolabels['dbid'] = dbid
        return self.get_local_file(k_db.get_info('file', fuzzy_match=False, dbid=dbid))

    def get_local_episode(self):
        self.set_external_ids(required=True)  # Note: Don't forget about libraries that need TVDB ids from Trakt!!! Need to join ID lookup thread here!!!
        dbid = KodiLibrary(dbtype='tvshow').get_info(
            'dbid', fuzzy_match=False,
            tmdb_id=self.item.get('tmdb'),
            tvdb_id=self.item.get('tvdb'),
            imdb_id=self.item.get('imdb'))
        return self.get_local_file(KodiLibrary(dbtype='episode', tvshowid=dbid).get_info(
            'file', season=self.item.get('season'), episode=self.item.get('episode')))

    @staticmethod
    def get_local_file(file):
        if not file:
            return
        if file.endswith('.strm'):
            from tmdbhelper.lib.files.futils import read_file
            contents = read_file(file)
            if contents.startswith('plugin://plugin.video.themoviedb.helper'):
                return
            return contents
        return file

    def get_providers(self):
        try:
            self._providers = self.details.infoproperties['providers'].split(' / ')
        except (KeyError, AttributeError):
            self._providers = None
        return self._providers

    def get_player_priority(self, player):
        player_provider = self.providers and player.get('provider')
        if player_provider and player_provider in self.providers:
            priority = self.providers.index(player_provider) + 1  # Add 1 because sorted() puts 0 index last
            return (True, priority)
        if player.get('is_provider', True):
            priority = player.get('priority', PLAYERS_PRIORITY) + 100  # Increase priority baseline by 100 to prevent other players displaying above providers
        return (False, priority)

    def get_prioritised_players(self):

        def _set_priority(item):
            _, player = item
            player['is_provider'], player['priority'] = self.get_player_priority(player)
            return player['priority'], player.get('plugin', '\uFFFF').lower()

        self._players_prioritised = sorted(self.players.items(), key=_set_priority)
        return self._players_prioritised

    def get_chosen_default(self):
        """
        Check if chosen item has a specific default player and return it as 'filename mode'
        """
        from tmdbhelper.lib.files.futils import get_json_filecache
        cd = get_json_filecache(PLAYERS_CHOSEN_DEFAULTS_FILENAME)
        if not cd:
            self._chosen_default = None
            return self._chosen_default
        try:
            if self.tmdb_type == 'movie':
                cd = cd['movie'][f'{self.tmdb_id}']
                return f"{cd['file']} {cd['mode']}"
            cd = cd['tv'][f'{self.tmdb_id}']
            cd = cd.get('season', {}).get(f'{self.season}') or cd
            cd = cd.get('episode', {}).get(f'{self.episode}') or cd
            self._chosen_default = f"{cd['file']} {cd['mode']}"
            return self._chosen_default
        except KeyError:
            self._chosen_default = None
            return self._chosen_default

    def get_dialog_players(self):

        def _check_assert(keys=tuple()):
            if not self.item:
                return True  # No item so no need to assert values as we're only building to choose default player
            for i in keys:
                if i.startswith('!'):  # Inverted assert check for NOT value
                    if self.item.get(i[1:]) and self.item.get(i[1:]) != 'None':
                        return False  # Key has a value so player fails assert check
                else:  # Standard assert check for value
                    if not self.item.get(i) or self.item.get(i) == 'None':
                        return False  # Key didn't have a value so player fails assert check
            return True  # Player passed the assert check

        dialog_play = self.get_local_item()
        dialog_search = []

        for file, player in self.players_prioritised:

            if player.get('disabled', '').lower() == 'true':
                continue  # Skip disabled players

            if self.tmdb_type == 'movie':
                if player.get('play_movie') and _check_assert(player.get('assert', {}).get('play_movie', [])):
                    dialog_play.append(self.get_built_player(player_id=file, mode='play_movie', player=player))
                if player.get('search_movie') and _check_assert(player.get('assert', {}).get('search_movie', [])):
                    dialog_search.append(self.get_built_player(player_id=file, mode='search_movie', player=player))
                continue

            if self.tmdb_type == 'tv':
                if player.get('play_episode') and _check_assert(player.get('assert', {}).get('play_episode', [])):
                    dialog_play.append(self.get_built_player(player_id=file, mode='play_episode', player=player))
                if player.get('search_episode') and _check_assert(player.get('assert', {}).get('search_episode', [])):
                    dialog_search.append(self.get_built_player(player_id=file, mode='search_episode', player=player))
                continue

        return dialog_play + dialog_search

    def get_built_player(self, player_id, mode, player=None):
        player = player or self.players.get(player_id)
        if player:
            file = player_id
        else:
            for file, player in self.players_prioritised:
                if mode not in player:
                    continue
                if player_id in (player.get('plugin'), player.get('provider'), player.get('name')):
                    break
            else:
                file = player_id
                player = {}
        if mode in ['play_movie', 'play_episode']:
            name = get_localized(32061)
            is_folder = False
        else:
            name = get_localized(137)
            is_folder = True
        return {
            'file': file, 'mode': mode,
            'is_folder': is_folder,
            'is_provider': player.get('is_provider') if not is_folder else False,
            'is_resolvable': player.get('is_resolvable'),
            'requires_ids': player.get('requires_ids', False),
            'make_playlist': player.get('make_playlist'),
            'api_language': player.get('api_language'),
            'language': player.get('language'),
            'name': f'{name} {player.get("name")}',
            'plugin_name': player.get('plugin'),
            'plugin_icon': player.get('icon', '').format(ADDONPATH) or KodiAddon(player.get('plugin', '')).getAddonInfo('icon'),
            'fallback': player.get('fallback', {}).get(mode),
            'actions': player.get(mode)}


class PlayerDetails():
    def get_external_ids(self):
        from tmdbhelper.lib.player.details.details import get_external_ids
        self._external_ids = get_external_ids(self.tmdb_type, self.tmdb_id, season=self.season, episode=self.episode)
        return self._external_ids

    def get_item_details(self, language=None):
        from tmdbhelper.lib.player.details.details import get_item_details
        self._details = get_item_details(self.tmdb_type, self.tmdb_id, season=self.season, episode=self.episode, language=language)
        return self._details

    def set_detailed_item(self):
        from tmdbhelper.lib.player.details.details import set_detailed_item
        self._item = set_detailed_item(self.tmdb_type, self.tmdb_id, season=self.season, episode=self.episode, details=self.details) or {}
        return self._item

    def get_language_details(self, language=None, year=None):
        from tmdbhelper.lib.player.details.details import get_language_details
        self._item = get_language_details(self.item, self.tmdb_type, self.tmdb_id, self.season, self.episode, language=language, year=year)
        return self._item

    def get_next_episodes(self):
        from tmdbhelper.lib.player.details.details import get_next_episodes
        self._next_episodes = get_next_episodes(self.tmdb_id, self.season, self.episode, self.selected.player.file)
        return self._next_episodes


class PlayerProperties():
    @property
    def players_prioritised(self):
        try:
            return self._players_prioritised
        except AttributeError:
            self._players_prioritised = self.get_prioritised_players()
            return self._players_prioritised

    @property
    def details(self):
        try:
            return self._details
        except AttributeError:
            self.p_dialog.update(f'{get_localized(32375)}...')
            self._details = self.get_item_details()
            return self._details

    @property
    def item(self):
        try:
            return self._item
        except AttributeError:
            self._item = self.set_detailed_item()
            return self._item

    @property
    def providers(self):
        try:
            return self._providers
        except AttributeError:
            self._providers = self.get_providers()
            return self._providers

    @property
    def next_episodes(self):
        try:
            return self._next_episodes
        except AttributeError:
            self._next_episodes = self.get_next_episodes()
            return self._next_episodes

    @property
    def dialog_players(self):
        try:
            return self._dialog_players
        except AttributeError:
            self.p_dialog.update(f'{get_localized(32376)}...')
            self._dialog_players = self.get_dialog_players()
            self.p_dialog.close()
            return self._dialog_players

    @property
    def chosen_default(self):
        try:
            return self._chosen_default
        except AttributeError:
            self._chosen_default = self.get_chosen_default()
            return self._chosen_default

    @property
    def external_ids(self):
        try:
            return self._external_ids
        except AttributeError:
            self._external_ids = self.external_ids()
            return self._external_ids

    @property
    def thread_external_ids(self):
        try:
            return self._thread_external_ids
        except AttributeError:
            self._thread_external_ids = SafeThread(target=self.get_external_ids)
            return self._thread_external_ids


class PlayerHacksMixin:
    @staticmethod
    def player_hacks_run(instance):
        try:
            instance.run()
        except AttributeError:
            return

    def player_hacks_update_listing_set(self, folder_path=None, reset_focus=None):
        from tmdbhelper.lib.player.phacks.update_listing import PlayerHacksUpdateListing
        self.player_hacks_update_listing = PlayerHacksUpdateListing(folder_path, reset_focus)

    def player_hacks_update_listing_run(self):
        self.player_hacks_run(self.player_hacks_update_listing)

    def player_hacks_resolved_url_set(self, listitem, action=None):
        from tmdbhelper.lib.player.phacks.resolved_url import PlayerHacksResolvedURL
        self.player_hacks_resolved_url = PlayerHacksResolvedURL(listitem, action, handle=self.handle, f_strm=self.is_strm, equeue=self.playqueue_next_episodes)

    def player_hacks_resolved_url_run(self):
        self.player_hacks_run(self.player_hacks_resolved_url)


class Players(
    PlayerProperties,
    PlayerDetails,
    PlayerMethods,
    PlayerHacksMixin,
):

    selected = None
    default_player = None
    tmdb_type = None
    season = None
    episode = None

    def __init__(
        self,
        islocal=False,
        player=None,
        mode=None,
        handle=None,
        **kwargs
    ):

        # Kodi launches busy dialog on home screen that needs to be told to close
        # Otherwise the busy dialog will prevent window activation for folder path
        executebuiltin('Dialog.Close(busydialog)')

        self.api_language = None
        self.player = player  # the player file name
        self.mode = mode  # search or play
        self.handle = handle

        PlayerHacks.force_recache_kodidb_hack()  # Check if user wants to force rebuilding Kodi library cache first in case of new items
        self.thread_external_ids.start()  # We thread this lookup and rejoin later as Trakt might be slow and we dont want to delay if unneeded
        self.is_strm = islocal

    @cached_property
    def p_dialog(self):
        from tmdbhelper.lib.addon.dialog import ProgressDialog
        return ProgressDialog('TMDbHelper', f'{get_localized(32374)}...', total=3)

    @cached_property
    def action_log(self):
        return []

    @cached_property
    def player_forced(self):
        from tmdbhelper.lib.player.player_id import PlayerId
        return PlayerId(self.tmdb_type, self.player, self.mode).player_id

    @cached_property
    def players(self):
        from tmdbhelper.lib.player.files import PlayerFiles
        return PlayerFiles().dictionary

    def select_default(self, header=None, detailed=True):
        """ Returns user selected player via dialog - detailed bool switches dialog style """
        from tmdbhelper.lib.player.select import PlayerSelectAdditionalItems, PlayerSelectCombined
        instance = PlayerSelectCombined(players=self.dialog_players)
        instance.additional_players = PlayerSelectAdditionalItems.clear_default_player()
        return instance.select(header=header, detailed=detailed)

    def _get_player_or_fallback(self, fallback):
        if not fallback:
            return
        player_id, mode = fallback.split()
        if not player_id or not mode:
            return
        player = self.get_built_player(player_id, mode)
        if not player:
            return

        # Look for the fallback player in the dialog list and return it if we have it
        for x, i in enumerate(self.dialog_players):
            if i == player:
                player['idx'] = x
                return player

        # If we don't have the fallback but the fallback has a fallback then try that instead
        if player.get('fallback'):
            return self._get_player_or_fallback(player['fallback'])

    def _get_path_from_rules(self, folder, action, strict=False):
        """ Returns tuple of (path, is_folder) """
        _matches = []
        _action_log = []
        for x, f in enumerate(folder):
            _lastaction = ['   Itm: ', f.get('label'), '\n']
            for k, v in action.items():  # Iterate through our key (infolabel) / value (infolabel must match) pairs of our action
                if k == 'position':  # We're looking for an item position not an infolabel
                    if try_int(self.string_format_map(v)) != x + 1:  # Format our position value and add one since people are dumb and don't know that arrays start at 0
                        break  # Not the item position we want so let's go to next item in folder
                    continue  # Continue to check other actions in step
                itm_key_val = f'{f.get(k, "")}'  # Wrangle to string
                _lastaction += ('   Key: ', k, ' = ', itm_key_val, '\n')
                if not itm_key_val:
                    _action_log += _lastaction
                    break  # Item doesn't have key so go to next item
                str_fmt_map = self.string_format_map(v)
                _lastaction += ('   Fmt: ', str_fmt_map, '\n')
                if not re.match(str_fmt_map, itm_key_val):  # Format our value and check if it regex matches the infolabel key
                    _action_log += _lastaction
                    break  # Item's key value doesn't match value we are looking for so let's got to next item in folder
            else:  # Item matched our criteria so let's return it
                if not f.get('file'):
                    continue  # If the item doesn't have a path we should keep looking
                _matches.append(f)
                self.action_log += _lastaction
                self.action_log += ('FMATCH: ', f['file'], '\n')
                if not strict:  # Not strict match so don't bother checking rest of folder
                    break

        if not _matches:
            self.action_log += ('STEP FAILED!', '\n') if folder and folder[0] else ('NO RESULTS!', '\n')
            self.action_log += _action_log
            return

        if not strict or len(_matches) == 1:  # Strict match must give only one item
            f = _matches[0]
            is_folder = False if f.get('filetype') == 'file' else True  # Set false for files so we can play
            return (f['file'], is_folder)  # Get ListItem.FolderPath for item and return as player

        return _matches

    @staticmethod
    def action_dialog_select(folder, auto=False):
        from tmdbhelper.lib.player.actions.dialog import PlayerActionDialog
        return PlayerActionDialog(folder, auto).item_tuple

    def _get_path_from_actions(self, actions, is_folder=True):
        """ Returns tuple of (path, is_folder) """
        is_dialog = None
        keyboard_input = None
        path = (actions[0], is_folder)
        if not is_folder:
            return path
        for action in actions[1:]:
            # Start thread with keyboard inputter if needed
            if action.get('keyboard'):
                if action['keyboard'] in ['Up', 'Down', 'Left', 'Right', 'Select']:
                    keyboard_input = KeyboardInputter(action=f'Input.{action.get("keyboard")}')
                    self.action_log += ('KEYBRD: ', action['keyboard'], '\n')
                else:
                    text = self.string_format_map(action['keyboard'])
                    keyboard_input = KeyboardInputter(text=text[::-1] if action.get('direction') == 'rtl' else text)
                    self.action_log += ('KEYBRD: ', text, '\n')
                keyboard_input.setName('keyboard_input')
                keyboard_input.start()
                continue  # Go to next action

            # Get the next folder from the plugin
            str_fmt_map = self.string_format_map(path[0])
            self.action_log += ('FOLDER: ', str_fmt_map, '\n', 'ACTION: ', action, '\n')
            folder = get_directory(str_fmt_map)

            # Kill our keyboard inputter thread
            if keyboard_input:
                keyboard_input.exit = True
                keyboard_input = None

            # Pop special actions
            is_return = action.pop('return', None)
            is_dialog = action.pop('dialog', None)
            is_strict = action.pop('strict', None)

            # Get next path if there's still actions left
            next_path = self._get_path_from_rules(folder, action, is_strict) if action else None

            # Strict flag checks that we received a single item
            if is_strict and next_path and isinstance(next_path, list):
                if is_dialog:  # A dialog action combined with strict flag allows users to choose
                    folder = next_path  # Set our folder to list of matches to choose in dialog
                next_path = None  # We didn't get a next path so

            # Special action to fallback to select dialog if match is not found directly
            if is_dialog and not next_path:
                next_path = self.action_dialog_select(folder, auto=is_dialog.lower() == 'auto')

            # Early return flag ignores a step failure and instead continues onto trying next step
            # Check against next_path[1] also to make sure we aren't trying to play a folder
            if is_return and (not next_path or next_path[1]):
                continue

            # No next path and no special flags means that player failed
            if not next_path:
                return

            # File is playable and user manually selected or early return flag set
            # Useful for early exit to play episodes in flattened miniseries instead of opening season folder
            if not next_path[1] and (is_dialog or is_return):
                return next_path

            # Set next path to path for next action
            path = next_path

        # If dialog repeat flag set then repeat action over until find playable or user cancels
        if path and is_dialog == 'repeat':
            return self._get_path_from_actions([path[0], {'dialog': 'repeat'}], path[1])

        return path

    def _get_path_from_player(self, player=None):
        """ Returns tuple of (path, is_folder) """
        if not player or not isinstance(player, dict):
            return
        actions = player.get('actions')
        if not actions:
            return
        if isinstance(actions, list):
            return self._get_path_from_actions(actions)
        if isinstance(actions, str):
            if not player.get('is_local', False):
                actions = self.string_format_map(actions)  # Format our path if a single path and not a file
            return (actions, player.get('is_folder', False))

    def get_default_player(self):
        """ Returns default player """

        if self.ignore_default:
            return

        if not self.dialog_players:
            return

        if self.player_forced:
            return self._get_player_or_fallback(self.player_forced)

        if self.chosen_default:
            return self._get_player_or_fallback(self.chosen_default)

        x = 0

        if self.dialog_players[x].get('is_local'):
            if get_setting('default_player_kodi', 'int') == 1:
                player = self.dialog_players[x]
                player['idx'] = x
                player['fallback'] = player.get('fallback') or self.default_player or ''  # Use default_player if this one fails
                return player

            if len(self.dialog_players) > 1:
                x = 1

        if self.dialog_players[x].get('is_provider'):
            if get_setting('default_player_provider'):
                player = self.dialog_players[x]
                player['idx'] = x
                player['fallback'] = player.get('fallback') or self.default_player or ''  # Use default_player if this one fails
                return player

        # No default player setting
        if not self.default_player:
            return

        return self._get_player_or_fallback(self.default_player)

    @cached_property
    def resolver(self):
        resolver = ResolverPlayerSelect(self.item, dialog_players=self.dialog_players, action_log=self.action_log)
        resolver.resolved_path_func = self._get_path_from_player  # TODO: Temp shim: move into class
        resolver.fallback_item_func = self._get_player_or_fallback  # TODO: Temp shim: move into class
        return resolver

    def get_resolved_metaitem(self, player=None, allow_default=False):
        self.resolver.update_player(self.get_default_player() if allow_default and not player else player)
        if not self.resolver.player:
            return
        self.selected = self.resolver
        self.set_external_ids(required=self.selected.player.requires_ids)  # Update item from external ID thread

        # Allow players to override language settings
        # # Compare against self.api_language to check if another player changed language previously
        if self.selected.player.api_language != self.api_language:
            self.api_language = self.selected.player.api_language
            self.get_item_details(language=self.api_language)
            self.set_external_ids(required=self.selected.player.requires_ids)
            self.action_log += ('APILAN: ', self.api_language, '\n')

        # Allow for a separate translation language to add "{de_title}" keys ("de" is iso language code)
        self.get_language_details(self.selected.player.language, self.selected.meta.year) if self.selected.player.language else None

        return self.selected.item

    def get_resolved_listitem(self):
        if not self.item:
            return
        get_property('PlayerInfoString', clear_property=True)
        path = self.get_resolved_metaitem(allow_default=True) or {}
        self.details.params = {}
        self.details.path = path.pop('url', None)
        self.details.infoproperties.update(path)
        return self.details.get_listitem()

    def queue_next_episodes(self, route='make_upnext'):
        if not self.selected or self.selected.mode != 'play_episode':
            return
        if self.season is None or self.episode is None:
            return
        if not self.next_episodes or len(self.next_episodes) < 2:
            return

        PlayerHacks.wait_for_player_hack(to_start=True, timeout=30)

        if route == 'make_upnext':
            from tmdbhelper.lib.player.putils import make_upnext
            return make_upnext(self.next_episodes[0], self.next_episodes[1])
        if route == 'make_playlist':
            from tmdbhelper.lib.player.putils import make_playlist
            return make_playlist(self.next_episodes)

    def configure_action(self, listitem, handle=None):
        path = listitem.getPath()
        if path.startswith('executebuiltin://'):
            listitem.setProperty('is_folder', 'true')
            return path.replace('executebuiltin://', '')
        if listitem.getProperty('is_folder') == 'true':
            return format_folderpath(path)
        if not handle or listitem.getProperty('is_resolvable') == 'false':
            return path
        if listitem.getProperty('is_resolvable') == 'select' and not Dialog().yesno(
                f'{listitem.getProperty("player_name")} - {get_localized(32353)}',
                get_localized(32354),
                yeslabel=f'{get_localized(107)} (setResolvedURL)',
                nolabel=f'{get_localized(106)} (PlayMedia)'):
            return path

    def playqueue_next_episodes(self):
        make_playlist = self.selected.make_playlist
        if not make_playlist:
            return
        if make_playlist.lower() == 'upnext':
            self.queue_next_episodes(route='make_upnext')
            return
        if make_playlist.lower() == 'true':
            self.queue_next_episodes(route='make_playlist')
            return

    @cached_property
    def listitem(self):
        return self.get_resolved_listitem()

    @cached_property
    def action(self):
        return self.configure_action(self.listitem, self.handle)

    def play(self, folder_path=None, reset_focus=None, ignore_default=False):
        self.ignore_default = boolean(ignore_default)

        if not self.listitem.getPath():
            return
        if self.listitem.getPath() == PLUGINPATH:
            return

        # Output action log
        kodi_log(self.action_log, 2)
        self.action_log = []

        # Reset folder hack
        self.player_hacks_update_listing_set(folder_path, reset_focus)
        self.player_hacks_update_listing_run()

        # Play item
        self.player_hacks_resolved_url_set(self.listitem, action=self.action)
        self.player_hacks_resolved_url_run()


class PlayersMovie(Players):
    tmdb_type = 'movie'

    def __init__(
        self,
        tmdb_id=None,
        **kwargs
    ):
        self.tmdb_id = tmdb_id
        super().__init__(**kwargs)

    @cached_property
    def default_player(self):
        return get_setting('default_player_movies', 'str')


class PlayersEpisode(Players):
    tmdb_type = 'tv'

    def __init__(
        self,
        tmdb_id=None,
        season=None,
        episode=None,
        **kwargs
    ):
        self.tmdb_id = tmdb_id
        self.season = season
        self.episode = episode
        super().__init__(**kwargs)

    @cached_property
    def default_player(self):
        return get_setting('default_player_episodes', 'str')


def PlayersFactory(tmdb_type, **kwargs):
    if tmdb_type == 'movie':
        return PlayersMovie(**kwargs)

    if tmdb_type in ('tv', 'season', 'episode'):
        return PlayersEpisode(**kwargs)
