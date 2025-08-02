from flask import Flask, request
from binance.client import Client
import os

API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")
PASSPHRASE = os.getenv("BOT_PASSPHRASE")

client = Client(API_KEY, API_SECRET, testnet=False)  # testnet=True nếu muốn chạy thử

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json

    if data['passphrase'] != PASSPHRASE:
        return {'error': 'Unauthorized'}, 403

    symbol = data['symbol']
    side = data['side'].upper()  
    quantity = float(data['quantity'])
    leverage = int(data.get('leverage', 10))  
    tp = float(data.get('tp', 0))
    sl = float(data.get('sl', 0))

    # Set leverage
    client.futures_change_leverage(symbol=symbol, leverage=leverage)

    # Market order
    order = client.futures_create_order(
        symbol=symbol,
        side=side,
        type='MARKET',
        quantity=quantity
    )

    # TP/SL
    if tp > 0:
        client.futures_create_order(
            symbol=symbol,
            side="SELL" if side == "BUY" else "BUY",
            type="TAKE_PROFIT_MARKET",
            stopPrice=tp,
            closePosition=True
        )

    if sl > 0:
        client.futures_create_order(
            symbol=symbol,
            side="SELL" if side == "BUY" else "BUY",
            type="STOP_MARKET",
            stopPrice=sl,
            closePosition=True
        )

    return {'message': 'Order executed', 'order': order}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
