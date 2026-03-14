from openai import OpenAI

client = OpenAI(api_key="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")

response = client.responses.create(
    model="gpt-4.1-mini",
    input="Say hello"
)

print(response.output_text)