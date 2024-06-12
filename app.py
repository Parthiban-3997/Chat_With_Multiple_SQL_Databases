import streamlit as st
import os
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_community.utilities import SQLDatabase
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
import toml

# Function to update config.toml file
def update_secrets_file(data):
    secrets_file_path = ".streamlit/config.toml"
    secrets_data = {}
    
    # Load existing data from secrets.toml
    if os.path.exists(secrets_file_path):
        with open(secrets_file_path, "r") as file:
            secrets_data = toml.load(file)
    
    # Update secrets data with new data
    secrets_data.update(data)
    
    # Write updated data back to secrets.toml
    with open(secrets_file_path, "rw+") as file:
        toml.dump(secrets_data, file)


# Initialize database connections
def init_databases():
    secrets_file_path = ".streamlit/config.toml"
    secrets_data = {}
    if os.path.exists(secrets_file_path):
        with open(secrets_file_path, "r") as file:
            content = file.read().strip()
            if content:
                secrets_data = toml.loads(content)
    
    db_connections = {}
    for database in secrets_data.get("Databases", "").split(','):
        database = database.strip()
        if database:
            db_uri = f"mysql+mysqlconnector://{secrets_data['User']}:{secrets_data['Password']}@{secrets_data['Host']}:{secrets_data['Port']}/{database}"
            db_connections[database] = SQLDatabase.from_uri(db_uri)
    return db_connections


# Function to get SQL chain
def get_sql_chain(dbs, llm):
    template = """
    You are a Senior and vastly experienced Data analyst at a company with around 20 years of experience. 
    You are interacting with a user who is asking you questions about the company's databases.
    Based on the table schemas below, write SQL queries that would answer the user's question. Take the conversation history into account.
    
    <SCHEMAS>{schemas}</SCHEMAS>
    
    Conversation History: {chat_history}
    
    Write the SQL queries for each relevant database, prefixed by the database name (e.g., DB1: SELECT * FROM ...; DB2: SELECT * FROM ...).
    Do not wrap the SQL queries in any other text, not even backticks.
    
    For example:
    Question: which 3 artists have the most tracks?
    SQL Query: SELECT ArtistId, COUNT(*) as track_count FROM Track GROUP BY ArtistId ORDER BY track_count DESC LIMIT 3;
    Question: Name 10 artists
    SQL Query: SELECT Name FROM Artist LIMIT 10;
    Question: How much is the price of the inventory for all small size t-shirts?
    SQL Query: SELECT SUM(price * stock_quantity) FROM t_shirts WHERE size = 'S';
    Question: If we have to sell all the Levi's T-shirts today with discounts applied. How much revenue our store will generate (post discounts)?
    SQL Query: SELECT SUM(a.total_amount * ((100 - COALESCE(discounts.pct_discount, 0)) / 100)) AS total_revenue 
               FROM (SELECT SUM(price * stock_quantity) AS total_amount, t_shirt_id 
               FROM t_shirts 
               WHERE brand = 'Levi' GROUP BY t_shirt_id) a   
               LEFT JOIN discounts ON a.t_shirt_id = discounts.t_shirt_id;
    Question: For each brand, find the total revenue generated from t-shirts with a discount applied, grouped by the discount percentage.
    SQL Query: SELECT brand, COALESCE(discounts.pct_discount, 0) AS discount_pct, SUM(t.price * t.stock_quantity * (1 - COALESCE(discounts.pct_discount, 0) / 100)) AS total_revenue
               FROM t_shirts t
               LEFT JOIN discounts ON t.t_shirt_id = discounts.t_shirt_id
               GROUP BY brand, COALESCE(discounts.pct_discount, 0);
    Question: Find the top 3 most popular colors for each brand, based on the total stock quantity.
    SQL Query: SELECT brand, color, SUM(stock_quantity) AS total_stock
               FROM t_shirts
               GROUP BY brand, color
               ORDER BY brand, total_stock DESC;
               
    Question: Calculate the average price per size for each brand, excluding sizes with less than 10 t-shirts in stock.
    SQL Query: SELECT brand, size, AVG(price) AS avg_price
               FROM t_shirts
               WHERE stock_quantity >= 10
               GROUP BY brand, size
               HAVING COUNT(*) >= 10;
               
    Question: Find the brand and color combination with the highest total revenue, considering discounts.
    SQL Query: SELECT brand, color, SUM(t.price * t.stock_quantity * (1 - COALESCE(d.pct_discount, 0) / 100)) AS total_revenue
               FROM t_shirts t
               LEFT JOIN discounts d ON t.t_shirt_id = d.t_shirt_id
               GROUP BY brand, color
               ORDER BY total_revenue DESC
               LIMIT 1;
               
    Question: Create a view that shows the total stock quantity and revenue for each brand, size, and color combination.
    SQL Query: CREATE VIEW brand_size_color_stats AS
               SELECT brand, size, color, SUM(stock_quantity) AS total_stock, SUM(price * stock_quantity) AS total_revenue
               FROM t_shirts
               GROUP BY brand, size, color;
    
    Question: How much is the price of the inventory for all varients t-shirts and group them y brands?
    SQL Query: SELECT brand, SUM(price * stock_quantity) FROM t_shirts GROUP BY brand;
    
    Question: List the total revenue of t-shirts of L size for all brands
    SQL Query: SELECT brand, SUM(price * stock_quantity) AS total_revenue FROM t_shirts WHERE size = 'L' GROUP BY brand;   
    
    Question: How many shirts are available in stock grouped by colours from each size and finally show me all brands?
    SQL Query: SELECT brand, color, size, SUM(stock_quantity) AS total_stock FROM t_shirts GROUP BY brand, color, size

    Your turn:
    
    Question: {question}
    SQL Queries:
    """
    
    prompt = ChatPromptTemplate.from_template(template)
    llm = llm

    def get_schema(_):
        schemas = {db_name: db.get_table_info() for db_name, db in dbs.items()}
        return schemas

    return (
        RunnablePassthrough.assign(schemas=get_schema)
        | prompt
        | llm
        | StrOutputParser()
        | (lambda result: {line.split(":")[0]: line.split(":")[1].strip() for line in result.strip().split("\n") if ":" in line and line.strip()})
    )

# Function to get response
def get_response(user_query, dbs, chat_history, llm):
    sql_chain = get_sql_chain(dbs, llm)
    
    template = """
    You are a Senior and vastly experienced Data analyst at a company with around 20 years of experience.
    You are interacting with a user who is asking you questions about the company's databases.
    Based on the table schemas below, question, sql queries, and sql responses, write an 
    accurate natural language response so that the end user can understand things
    and make sure do not include words like "Based on the SQL queries I ran". 
    Just provide only the answer with some text that the user expects.
    <SCHEMAS>{schemas}</SCHEMAS>
    Conversation History: {chat_history}
    SQL Queries: <SQL>{queries}</SQL>
    User question: {question}
    SQL Responses: {responses}"""
    
    prompt = ChatPromptTemplate.from_template(template)
    llm = llm
   
    def run_queries(var):
        responses = {}
        for db_name, query in var["queries"].items():
            responses[db_name] = dbs[db_name].run(query)
        return responses
    
    chain = (
        RunnablePassthrough.assign(queries=sql_chain).assign(
            schemas=lambda _: {db_name: db.get_table_info() for db_name, db in dbs.items()},
            responses=run_queries)  # The comma at the end of the assign() method call is used to indicate that there may be more keyword arguments or method calls following it
        | prompt
        | llm
        | StrOutputParser()
    )
    
    return chain.invoke({
        "question": user_query,
        "chat_history": chat_history,
    })

# Streamlit app configuration
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        AIMessage(content="Hello! I'm a SQL assistant. Ask me anything about your database."),
    ]

st.set_page_config(page_title="Chat with MySQL", page_icon="🛢️")
st.title("Chat with MySQL")

with st.sidebar:
    st.subheader("Settings")
    st.write("This is a simple chat application using MySQL. Connect to the database and start chatting.")
    
    if "db" not in st.session_state:
        st.session_state.Host = st.text_input("Host")
        st.session_state.Port = st.text_input("Port")
        st.session_state.User = st.text_input("User")
        st.session_state.Password = st.text_input("Password", type="password")
        st.session_state.Databases = st.text_input("Databases", placeholder="Enter DB's separated by (,)")
        st.session_state.openai_api_key = st.text_input("OpenAI API Key", type="password", help="Get your API key from [OpenAI Website](https://platform.openai.com/api-keys)")
        st.session_state.groq_api_key = st.text_input("Groq API Key", type="password", help="Get your API key from [GROQ Console](https://console.groq.com/keys)")

        st.info("Note: For interacting multiple databases, GPT-4 Model is recommended for accurate results else proceed with Groq Model")
        
        os.environ["OPENAI_API_KEY"] = str(st.session_state.openai_api_key)

        if st.button("Connect"):
            with st.spinner("Connecting to databases..."):

                # Update secrets.toml with connection details
                update_secrets_file({
                    "Host": st.session_state.Host,
                    "Port": st.session_state.Port,
                    "User": st.session_state.User,
                    "Password": st.session_state.Password,
                    "Databases": st.session_state.Databases
                })

                dbs = init_databases()
                st.session_state.dbs = dbs

                if len(dbs) > 1:
                    st.success(f"Connected to {len(dbs)} databases")
                else:
                    st.success("Connected to database")
                
                

        if st.session_state.openai_api_key == "" and st.session_state.groq_api_key == "":
            st.error("Enter one API Key At least")
        elif st.session_state.openai_api_key:    
            st.session_state.llm = ChatOpenAI(model="gpt-4-turbo", api_key=st.session_state.openai_api_key)
        elif st.session_state.groq_api_key:
            st.session_state.llm = ChatGroq(model="llama3-70b-8192", temperature=0.4, api_key=st.session_state.groq_api_key)
        else:
            pass

# Display chat messages
for message in st.session_state.chat_history:
    if isinstance(message, AIMessage):
        with st.chat_message("AI"):
            st.markdown(message.content)
    elif isinstance(message, HumanMessage):
        with st.chat_message("Human"):
            st.markdown(message.content)

# Handle user input
user_query = st.chat_input("Type a message...")
if user_query is not None and user_query.strip() != "":
    st.session_state.chat_history.append(HumanMessage(content=user_query))
    
    with st.chat_message("Human"):
        st.markdown(user_query)
        
    with st.chat_message("AI"):
        response = get_response(user_query, st.session_state.dbs, st.session_state.chat_history, st.session_state.llm)
        st.markdown(response)
        
    st.session_state.chat_history.append(AIMessage(content=response))