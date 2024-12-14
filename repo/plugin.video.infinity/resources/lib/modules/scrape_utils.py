# -*- coding: utf-8 -*-
"""
	Scrapers Utility Module adapted from FS OneMoar Dev 08/21/23
"""

import re
from string import printable
from resources.lib.modules import cleantitle

RES_4K = ('2160', '216o', '.4k', 'ultrahd', 'ultra.hd', '.uhd.')
RES_1080 = ('1080', '1o8o', '108o', '1o80', '.fhd.')
RES_720 = ('720', '72o')
SCR = ('dvdscr', 'screener', '.scr.', '.r5', '.r6')
CAM = ('1xbet', 'betwin', '.cam.', 'camrip', 'cam.rip', 'dvdcam', 'dvd.cam', 'dvdts', 'hdcam', '.hd.cam', '.hctc', '.hc.tc', '.hdtc',
				'.hd.tc', 'hdts', '.hd.ts', 'hqcam', '.hg.cam', '.tc.', '.tc1', '.tc7', '.ts.', '.ts1', '.ts7', 'tsrip', 'telecine', 'telesync', 'tele.sync')

season_list = ('one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eigh', 'nine', 'ten', 'eleven', 'twelve', 'thirteen', 'fourteen',
			'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen', 'twenty', 'twenty-one', 'twenty-two', 'twenty-three',
			'twenty-four', 'twenty-five')
season_ordinal_list = ('first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth', 'ninth', 'tenth', 'eleventh', 'twelfth',
			'thirteenth', 'fourteenth', 'fifteenth', 'sixteenth', 'seventeenth', 'eighteenth', 'nineteenth', 'twentieth', 'twenty-first',
			'twenty-second', 'twenty-third', 'twenty-fourth', 'twenty-fifth')
season_ordinal2_list = ('1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th', '9th', '10th', '11th', '12th', '13th', '14th', '15th', '16th',
			'17th', '18th', '19th', '20th', '21st', '22nd', '23rd', '24th', '25th')

unwanted_tags = ('tamilrockers.com', 'www.tamilrockers.com', 'www.tamilrockers.ws', 'www.tamilrockers.pl',
			'www-tamilrockers-cl', 'www.tamilrockers.cl', 'www.tamilrockers.li', 'www-tamilrockers-tw',
			'www.tamilrockerrs.pl',
			'www.tamilmv.bid', 'www.tamilmv.biz', 'www.1tamilmv.org',
			'gktorrent-bz', 'gktorrent-com',
			'www.torrenting.com', 'www.torrenting.org', 'www-torrenting-com', 'www-torrenting-org',
			'katmoviehd.pw', 'katmoviehd-pw',
			'www.torrent9.nz', 'www-torrent9-uno', 'torrent9-cz', 'torrent9.cz', 'torrent9-red', 'torrent9-bz',
			'agusiq-torrents-pl',
			'oxtorrent-bz', 'oxtorrent-com', 'oxtorrent.com', 'oxtorrent-sh', 'oxtorrent-vc',
			'www.movcr.tv', 'movcr-com', 'www.movcr.to',
			'(imax)', 'imax',
			'xtorrenty.org', 'nastoletni.wilkoak', 'www.scenetime.com', 'kst-vn',
			'www.movierulz.vc', 'www-movierulz-ht', 'www.2movierulz.ac', 'www.2movierulz.ms',
			'www.3movierulz.com', 'www.3movierulz.tv', 'www.3movierulz.ws', 'www.3movierulz.ms',
			'www.7movierulz.pw', 'www.8movierulz.ws',
			'mkvcinemas.live', 'torrentcounter-to',
			'www.bludv.tv', 'ramin.djawadi', 'extramovies.casa', 'extramovies.wiki',
			'13+', '18+', 'taht.oyunlar', 'crazy4tv.com', 'karibu', '989pa.com',
			'best-torrents-net', '1-3-3-8.com', 'ssrmovies.club',
			'va:', 'zgxybbs-fdns-uk', 'www.tamilblasters.mx',
			'www.1tamilmv.work', 'www.xbay.me',
			'crazy4tv-com', '(es)')

def get_qual(term):
	if any(i in term for i in SCR): return 'SCR'
	elif any(i in term for i in CAM): return 'CAM'
	elif any(i in term for i in RES_720): return '720p'
	elif any(i in term for i in RES_1080): return '1080p'
	elif any(i in term for i in RES_4K): return '4K'
	elif '.hd.' in term: return '720p'
	else: return 'SD'

def get_release_quality(release_info, release_link=None):
	try:
		quality = None ; info = []
		if release_info: quality = get_qual(release_info)
		if not quality:
			if release_link:
				release_link = release_link.lower()
				quality = get_qual(release_link)
				if not quality: quality = 'SD'
			else: quality = 'SD'
		return quality, info
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return 'SD', []

def aliases_to_array(aliases, filter=None):
	try:
		if all(isinstance(x, str) for x in aliases): return aliases
		if not filter: filter = []
		if isinstance(filter, str): filter = [filter]
		return [x.get('title') for x in aliases if not filter or x.get('country') in filter]
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return []

def check_title(title, aliases, release_title, hdlr, year, years=None): # non pack file title check, single eps and movies
	if years: # for movies only, scraper to pass None for episodes
		if not any(value in release_title for value in years): return False
	else: 
		if not re.search(r'%s' % hdlr, release_title, re.I): return False
	aliases = aliases_to_array(aliases)
	title_list = []
	title_list_append = title_list.append
	if aliases:
		for item in aliases:
			try:
				alias = item.replace('&', 'and').replace(year, '')
				if years: # for movies only, scraper to pass None for episodes
					for i in years: alias = alias.replace(i, '')
				if alias in title_list: continue
				title_list_append(alias)
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
	try:
		
		title = title.replace('&', 'and').replace(year, '') # year only in meta title if an addon custom query added it
		if title not in title_list: title_list_append(title)
		release_title = re.sub(r'([(])(?=((19|20)[0-9]{2})).*?([)])', '\\2', release_title) #remove parenthesis only if surrounding a 4 digit date
		t = re.split(r'%s' % hdlr, release_title, 1, re.I)[0].replace(year, '').replace('&', 'and')
		if years:
			for i in years: t = t.split(i)[0]
		t = re.split(r'2160p|216op|4k|1080p|1o8op|108op|1o80p|720p|72op|480p|48op', t, 1, re.I)[0]
		cleantitle_t = cleantitle.get(t)
		if all(cleantitle.get(i) != cleantitle_t for i in title_list): return False

# filter to remove episode ranges that should be picked up in "filter_season_pack()" ex. "s01e01-08"
		if hdlr != year: # equal for movies but not for shows
			range_regex = (
					r's\d{1,3}e\d{1,3}[-.]e\d{1,3}',
					r's\d{1,3}e\d{1,3}[-.]\d{1,3}(?!p|bit|gb)(?!\d{1,3})',
					r's\d{1,3}[-.]e\d{1,3}[-.]e\d{1,3}',
					r'season[.-]?\d{1,3}[.-]?ep[.-]?\d{1,3}[-.]ep[.-]?\d{1,3}',
					r'season[.-]?\d{1,3}[.-]?episode[.-]?\d{1,3}[-.]episode[.-]?\d{1,3}') # may need to add "to", "thru"
			for regex in range_regex:
				if bool(re.search(regex, release_title, re.I)): return False
		return True
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return False

def filter_season_pack(show_title, aliases, year, season, release_title):
	aliases = aliases_to_array(aliases)
	title_list = []
	title_list_append = title_list.append
	if aliases:
		for item in aliases:
			try:
				alias = item.replace('!', '').replace('(', '').replace(')', '').replace('&', 'and').replace(year, '')
				if alias in title_list: continue
				title_list_append(alias)
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
	try:
		show_title = show_title.replace('!', '').replace('(', '').replace(')', '').replace('&', 'and')
		if show_title not in title_list: title_list_append(show_title)

		season_fill = season.zfill(2)
		season_check = '.s%s.' % season
		season_fill_check = '.s%s.' % season_fill
		season_fill_checke = '.s%se' % season_fill # added 3/2/22 to pick up episode range packs ex "Reacher.s01e01-08"
		season_full_check = '.season.%s.' % season
		season_full_check_ns = '.season%s.' % season
		season_full_fill_check = '.season.%s.' % season_fill
		season_full_fill_check_ns = '.season%s.' % season_fill
		split_list = (season_check, season_fill_check, season_fill_checke, '.' + season + '.season', 'total.season', 'season', 'the.complete', 'complete', year)
		string_list = (season_check, season_fill_check, season_fill_checke, season_full_check, season_full_check_ns, season_full_fill_check, season_full_fill_check_ns)

		release_title = release_title_format(release_title)
		t = release_title.replace('-', '.')
		for i in split_list: t = t.split(i)[0]
		if all(cleantitle.get(x) != cleantitle.get(t) for x in title_list): return False, 0, 0

# remove single episodes ONLY (returned in single ep scrape), keep episode ranges as season packs
		episode_regex = (
				r's\d{1,3}e\d{1,3}[-.](?!\d{2,3}[-.])(?!e\d{1,3})(?!\d{2}gb)',
				r'season[.-]?\d{1,3}[.-]?ep[.-]?\d{1,3}[-.](?!\d{2,3}[-.])(?!e\d{1,3})(?!\d{2}gb)',
				r'season[.-]?\d{1,3}[.-]?episode[.-]?\d{1,3}[-.](?!\d{2,3}[-.])(?!e\d{1,3})(?!\d{2}gb)')
		for item in episode_regex:
			if bool(re.search(item, release_title)): return False, 0, 0

# return and identify episode ranges
		range_regex = (
				r's\d{1,3}e(\d{1,3})[-.]e(\d{1,3})',
				r's\d{1,3}e(\d{1,3})[-.](\d{1,3})(?!p|bit|gb)(?!\d{1,3})',
				r's\d{1,3}[-.]e(\d{1,3})[-.]e(\d{1,3})',
				r'season[.-]?\d{1,3}[.-]?ep[.-]?(\d{1,3})[-.]ep[.-]?(\d{1,3})',
				r'season[.-]?\d{1,3}[.-]?episode[.-]?(\d{1,3})[-.]episode[.-]?(\d{1,3})') # may need to add "to", "thru"
		for regex in range_regex:
			match = re.search(regex, release_title)
			if match:
				# from resources.lib.modules import log_utils
				# log_utils.log('pack episode range found -- > release_title=%s' % release_title)
				episode_start = int(match.group(1))
				episode_end = int(match.group(2))
				return True, episode_start, episode_end

# remove season ranges - returned in showPack scrape, plus non conforming season and specific crap
		rt = release_title.replace('-', '.')
		if any(i in rt for i in string_list):
			for item in (
				season_check.rstrip('.') + r'[.-]s([2-9]{1}|[1-3]{1}[0-9]{1})(?:[.-]|$)', # ex. ".s1-s9.", .s1-s39.
				season_fill_check.rstrip('.') + r'[.-]s\d{2}(?:[.-]|$)', # ".s01-s09.", .s01-s39.
				season_fill_check.rstrip('.') + r'[.-]\d{2}(?:[.-]|$)', # ".s01.09."
				r'\Ws\d{2}\W%s' % season_fill_check.lstrip('.'), # may need more reverse ranges
				season_full_check.rstrip('.') + r'[.-]to[.-]([2-9]{1}|[1-3]{1}[0-9]{1})(?:[.-]|$)', # ".season.1.to.9.", ".season.1.to.39"
				season_full_check.rstrip('.') + r'[.-]season[.-]([2-9]{1}|[1-3]{1}[0-9]{1})(?:[.-]|$)', # ".season.1.season.9.", ".season.1.season.39"
				season_full_check.rstrip('.') + r'[.-]([2-9]{1}|[1-3]{1}[0-9]{1})(?:[.-]|$)', # "season.1.9.", "season.1.39.
				season_full_check.rstrip('.') + r'[.-]\d{1}[.-]\d{1,2}(?:[.-]|$)', # "season.1.9.09."
				season_full_check.rstrip('.') + r'[.-]\d{3}[.-](?:19|20)[0-9]{2}(?:[.-]|$)', # single season followed by 3 digit followed by 4 digit year ex."season.1.004.1971"
				season_full_fill_check.rstrip('.') + r'[.-]\d{3}[.-]\d{3}(?:[.-]|$)', # 2 digit season followed by 3 digit dash range ex."season.10.001-025."
				season_full_fill_check.rstrip('.') + r'[.-]season[.-]\d{2}(?:[.-]|$)' # 2 digit season followed by 2 digit season range ex."season.01-season.09."
					):
				if bool(re.search(item, release_title)): return False, 0, 0
			return True, 0, 0
		return False, 0, 0
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return True

def filter_show_pack(show_title, aliases, imdb, year, season, release_title, total_seasons):
	aliases = aliases_to_array(aliases)
	title_list = []
	title_list_append = title_list.append
	if aliases:
		for item in aliases:
			try:
				alias = item.replace('!', '').replace('(', '').replace(')', '').replace('&', 'and').replace(year, '')
				if alias in title_list: continue
				title_list_append(alias)
			except:
				from resources.lib.modules import log_utils
				log_utils.error()
	try:
		show_title = show_title.replace('!', '').replace('(', '').replace(')', '').replace('&', 'and')
		if show_title not in title_list: title_list_append(show_title)

		split_list = ('.all.seasons', 'seasons', 'season', 'the.complete', 'complete', 'all.torrent', 'total.series', 'tv.series', 'series', 'edited', 's1', 's01', year)#s1 or s01 used so show pack only kept that begin with 1
		release_title = release_title_format(release_title)
		t = release_title.replace('-', '.')

		for i in split_list: t = t.split(i)[0]
		if all(cleantitle.get(x) != cleantitle.get(t) for x in title_list): return False, 0

# remove single episodes(returned in single ep scrape)
		episode_regex = (
				r's\d{1,3}e\d{1,3}',
				r's[0-3]{1}[0-9]{1}[.-]e\d{1,2}',
				r's\d{1,3}[.-]\d{1,3}e\d{1,3}',
				r'season[.-]?\d{1,3}[.-]?ep[.-]?\d{1,3}',
				r'season[.-]?\d{1,3}[.-]?episode[.-]?\d{1,3}')
		for item in episode_regex:
			if bool(re.search(item, release_title)):
				return False, 0

# remove season ranges that do not begin at 1
		season_range_regex = (
				r'(?:season|seasons|s)[.-]?(?:0?[2-9]{1}|[1-3]{1}[0-9]{1})(?:[.-]?to[.-]?|[.-]?thru[.-]?|[.-])(?:season|seasons|s|)[.-]?(?:0?[3-9]{1}(?!\d{2}p)|[1-3]{1}[0-9]{1}(?!\d{2}p))',) # seasons.5-6, seasons5.to.6, seasons.5.thru.6, season.2-9.s02-s09.1080p
		for item in season_range_regex:
			if bool(re.search(item, release_title)):
				return False, 0

# remove single seasons - returned in seasonPack scrape
		season_regex = (
				r'season[.-]?([1-9]{1})[.-]0{1}\1[.-]?complete', # "season.1.01.complete" when 2nd number matches the fiirst group with leading 0
				r'season[.-]?([2-9]{1})[.-](?:[0-9]+)[.-]?complete', # "season.9.10.complete" when first number is >1 followed by 2 digit number
				r'season[.-]?\d{1,2}[.-]s\d{1,2}', # season.02.s02
				r'season[.-]?\d{1,2}[.-]complete', # season.02.complete
				r'season[.-]?\d{1,2}[.-]\d{3,4}p{0,1}', # "season.02.1080p" and no seperator "season02.1080p"
				r'season[.-]?\d{1,2}[.-](?!thru|to|\d{1,2}[.-])', # "season.02." or "season.1" not followed by "to", "thru", or another single or 2 digit number then a dot(which would be a range)
				r'season[.-]?\d{1,2}[.]?$', # end of line ex."season.1", "season.01", "season01" can also have trailing dot or end of line(dash would be a range)
				r'season[.-]?\d{1,2}[.-](?:19|20)[0-9]{2}', # single season followed by 4 digit year ex."season.1.1971", "season.01.1971", or "season01.1971"
				r'season[.-]?\d{1,2}[.-]\d{3}[.-]{1,2}(?:19|20)[0-9]{2}', # single season followed by 3 digits then 4 digit year ex."season.1.004.1971" or "season.01.004.1971" (comic book format)
				r'(?<!thru)(?<!to)(?<!\d{2})[.-]s\d{2}[.-]complete', # ".s01.complete" not preceded by "thru", "to", or 2 digit number
				r'(?<!thru)(?<!to)(?<!s\d{2})[.-]s\d{2}(?![.-]thru)(?![.-]to)(?![.-]s\d{2})(?![.-]\d{2}[.-])' # .s02. not preceded by "thru", "to", or "s01". Not followed by ".thru", ".to", ".s02", "-s02", ".02.", or "-02."
				)
		for item in season_regex:
			if bool(re.search(item, release_title)):
				return False, 0


# remove spelled out single seasons
		season_regex = ()
		season_regex += tuple([r'complete[.-]%s[.-]season' % x for x in season_ordinal_list])
		season_regex += tuple([r'complete[.-]%s[.-]season' % x for x in season_ordinal2_list])
		season_regex += tuple([r'season[.-]%s' % x for x in season_list]) 
		for item in season_regex:
			if bool(re.search(item, release_title)):
				return False, 0


# from here down we don't filter out, we set and pass "last_season" it covers for the range and addon can filter it so the db will have full valid showPacks.
# set last_season for range type ex "1.2.3.4" or "1.2.3.and.4" (dots or dashes)
		dot_release_title = release_title.replace('-', '.')
		dot_season_ranges = []
		all_seasons = '1'
		season_count = 2
		while season_count <= int(total_seasons):
			dot_season_ranges.append(all_seasons + '.and.%s' % str(season_count))
			all_seasons += '.%s' % str(season_count)
			dot_season_ranges.append(all_seasons)
			season_count += 1
		if any(i in dot_release_title for i in dot_season_ranges):
			keys = [i for i in dot_season_ranges if i in dot_release_title]
			last_season = int(keys[-1].split('.')[-1])
			return True, last_season



# "1.to.9" type range filter (dots or dashes)
		to_season_ranges = []
		start_season = '1'
		season_count = 2
		while season_count <= int(total_seasons):
			to_season_ranges.append(start_season + '.to.%s' % str(season_count))
			season_count += 1
		if any(i in dot_release_title for i in to_season_ranges):
			keys = [i for i in to_season_ranges if i in dot_release_title]
			last_season = int(keys[0].split('to.')[1])
			return True, last_season

# "1.thru.9" range filter (dots or dashes)
		thru_ranges = [i.replace('to', 'thru') for i in to_season_ranges]
		if any(i in dot_release_title for i in thru_ranges):
			keys = [i for i in thru_ranges if i in dot_release_title]
			last_season = int(keys[0].split('thru.')[1])
			return True, last_season

# "1-9" range filter
		dash_ranges = [i.replace('.to.', '-') for i in to_season_ranges]
		if any(i in release_title for i in dash_ranges):
			keys = [i for i in dash_ranges if i in release_title]
			last_season = int(keys[0].split('-')[1])
			return True, last_season

# "1~9" range filter
		tilde_ranges = [i.replace('.to.', '~') for i in to_season_ranges]
		if any(i in release_title for i in tilde_ranges):
			keys = [i for i in tilde_ranges if i in release_title]
			last_season = int(keys[0].split('~')[1])
			return True, last_season



# "01.to.09" 2 digit range filter (dots or dashes)
		to_season_ranges = []
		start_season = '01'
		season_count = 2
		while season_count <= int(total_seasons):
			to_season_ranges.append(start_season + '.to.%s' % '0' + str(season_count) if int(season_count) < 10 else start_season + '.to.%s' % str(season_count))
			season_count += 1
		if any(i in dot_release_title for i in to_season_ranges):
			keys = [i for i in to_season_ranges if i in dot_release_title]
			last_season = int(keys[0].split('to.')[1])
			return True, last_season

# "01.thru.09" 2 digit range filter (dots or dashes)
		thru_ranges = [i.replace('to', 'thru') for i in to_season_ranges]
		if any(i in dot_release_title for i in thru_ranges):
			keys = [i for i in thru_ranges if i in dot_release_title]
			last_season = int(keys[0].split('thru.')[1])
			return True, last_season

# "01-09" 2 digit range filtering
		dash_ranges = [i.replace('.to.', '-') for i in to_season_ranges]
		if any(i in release_title for i in dash_ranges):
			keys = [i for i in dash_ranges if i in release_title]
			last_season = int(keys[0].split('-')[1])
			return True, last_season

# "01~09" 2 digit range filtering
		tilde_ranges = [i.replace('.to.', '~') for i in to_season_ranges]
		if any(i in release_title for i in tilde_ranges):
			keys = [i for i in tilde_ranges if i in release_title]
			last_season = int(keys[0].split('~')[1])
			return True, last_season



# "s1.to.s9" single digit range filter (dots or dashes)
		to_season_ranges = []
		start_season = 's1'
		season_count = 2
		while season_count <= int(total_seasons):
			to_season_ranges.append(start_season + '.to.s%s' % str(season_count))
			season_count += 1
		if any(i in dot_release_title for i in to_season_ranges):
			keys = [i for i in to_season_ranges if i in dot_release_title]
			last_season = int(keys[0].split('to.s')[1])
			return True, last_season

# "s1.thru.s9" single digit range filter (dots or dashes)
		thru_ranges = [i.replace('to', 'thru') for i in to_season_ranges]
		if any(i in dot_release_title for i in thru_ranges):
			keys = [i for i in thru_ranges if i in dot_release_title]
			last_season = int(keys[0].split('thru.s')[1])
			return True, last_season

# "s1-s9" single digit range filtering (dashes)
		dash_ranges = [i.replace('.to.', '-') for i in to_season_ranges]
		if any(i in release_title for i in dash_ranges):
			keys = [i for i in dash_ranges if i in release_title]
			last_season = int(keys[0].split('-s')[1])
			return True, last_season

# "s1~s9" single digit range filtering (dashes)
		tilde_ranges = [i.replace('.to.', '~') for i in to_season_ranges]
		if any(i in release_title for i in tilde_ranges):
			keys = [i for i in tilde_ranges if i in release_title]
			last_season = int(keys[0].split('~s')[1])
			return True, last_season



# "s01.to.s09"  2 digit range filter (dots or dash)
		to_season_ranges = []
		start_season = 's01'
		season_count = 2
		while season_count <= int(total_seasons):
			to_season_ranges.append(start_season + '.to.s%s' % '0' + str(season_count) if int(season_count) < 10 else start_season + '.to.s%s' % str(season_count))
			season_count += 1
		if any(i in dot_release_title for i in to_season_ranges):
			keys = [i for i in to_season_ranges if i in dot_release_title]
			last_season = int(keys[0].split('to.s')[1])
			return True, last_season

# "s01.thru.s09" 2 digit  range filter (dots or dashes)
		thru_ranges = [i.replace('to', 'thru') for i in to_season_ranges]
		if any(i in dot_release_title for i in thru_ranges):
			keys = [i for i in thru_ranges if i in dot_release_title]
			last_season = int(keys[0].split('thru.s')[1])
			return True, last_season

# "s01-s09" 2 digit  range filtering (dashes)
		dash_ranges = [i.replace('.to.', '-') for i in to_season_ranges]
		if any(i in release_title for i in dash_ranges):
			keys = [i for i in dash_ranges if i in release_title]
			last_season = int(keys[0].split('-s')[1])
			return True, last_season

# "s01~s09" 2 digit  range filtering (dashes)
		tilde_ranges = [i.replace('.to.', '~') for i in to_season_ranges]
		if any(i in release_title for i in tilde_ranges):
			keys = [i for i in tilde_ranges if i in release_title]
			last_season = int(keys[0].split('~s')[1])
			return True, last_season

# "s01.s09" 2 digit  range filtering (dots)
		dot_ranges = [i.replace('.to.', '.') for i in to_season_ranges]
		if any(i in release_title for i in dot_ranges):
			keys = [i for i in dot_ranges if i in release_title]
			last_season = int(keys[0].split('.s')[1])
			return True, last_season

		return True, total_seasons
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		# return True, total_seasons

def info_from_name(release_title, title, year, hdlr=None, episode_title=None, season=None, pack=None):
	try:
		release_title = release_title.lower().replace('&', 'and').replace("'", "")
		release_title = re.sub(r'[^a-z0-9]+', '.', release_title)
		title = title.lower().replace('&', 'and').replace("'", "")
		title = re.sub(r'[^a-z0-9]+', '.', title)
		name_info = release_title.replace(title, '').replace(year, '')
		if hdlr: name_info = name_info.replace(hdlr.lower(), '')
		if episode_title:
			episode_title = episode_title.lower().replace('&', 'and').replace("'", "")
			episode_title = re.sub(r'[^a-z0-9]+', '.', episode_title)
			name_info = name_info.replace(episode_title, '')
		if pack:
			if pack == 'season':
				season_fill = season.zfill(2)
				str1_replace = ('.s%s' % season, '.s%s' % season_fill, '.season.%s' % season, '.season%s' % season, '.season.%s' % season_fill, '.season%s' % season_fill, 'complete')
				for i in str1_replace: name_info = name_info.replace(i, '')
			elif pack == 'show':
				str2_replace = ('.all.seasons', 'seasons', 'season', 'the.complete', 'complete', 'all.torrent', 'total.series', 'tv.series', 'series', 'edited', 's1', 's01')
				for i in str2_replace: name_info = name_info.replace(i, '')
		name_info = name_info.lstrip('.').rstrip('.')
		name_info = '.%s.' % name_info
		return name_info
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return release_title

def release_title_format(release_title):
	try:
		release_title = release_title.lower().replace("'", "").lstrip('.').rstrip('.')
		fmt = '.%s.' % re.sub(r'[^a-z0-9-~]+', '.', release_title).replace('.-.', '-').replace('-.', '-').replace('.-', '-').replace('--', '-')
		return fmt
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return release_title

def clean_name(release_title):
	try:
		release_title = re.sub(r'【.*?】', '', release_title)
		release_title = strip_non_ascii_and_unprintable(release_title).lstrip('+.-:/ ').replace(' ', '.')
		releasetitle_startswith = release_title.lower().startswith
		if releasetitle_startswith('rifftrax'): return release_title # removed by "undesirables" anyway so exit
		for i in unwanted_tags:
			if releasetitle_startswith(i):
				release_title = re.sub(r'^%s' % i.replace('+', '\+'), '', release_title, 1, re.I)
		release_title = release_title.lstrip('+.-:/ ')
		release_title = re.sub(r'^\[.*?]', '', release_title, 1, re.I)
		release_title = release_title.lstrip('.-[](){}:/')
		return release_title
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return release_title

def strip_non_ascii_and_unprintable(text):
	try:
		result = ''.join(char for char in text if char in printable)
		return result.encode('ascii', errors='ignore').decode('ascii', errors='ignore')
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return text

def _size(siz):
	try:
		if siz in ('0', 0, '', None): return 0, ''
		div = 1 if siz.lower().endswith(('gb', 'gib')) else 1024
		# if ',' in siz and siz.lower().endswith(('mb', 'mib')): siz = size.replace(',', '')
		# elif ',' in siz and siz.lower().endswith(('gb', 'gib')): siz = size.replace(',', '.')
		dec_count = len(re.findall(r'[.]', siz))
		if dec_count == 2: siz = siz.replace('.', ',', 1) # torrentproject2 likes to randomly use 2 decimals vs. a comma then a decimal
		float_size = round(float(re.sub(r'[^0-9|/.|/,]', '', siz.replace(',', ''))) / div, 2) #comma issue where 2,750 MB or 2,75 GB (sometimes replace with "." and sometimes not)
		str_size = '%.2f GB' % float_size
		return float_size, str_size
	except:
		from resources.lib.modules import log_utils
		log_utils.error('failed on siz=%s' % siz)
		return 0, ''

def convert_size(size_bytes, to='GB'):
	try:
		import math
		if size_bytes == 0: return 0, ''
		power = {'B' : 0, 'KB': 1, 'MB' : 2, 'GB': 3, 'TB' : 4, 'EB' : 5, 'ZB' : 6, 'YB': 7}
		i = power[to]
		p = math.pow(1024, i)
		float_size = round(size_bytes / p, 2)
		# if to == 'B' or to  == 'KB': return 0, ''
		str_size = "%s %s" % (float_size, to)
		return float_size, str_size
	except:
		from resources.lib.modules import log_utils
		log_utils.error()
		return 0, ''
