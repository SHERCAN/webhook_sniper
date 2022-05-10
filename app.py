# modules-----------------------------
import sys
from threading import Thread
from json import load
from time import sleep
from requests import post
from binance.client import Client
import datetime as dt
from flask import Flask, request, render_template
# --------------------
# clases-----------------------
balance = 0.0
list_symbols = ['BTCUSDT', 'ETHUSDT', 'XRPUSDT']
with open('datos.json') as json_file:
    symbols = load(json_file)
# clase cliente


class Cliente:
    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        with open('datos.json') as json_file:
            claves = load(json_file)
        self.client = Client(claves['shercan']['key'],
                             claves['shercan']['secret'])

# ordenes de compra y venta


class Mensaje:

    def __init__(self):
        pass

    def send(self, data: str):
        post('https://api.telegram.org/bot5243749301:AAHIDCwt13NLYpmJ7WVaJLs57G0Z_IyFTLE/sendMessage',data={'chat_id': '-548326689', 'text': data})


class Ordenes:
    def __init__(self, symbol: str) -> None:
        self.cliente = Cliente(symbol.replace('PERP', ''))
        self.message = Mensaje()

    def create_order(self, position: str,close:str):
        quan_before=0
        if symbols[self.cliente.symbol]['quantity'] != 0:
            quan_before = float(symbols[self.cliente.symbol]['quantity'])

        try:
            self.cliente.client.futures_cancel_all_open_orders(symbol=symbols[self.cliente.symbol]['symbol'])
        except:
            pass
        quantity_n = str(((balance/6)*symbols[self.cliente.symbol]['leverage'])/float(close))[0:symbols[self.cliente.symbol]["accuracy"]]

        if symbols[self.cliente.symbol]['id'] != 0:
            quantity_n= str(float(quantity_n)+quan_before)

        order = self.cliente.client.futures_create_order(
            symbol=symbols[self.cliente.symbol]['symbol'],
            side=position,
            type='MARKET',
            quantity=quantity_n)
        sleep(0.2)
        symbols[self.cliente.symbol]['side'] = position
        symbols[self.cliente.symbol]['quantity'] = abs(self.cliente.client.futures_position_information(symbol=symbols[self.cliente.symbol]['symbol'])[0]['positionAmt'])
        symbols[self.cliente.symbol]['id'] = order['orderId']
        #print(symbols[self.cliente.symbol],'Quan',quan_before)

        order_exe = Thread(target=self.create_order_exe,args=(symbols[self.cliente.symbol]['id'], 'create',))
        order_exe.start()

# creación del stop loss

    def stop_loss(self, position: str):

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
        #print('stop',stop,'price',price)
        try:
            stop = self.cliente.client.futures_create_order(
                symbol=symbols[self.cliente.symbol]['symbol'],
                side=pos,
                type='STOP',
                quantity=symbols[self.cliente.symbol]['quantity'],
                price=price,
                stopPrice=stop,
                reduceOnly=True
            )
        except Exception as e:
            print('Compra realizada por fuera ')        
        order_exe = Thread(target=self.create_order_exe,args=(stop['orderId'], 'stop',))
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
        
        order_exe = Thread(target=self.create_order_exe,args=(take['orderId'], 'take',))
        order_exe.start()
        return price

# seguimiento de las ordenes

    def create_order_exe(self, order_id, intro: str):
        global balance
        
        while True:
            sleep(0.5)
            while True:
                try:
                    order = self.cliente.client.futures_get_order(orderId=order_id, symbol=symbols[self.cliente.symbol]['symbol'])
                    break
                except Exception as e:
                    now=dt.datetime.now(tz = dt.timezone(offset = dt.timedelta(hours = -5))).replace(microsecond = 0).isoformat()
                    print(str(now), 'Error '+str(e)+' con '+intro+' y '+symbols[self.cliente.symbol]['symbol'], order_id)
                    self.message.send('Error '+str(e)+' con '+intro+' y '+symbols[self.cliente.symbol]['symbol']+' '+str(order_id))
                sleep(5)
            
            if (order['status'] == 'FILLED' and intro == 'create'):
                symbols[self.cliente.symbol]['price'] = float(order['avgPrice'])
                symbols[self.cliente.symbol]['quote'] = float(order['cumQuote'])*0.9996
                price_stop = self.stop_loss(symbols[self.cliente.symbol]['side'])
                price_take = self.take_profit(symbols[self.cliente.symbol]['side'])
                self.message.send('Se compro '+symbols[self.cliente.symbol]['symbol']+' el precio de compra fue ' +str(symbols[self.cliente.symbol]["price"])+' el precio del stop es '+str(price_stop)+' y el precio del take es de '+str(price_take))
                now=dt.datetime.now(tz = dt.timezone(offset = dt.timedelta(hours = -5))).replace(microsecond = 0).isoformat()
                print(str(now), 'Se compro '+symbols[self.cliente.symbol]['symbol']+' el precio de compra fue ' +str(symbols[self.cliente.symbol]["price"])+' el precio del stop es '+str(price_stop)+' y el precio del take es de '+str(price_take))
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
                symbols[self.cliente.symbol]['quantity'] = 0.0
                self.message.send('Se tomo el stop loss de '+symbols[self.cliente.symbol]['symbol']+' y el balance es de '+str(round(balance, 2)))
                now=dt.datetime.now(tz = dt.timezone(offset = dt.timedelta(hours = -5))).replace(microsecond = 0).isoformat()
                print(str(now), 'Se tomo el stop loss de ' +
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
                symbols[self.cliente.symbol]['quantity'] = 0.0
                self.message.send('Se tomo el take profit de ' +
                                  symbols[self.cliente.symbol]['symbol']+' y el balance es de '+str(round(balance, 2)))
                now=dt.datetime.now(tz = dt.timezone(offset = dt.timedelta(hours = -5))).replace(microsecond = 0).isoformat()
                print(str(now), 'Se tomo el take profit de ' +
                      symbols[self.cliente.symbol]['symbol']+' y el balance es de '+str(round(balance, 2)))
                break
            if order['status'] == 'CANCELED':
                self.cliente.client.futures_cancel_all_open_orders(symbol=symbols[self.cliente.symbol]['symbol'])
                break
            
            sleep(0.5)
        sys.exit()

# inicio de programa
if __name__ == "__main__":
    from waitress import serve
    cliente = Cliente('BNBUSDT')
    list_balance = cliente.client.futures_account_balance()
    balance = float([x['balance']
                    for x in list_balance if x['asset'] == 'USDT'][0])
    for i in list_symbols:
        cliente.client.futures_change_leverage(symbol=i, leverage=symbols[i]['leverage'])
        info_coin=cliente.client.futures_position_information(symbol=i)
        cant_pos=float(info_coin[0]['positionAmt'])
        if cant_pos!=0:
            cliente.client.futures_cancel_all_open_orders(symbol=i)
            if cant_pos>0:
                symbols[i]['price']=float(info_coin[0]['entryPrice'])
                symbols[i]['quantity']=abs(cant_pos)
                symbols[i]['id'] = 100
                orders_before = Ordenes(i)
                orders_before.stop_loss('BUY')
                orders_before.take_profit('BUY')
            else:
                symbols[i]['price']=float(info_coin[0]['entryPrice'])
                symbols[i]['quantity']=abs(cant_pos)
                symbols[i]['id'] = 100
                orders_before = Ordenes(i)
                orders_before.stop_loss('SELL')
                orders_before.take_profit('SELL')
    now=dt.datetime.now(tz = dt.timezone(offset = dt.timedelta(hours = -5))).replace(microsecond = 0).isoformat()
    print('Inicio', str(balance), str(now))
    print(symbols)
    del cliente
    app = Flask(__name__)

    @app.route('/')
    def main():
        return render_template('main.html')

    @app.route('/webhook', methods=['POST'])
    def webhook():
        mensaje = 'nothing'

        if request.method == 'POST':
            recive = request.json

            if recive['position'] == '1' and recive['order'] == 'buy' and recive['ticker'] == 'BTCUSDTPERP':
                orders_buy_btc = Ordenes(recive['ticker'])
                orders_buy_btc.create_order('BUY',recive['price'])
                mensaje = 'Se realizo una orden en long BTC'
                try:
                    del orders_sell_btc
                except:
                    pass
            elif recive['position'] == '1' and recive['order'] == 'buy' and recive['ticker'] == 'XRPUSDTPERP':
                orders_buy_xrp = Ordenes(recive['ticker'])
                orders_buy_xrp.create_order('BUY',recive['price'])
                mensaje = 'Se realizo una orden en long XRP'
                try:
                    del orders_sell_xrp
                except:
                    pass
            elif recive['position'] == '1' and recive['order'] == 'buy' and recive['ticker'] == 'ETHUSDTPERP':
                orders_buy_eth = Ordenes(recive['ticker'])
                orders_buy_eth.create_order('BUY',recive['price'])
                mensaje = 'Se realizo una orden en long ETH'
                try:
                    del orders_sell_eth
                except:
                    pass
            elif recive['position'] == '-1' and recive['order'] == 'sell' and recive['ticker'] == 'BTCUSDTPERP':
                orders_sell_btc = Ordenes(recive['ticker'])
                orders_sell_btc.create_order('SELL',recive['price'])
                mensaje = 'Se realizo una orden en short BTC'
                try:
                    del orders_buy_btc
                except:
                    pass
            elif recive['position'] == '-1' and recive['order'] == 'sell' and recive['ticker'] == 'XRPUSDTPERP':
                orders_sell_xrp = Ordenes(recive['ticker'])
                orders_sell_xrp.create_order('SELL',recive['price'])
                mensaje = 'Se realizo una orden en short XRP'
                try:
                    del orders_buy_xrp
                except:
                    pass
            elif recive['position'] == '-1' and recive['order'] == 'sell' and recive['ticker'] == 'ETHUSDTPERP':
                orders_sell_eth = Ordenes(recive['ticker'])
                orders_sell_eth.create_order('SELL',recive['price'])
                mensaje = 'Se realizo una orden en short ETH'
                try:
                    del orders_buy_eth
                except:
                    pass
            return mensaje
    #app.run(host='127.0.0.1', port=80)
    serve(app, host='0.0.0.0', port=80, url_scheme='https')
# ----------json recepción
'''
Envio del dato desde el cliente, de esta manera
{"order":"{{strategy.order.action}}","position":"{{plot_15}}","ticker":"{{ticker}}","price":"{{close}}"}
'''
