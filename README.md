# SQL Chat Assistant with Multi-Database Support

This project is a Streamlit application that allows users to interact with multiple SQL databases through a natural language interface. The application leverages the power of language models, such as GPT-4 and GROQ models, to understand user queries and generate appropriate SQL queries to retrieve the desired information from the connected databases.


## Deployed Link

Document Q&A app is Deployed And Available [Here](https://chatwithmultiplesqldatabases.streamlit.app/)


## Screenshots

![db_1](https://github.com/Parthiban-R-3997/Chat_With_Multiple_Data_Sources/assets/26496805/a2f233a3-8100-42a9-9a26-f42047a4d36e)
![db_2](https://github.com/Parthiban-R-3997/Chat_With_Multiple_Data_Sources/assets/26496805/72417ea9-baa6-41fe-8d3c-07a8b9bca5a3)
![db_3](https://github.com/Parthiban-R-3997/Chat_With_Multiple_Data_Sources/assets/26496805/d1e18b55-ffa7-4cf8-a60b-c000ef816f0a)
![db_4](https://github.com/Parthiban-R-3997/Chat_With_Multiple_Data_Sources/assets/26496805/d8fdecef-0d0b-424f-936f-8e7ad3a80743)
![db_5](https://github.com/Parthiban-R-3997/Chat_With_Multiple_Data_Sources/assets/26496805/108f2f5b-b2ed-48b9-b892-74bbc8cef64d)
![db_6](https://github.com/Parthiban-R-3997/Chat_With_Multiple_Data_Sources/assets/26496805/741b27f6-5ef6-49c0-866b-97831e1b3824)

## Key Features

- **Multi-Database Support**: The application can connect to multiple databases simultaneously, allowing users to query data across different data sources.
- **Natural Language Interface**: Users can ask questions about the databases in natural language, and the application will translate the queries into SQL queries and execute them against the relevant databases.
- **Chain of Thought Prompting**: This project utilizes the Chain of Thought prompting technique from LangChain, which encourages the language model to break down complex problems into smaller steps, leading to more accurate and interpretable results.
- **Few-Shot Learning**: The application provides a set of examples to the language model, allowing it to learn the desired behavior and generate more accurate SQL queries based on the provided context.

## Project Uniqueness

This project stands out due to its innovative approach to handling multi-database queries using natural language. By combining the power of language models with LangChain's Chain of Thought prompting and Few-Shot Learning techniques, the application can effectively understand and process complex queries spanning multiple databases.

The use of Chain of Thought prompting encourages the language model to break down the problem into smaller steps, making it easier to understand the user's intent and generate appropriate SQL queries. Additionally, Few-Shot Learning allows the model to learn from a set of examples, enhancing its ability to generate accurate SQL queries for a wide range of scenarios.

Furthermore, the application's ability to connect to multiple databases simultaneously makes it a powerful tool for data analysts and business professionals who need to work with data from different sources. This feature eliminates the need for manual data consolidation and enables seamless querying across multiple data sources.

Consider the following diagram to understand how the different chains and components are built:

![Chatbot Architecture](./docs/mysql-chains.png)

## Getting Started

To run the SQL Chat Assistant with Multi-Database Support locally, follow these steps:

1. Clone the repository: `git clone https://github.com/your-repo/sql-chat-assistant.git`
2. Install the required dependencies: `pip install -r requirements.txt`
3. Set up your database connections.
4. If you're connecting to a local database, you'll need to expose it using ngrok. Install the ngrok .exe file from [here](https://ngrok.com/download) and generate the authtoken from [here](https://dashboard.ngrok.com/get-started/your-authtoken).
5. Finally run the following command to start ngrok and expose your local database on port 3306: `ngrok tcp 3306`
6. Copy the ngrok URL (e.g., `tcp://x.tcp.ngrok.io:12345`) and use it as the `Host` and 'Port' value.
7. Run the Streamlit application: `streamlit run app.py`

For detailed instructions and additional configuration options, please refer to the project's documentation.

## Contributing

Contributions to this project are welcome! If you have any ideas, bug fixes, or improvements, feel free to submit a pull request. Please ensure that your code adheres to the project's coding standards and is well-documented.

## License

This project is licensed under the [MIT License](LICENSE).
