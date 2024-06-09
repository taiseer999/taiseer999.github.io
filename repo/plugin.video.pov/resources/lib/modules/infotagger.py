infotag_dict = {'country': 'setCountries',
				'director': 'setDirectors',
				'duration': 'setDuration',
				'genre': 'setGenres',
				'imdbnumber': 'setIMDBNumber',
				'mediatype': 'setMediaType',
				'mpaa': 'setMpaa',
				'original_title': 'setOriginalTitle',
				'playcount': 'setPlaycount',
				'plot': 'setPlot',
				'premiered': 'setPremiered',
				'rating': 'setRating',
				'studio': 'setStudios',
				'tagline': 'setTagLine',
				'title': 'setTitle',
				'trailer': 'setTrailer',
				'votes': 'setVotes',
				'writer': 'setWriters',
				'year': 'setYear',
				# tvshow exclusive
				'air_date': 'setPremiered',
				'aired': 'setFirstAired',
				'episode': 'setEpisode',
				'season': 'setSeason',
				'status': 'setTvShowStatus',
				'tvshowtitle': 'setTvShowTitle',
				'ep_name': 'setTitle'}

def infoTagger(infotag, meta=None):
	if not meta: return
	meta_get = meta.get
	if 'episode' in meta: infotag_dict['premiered'] = 'setFirstAired'
	for key in infotag_dict:
		try:
			if not key in meta or not (arg := meta[key]): continue
			if   key in {'director', 'genre', 'studio', 'writer'}: arg = arg.split(', ')
			elif key in {'episode', 'season', 'year'}: arg = int(arg)
			func = getattr(infotag, infotag_dict[key])
			func(arg)
		except: pass

