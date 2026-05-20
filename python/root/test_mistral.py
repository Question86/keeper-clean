from local_mistral_agent import LocalMistralAgent

agent = LocalMistralAgent()
response = agent.generate('Write a Python function to sort a list')
print('Generated code:')
print(response)

chat_response = agent.chat('Hello, how are you?')
print('Chat response:')
print(chat_response)
