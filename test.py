from langchain_groq import ChatGroq

llm = ChatGroq(model_name="llama3-8b-8192")
print(llm.invoke("Hello"))