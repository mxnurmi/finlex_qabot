from flask import Flask
from flask import render_template
from flask import request
from main import searchTool
import numpy as np
from util import findTitle,highLight,create_model,create_samples,create_inputs
app = Flask(__name__)
model=create_model()


@app.route('/')
def front_page():
    searchword = request.args.get('key', '')
    paragraphs=searchTool(searchword)
    if not paragraphs:
        print("The search didn\'t return any matching terms")
        return render_template('search.html',key='',results=[])

    texts=list(map(findTitle,paragraphs))
    samples=map(lambda t:t["text"],texts)
    samples=create_samples(samples,searchword)[0:10]
    inputs=create_inputs(samples)
    pred_start, pred_end = model.predict(inputs)
    spans=findSpans(pred_start, pred_end,samples)
    print(spans)
    results=[]
    highlight_texts=list(map(lambda text,span:highLight(text.context,span),samples,spans))
    for idx,text in enumerate(highlight_texts):
        results.append({"text":text,"title":texts[idx]["title"]})
    return render_template('search.html',key=searchword, results=results)

def findSpans(pred_start, pred_end,samples):
    result=[]
    for idx, (start, end) in enumerate(zip(pred_start, pred_end)):
        sample = samples[idx]
        offsets = sample.context_token_to_char
        start = np.argmax(start)
        end = np.argmax(end)
        pred_ans = None
        if start >= len(offsets):
            result.append((0,0))
            continue
        pred_char_start = offsets[start][0]
        if end < len(offsets):
            result.append((pred_char_start,offsets[end][1]))
        else:
            result.append((pred_char_start,len(sample.context)-1))
    return result
