#import sparql
#%%
from SPARQLWrapper import SPARQLWrapper, JSON
import whoosh.index as index
from whoosh import index
from whoosh.fields import Schema, TEXT
from whoosh.qparser import QueryParser
from whoosh.analysis import LanguageAnalyzer
import os.path
# https://pypi.org/project/sparql-client/
import re

#%%

endpoint = "http://data.finlex.fi/sparql"

def fetchLawData(q, endpoint):
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
        
        print(jsondata)
        
        for result in jsondata["results"]["bindings"]:
            item = result["content"]["value"]
            #item = item.encode('utf-8').strip()
            text.append(item)
    except Exception as e:
        print("The data fetch failed", e)
        
    
    #Return only the latest item TODO: better way would be to only fetch the latest?
    lex = text[-1]
      
    return lex


# if __name__ == "__main__":

#     #NOTE: spaces in the queries are super important for them to work!!
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

q2 = ("""
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
    BIND(IRI(CONCAT(str(?document_version),"/fin/txt")) AS ?format)
    
    # replace sfl:text with sfl:html for html version
    ?format sfl:text ?content.}
    """)

lex = fetchLawData(q2, endpoint)

# %%

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

preprosessed_lex = preprocessLawText(lex)
#print(preprosessed_lex[0])

# %%

def indexLawText(law_as_list):
    """
    Index the preprocessed law text
    
    Parameters:
    law_as_list: Preprocessed input text

    """
    #TODO:use writer.add_document() to add each pykala per luku
    # e.g. writer.add_document(content=u"Luku 1")

    stem_ana = LanguageAnalyzer("fi") #TODO: should be LanguageAnalyzer("es") ('ar','da','nl','en','fi','fr','de','hu','it','no','pt','ro','ru','es','sv','tr')
    schema = Schema(content=TEXT(analyzer=stem_ana, stored=True))

    if not os.path.exists("index"):
        os.mkdir("index")

    if index.exists_in("index"):
        print("overwriting old index")

    ix = index.create_in("index", schema)

    ix = index.open_dir("index")
    writer = ix.writer()

    for seg in law_as_list:
        #print(len(seg))
        writer.add_document(content=seg)
    
    writer.commit(optimize=True)

    return ix

ix = indexLawText(preprosessed_lex)

# %%

def searchFromIndexedLaw(ix, querystr):
    """
    Search query from the indexed law text

    Parameters:
    ix: Index object that contains info about the indexed text
    querystr: Search query as String

    """

    qp = QueryParser("content", schema=ix.schema)
    query = qp.parse(querystr)

    topAnswers = []

    with ix.searcher() as searcher:
        results = searcher.search(query, limit=20)
        
        for item in results:
            topAnswers.append(item["content"])
            #print(item["content"])

        #topAnswers = results[0:10]

    return topAnswers

answers = searchFromIndexedLaw(ix=ix, querystr="kuolema") #TODO: one issue is with queries with lemma / stemma e.g. murha vs murhasta

print(answers[0:4])


# %%
