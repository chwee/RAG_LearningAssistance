import os
import openai
import chainlit as cl
from pathlib import Path 
import shutil

from llama_index.core import (
    Settings,
    StorageContext,
    VectorStoreIndex,
    SimpleDirectoryReader,
    load_index_from_storage,
)
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.query_engine.retriever_query_engine import RetrieverQueryEngine
from llama_index.core.callbacks import CallbackManager
from llama_index.core.service_context import ServiceContext
from chainlit.input_widget import Select
from chainlit.input_widget import TextInput

# openai.api_key = os.environ.get("OPENAI_API_KEY")
openai.api_key = ""
list_topics=["IT1111", "IT2222", "IT3333", "IT4444"]
try:
    # rebuild storage context
    storage_context = StorageContext.from_defaults(persist_dir="./prompt")
    # load index
    index = load_index_from_storage(storage_context)
except:
    documents = SimpleDirectoryReader("./data").load_data(show_progress=True)
    index = VectorStoreIndex.from_documents(documents)
    index.storage_context.persist("./prompt")

current_topic=""

async def Updata_RAG_Topic(topic):
    storage_context = StorageContext.from_defaults(persist_dir="./"+topic)
    # load index
    index = load_index_from_storage(storage_context)
    Settings.llm = OpenAI(
        model="gpt-3.5-turbo", temperature=0.1, max_tokens=1024, streaming=True
    )
    Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")
    Settings.context_window = 4096

    service_context = ServiceContext.from_defaults(callback_manager=CallbackManager([cl.LlamaIndexCallbackHandler()]))
    query_engine = index.as_query_engine(streaming=True, similarity_top_k=2, service_context=service_context)
    cl.user_session.set("query_engine", query_engine)

    await cl.Message(
        author="Assistant", content="Hello! Im an AI assistant. How may I help you "+ topic +" information?"
    ).send()




@cl.on_chat_start
async def start():
    actions = [
        cl.Action(name="upload", value="example_value", description="Click me!")
    ]

    await cl.Message(content="To upload new module content:", actions=actions).send()



    settings = await cl.ChatSettings(
        [
            Select(
                id="Topics",
                label="Modules Available",
                values=list_topics,
                initial_index=0,
            )
        ]
    ).send()
    value = settings["Topics"]
    global current_topic 
    current_topic = settings["Topics"]

    Settings.llm = OpenAI(
        model="gpt-3.5-turbo", temperature=0.1, max_tokens=1024, streaming=True
    )
    Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")
    Settings.context_window = 4096

    service_context = ServiceContext.from_defaults(callback_manager=CallbackManager([cl.LlamaIndexCallbackHandler()]))
    query_engine = index.as_query_engine(streaming=True, similarity_top_k=2, service_context=service_context)
    cl.user_session.set("query_engine", query_engine)

    topic = settings['Topics']

    await cl.Message(
        author="Assistant-"+topic, content="Hello! Im an AI assistant. How may I help you?"
    ).send()

@cl.on_settings_update
async def setup_agent(settings):
    print("on_settings_update", settings)
    topic = settings['Topics']
    global current_topic 
    current_topic = settings["Topics"]
    #change the RAG Topics
    storage_context = StorageContext.from_defaults(persist_dir="./"+topic)
    # load index
    index = load_index_from_storage(storage_context)
    Settings.llm = OpenAI(
        model="gpt-3.5-turbo", temperature=0.1, max_tokens=1024, streaming=True
    )
    Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")
    Settings.context_window = 4096

    service_context = ServiceContext.from_defaults(callback_manager=CallbackManager([cl.LlamaIndexCallbackHandler()]))
    query_engine = index.as_query_engine(streaming=True, similarity_top_k=2, service_context=service_context)
    cl.user_session.set("query_engine", query_engine)

    await cl.Message(
        author="Assistant-"+topic, content="Hello! Im an AI assistant. How may I help you "+ topic +" information?"
    ).send()


@cl.on_message
async def main(message: cl.Message):
    query_engine = cl.user_session.get("query_engine") # type: RetrieverQueryEngine

    global current_topic 
   
    msg = cl.Message(content="", author="Assistant-"+ current_topic)

    res = await cl.make_async(query_engine.query)(message.content)

    for token in res.response_gen:
        await msg.stream_token(token)
    await msg.send()


@cl.action_callback("upload")
async def on_action(action: cl.Action):
    print("The user clicked on the action button!")
     # Wait for the user to upload a PDF file
    files = await cl.AskFileMessage(
        content="Please upload a PDF file to begin!", accept=["application/pdf"]
    ).send()

    pdf_file = files[0]

    dirname = os.path.dirname(pdf_file.path)
    
    filename= Path(pdf_file.name).stem 
    print(dirname)
    print(filename)
    print(pdf_file.path)

    #ask for the new module name, use to create dir
    res = await cl.AskUserMessage(content="What is the module name?", timeout=30).send()
    new_module = res['output']
    if res:
        await cl.Message(
            content=f"Your new module name is: {res['output']}",
        ).send()

    list_topics.append(new_module)
    settings = await cl.ChatSettings(
        [
            Select(
                id="Topics",
                label="Modules Available",
                values=list_topics,
                # initial_index=0,
            )
        ]
    ).send()


    #create new dir then subdir data to store the source file generationg vector database
    directory = "./"+new_module+"/data"
    try:
      os.makedirs(directory)
      print(f"Directory '{directory}' created successfully")
    except OSError as e:
      print(f"Error: {e}")

    #copy scr file to dest file
    destination_file = directory+"/"+new_module+".pdf"
    shutil.copy2(pdf_file.path, destination_file)

    #store into vector 
    create_documents = SimpleDirectoryReader(directory).load_data(show_progress=True)
    create_index = VectorStoreIndex.from_documents(create_documents)
    create_index.storage_context.persist("./"+new_module)


    shutil.rmtree(dirname, ignore_errors=True)

    # You can then process the PDF file as needed
    await cl.Message(
        content=f"`{pdf_file.name}` uploaded successfully!"
    ).send()

    content=f"`{pdf_file.name}` uploaded successfully!"

    return content
