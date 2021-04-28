#%%
from SPARQLWrapper import SPARQLWrapper, JSON
import whoosh.index as index
from whoosh import qparser
from whoosh.fields import Schema, TEXT
from whoosh.qparser import QueryParser
from whoosh.analysis import LanguageAnalyzer
import os.path
import re

#%%

def fetchLawData(q, endpoint="http://data.finlex.fi/sparql"):
    #res = sparql.Service(endpoint, qs_encoding='utf-8').query(q)
    #data = []
    #variables = (res.variables)
    #row is what we want
    
    text = []
    
    sparql = SPARQLWrapper(endpoint)
    
    sparql.setReturnFormat(JSON)
    #results = sparql.query().convert()
    
    sparql.setQuery(q)
    
    try:
        jsondata = sparql.query().convert()
        #print(jsondata)
        for result in jsondata["results"]["bindings"]:
            item = result["content"]["value"]
            text.append(item)
    except Exception as e:
        print("The sparkql data fetch failed", e)
        
    #Return only the latest item TODO: better way would be to only fetch the latest?
    lex = text[-1]
      
    return lex

# %%
#import re
#item = "Hei testi. Miten menee."
#match = re.search(r"([A-ZÅÄÖ]).*?([A-ZÅÄÖ])", item)
#print(match)

# %%

def split_item(item):
    titlesearch = re.sub("\n", " ", item)
    match = re.search(r"([A-ZÅÄÖ]).*?([A-ZÅÄÖ])", titlesearch)
    second = match.span()[1]
    title = titlesearch[:second-2]

    split_items = re.split("\n", item)
    final_items = []

    for i, split_item in enumerate(split_items):
        if (i != 0 and i % 2 == 0):
            if i == 2:
                new = "" + split_items[i - 1] + " " + split_items[i] #first item is always title so then we don't add one
            else:
                new = "" + title + " " + split_items[i - 1] + split_items[i]

            new = re.sub("\n", " ", new)
            final_items.append(new)

        if i == (len(split_items) - 1) and i % 2 != 0:
            new = "" + title + split_item
            new = re.sub("\n", " ", new)
            final_items.append(new)

    #print(final_items)
    " ".join(final_items)

    return final_items


def preprocessLawText(txt):
    
    #TODO: preprocess text, best way might be by splitting with "§ (" -> nvm, problem if pykala doesn't have earlier version. use re to detect when there is number + § instead

    #test_txt = re.split("\n\n+", txt) # this can be used for smaller segments
    #print(test_txt[29])

    new_txt = re.sub("\n+", "\n", txt) #remove when multiple \n
    new_txt_list = re.split("\n\d+ §", new_txt) # #[.]\s
    #print(new_txt_list)

    final_txt = []
    #maxi = -1
    #mini = 10000
    #mini_thres = 30
    #count = 0

    length_threshold = 1000
    for item in new_txt_list:
        
        #check_item = add_to_next + item
        #if (i % 3 == 0 and i != 0):
            #new_item = re.sub("\n", " ", ("" + new_txt_list[i-1] + new_txt_list[i] + new_txt_list[i+1]) )

        #if len(new_item) > length_threshold:
            #print("hep")
            #new_l = split_item(new_item)
            #for shorter_item in new_l:
                 #final_txt.append(shorter_item)

        new_item = item
        if len(new_item) > length_threshold:
            new_item = split_item(new_item)
            #print(new_item)
        #else:
            #new_item = re.sub("\n", " ", item)

        #if len(new_item < 100):
            #skip_next = True
            #add_to_next = add_to_next + new_item

        #print(len(new_item))


        # val = len(new_item)

        # if val < mini_thres:
        #     count += 1

        # if (val > maxi):
        #     maxi = len(new_item)
        
        # if (val < mini):
        #     mini = len(new_item)

        # print("max, min")
        # print(maxi, mini)

        #print(len(new_item))

        #if i == (len(new_txt_list) - 1):
            #skip_next = False

        #if skip_next == False:
            #final_txt.append(new_item)
            #add_to_next = ""
        #else:
            #add_to_next = add_to_next + new_item
            #skip_next = False
        #print("new")
        #print(" ")
        #print(new_item)

        #new_item = re.sub("\n", " ", new_item) 

        final_txt.append(new_item)
    #print(final_txt)

    
    return final_txt

# %%

def indexLawText(law_as_list):
    """
    Index the preprocessed law text
    
    Parameters:
    law_as_list (list): Preprocessed input text

    """
    #TODO:use writer.add_document() to add each pykala per luku
    # e.g. writer.add_document(content=u"Luku 1")

    ana = LanguageAnalyzer("sv") #TODO: should be LanguageAnalyzer("es") ('ar','da','nl','en','fi','fr','de','hu','it','no','pt','ro','ru','es','sv','tr')
    schema = Schema(content=TEXT(analyzer=ana, stored=True))

    if not os.path.exists("index"):
        os.mkdir("index")

    if index.exists_in("index"):
        print("Overwriting old index...")
    
    ix = index.create_in("index", schema)

    ix = index.open_dir("index")
    writer = ix.writer()

    for seg in law_as_list:
        #print(len(seg))
        writer.add_document(content=seg)
    
    writer.commit(optimize=True)
    print("Indexing done. You can now use the searchTool() for your queries")
    return ix

# %%

def searchFromIndexedLaw(ix, querystr):
    """
    Search query from the indexed law text

    Parameters:
    ix: Index object that contains info about the indexed text; if None, uses "./index"
    querystr: Search query as String

    """
    if ix == None:
        if index.exists_in("index"):
            ix = index.open_dir("index")
        else: 
            raise Exception("The index folder is missing, initialize it with initSearchTool() first")

    og = qparser.OrGroup.factory(0.5)
    qp = QueryParser("content", schema=ix.schema, group=og)

    query_parsed = ""
    ana = LanguageAnalyzer("sv") 
    for token in ana(querystr):
        query_parsed += " " + token.text
    
    query = qp.parse(query_parsed)

    topAnswers = []

    with ix.searcher() as searcher:
        results = searcher.search(query, limit=10)
        
        for item in results:
            topAnswers.append(item["content"])
            #print(item["content"])

        #topAnswers = results[0:10]

    return topAnswers


def initSearchTool(query=None):
    """
    Initialize the search tool. Fetches and 

    Parameters:
    ix: Index object that contains info about the indexed text; if None, uses "./index"
    querystr: Search query as String

    """

    if (query==None):
        q = ("""
            PREFIX sfl: <http://data.finlex.fi/schema/sfl/>
            PREFIX eli: <http://data.europa.eu/eli/ontology#>
            
            # Query : Get different temporal versions of Criminal Code
            SELECT ?document_version ?format ?content 
            WHERE {
            # you can replace <http://data.finlex.fi/eli/sd/1889/39> with eg. one of the following: #copyright = 1961/404
            # http://data.finlex.fi/eli/sd/1889/39/johtolause
            # http://data.finlex.fi/eli/sd/1889/39/luku/1
            # http://data.finlex.fi/eli/sd/1889/39/luku/1/pykala/1
            <http://data.finlex.fi/eli/sd/1961/404> eli:has_member ?document_version .
            
            # lang options: fin,swe
            # format options: txt and html
            BIND(IRI(CONCAT(str(?document_version),"/swe/txt")) AS ?format)
            
            # replace sfl:text with sfl:html for html version
            ?format sfl:text ?content.}
            """)
    else:
        q = query

    lex = fetchLawData(q)
    preprosessed_lex = preprocessLawText(lex)
    _ix = indexLawText(preprosessed_lex)

def searchTool(search_query):

    answers = searchFromIndexedLaw(ix=None, querystr=search_query)

    for i,answer in enumerate(answers):
     #   if i == 5:
      #      break
        print("Answer number %i: %s" % (i+1,answer))
        print("")

    return answers

# %%
initSearchTool()

x = searchTool("kan jag använda material för min vetenskapiska presentation?")
#x = searchTool("vetenskap")
#print(x[1])

# %%
