import base64
from openai import OpenAI

client = OpenAI()

def encode_b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")
    
# b64 = encode_b64("PXL_20260212_113723927.jpg")
b64 = encode_b64("PXL_20260212_133301524.jpg")

resp = client.responses.create(
    model="gpt-5.2",
    input=[
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": "このレシート画像を読み取り、次のJSONで返して: store_name, datetime, items[{name, price}], subtotal, tax, total"},
                {"type": "input_image", "image_url": f"data:image/jpeg;base64,{b64}"},
            ],
        }
    ]
)

print(resp.output_text)