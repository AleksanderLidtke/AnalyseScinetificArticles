# -*- coding: utf-8 -*-
"""
Test downloading scientific articles' infomration from the web.

Created on Sun Apr 19 20:46:55 2015

@author: alek
"""

import os, requests, re, difflib, time, numpy, httplib, subprocess

try:
    from selenium import webdriver
except ImportError:
    print "Install Selenium using sudo pip install selenium. If you aren't running Unix and can't use pip then you should abandon Windows."

import Article, GoogleScholarSearch

CACHE_DIR = '/home/alek/Desktop/' # Will store the page sources here.

scholarSearchEngine = GoogleScholarSearch.GoogleScholarSearchEngine() # Convenient to search through Google Scholar.

" General regexes. "
IntegersParern = re.compile("\d+") # Any integer.
YearPattern = re.compile('\([0-9a-zA-Z\s]*\d{4}\)') # Any four-digit year encolsed in parentheses; may be preceded by a month in any format and also a day.
LinksPattern = re.compile('"((http|ftp)s?://.*?)"') # Will find URLs in a website text.

" CiteULike.org-specific regexes. "
TitlePattern = re.compile(';</span>.+</a></h2>') # A number of regexes designed to extract bits of information from the lines of CiteULike.org results website.
JournalPattern = re.compile('<i>[a-zA-Z\s\W\d]+</i>')
NoPattern = re.compile("No\.\s\d+")
VolPattern = re.compile("Vol\.\s\d+")
DOIPattern = re.compile(">doi\:[\W\w]+</a></div>")
AuthorPattern = re.compile('>[a-zA-Z\s.-]+</a>')
TagPattern = re.compile('>[a-zA-Z]+</a>')
ArticleIDsPattern = re.compile('<tr class="list {article_id:\d+}" data-article_id=\d+>') # Will find the beginnings of the articles from CIteULike.org.

" Google Scholar-specific regexes. "
CitedByPattern = re.compile('cites=\d+') # Will find those parts of the links that enable the papers that cite a given article to be displayed on Google Scholar.
TitlePatternGoogle = re.compile('nossl=1">[\s\w\d\:\-\,\.\;\&\#]+</a></h3>') # Just think of all the stuff people might put in titles... Also sometimes Google will put weird stuff like &#8208; instead of -, which probably has to do with encoding. But I know too little about this to fix it.
YearPatternGoogle = re.compile('\,\s\d{4}[\s\-<]*')
ArticleInfoPatternGoogle = re.compile('[\.\,\-\s\w]+\,\s\d{4}[\s\-<]*') # Will find the list of authors, journal, and year.
CitedByNumberPattern = re.compile('Cited\sby\s\d+') # How many times the given article has been cited.

def getArticlesCiteULike(authors=[], keywords=[], yearStart=1800, yearEnd=3000, title="", isbn="none", pageLimit=2):
    """ Find scientific articles that match given criteria on-line.
    
    Arguments
    ----------
    authors - list of strings with author names; can be surnames or surnames with
        names or initials.
    keywords - list of strings with the keywords to look for.
    yearStart - starting year of the published year bracket within which to find
        the articles.
    yearEnd - fina; year of the published year bracket within which to find
        the articles.
    title - string with the title of the article.
    isbn - str with the ISBN of the publication.
    pageLimit - int, how many pages of the results will be searched.
        
    Returns
    ----------
    A list of Articles @see Article.
    """
    pageNo = 1 # Number of the page with results.
    
    " Go through all the result pages we might get. "
    while pageNo <= pageLimit: # Unlikely that we'll get so many results but we don't want infinite loops, do we?
        " Build the search URL. "
        if not title: # We aren't looking for a specific title.
            BASE_SEARCH_URL = "http://www.citeulike.org/search/all/page/{}?q=".format( pageNo ) # All the search criteria are appended to this.
            searchURL = BASE_SEARCH_URL # Start from this and add all the search criteria.
            for tag in keywords:
                searchURL += "tag%3A"
                searchURL += '"{}"'.format(tag)
                searchURL += "+"
            for author in authors:
                searchURL += "author%3A"
                searchURL += '"{}"'.format(author) # author has to be in quotes.
                searchURL += "+"
            searchURL += "year%3A%5B{}+TO+{}%5D".format(yearStart,yearEnd)
            searchURL += "+isbn%3A{}".format(isbn)
        else: # The URL to look for specific titles is a bit different.
            BASE_SEARCH_URL = "http://www.citeulike.org/search/all/page/{}?q=title>".format( pageNo )
            searchURL = BASE_SEARCH_URL # Start from this and add all the search criteria.
            searchURL += title + "+"
            for tag in keywords:
                searchURL += "tag%3A"
                searchURL += '"{}"'.format(tag)
                searchURL += "+"
            for author in authors:
                searchURL += "author%3A"
                searchURL += '"{}"'.format(author) # author has to be in quotes.
                searchURL += "+"
            searchURL += "year%3A%5B{}+TO+{}%5D".format(yearStart,yearEnd)
            searchURL += "+isbn%3A{}".format(isbn)

        " Perform the actual search. "
        the_page = requests.get(searchURL).text # Get the text version of the website. Use requests not urllib2 because the page will be too large for it.
        
        lines = the_page.split("\n") # Parsing lines is easier than coming up with regexes to get the info about all the articles from the_page. Besides not every article will have all the information.
        
        # Initialise the artcile attributes.
        articleID=-1; articleTitle=""; authors=[]; year=0; journalTitle=""; doi=""; volume=-1; number=-1; tags=[]; abstract="";
        articles = [] # Articles we've found.
        firstArticle = True # If this is the first article we're reading.
        for i in range(len(lines)):
            if lines[i].startswith('<tr class="list {article_id:'):
                if firstArticle: # articleID and all the rest aren't defined yet.
                    articleID = int(IntegersParern.findall(lines[i])[0])
                    firstArticle = False
                else: # First add the artcile we've just parsed, then proceed to parsing the new one.
                    articles.append( Article.Article(articleID, articleTitle, authors, year, journalTitle, doi, volume, number, tags, abstract) )
                    articleID = int(IntegersParern.findall(lines[i])[0])
            if '<a class="title"' in lines[i]:
                articleTitle = TitlePattern.findall(lines[i])[0].rstrip("</a></h2>").lstrip(";</span>")
            if "<a href='http://dx.doi.org" in lines[i]:
                try:
                    journalTitle = JournalPattern.findall(lines[i])[0].rstrip("</i>").lstrip("<i>")
                except IndexError:
                    print "\nNo journalTitle for:\n\t{}".format(lines[i])
                    journalTitle = "UNKNOWN JOURNAL"
                    
                try:
                    year = int( YearPattern.findall(lines[i])[0][-5:-1] ) # This may have a day and month in front, only extract the year (always last and followed by ")" ).
                except IndexError:
                    print "\nNo year for:\n\t{}".format(lines[i])
                    year = 0
                
                try:
                    volume = int(VolPattern.findall(lines[i])[0].lstrip("Vol. "))
                except IndexError:
                    print "\nNo volume for:\n\t{}".format(lines[i])
                    volume = -1
                
                try:
                    number = int(NoPattern.findall(lines[i])[0].lstrip("No. "))
                except (IndexError, ValueError):
                    print "\nNo number for:\n\t{}".format(lines[i])
                    number = -1
                
                doi = DOIPattern.findall(lines[i])[0].lstrip(">").rstrip("</a></div>")
            if '<a class="author"' in lines[i]:
                authors = map(lambda x: x.lstrip(">").rstrip("</a>"), AuthorPattern.findall(lines[i]))
            if '<span class="taglist">' in lines[i]:
                tags = map(lambda x: x.lstrip(">").rstrip("</a>"), TagPattern.findall(lines[i]))
            if '<h3>Abstract</h3>' in lines[i]:
                abstract = lines[i+1].lstrip("<p>").rstrip("</p>")
        # Add the last article.
        articles.append( Article.Article(articleTitle, authors, year, journalTitle, doi, volume, number, tags, abstract, articleID) )

        pageNo += 1 # Go to the next results page.
        
    return articles

def getSourceWithFirefox(url, cacheName=None):
    """ Get the string with the source of the website at the URL. If desired,
    will cache the source in a text file.
    
    Argumets
    ----------
    url - str with a full URL of a website
    cacheName - None or str, if is type str will be the name of the text file
        where the source is going to be saved.
        
    Returns
    ----------
    str with the source of the website.
    """
    firefoxDriver = webdriver.Firefox() # Open Firefox.
    
    firefoxDriver.get(url) # Go to the page.
    src = firefoxDriver.page_source # Get source because.
    
    firefoxDriver.close()
    
    return src

def getArticlesFromSource(source, searchTerms):
    """ Parses a given Google Scholar results page and returns a list of 
        Articles that are displayed there. This can be used to find citing or 
        related Articles using the citingArticlesURL or relatedArticlesURL fields.
        
        Returns a list of Artciles. Each Article contains the information related
        itin the following fields that every Article has:
            Title    : str, title of the publication
            Authors  : list of strings with author names (example: DF Easton, DT Bishop, D Ford)
            Journal  : str, name of the journal (example: Nature, Cancer Research)
            Year     : str, journal name & year (example: Nature, 2001)
            Keywords : list of strings with search terms used in the query
            Abstract : str, abstract of the publication
            
        Additional fields are added when creating the Articles here:
            JournalURL  : string with a link to the journal main website (example: www.nature.com),
                "Unavailable" if journal's URL is unkown.
            fullURL     : string with a link to the full text in HTML/PDF format,
                "Unavailable" if full text is unavailable
            pubURL      : string with a link to the publicly available version of the paper
            citingArticlesURL : string with a link to the site with articles citing this one
            relatedArticlesURL: string with a link to the site with articles related this one
                according to Google Scholar
            pubNoCitations    : number of times the publication is cited
            

        Arguments
        ----------
        @param source - ASCII str, HTML source of the page from which to extract the Articles.
        @param searchTerms - list of strings that we'll search for.
        
        Returns
        ----------
        @return List of Articles (@see Article.Article), or an empty list if
            nothing is found.
    """
    soup = GoogleScholarSearch.BeautifulSoup(source)
    results = [] # Store the articles here.
    
    for record in soup.find_all('div',{'class': 'gs_r'}):#soup('p', {'class': 'g'}):
        allAs = record.find_all('a') # All <a></a> fields corresponding to this article.

        " Get the public URL and the title, maybe full text URL if we're lucky. "
        if len( allAs[0].find_all("span") ): # The first <a> has some <span> children.
            fullURL = allAs[0].attrs['href'] # URL to the full text in HTML or PDF format (typically).
            pubURL = allAs[1].attrs['href'] # This will be the public URL one gets when they click on the title.
            pubTitle = allAs[1].text # Public URL has the title of the article as text.
        else: # The first <a> of the result is the one with the title and public URL.
            fullURL = "Unavailable" # No full text for this article... :(
            pubURL = allAs[0].attrs['href']
            pubTitle = allAs[0].text
            
        " Get the articles citing and related to this one. "
        citingArticlesURL = "UNKNOWN" # Initialise in case something goes wrong in parsing and this will be undefined.
        relatedArticlesURL = "UNKNOWN"#TOOO these won't always be found, why?
        pubNoCitations = 0
        for a in allAs:
            if "Cited by" in a.text:
                pubNoCitations = int(  GoogleScholarSearch.IntegerPattern.findall(a.text)[0] )
                citingArticlesURL = a.attrs['href'] # Articles that cite this one.
            elif "Related articles" in a.text:
                relatedArticlesURL = a.attrs['href'] # URL to the related articles.
        
        " Get the authors; they're displayed in green, use it. "
        authorPart = record.find('div',attrs={'class':'gs_a'}).text #record.first('font', {'color': 'green'}).string
        if authorPart is None:    
            authorPart = ''
            # Sometimes even BeautifulSoup can fail, fall back to regex.
            m = re.findall('<font color="green">(.*)</font>', str(record))
            if len(m)>0:
                authorPart = m[0]

        " Get journal name, publication year, and authors' list. "
        # Assume that the fields are delimited by ' - ', the first entry will be the
        # list of authors, the last entry is the journal URL. We also have journal name and year there.
        try: #TODO this IntegerPattern will sometimes fail here.
            pubJournalYear = int(GoogleScholarSearch.IntegerPattern.findall(authorPart)[0]) # We might get other integers, but not preceded by whitespaces.
        except IndexError:
            print authorPart
            pubJournalYear=9999
        
        idx_start = authorPart.find(' - ') # Here the authors' list ends.
        idx_end = authorPart.rfind(' - ') # Here the journal's public URL starts.
        idx_jrnlNameEnd = authorPart.rfind(',') # After the journal name.
        
        pubJournalName = authorPart[idx_start:idx_jrnlNameEnd].lstrip().lstrip("-")
        
        pubAuthors = authorPart[:idx_start]                
        pubJournalURL = authorPart[idx_end + 3:]
        # If (only one ' - ' is found) and (the end bit contains '\d\d\d\d')
        # then the last bit is journal year instead of journal URL
        if pubJournalYear=='' and re.search('\d\d\d\d', pubJournalURL)!=None:
            pubJournalYear = pubJournalURL
            pubJournalURL = 'Unavailable'
        
        " Get the abstract. "
        abstractDiv = record.find('div',attrs={'class':'gs_rs'}) # Abstract info sits here.
        if not abstractDiv is None:
            pubAbstract = abstractDiv.text
        else:
            pubAbstract = "Abstract unavailable"
            print record#TODO see why this might trigger and maybe filter out such cases
                # Sosmetimes there simply is no abstract?
            print "-"*10
        
        " Save the results. "
        results.append( Article.Article(pubTitle,map(str,pubAuthors.split(',')),pubJournalYear,pubJournalName,tagList=searchTerms,abstract=pubAbstract) )
        # All the URLs.
        results[-1].fullURL = fullURL
        results[-1].pubURL = pubURL
        results[-1].citingArticlesURL = citingArticlesURL
        results[-1].relatedArticlesURL = relatedArticlesURL
        # This might be useful to something, e.g. seeing whcih publications have the most impact.
        results[-1].pubNoCitations = pubNoCitations
        
    return results # If everything's gone smoothly...
    
if __name__=="__main__": # If this is run as a stand-alone script run the verification/example searches.
    " Example search for many articles following search terms. "
#    authors = ["langmuir", "tonks"] # Author names.
#    tags = ["langmuir", "probe"] # Tags we want to look for.
#    years = (1900,2015) # Year brackets we're interested in.
#    isbn = "none"
#    articles = getArticlesCiteULike(authors, tags, years[0], years[1], isbn) # One way, seems to be more restrictive because we can specify additional criteria, like min and max year etc.
#    article = scholarSearchEngine.search(tags) # Another way, also works.

    " Search for the desired article. "
    theArticle = Article.Article("The Theory of Collectors in Gaseous Discharges", ["H.M. Mott-Smith", "Irving Langmuir"], 1926, "Physical Review", doi="10.1103/physrev.28.727", volume=28, number=4, citeULikeID=2534514) # The desired article.
    
    # Get all the articles from the page when we look for the title of theArticle of interest.
    searchURL = "/scholar?hl=en&q=" # Now we're searching for articles.
    searchURL += theArticle.Title.replace(" ","%20") # Search by title. We can't have space in there.
    papers = scholarSearchEngine.getArticlesFromPage(searchURL, ["Mock","terms"])
    
    # Find theArticle from the many that will be displayed - will define articleID.
    articleID = 0 # Which article from the page is the one we're looking for.
    currentMaxCited = 0
    currentHighestAuthorSimilarity = 0
    for i in range(len(papers)): # Articles that we have to look at to match to the article.
        if theArticle.Year==papers[i].Year: # This article is from the same year, promising.
            if difflib.SequenceMatcher(a="".join(theArticle.Authors).lower(), b="".join(papers[i].Authors).lower()).ratio() > currentHighestAuthorSimilarity: # The authors of this article look more like the authors of the input article.
                currentHighestAuthorSimilarity = difflib.SequenceMatcher(a="".join(theArticle.Authors).lower(), b="".join(papers[i].Authors).lower()).ratio()
                if papers[i].pubNoCitations> currentMaxCited: # We're probably after the popular articles. Sometimes will get copies of the original article with fewer citations.
                    articleID = i # This is probably theArticle we're after.
    print "Found article:\n{}\n when looking for:\n{}.".format(papers[articleID],theArticle)

    " Get articles citing theArticle. "
    citingArticles = [] # Collect citing articles from all the result pages.
    citingArticlesURLParts = papers[articleID].citingArticlesURL.split("?") # Need to split this to be able to display different result pages.
    noArticlesSoFar = 0 # How many have we downloaded so far?

    for startArticleIndex in range(0,papers[articleID].pubNoCitations,20): # The first article to be displayed on the Scholar page. Go every 20 articles to limit the number of requests we send.
#        print "Looking at start index {}.".format(startArticleIndex)
        url = "https://scholar.google.com"+citingArticlesURLParts[0]+"?"+"start={}&num=20&".format(startArticleIndex)+citingArticlesURLParts[1]

        try: # Try to get the cached source in the first instance.
            with open(os.path.join(CACHE_DIR,url.lstrip('https://scholar.google.com/scholar?')),"r") as cacheFile:
                src=cacheFile.read()
#                print "Got citing artciles starting on article index {} from cache. Currently have {} citingArticles.".format(startArticleIndex,len(citingArticles))
        except IOError: # No cache file - retrieve source with Firefox.
            src = getSourceWithFirefox(url) # Get the source of the website.
            src = src.encode('ascii', 'ignore') # Convert src from unicode to something, which can be written to a file.
#            print "Got citing artciles starting on article index {} from the web. Currently have {} citingArticles.".format(startArticleIndex,len(citingArticles))
            with open(os.path.join(CACHE_DIR,url.lstrip('https://scholar.google.com/scholar?')),"w") as cacheFile:
                cacheFile.write(src)
                dt = 60+numpy.random.randint(0,60,1)[0]
                print "\tSleeping for {} seconds.".format(dt)
                time.sleep(dt) # Wait a while to not send requests too quickly
            
        if not "Please show you\'re not a robot" in src: # Searching still works.
            temp = getArticlesFromSource(src,papers[articleID].Keywords) #TODO Check if I get all the articles now that I don't treat [CITATION]s any differently.
            
            citingArticles.extend(temp) # Add articles from this page to the results.
            print len(temp),startArticleIndex
#            print "\tParsed citing artciles starting on article index {}".format(startArticleIndex)
            
        else: # Let the user know they have to convince Google they're a human.
            proc = subprocess.Popen(['zenity', '--info', '--text="Please show Google that you are not a robot and click OK to continue downloading articles."'])
            proc.wait() # Wait for the user to click OK having shown that they're human.

            # Get the actual source of the website for this batch of articles , cache it and retrieve Articles from it.
            src = getSourceWithFirefox(url)
            src = src.encode('ascii', 'ignore')
            with open(os.path.join(CACHE_DIR,url.lstrip('https://scholar.google.com/scholar?')),"w") as cacheFile:
                cacheFile.write(src)
            temp = getArticlesFromSource(src,papers[articleID].Keywords)
            citingArticles.extend(temp)
#            print "Got citing artciles starting on article index {} from the web. Currently have {} citingArticles.".format(startArticleIndex,len(citingArticles))
        
    " Get articles related to theArticle. "
    #TODO add a loop through results' pages and time.sleep here.
#    relatedArticles = scholarSearchEngine.getArticlesFromPage(papers[articleID].relatedArticlesURL,papers[articleID].Keywords)