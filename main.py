#import sparql
from SPARQLWrapper import SPARQLWrapper, JSON
# https://pypi.org/project/sparql-client/

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
        
    
    #Return only the latest item TODO: we should update the queries so that they only fetch latest
    lex = text[-1]
      
    return lex


def preprocessLawText(text):
    return 0


if __name__ == "__main__":

    
    #NOTE: spaces in the queries are super important for them to work!!
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

    print(lex)
    #everything = []
    
    #paragraphs = lex.split("\n")
    #print(paragraphs)
    

    #for word in lex:
        #print("hep")
        #print(type(item))
        
        #print(item)
        
        #print(type(item))
        
        #everything.append(word)
        
        #for word in item:
            #print(word)
            #everything.append(word)
            
    #everything2 = [string for string in everything if string != ""]
    
#print(t)

#sparql.Service(endpoint, "utf-8").query(q2)

#    q1 = (
#      'PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>'
#      'PREFIX sfl: <http://data.finlex.fi/schema/sfl/>'
#    
#      # Query : List 10 of the oldest statutes
#      'SELECT ?s WHERE'
#      '{ ?s rdf:type sfl:Statute .'
#      '} ORDER BY ?s LIMIT 10'
#    )
    
    #    q3 = (
#          'PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>'
#      'PREFIX sfcl: <http://data.finlex.fi/schema/sfcl/>'
#    
#      # Query : List judgments
#      'SELECT ?j WHERE'
#      '{'
#       '?j rdf:type sfcl:Judgment .'
#     '} LIMIT 10'
#    )
    