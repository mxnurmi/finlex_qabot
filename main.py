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

# if __name__ == "__main__":

#     #NOTE: spaces in the queries change the querie so be careful with them
#     q2 = ("""
#       PREFIX sfl: <http://data.finlex.fi/schema/sfl/>
#       PREFIX eli: <http://data.europa.eu/eli/ontology#>
    
#       # Query : Get different temporal versions of Criminal Code
#       SELECT ?document_version ?format ?content 
#       WHERE {
#         # you can replace <http://data.finlex.fi/eli/sd/1889/39> with eg. one of the following:
#         # http://data.finlex.fi/eli/sd/1889/39/johtolause
#         # http://data.finlex.fi/eli/sd/1889/39/luku/1
#         # http://data.finlex.fi/eli/sd/1889/39/luku/1/pykala/1
#        <http://data.finlex.fi/eli/sd/1889/39> eli:has_member ?document_version .
    
#        # lang options: fin,swe
#        # format options: txt and html
#        BIND(IRI(CONCAT(str(?document_version),"/fin/txt")) AS ?format)
    
#        # replace sfl:text with sfl:html for html version
#        ?format sfl:text ?content.}
#       """)
    
    #lex = fetchLawData(q2, endpoint)

    #print(lex)
    #everything = []
    
    #paragraphs = lex.split("\n")
    #print(paragraphs)

# %%

# q1 = ("""
#     PREFIX sfl: <http://data.finlex.fi/schema/sfl/>
#     PREFIX eli: <http://data.europa.eu/eli/ontology#>
    
#     # Query : Get different temporal versions of Criminal Code
#     SELECT ?document_version ?format ?content 
#     WHERE {
#     # you can replace <http://data.finlex.fi/eli/sd/1889/39> with eg. one of the following:
#     # http://data.finlex.fi/eli/sd/1889/39/johtolause
#     # http://data.finlex.fi/eli/sd/1889/39/luku/1
#     # http://data.finlex.fi/eli/sd/1889/39/luku/1/pykala/1
#     <http://data.finlex.fi/eli/sd/1889/39> eli:has_member ?document_version .
    
#     # lang options: fin,swe
#     # format options: txt and html
#     BIND(IRI(CONCAT(str(?document_version),"/swe/txt")) AS ?format)
    
#     # replace sfl:text with sfl:html for html version
#     ?format sfl:text ?content.}
#     """)

# lex = fetchLawData(q1, endpoint)


def preprocessLawText(txt):
    
    #TODO: preprocess text, best way might be by splitting with "§ (" -> nvm, problem if pykala doesn't have earlier version. use re to detect when there is number + § instead

    #test_txt = re.split("\n\n+", txt) # this can be used for smaller segments
    #print(test_txt[29])

    new_txt = re.sub("\n+", "\n", txt) #remove when multiple \n
    new_txt_list = re.split("\n\d+ §", new_txt)

    final_txt = []
    for item in new_txt_list:
        new_item = re.sub("\n", " ", item)
        #print(len(new_item))
        final_txt.append(new_item)

    return final_txt

# %%

def indexLawText(law_as_list):
    """
    Index the preprocessed law text
    
    Parameters:
    law_as_list: Preprocessed input text

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
            # you can replace <http://data.finlex.fi/eli/sd/1889/39> with eg. one of the following:
            # http://data.finlex.fi/eli/sd/1889/39/johtolause
            # http://data.finlex.fi/eli/sd/1889/39/luku/1
            # http://data.finlex.fi/eli/sd/1889/39/luku/1/pykala/1
            <http://data.finlex.fi/eli/sd/1889/39> eli:has_member ?document_version .
            
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
    ix = indexLawText(preprosessed_lex)

def searchTool(search_query):

    answers = searchFromIndexedLaw(ix=None, querystr=search_query)

    #for i,answer in enumerate(answers):
     #   if i == 5:
      #      break
       # print("Answer number %i: %s" % (i+1,answer))
        #print("")

    return answers

# %%
#initSearchTool()

#x = searchTool("Är ett förskingringsförsök straffbart?")
#print(x[0])
