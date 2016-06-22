# -*- coding: utf-8 -*-
"""
Created on Sat Oct  3 13:06:06 2015

Parse results of Google Scholar search for specific terms. Original code from:
@see http://code.activestate.com/recipes/523047-search-google-scholar/#c2
I've updated it to BeautifulSoup4 and current syntax of Google Scholar source.
Also started saving the results in a class object for compatibility with other code.

@author: Alek
@version: 1.0.5
@since: Sat 11 Jun 2016

CHANGELOG:
Sat  3 Oct 2015 - 1.0.0 - Alek - Issued the first version based on a class from the Internet.
Mon  5 Oct 2015 - 1.0.1 - Alek - Now don't try to parse citations.
                - 1.0.2 - Alek - Now convert authors' list to str from Unicode.
Sat 11 Jun 2016 - 1.0.3 - Alek - Explicitly specified a parser for BeautifulSoup.
                - 1.0.4 - Alek - Raise RuntimeError when getArticlesFromPage finds no Articles.
                - 1.0.5 - Alek - Use BeautifulSoup to get the articles' titles.
"""
import httplib, urllib, re
from bs4 import BeautifulSoup
import Article

IntegerPattern = re.compile('\s+\d+\s*') # Expects at least one whitespace in front the integer. May be followed by a whtitespace too.

headers = {'User-Agent': 'Mozilla/5.0', # Just pretend to be a Mozilla. (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11
   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
   'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
   'Accept-Encoding': 'none',
   'Accept-Language': 'en-US,en;q=0.8',
   'Connection': 'keep-alive'}
       
class GoogleScholarSearchEngine:
    """ This class searches Google Scholar (http://scholar.google.com)

    Search for articles and publications containing terms of interest.
    
    Example
    ----------
    <tt>
    > from google_search import *\n
    > searcher = GoogleScholarSearch()\n
    > searcher.search(['breast cancer', 'gene'])
    </tt>
    """
    def __init__(self):
        """  Empty initialiser.
        """
        self.SEARCH_HOST = "scholar.google.com"
        self.SEARCH_BASE_URL = "/scholar"

    def search(self, searchTerms, limit=10):
        """ Searches Google Scholar using the specified terms.
        
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
        @param searchTerms - list of strings that we'll search for.
        @param limit - int, maximum number of results to be returned (default=10).
        
        Returns
        ----------
        @return List of Articles (@see Article.Article), or an empty list if
            nothing is found.
        
        Raises
        ----------
        IOError when the connection to Google Scholar cannot be established.
        """
        params = urllib.urlencode({'q': "+".join(searchTerms), 'num': limit})
        url = self.SEARCH_BASE_URL+"?"+params # URL of the actual search with all the terms.
        return self.getArticlesFromPage( url, searchTerms)
        
    def getArticlesFromPage(self, url, searchTerms):
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
        @param url - str, URL to be appended to the self.SEARCH_HOST (i.e. scholar.google.com)
            to get to the results page (example: /scholar?q=related:X7dZ0Xg524gJ:scholar.google.com/&hl=en&as_sdt=0,5)
        @param searchTerms - list of strings that we'll search for.
        
        Returns
        ----------
        @return List of Articles (@see Article.Article), or an empty list if
            nothing is found.
        
        Raises
        ----------
        IOError when the connection to Google Scholar cannot be established.
        RuntimeError - when no articles are found.
        """
        conn = httplib.HTTPConnection(self.SEARCH_HOST, timeout=30)
        conn.request("GET", url, body=None, headers=headers)
        resp = conn.getresponse()
        results = [] # The list of Articles we'll return.
        
        if resp.status==302: # We got a redirect.
            pass#print resp.geturl() # TODO handle this
            print "Got error 302 - redirection."
        elif resp.status==200:
            html = resp.read()
            html = html.decode('ascii', 'ignore') # Raw HTML file of the website with the search results.
            # Screen-scrape the result to obtain the publication information
            soup = BeautifulSoup(html, "lxml")
            
            for record in soup.find_all('div',{'class': 'gs_r'}):#soup('p', {'class': 'g'}):
            #TODO this could work better:
            # work with record.find('div',{'class': 'gs_ri'}), which filters out full view and full text links
            #title,pubURL in: record.find_all('div',{'class': 'gs_ri'})[0].find_all('h3',{'class': 'gs_rt'})
                
            #authors,journal,year record.find_all('div',{'class': 'gs_ri'})[0].find_all('div',{'class': 'gs_a'})
#                authorsPart=record.find('div',{'class': 'gs_ri'}).find('div',{'class': 'gs_a'})
            #abstract record.find_all('div',{'class': 'gs_ri'})[0].find_all('div',{'class': 'gs_rs'})
#                abstractPart=record.find('div',{'class': 'gs_ri'}).find('div',{'class': 'gs_rs'})
                if "[CITATION]" in record.text: # This isn't an actual article.
                    continue
                else:
                    allAs = record.find_all('a') # All <a></a> fields corresponding to this article.
    
                    " Get the public URL and the title, maybe full text URL if we're lucky. "
                    titleURLPart=record.find('div',{'class': 'gs_ri'}).find('h3',{'class': 'gs_rt'})
                    pubURL=titleURLPart.find('a').get('href')
                    pubTitle=titleURLPart.find('a').get_text()
                    
                    if len( allAs[0].find_all("span") ): # The first <a> has some <span> children.
                        fullURL = allAs[0].attrs['href'] # URL to the full text in HTML or PDF format (typically).
                    else: # The first <a> of the result is the one with the title and public URL.
                        fullURL = "Unavailable" # No full text for this article... :(
                    
                    " Get the articles citing and related to this one. "
                    citingArticlesURL = "UNKNOWN" # Initialise in case something goes wrong in parsing and this will be undefined.
                    relatedArticlesURL = "UNKNOWN"#TOOO these won't always be found, why?
                    for a in allAs:
                        if "Cited by" in a.text:
                            pubNoCitations = int(  IntegerPattern.findall(a.text)[0] )
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
                        pubJournalYear = int(IntegerPattern.findall(authorPart)[0]) # We might get other integers, but not preceded by whitespaces.
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
                            # Sometimes there simply is no abstract?
                        print "-"*10
                    
                    " Save the results. "
                    results.append( Article.Article(pubTitle.encode('utf-8'),map(lambda x: x.encode('utf-8'),pubAuthors.split(',')),pubJournalYear,pubJournalName.encode('utf-8'),tagList=searchTerms,abstract=pubAbstract.encode('utf-8')) )
                    # All the URLs.
                    results[-1].fullURL = fullURL
                    results[-1].pubURL = pubURL
                    results[-1].citingArticlesURL = citingArticlesURL
                    results[-1].relatedArticlesURL = relatedArticlesURL
                    # This might be useful to something, e.g. seeing whcih publications have the most impact.
                    results[-1].pubNoCitations = pubNoCitations
            
            if len(results)==0: # Check if we got any articles in the end.
                raise RuntimeError("No articles found with URL: {}, source:\n{}".format(url,html))
        else:
            raise IOError("Connection can't be established. Error code: {}, Reason: {}".format(resp.status,resp.reason))
        
        return results # If everything's gone smoothly...

if __name__ == '__main__':
    search = GoogleScholarSearchEngine()
    pubs = search.search(["breast cancer", "gene"], 10)
    for pub in pubs:
        print pub
        # This is how to get the citing abd related Articles.
#        search.getArticlesFromPage(pub.citingArticlesURL,["breast cancer", "gene"],)