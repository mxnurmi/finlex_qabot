import re
import numpy as np
import tensorflow as tf
import tensorflow_hub as hub
from tensorflow import keras
from tensorflow.keras import layers
from tokenizers import BertWordPieceTokenizer
max_seq_length = 384
bert_layer = hub.KerasLayer("https://tfhub.dev/tensorflow/bert_multi_cased_L-12_H-768_A-12/4", trainable=True)
vocab_file = bert_layer.resolved_object.vocab_file.asset_path.numpy().decode("utf-8")
tokenizer = BertWordPieceTokenizer(vocab=vocab_file, lowercase=False)

class Sample:
    def __init__(self, question, context):
        self.question = question
        self.context = context
        self.skip = False


    def preprocess(self):
        context = " ".join(str(self.context).split())
        question = " ".join(str(self.question).split())
        tokenized_context = tokenizer.encode(context)
        tokenized_question = tokenizer.encode(question)
        input_ids = tokenized_context.ids + tokenized_question.ids[1:]
        token_type_ids = [0] * len(tokenized_context.ids) + [1] * len(tokenized_question.ids[1:])
        attention_mask = [1] * len(input_ids)
        padding_length = max_seq_length - len(input_ids)
        if padding_length > 0:
            input_ids = input_ids + ([0] * padding_length)
            attention_mask = attention_mask + ([0] * padding_length)
            token_type_ids = token_type_ids + ([0] * padding_length)
        elif padding_length < 0:
            self.skip = True
            return
        self.input_word_ids = input_ids
        self.input_type_ids = token_type_ids
        self.input_mask = attention_mask
        self.context_token_to_char = tokenized_context.offsets

def create_model():
    
    print("create model...")
    input_word_ids = tf.keras.layers.Input(shape=(max_seq_length,), dtype=tf.int32, name='input_word_ids')
    input_mask = tf.keras.layers.Input(shape=(max_seq_length,), dtype=tf.int32, name='input_mask')
    input_type_ids = tf.keras.layers.Input(shape=(max_seq_length,), dtype=tf.int32, name='input_type_ids')
    
    
    output = bert_layer({"input_word_ids":input_word_ids, "input_mask":input_mask, "input_type_ids":input_type_ids})
    pooled_output=output["pooled_output"] 
    sequence_output=output["sequence_output"]
    
    start_logits = layers.Dense(1, name="start_logit", use_bias=False)(sequence_output)
    start_logits = layers.Flatten()(start_logits)
    end_logits = layers.Dense(1, name="end_logit", use_bias=False)(sequence_output)
    end_logits = layers.Flatten()(end_logits)
    start_probs = layers.Activation(keras.activations.softmax)(start_logits)
    end_probs = layers.Activation(keras.activations.softmax)(end_logits)
    model = keras.Model(inputs=[input_word_ids, input_mask, input_type_ids], outputs=[start_probs, end_probs])
    loss = keras.losses.SparseCategoricalCrossentropy(from_logits=False)
    optimizer = keras.optimizers.Adam(lr=1e-5, beta_1=0.9, beta_2=0.98, epsilon=1e-9)
    model.compile(optimizer=optimizer, loss=[loss, loss])
    print("Load weights...")
    model.load_weights("weights.h5")
    print("Done")
    return model
def create_samples(contexts, question):
    result=[]
    for context in contexts:
        sample=Sample(question,context)
        sample.preprocess()
        if sample.skip:
            continue
        result.append(sample)
    return result

def create_inputs(squad_examples):
    dataset_dict = {
        "input_word_ids": [],
        "input_type_ids": [],
        "input_mask": [],
    }
    for item in squad_examples:
        if item.skip == False:
            for key in dataset_dict:
                dataset_dict[key].append(getattr(item, key))
    for key in dataset_dict:
        dataset_dict[key] = np.array(dataset_dict[key])
    x = [dataset_dict["input_word_ids"],
         dataset_dict["input_mask"],
         dataset_dict["input_type_ids"]]
    return x

def findTitle(text):
    match = re.search(r"([A-ZÅÄÖ]).*?([A-ZÅÄÖ])", text)
    second = match.span()[1]
    return {"title":"<h2>"+text[:second-2]+"</h2>","text":text[second-1:]}


def highLight(text,span):
    start=span[0]
    end=span[1]
    return text[:start]+"<span style='background:yellow'>"+text[start:end]+"</span>"+text[end:]


