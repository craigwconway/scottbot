import nltk
from nltk.stem import WordNetLemmatizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import hashlib
import random
import re
import requests
import string

from bs4 import BeautifulSoup

import warnings
warnings.filterwarnings('ignore')


nltk.download('popular', quiet=True)
nltk.download('punkt')
nltk.download('wordnet')

NAME = "ScottBot"
DEFAULT = "I am " + NAME
INTRO = "I communicate with lines from my favorite movies and music."
HI = ("Hello", "Hi", "Greetings Program", "Sup",
      "What's up", "Hey", "Yo", "Hey dude", DEFAULT)
BYE = ['Bye', 'Goodbye', 'Later', 'L8R', 'Peace', 'See ya', 'cya']
THX = ['Thanks', 'Thank you', 'thx']
YW = ["You're welcome", "Whatever", "Sure", "yw"]
IDK = ["Huh?",  "What?", "Um...ok", "Uhhhhh...", DEFAULT, INTRO]
QUESTION = ['who', 'what', 'when', 'where',
            'why', 'how', 'can', 'could', 'would', 'will']
ANSWER = ["Yes", "No", "Maybe", "Why?", "Sure", DEFAULT, INTRO,
          "You'll figure it out ;)",
          "Don't ask these stupid questions, we're stuck, just send down the bucket. Come on."]
RE01 = re.compile("\t\t[A-Z]+")
RE02 = re.compile("\t\t\t[A-Z]+")
RE03 = re.compile("^[A-Z][A-Z]")
RE04 = re.compile("\t[A-Z]+[a-z]+")
RE05 = re.compile("                        [A-Z]+")
MOVIE_SOURCES = [
    ("https://sfy.ru/?script=rushmore", RE03),
    ("https://sfy.ru/?script=pulp_fiction", RE05),
    ("https://sfy.ru/?script=matrix_ds", RE01),
    ("https://sfy.ru/?script=lost_highway", RE02),
    ("https://sfy.ru/?script=graduate", RE01),
    ("https://sfy.ru/?script=ferris_bueller", RE01),
    ("https://sfy.ru/?script=fear_and_loathing", RE01),
    ("https://sfy.ru/?script=dune", RE01),
    ("https://sfy.ru/?script=clerks", RE02),
    ("https://sfy.ru/?script=breakfast_club", RE01),
    ("https://sfy.ru/?script=twin_peaks", RE01),
    ("https://sfy.ru/?script=goonies", RE04),
    ("https://sfy.ru/?script=tron_1982", RE01),
    ("https://sfy.ru/?script=blue_velvet", RE01),
]
MUSIC_SOURCES = [
    'beatles',
    'cake',
    'phish',
    'beck',
]
REMOVE_PUNCTUATION = dict((ord(punct), None) for punct in string.punctuation)


class ScottBot():

    def __init__(self):
        super().__init__()
        self.lemmer = WordNetLemmatizer()
        self.context = {}
        self.context_map = {}
        self.tokens = []
        self.responses = {}
        self.parse_movies()
        self.parse_songs()

    def lemmatizeTokens(self, tokens):
        return [self.lemmer.lemmatize(token) for token in tokens]

    def lemmatize(self, text):
        return self.lemmatizeTokens(nltk.word_tokenize(text.lower().translate(REMOVE_PUNCTUATION)))

    def parse_movies(self):
        for s in MOVIE_SOURCES:
            try:
                self.parse_movie_quotes(s[0], s[1])
            except:
                pass

    def parse_movie_quotes(self, url, regex):
        quotes = ''
        req = requests.get(url)
        html = BeautifulSoup(req.text)
        pre = html.find_all('pre')[0].text
        print(len(pre), url)
        quote_next_line = False
        for line in pre.split('\n'):
            if quote_next_line:
                quotes += self.clean(line) + ' '
                if '' == line.strip():
                    quotes += '||'
                    quote_next_line = False
                continue
            if regex.match(line):
                quote_next_line = True
        _quotes = [q for q in quotes.split(
            '||') if len(q.strip().split(' ')) > 2]
        print(len(_quotes), ' quotes')
        for q in _quotes:
            self.hash_quote(q, url)

    def parse_songs(self):
        for artist in MUSIC_SOURCES:
            search_url = 'http://www.songlyrics.com/index.php?section=search&submit=Search&searchIn1=artist&searchW={}'
            search_req = requests.get(search_url.format(artist))
            try:
                search_page = BeautifulSoup(search_req.text)
                results = search_page.findAll(
                    'div', attrs={"class": "serpresult"})
                for result in results:
                    link = result.find_all('a', href=True)
                    url = link[0]['href']
                    song_page_req = requests.get(url)
                    song_page = BeautifulSoup(song_page_req.text)
                    lyrics = song_page.find('p', attrs={"id": "songLyricsDiv"})
                    seperator = '\n\n' if '\n\n' in lyrics.text else '\n\r\n'
                    lyric_arr = lyrics.text.split(seperator)
                    print(len(lyric_arr), url)
                    for lyric in lyric_arr:
                        self.hash_quote(lyric + '.', url)
            except:
                pass

    def hash_quote(self, quote, source):
        if quote.lower().startswith("we do not have the lyrics for"):
            return
        hash_object = hashlib.md5(str.encode(quote))
        key = hash_object.hexdigest()
        self.context[key] = (quote, source)
        for t in nltk.sent_tokenize(quote.lower()):
            self.tokens.append(t)
            self.context_map[t] = key

    def bot_response(self, user_input, no_match_response):
        TfidfVec = TfidfVectorizer(
            tokenizer=self.lemmatize, stop_words='english')
        tfidf = TfidfVec.fit_transform(self.tokens + [user_input])
        vals = cosine_similarity(tfidf[-1], tfidf)
        n = -2  # closest match
        if len(vals.argsort()[0]) > 9:
            n = -1 * random.choice(range(2, 8))
        idx = vals.argsort()[0][n]
        flat = vals.flatten()
        flat.sort()
        req_tfidf = flat[n]
        if(req_tfidf == 0):
            return no_match_response
        matched = self.tokens[idx]
        key = self.context_map[matched]
        keys = list(self.context.keys())
        next_key = keys[keys.index(key)+1]
        r = {}
        r['n'] = n
        r['context'] = self.context[key][0]
        r['response'] = self.context[next_key][0]
        r['source'] = self.context[next_key][1]
        return r

    def respond(self, user_input):
        for i in [HI, BYE]:
            if self.is_match(user_input, i) and random.randint(1, 100) <= 50:
                return self.wrap_response(random.choice(i))
        if self.is_match(user_input, THX) and random.randint(1, 100) <= 30:
            return self.wrap_response(random.choice(YW))
        if self.is_match(user_input, QUESTION) and random.randint(1, 100) <= 5:
            return self.wrap_response(random.choice(ANSWER))
        return self.bot_response(user_input, self.wrap_response(random.choice(IDK)))

    def greet(self):
        return self.wrap_response(random.choice(HI) + ". " + INTRO + " Let's chat!")

    def wrap_response(self, response):
        r = {}
        r['response'] = response
        return r

    def clean(self, text):
        for m in re.compile('\(.*?\)').findall(text):
            text = text.replace(m, '')
        return text.strip().replace('  ', ' ').replace('\t', ' ')

    def is_match(self, line, arr):
        for i in arr:
            if line.startswith(i.lower()):
                return True
        return False


if __name__ == "__main__":
    pass
