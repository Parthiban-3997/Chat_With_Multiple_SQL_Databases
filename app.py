import streamlit as st
import os
import toml
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_community.utilities import SQLDatabase
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
#from dotenv import load_dotenv

#load_dotenv() 

# Function to update config.toml file
def update_secrets_file(user, data):
    secrets_file_path = ".streamlit/config.toml"
    secrets_data = {}

    # Load existing data from config.toml
    if os.path.exists(secrets_file_path):
        try:
            with open(secrets_file_path, "r") as file:
                secrets_data = toml.load(file)
        except toml.TomlDecodeError:
            secrets_data = {}

    # Update user-specific secrets data
    secrets_data[user] = data

    # Write updated data back to config.toml
    with open(secrets_file_path, "w") as file:
        toml.dump(secrets_data, file)


# Initialize database connections
def init_databases(user):
    secrets_file_path = ".streamlit/config.toml"
    secrets_data = {}
    if os.path.exists(secrets_file_path):
        with open(secrets_file_path, "r") as file:
            secrets_data = toml.load(file)
    
    user_data = secrets_data.get(user, {})
    
    db_connections = {}
    for database in user_data.get("Databases", "").split(','):
        database = database.strip()
        if database:
            db_uri = f"mysql+mysqlconnector://{user_data['User']}:{user_data['Password']}@{user_data['Host']}:{user_data['Port']}/{database}"
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

    Question: Which 3 artists have the most tracks?
    SQL Query: SELECT ArtistId, COUNT(*) as track_count FROM Track GROUP BY ArtistId ORDER BY track_count DESC LIMIT 3;

    Question: Name 10 artists
    SQL Query: SELECT Name FROM Artist LIMIT 10;

    Question:can you show SRK( a.k.a Shah Rukh Khan) movies where the imdb rating is greater than average rating of all movies and also show which movie had highest revenue in millions (INR)
    SQL Query:  SELECT m.title, m.imdb_rating, f.revenue 
                FROM movies m 
                JOIN financials f ON m.movie_id = f.movie_id 
                JOIN movie_actor ma ON m.movie_id = ma.movie_id 
                JOIN actors a ON ma.actor_id = a.actor_id 
                WHERE a.name = 'Shah Rukh Khan' AND m.imdb_rating > (SELECT AVG(imdb_rating) FROM movies) 
                ORDER BY f.revenue DESC;

    Question: How many Van huesen black medium t shirts are available in stock?
    SQL Query: SELECT SUM(stock_quantity) FROM t_shirts WHERE brand = 'Van Huesen' AND color = 'Black' AND size = 'M';

    Question: How much is the price of the inventory for all small size t-shirts?
    SQL Query: SELECT SUM(price * stock_quantity) FROM t_shirts WHERE size = 'S';

    Question: If we have to sell all the Levi's T-shirts today with discounts applied, how much revenue our store will generate (post discounts)?
    SQL Query: SELECT SUM(a.total_amount * ((100 - COALESCE(discounts.pct_discount, 0)) / 100)) AS total_revenue FROM (SELECT SUM(price * stock_quantity) AS total_amount, t_shirt_id FROM t_shirts WHERE brand = 'Levi' GROUP BY t_shirt_id) a LEFT JOIN discounts ON a.t_shirt_id = discounts.t_shirt_id;

    Question: For each brand, find the total revenue generated from t-shirts with a discount applied, grouped by the discount percentage.
    SQL Query: SELECT brand, COALESCE(discounts.pct_discount, 0) AS discount_pct, SUM(t.price * t.stock_quantity * (1 - COALESCE(discounts.pct_discount, 0) / 100)) AS total_revenue FROM t_shirts t LEFT JOIN discounts ON t.t_shirt_id = discounts.t_shirt_id GROUP BY brand, COALESCE(discounts.pct_discount, 0);

    Question: Find the top 3 most popular colors for each brand, based on the total stock quantity.
    SQL Query: SELECT brand, color, SUM(stock_quantity) AS total_stock FROM t_shirts GROUP BY brand, color ORDER BY brand, total_stock DESC;

    Question: Calculate the average price per size for each brand, excluding sizes with less than 10 t-shirts in stock.
    SQL Query: SELECT brand, size, AVG(price) AS avg_price FROM t_shirts WHERE stock_quantity >= 10 GROUP BY brand, size HAVING COUNT(*) >= 10;

    Question: Find the brand and color combination with the highest total revenue, considering discounts.
    SQL Query: SELECT brand, color, SUM(t.price * t.stock_quantity * (1 - COALESCE(d.pct_discount, 0) / 100)) AS total_revenue FROM t_shirts t LEFT JOIN discounts d ON t.t_shirt_id = d.t_shirt_id GROUP BY brand, color ORDER BY total_revenue DESC LIMIT 1;

    Question: Create a view that shows the total stock quantity and revenue for each brand, size, and color combination.
    SQL Query: CREATE VIEW brand_size_color_stats AS SELECT brand, size, color, SUM(stock_quantity) AS total_stock, SUM(price * stock_quantity) AS total_revenue FROM t_shirts GROUP BY brand, size, color;

    Question: How much is the price of the inventory for all variants of t-shirts and group them by brands?
    SQL Query: SELECT brand, SUM(price * stock_quantity) FROM t_shirts GROUP BY brand;

    Question: List the total revenue of t-shirts of L size for all brands.
    SQL Query: SELECT brand, SUM(price * stock_quantity) AS total_revenue FROM t_shirts WHERE size = 'L' GROUP BY brand;

    Question: How many shirts are available in stock grouped by colours from each size and finally show me all brands?
    SQL Query: SELECT brand, color, size, SUM(stock_quantity) AS total_stock FROM t_shirts GROUP BY brand, color, size;

    Question: select all the movies with minimum and maximum release_year. Note that there can be more than one movies in min and max year hence output rows can be more than 2?
    SQL Query: select * from movies where release_year in (select min(release_year) from movies, select max(release_year) from movies);

    Question: Generate a yearly report for Croma India where there are two columns 1. Fiscal Year and 2. Total Gross Sales amount In that year from Croma
    SQL Query: select get_fiscal_year(date) as fiscal_year, sum(round(sold_quantity*g.gross_price,2)) as yearly_sales from fact_sales_monthly s join fact_gross_price g on g.fiscal_year=get_fiscal_year(s.date) and g.product_code=s.product_code where customer_code=90002002 group by get_fiscal_year(date) order by fiscal_year;

    Question: What is the total freight cost incurred by each customer in the month of May 2024?
    SQL Query: SELECT s.customer_name, SUM(f.freight_cost) AS total_freight_cost FROM gdb0041.sales_monthly s JOIN gdb056.freight_cost f ON s.customer_id = f.customer_id WHERE s.month = 'May 2024' GROUP BY s.customer_id;

    Question: Which market has the highest gross price sales in the last quarter?
    SQL Query: SELECT s.market, SUM(g.gross_price) AS total_gross_price FROM gdb041.sales_monthly s JOIN gdb056.gross_price g ON s.market_id = g.market_id WHERE s.quarter = 'Q2 2024' GROUP BY s.market_id ORDER BY total_gross_price DESC LIMIT 1;

    Question: What is the manufacturing cost of products sold in each region last year?
    SQL Query: SELECT s.region, SUM(m.manufacturing_cost) AS total_manufacturing_cost FROM gdb0041.sales_monthly s JOIN gdb056.manufacturing_cost m ON s.product_id = m.product_id WHERE s.year = 2023 GROUP BY s.region;

    Question: How many pre-invoice deductions were applied to each customer's sales in the last six months?
    SQL Query: SELECT s.customer_name, COUNT(p.pre_invoice_deduction_id) AS total_pre_invoice_deductions FROM gdb041.sales_monthly s JOIN gdb056.pre_invoice_deductions p ON s.sales_id = p.sales_id WHERE s.date BETWEEN DATE_SUB(NOW(), INTERVAL 6 MONTH) AND NOW() GROUP BY s.customer_id;

    Question: What are the post-invoice deductions for each product in the current year?
    SQL Query: SELECT f.product_name, SUM(p.amount) AS total_post_invoice_deductions FROM gdb0041.forecast_monthly f JOIN gdb056.post_invoice_deductions p ON f.product_id = p.product_id WHERE YEAR(f.date) = YEAR(NOW()) GROUP BY f.product_id;

    Question: How many movies did Sanjay Dutt act in, and which film gained the most revenue, ordered from highest to lowest revenue?
    SQL Query: SELECT m.title, SUM(b.revenue) AS total_revenue FROM movies m JOIN box_office b ON m.movie_id = b.movie_id JOIN movie_actor ma ON m.movie_id = ma.movie_id JOIN actors a ON ma.actor_id = a.actor_id WHERE a.name = 'Sanjay Dutt' GROUP BY m.title ORDER BY total_revenue DESC;    
        

    Your turn:
    
    Question: {question}
    SQL Queries:
    """
    
    prompt = ChatPromptTemplate.from_template(template)
    llm = llm

    def get_schema(_):
        schemas = {db_name: db.get_table_info() for db_name, db in dbs.items()}
        return schemas

    def parse_multi_line_queries(result):
        queries = {}
        lines = result.strip().split("\n")
        current_db = None
        current_query = []

        for line in lines:
            if ":" in line and not current_db:  # Only split on colon for the database name
                current_db, query_start = line.split(":", 1)
                current_db = current_db.strip()
                current_query.append(query_start.strip())
            else:
                current_query.append(line.strip())

        if current_db:
            queries[current_db] = " ".join(current_query).strip()

        return queries
    
    return (
        RunnablePassthrough.assign(schemas=get_schema)
        | prompt
        | llm
        | StrOutputParser()
        | parse_multi_line_queries
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
    SQL Responses: {responses}
    """
    
    prompt = ChatPromptTemplate.from_template(template)
    llm = llm
   
    def run_queries(var):
        responses = {}
        for db_name, query in var["queries"].items():
            responses[db_name] = dbs[db_name].run(query)
            print(dbs.keys())
            print(var["queries"].keys())
        return responses
    
    chain = (
        RunnablePassthrough.assign(queries=sql_chain).assign(
            schemas=lambda _: {db_name: db.get_table_info() for db_name, db in dbs.items()},
            responses=run_queries,)  # The comma at the end of the assign() method call is used to indicate that there may be more keyword arguments or method calls following it
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

# Define model options
model_options_groq = [
    "llama3-70b-8192",
    "llama3-8b-8192",
    "mixtral-8x7b-32768"
]

model_options_openai = [
    "gpt-4o",
    "gpt-4-turbo",
    "gpt-3.5-turbo-0125"
]

with st.sidebar:
    st.subheader("Settings")
    st.write("This is a simple chat application using MySQL. Connect to the database and start chatting.")
    
    if "db" not in st.session_state:
        st.session_state.user_id = st.text_input("User ID",placeholder="Enter any random numbers")
        st.session_state.Host = st.text_input("Host")
        st.session_state.Port = st.text_input("Port")
        st.session_state.User = st.text_input("User")
        st.session_state.Password = st.text_input("Password", type="password")
        st.session_state.Databases = st.text_input("Databases", placeholder="Enter DB's separated by (,)")
        st.session_state.openai_api_key = st.text_input("OpenAI API Key", type="password", help="Get your API key from [OpenAI Website](https://platform.openai.com/api-keys)")
        selected_model_openai = st.selectbox("Select any OpenAI Model", model_options_openai)
        st.session_state.groq_api_key = st.text_input("Groq API Key", type="password", help="Get your API key from [GROQ Console](https://console.groq.com/keys)")
        selected_model_groq = st.selectbox("Select any Groq Model", model_options_groq)
        st.info("Note: For interacting multiple databases and dealing with complex queries, GPT-4 Model is recommended for accurate results else proceed with Groq Model")
        
       
        os.environ["OPENAI_API_KEY"] = str(st.session_state.openai_api_key)
       

        if st.button("Connect"):
            with st.spinner("Connecting to databases..."):

                # Update config.toml with user-specific connection details
                update_secrets_file(st.session_state.user_id, {
                    "Host": st.session_state.Host,
                    "Port": st.session_state.Port,
                    "User": st.session_state.User,
                    "Password": st.session_state.Password,
                    "Databases": st.session_state.Databases
                })

                dbs = init_databases(st.session_state.user_id)
                st.session_state.dbs = dbs

                if len(dbs) > 1:
                    st.success(f"Connected to {len(dbs)} databases")
                else:
                    st.success("Connected to database")
                
                

        if st.session_state.openai_api_key == "" and st.session_state.groq_api_key == "":
            st.error("Enter one API Key At least")
        elif st.session_state.openai_api_key:    
            st.session_state.llm = ChatOpenAI(model=selected_model_openai, api_key=st.session_state.openai_api_key)
        elif st.session_state.groq_api_key:
            st.session_state.llm = ChatGroq(model_name=selected_model_groq, temperature=0.5, api_key=st.session_state.groq_api_key)
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
