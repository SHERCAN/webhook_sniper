# modules-----------------------------
import sys
from threading import Thread
from json import load
from time import sleep
from requests import post
from binance.client import Client
from datetime import datetime as dt
from flask import Flask, request, render_template
# --------------------
# clases-----------------------
balance = 0.0
list_symbols=['BTCUSDT','ETHUSDT','XRPUSDT','SOLUSDT','BNBUSDT']
with open('datos.json') as json_file:
    symbols = load(json_file)
# clase cliente

class Cliente:
    def __init__(self, symbol: str) -> None:
        self.symbol=symbol
        with open('data.json') as json_file:
            claves = load(json_file)
        self.client = Client(claves['shercan']['key'],
                             claves['shercan']['secret'])      

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
        if symbols[self.cliente.symbol]['quantity']!=0:
            quan_before=symbols[self.cliente.symbol]['quantity']
        try:
            self.cliente.client.futures_cancel_all_open_orders(
                symbol=symbols[self.cliente.symbol]['symbol'])

        except:
            pass
        if symbols[self.cliente.symbol]['id'] == 0:
            quantity_n = str(((balance/6)*symbols[self.cliente.symbol]['leverage'])/float(
                self.cliente.client.futures_symbol_ticker(
                    symbol=symbols[self.cliente.symbol]['symbol'])['price']))[0:symbols[self.cliente.symbol]["accuracy"]]
        else:
            quantity_n = str(quan_before+(((balance/6)*symbols[self.cliente.symbol]['leverage'])/float(
                self.cliente.client.futures_symbol_ticker(
                    symbol=symbols[self.cliente.symbol]['symbol'])['price'])))[0:symbols[self.cliente.symbol]["accuracy"]]
        order = self.cliente.client.futures_create_order(
            symbol=symbols[self.cliente.symbol]['symbol'],
            side=position,
            type='MARKET',
            quantity=quantity_n
        )
        symbols[self.cliente.symbol]['side'] = position
        symbols[self.cliente.symbol]['quantity'] = order['origQty']
        symbols[self.cliente.symbol]['id'] = order['orderId']
        # print(datos)
        order_exe = Thread(target=self.create_order_exe,
                           args=(symbols[self.cliente.symbol]['id'], 'create',))
        order_exe.start()
        # print(order)
# creación del stop loss

    def stop_loss(self, position: str):
        # print(position)
        if position == 'BUY':
            pos = 'SELL'
            stop = round(
                symbols[self.cliente.symbol]['price']*(1.002-symbols[self.cliente.symbol]['stop']), symbols[self.cliente.symbol]["round"])
            price = round(
                symbols[self.cliente.symbol]['price']*(1-symbols[self.cliente.symbol]['stop']), symbols[self.cliente.symbol]["round"])
        elif position == 'SELL':
            pos = 'BUY'
            stop = round(
                symbols[self.cliente.symbol]['price']*(0.998+symbols[self.cliente.symbol]['stop']), symbols[self.cliente.symbol]["round"])
            price = round(
                symbols[self.cliente.symbol]['price']*(1+symbols[self.cliente.symbol]['stop']), symbols[self.cliente.symbol]["round"])
        # print(stop,price,pos,base)
        stop = self.cliente.client.futures_create_order(
            symbol=symbols[self.cliente.symbol]['symbol'],
            side=pos,
            type='STOP',
            quantity=symbols[self.cliente.symbol]['quantity'],
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
                symbols[self.cliente.symbol]['price']*(0.998+symbols[self.cliente.symbol]['take_l']), symbols[self.cliente.symbol]["round"])
            price = round(
                symbols[self.cliente.symbol]['price']*(1+symbols[self.cliente.symbol]['take_l']), symbols[self.cliente.symbol]["round"])
        elif position == 'SELL':
            pos = 'BUY'
            stop = round(
                symbols[self.cliente.symbol]['price']*(1.002-symbols[self.cliente.symbol]['take_s']), symbols[self.cliente.symbol]["round"])
            price = round(
                symbols[self.cliente.symbol]['price']*(1-symbols[self.cliente.symbol]['take_s']), symbols[self.cliente.symbol]["round"])
        take = self.cliente.client.futures_create_order(
            symbol=symbols[self.cliente.symbol]['symbol'],
            side=pos,
            type='TAKE_PROFIT',
            quantity=symbols[self.cliente.symbol]['quantity'],
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
                    orderId=order_id, symbol=symbols[self.cliente.symbol]['symbol'])
            except Exception as e:
                print(str(dt.now()),'Error '+str(e)+' con '+intro +
                      ' y '+symbols[self.cliente.symbol]['symbol'], order_id)
                self.message.send('Error '+str(e)+' con '+intro +
                      ' y '+symbols[self.cliente.symbol]['symbol'], order_id)
                sleep(5)
            #print(intro, order['status'], order['orderId'])
            if (order['status'] == 'FILLED' and intro == 'create'):
                symbols[self.cliente.symbol]['price'] = float(order['avgPrice'])
                symbols[self.cliente.symbol]['quote'] = float(order['cumQuote'])*0.9996
                price_stop = self.stop_loss(symbols[self.cliente.symbol]['side'])
                price_take = self.take_profit(symbols[self.cliente.symbol]['side'])
                self.message.send('Se compro '+symbols[self.cliente.symbol]['symbol']+' el precio de compra fue ' +
                                  str(symbols[self.cliente.symbol]["price"])+' el precio del stop es '+str(
                    price_stop)+' y el precio del take es de '+str(price_take))
                print(str(dt.now()),'Se compro '+symbols[self.cliente.symbol]['symbol']+' el precio de compra fue ' +
                                  str(symbols[self.cliente.symbol]["price"])+' el precio del stop es '+str(
                    price_stop)+' y el precio del take es de '+str(price_take))
                break
            if (order['status'] == 'FILLED' and intro == 'stop'):
                if order['side'] == 'SELL':
                    balance += float(order['cumQuote']) - \
                        symbols[self.cliente.symbol]['quote']
                else:
                    balance += symbols[self.cliente.symbol]['quote'] - \
                        float(order['cumQuote'])*0.9998
                self.cliente.client.futures_cancel_all_open_orders(
                    symbol=symbols[self.cliente.symbol]['symbol'])
                symbols[self.cliente.symbol]['id'] = 0
                symbols[self.cliente.symbol]['quantity']=0
                self.message.send('Se tomo el stop loss de ' +
                                  symbols[self.cliente.symbol]['symbol']+' y el balance es de '+str(round(balance, 2)))
                print(str(dt.now()),'Se tomo el stop loss de ' +
                                  symbols[self.cliente.symbol]['symbol']+' y el balance es de '+str(round(balance, 2)))
                break
            if (order['status'] == 'FILLED' and intro == 'take'):
                if order['side'] == 'SELL':
                    balance += float(order['cumQuote']) - \
                        symbols[self.cliente.symbol]['quote']
                else:
                    balance += symbols[self.cliente.symbol]['quote'] - \
                        float(order['cumQuote'])*0.9998
                self.cliente.client.futures_cancel_all_open_orders(
                    symbol=symbols[self.cliente.symbol]['symbol'])
                symbols[self.cliente.symbol]['id'] = 0
                symbols[self.cliente.symbol]['quantity']=0
                self.message.send('Se tomo el take profit de ' +
                                  symbols[self.cliente.symbol]['symbol']+' y el balance es de '+str(round(balance, 2)))
                print(str(dt.now()),'Se tomo el take profit de ' +
                                  symbols[self.cliente.symbol]['symbol']+' y el balance es de '+str(round(balance, 2)))
                break
            if order['status'] == 'CANCELED':
                self.cliente.client.futures_cancel_all_open_orders(
                    symbol=symbols[self.cliente.symbol]['symbol'])
                symbols[self.cliente.symbol]['id'] = 0
                symbols[self.cliente.symbol]['quantity']=0
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
    for i in list_symbols:
        cliente.client.futures_change_leverage(symbol=i,leverage=symbols[i]['leverage'])
    print('Inicio', str(balance), str(dt.now()))

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
