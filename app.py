# modules-----------------------------
import sys
from threading import Thread
from json import load
from time import sleep
from requests import post
from binance.client import Client
from flask import Flask, request, render_template
# --------------------
# clases-----------------------
balance = 0.0
# clase cliente


class Cliente:
    def __init__(self, symbol: str) -> None:
        with open('data.json') as json_file:
            claves = load(json_file)
        self.client = Client(claves['shercan']['key'],
                             claves['shercan']['secret'])

        with open('datos.json') as json_file:
            symbols = load(json_file)
        self.base = symbols[symbol]

# ordenes de compra y venta


class Mensaje:

    def __init__(self):
        pass

    def send(self, data: str):
        post('https://api.telegram.org/bot5243749301:AAHIDCwt13NLYpmJ7WVaJLs57G0Z_IyFTLE/sendMessage',
             data={'chat_id': '-548326689', 'text': data})


class Ordenes:
    def __init__(self, symbol: str) -> None:
        self.cliente = Cliente(symbol.replace('PERP', ''))
        self.message = Mensaje()

    def create_order(self, position: str):

        try:
            self.cliente.client.futures_cancel_all_open_orders(
                symbol=self.cliente.base['symbol'])

        except:
            pass
        if self.cliente.base['id'] == 0:
            quantity_n = str(((balance/6)*self.cliente.base['leverage'])/float(
                self.cliente.client.futures_symbol_ticker(
                    symbol=self.cliente.base['symbol'])['price']))[0:self.cliente.base["accuracy"]]
        else:
            quantity_n = str(2*((balance/6)*self.cliente.base['leverage'])/float(
                self.cliente.client.futures_symbol_ticker(
                    symbol=self.cliente.base['symbol'])['price']))[0:self.cliente.base["accuracy"]]
        order = self.cliente.client.futures_create_order(
            symbol=self.cliente.base['symbol'],
            side=position,
            type='MARKET',
            quantity=quantity_n
        )
        self.cliente.base['side'] = position
        self.cliente.base['quantity'] = order['origQty']
        self.cliente.base['id'] = order['orderId']
        # print(datos)
        order_exe = Thread(target=self.create_order_exe,
                           args=(self.cliente.base['id'], 'create',))
        order_exe.start()
        # print(order)
# creación del stop loss

    def stop_loss(self, position: str):
        # print(position)
        if position == 'BUY':
            pos = 'SELL'
            stop = round(
                self.cliente.base['price']*(1.002-self.cliente.base['stop']), self.cliente.base["round"])
            price = round(
                self.cliente.base['price']*(1-self.cliente.base['stop']), self.cliente.base["round"])
        elif position == 'SELL':
            pos = 'BUY'
            stop = round(
                self.cliente.base['price']*(0.998+self.cliente.base['stop']), self.cliente.base["round"])
            price = round(
                self.cliente.base['price']*(1+self.cliente.base['stop']), self.cliente.base["round"])
        # print(stop,price,pos,base)
        stop = self.cliente.client.futures_create_order(
            symbol=self.cliente.base['symbol'],
            side=pos,
            type='STOP',
            quantity=self.cliente.base['quantity'],
            price=price,
            stopPrice=stop,
            reduceOnly=True
        )
        # print(stop)
        order_exe = Thread(target=self.create_order_exe,
                           args=(stop['orderId'], 'stop',))
        order_exe.start()
        return price
# creación del take profit

    def take_profit(self, position: str):
        if position == 'BUY':
            pos = 'SELL'
            stop = round(
                self.cliente.base['price']*(0.998+self.cliente.base['take_l']), self.cliente.base["round"])
            price = round(
                self.cliente.base['price']*(1+self.cliente.base['take_l']), self.cliente.base["round"])
        elif position == 'SELL':
            pos = 'BUY'
            stop = round(
                self.cliente.base['price']*(1.002-self.cliente.base['take_s']), self.cliente.base["round"])
            price = round(
                self.cliente.base['price']*(1-self.cliente.base['take_s']), self.cliente.base["round"])
        take = self.cliente.client.futures_create_order(
            symbol=self.cliente.base['symbol'],
            side=pos,
            type='TAKE_PROFIT',
            quantity=self.cliente.base['quantity'],
            price=price,
            stopPrice=stop,
            reduceOnly=True
        )
        # print(take)
        order_exe = Thread(target=self.create_order_exe,
                           args=(take['orderId'], 'take',))
        order_exe.start()
        return price
# seguimiento de las ordenes

    def create_order_exe(self, order_id, intro: str):
        global balance
        while True:
            try:
                order = self.cliente.client.futures_get_order(
                    orderId=order_id, symbol=self.cliente.base['symbol'])
            except Exception as e:
                print('Error '+str(e)+' con '+intro +
                      ' y '+self.cliente.base['symbol'])
            #print(intro, order['status'], order['orderId'])
            if (order['status'] == 'FILLED' and intro == 'create'):
                self.cliente.base['price'] = float(order['avgPrice'])
                self.cliente.base['quote'] = float(order['cumQuote'])*0.9996
                price_stop = self.stop_loss(self.cliente.base['side'])
                price_take = self.take_profit(self.cliente.base['side'])
                self.message.send('Se compro '+self.cliente.base['symbol']+' el precio de compra fue ' +
                                  str(self.cliente.base["price"])+' el precio del stop es '+str(
                    price_stop)+' y el precio del take es de '+str(price_take))
                break
            if (order['status'] == 'FILLED' and intro == 'stop'):
                if order['side'] == 'SELL':
                    balance += float(order['cumQuote']) - \
                        self.cliente.base['quote']
                else:
                    balance += self.cliente.base['quote'] - \
                        float(order['cumQuote'])*0.9998
                self.cliente.client.futures_cancel_all_open_orders(
                    symbol=self.cliente.base['symbol'])
                self.cliente.base['id'] = 0
                self.message.send('Se tomo el stop loss de ' +
                                  self.cliente.base['symbol']+' y el balance es de '+str(round(balance, 2)))
                break
            if (order['status'] == 'FILLED' and intro == 'take'):
                if order['side'] == 'SELL':
                    balance += float(order['cumQuote']) - \
                        self.cliente.base['quote']
                else:
                    balance += self.cliente.base['quote'] - \
                        float(order['cumQuote'])*0.9998
                self.cliente.client.futures_cancel_all_open_orders(
                    symbol=self.cliente.base['symbol'])
                self.cliente.base['id'] = 0
                self.message.send('Se tomo el take profit de ' +
                                  self.cliente.base['symbol']+' y el balance es de '+str(round(balance, 2)))
                break
            if order['status'] == 'CANCELED':
                self.cliente.client.futures_cancel_all_open_orders(
                    symbol=self.cliente.base['symbol'])
                self.cliente.base['id'] = 0
                break
            sleep(1)
        sys.exit()


# inicio de programa
if __name__ == "__main__":
    from waitress import serve
    cliente = Cliente('BNBUSDT')
    list_balance = cliente.client.futures_account_balance()
    balance = float([x['balance']
                    for x in list_balance if x['asset'] == 'USDT'][0])
    print('Inicio', str(balance))

    app = Flask(__name__)

    @app.route('/')
    def main():
        return render_template('main.html')

    @app.route('/webhook', methods=['POST'])
    def webhook():
        mensaje = 'nothing'
        if request.method == 'POST':
            recive = request.json
            if recive['position'] == '1' and recive['order'] == 'buy':
                orders = Ordenes(recive['ticker'])
                orders.create_order('BUY')
                mensaje = 'Se realizo una orden en long'
            elif recive['position'] == '-1' and recive['order'] == 'sell':
                orders = Ordenes(recive['ticker'])
                orders.create_order('SELL')
                mensaje = 'Se realizo una orden en short'
            return mensaje
    #app.run(host='127.0.0.1', port=80)
    serve(app, host='0.0.0.0', port=80)
# ----------json recepción
'''
Envio del dato desde el cliente, de esta manera
{"order":"{{strategy.order.action}}","position":"{{plot_15}}","ticker":"{{ticker}}"}
'''
