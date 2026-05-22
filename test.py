import requests

response = requests.post('https://test.tspay.uz/api/transactions/', json={
    "merchant_id": "0f039e001bcd4020",
    "amount": 50000,
    "order_id": 1001  # majburiy (int)
})

if response.status_code == 200:
    data = response.json()
    cheque_id = data['cheque_id']    # doim mavjud UUID
    redirect_to(data['payment_url']) # foydalanuvchini yuborish
else:
    print("Xato:", response)