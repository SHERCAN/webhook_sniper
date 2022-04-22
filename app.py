# modules-----------------------------
from threading import Thread
from json import load
from time import sleep
from binance.client import Client
from flask import Flask, request, render_template
# --------------------
# clases-----------------------

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


class Ordenes:

    def __init__(self, symbol: str) -> None:
        self.cliente = Cliente(symbol.replace('PERP', ''))

    def create_order(self, position: str):
        balance = self.cliente.client.futures_account_balance()
        balance = float([x['balance']
                        for x in balance if x['asset'] == 'USDT'][0])/2
    # print(balance)
        try:
            self.cliente.client.futures_cancel_all_open_orders(
                symbol=self.cliente.base['symbol'])
        except:
            pass
        print("Llego a crear la orden de compra en market")
        """ order = self.cliente.client.futures_create_order(
            symbol=self.cliente.base['symbol'],
            side=position,
            type='MARKET',
            quantity=str((balance*30)/float(
                self.cliente.client.futures_symbol_ticker(
                    symbol=self.cliente.base['symbol'])['price']))[0:5]
        ) 
        self.cliente.base['side'] = position
        self.cliente.base['quantity'] = order['origQty']
        self.cliente.base['id'] = order['orderId']
        # print(datos)"""
        # order_exe = Thread(target=self.create_order_exe,
        #                   args=(self.cliente.base['id'], 'create',))
        order_exe = Thread(target=self.create_order_exe,
                           args=(5354530132, 'create',))
        order_exe.start()
        # print(order)

    def stop_loss(self, position: str):
        # print(position)
        if position == 'BUY':
            pos = 'SELL'
            stop = round(
                float(self.cliente.base['price'])*(1.002-self.cliente.base['stop']), 1)
            price = round(
                float(self.cliente.base['price'])*(1-self.cliente.base['stop']), 1)
        elif position == 'SELL':
            pos = 'BUY'
            stop = round(
                float(self.cliente.base['price'])*(0.998+self.cliente.base['stop']), 1)
            price = round(
                float(self.cliente.base['price'])*(1+self.cliente.base['stop']), 1)
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

    def take_profit(self, position: str):
        if position == 'BUY':
            pos = 'SELL'
            stop = round(
                float(self.cliente.base['price'])*(0.998+self.cliente.base['take_l']), 1)
            price = round(
                float(self.cliente.base['price'])*(1+self.cliente.base['take_l']), 1)
        elif position == 'SELL':
            pos = 'BUY'
            stop = round(
                float(self.cliente.base['price'])*(1.002-self.cliente.base['take_s']), 1)
            price = round(
                float(self.cliente.base['price'])*(1-self.cliente.base['take_s']), 1)
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

    def create_order_exe(self, order_id, intro: str):
        while True:
            order = self.cliente.client.futures_get_order(
                orderId=order_id, symbol=self.cliente.base['symbol'])
            print(intro, order['status'], order['orderId'])
            if ((order['status'] == 'FILLED' and intro == 'create') or
                    intro == 'create' and order['status'] == 'CANCELED'):
                self.cliente.base['price'] = order['avgPrice']
                print('Entro a crear las ordenes de stop y take')
                #self.stop_loss(self.cliente.base['side'])
                #self.take_profit(self.cliente.base['side'])
                break
            if ((order['status'] == 'FILLED' and intro == 'stop') or
                    intro == 'stop' and order['status'] == 'CANCELED'):
                self.cliente.client.futures_cancel_all_open_orders(
                    symbol=self.cliente.base['symbol'])
                break
            if ((order['status'] == 'FILLED' and intro == 'take') or
                    intro == 'take' and order['status'] == 'CANCELED'):
                self.cliente.client.futures_cancel_all_open_orders(
                    self.cliente.base['symbol'])
                break
            sleep(2)

    def prueba(self):
        print('Entro bien')


# inicio de programa
if __name__ == "__main__":
    app = Flask(__name__)

    @app.route('/')
    def main():
        print("Llegaste")
        return render_template('main.html')

    @app.route('/webhook', methods=['POST'])
    def webhook():
        mensaje = 'nothing'
        if request.method == 'POST':
            recive = request.json
            if recive['position'] == '1' and recive['order'] == 'buy':
                print('long')
                orders = Ordenes(recive['ticker'])
                orders.create_order('BUY')
                orders.prueba()
                mensaje = 'Se realizo una orden en long'
            elif recive['position'] == '-1' and recive['order'] == 'sell':
                print('short')
                orders.create_order('SELL')
                orders.prueba()
                mensaje = 'Se realizo una orden en short'
            return mensaje
    app.run(host='127.0.0.1', port=80)
    #app.run(host='0.0.0.0', port=80)
# ----------json recepción
'''
Envio del dato desde el cliente, de esta manera
{"order":"{{strategy.order.action}}","position":"{{plot_15}}","ticker":"{{ticker}}"}
'''
