# modules-----------------------------
import sys
from threading import Thread
from json import load,dump
from time import sleep
from requests import post
from binance.client import Client
import datetime as dt
from flask import Flask, request, render_template

# -----------------Variables globales-----------------------

balance = 0.0
list_symbols = ['BTCUSDT', 'LTCUSDT', 'ETHUSDT', 'BNBUSDT']
list_objects = []
with open('datos.json') as json_file:
    symbols = load(json_file)

# ------------------clase cliente--------------------

class Cliente:
    """
    Esta clase genera el cliente con conexión a Binance
    """

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        with open('datos.json') as json_file:
            claves = load(json_file)
        self.client = Client(claves['shercan']['key'],
                             claves['shercan']['secret'])

# -------------------Clase mensaje

class Mensaje:
    '''
    Esta clase envía los mensajes a Telegram
    '''

    def __init__(self):
        pass

    def send(self, data: str):
        post('https://api.telegram.org/bot5243749301:AAHIDCwt13NLYpmJ7WVaJLs57G0Z_IyFTLE/sendMessage',
             data={'chat_id': '-548326689', 'text': data})

# --------------------Clase ordenes---------

class Ordenes:
    '''Esta clase es la que recibe todo y envía ordenes cacelaciones, etc.'''

    def __init__(self, symbol: str) -> None:
        self.cliente = Cliente(symbol)
        self.message = Mensaje()

    def create_order(self, position: str, close: str, leverage: int = 2):
        '''Creación de la orden que llega desde el webhook'''
        quan_before = 0.0

        if symbols[self.cliente.symbol]['quantity'] != 0:
            quan_before = float(symbols[self.cliente.symbol]['quantity'])

        if symbols[self.cliente.symbol]['leverage'] != leverage:
            symbols[self.cliente.symbol]['leverage'] = leverage

            if symbols[self.cliente.symbol]['side'] == position:
                self.cliente.client.futures_change_leverage(
                symbol=symbols[self.cliente.symbol]['symbol'], leverage=leverage)

            elif quan_before != 0.0:
                try:
                    '''Weight:1'''
                    order = self.cliente.client.futures_create_order(
                        symbol=symbols[self.cliente.symbol]['symbol'],
                        side=position,
                        type='MARKET',
                        quantity=str(quan_before)[0:symbols[self.cliente.symbol]["accuracy"]])
                    sleep(0.1)
                    quan_before = 0.0
                except Exception as e:
                    print(symbols[self.cliente.symbol]['symbol'], position, 'MARKET', str(
                        quantity_n)[0:symbols[self.cliente.symbol]["accuracy"]])
                    self.message.send('El error en compra fue '+str(e))
                '''Weight:1'''
            self.cliente.client.futures_change_leverage(
                symbol=symbols[self.cliente.symbol]['symbol'], leverage=leverage)

        balance = update.balance
        quantity_n = str(((balance/4)*symbols[self.cliente.symbol]['leverage'])/float(
            close))[0:symbols[self.cliente.symbol]["accuracy"]]

        if symbols[self.cliente.symbol]['id'] != 0:
            quantity_n = str(float(quantity_n)+quan_before)
        try:
            '''Weight:1'''
            order = self.cliente.client.futures_create_order(
                symbol=symbols[self.cliente.symbol]['symbol'],
                side=position,
                type='MARKET',
                quantity=str(quantity_n)[0:symbols[self.cliente.symbol]["accuracy"]])
        except Exception as e:
            print(symbols[self.cliente.symbol]['symbol'], position, 'MARKET', str(
                quantity_n)[0:symbols[self.cliente.symbol]["accuracy"]])
            self.message.send('El error en compra fue '+str(e))
            order['orderId'] = 0

        sleep(1)
        try:
            '''Weight:1'''
            self.cliente.client.futures_cancel_all_open_orders(
                symbol=symbols[self.cliente.symbol]['symbol'])
            sleep(0.5)
            '''Weight:5'''
            posicion = self.cliente.client.futures_position_information(
                symbol=symbols[self.cliente.symbol]['symbol'])[0]['positionAmt']
        except:
            print(symbols[self.cliente.symbol]['symbol'], position, 'MARKET', str(
                quantity_n)[0:symbols[self.cliente.symbol]["accuracy"]])
            self.message.send('El error en compra fue '+str(e))
            order['orderId'] = 0

        symbols[self.cliente.symbol]['quantity'] = abs(float(posicion))
        symbols[self.cliente.symbol]['id'] = order['orderId']
        order_exe = Thread(target=self.create_order_exe, args=(
            symbols[self.cliente.symbol]['id'], 'create',))
        order_exe.start()

    def stop_loss(self, position: str):
        '''Calculo de los stop loss de todas las ordenes'''
        if position == 'BUY':
            pos = 'SELL'
            stop = round(
                symbols[self.cliente.symbol]['price']*(1.002-symbols[self.cliente.symbol]['stop_l']), symbols[self.cliente.symbol]["round"])
            price = round(
                symbols[self.cliente.symbol]['price']*(1-symbols[self.cliente.symbol]['stop_l']), symbols[self.cliente.symbol]["round"])
        elif position == 'SELL':
            pos = 'BUY'
            stop = round(
                symbols[self.cliente.symbol]['price']*(0.998+symbols[self.cliente.symbol]['stop_s']), symbols[self.cliente.symbol]["round"])
            price = round(
                symbols[self.cliente.symbol]['price']*(1+symbols[self.cliente.symbol]['stop_s']), symbols[self.cliente.symbol]["round"])

        try:
            '''Weight:1'''
            loss = self.cliente.client.futures_create_order(
                symbol=symbols[self.cliente.symbol]['symbol'],
                side=pos,
                type='STOP',
                quantity=symbols[self.cliente.symbol]['quantity'],
                price=price,
                stopPrice=stop,
                reduceOnly=True
            )
        except Exception as e:
            print(symbols[self.cliente.symbol]['symbol'], pos, 'STOP',
                  symbols[self.cliente.symbol]['quantity'], price, stop,)
            self.message.send('El error en stop fue '+str(e))
        order_exe = Thread(target=self.create_order_exe,
                           args=(loss['orderId'], 'stop',))
        order_exe.start()
        return price

    def take_profit(self, position: str):
        '''Calculo del take profit de todas las ordenes'''
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
        try:
            '''Weight:1'''
            take = self.cliente.client.futures_create_order(
                symbol=symbols[self.cliente.symbol]['symbol'],
                side=pos,
                type='TAKE_PROFIT',
                quantity=symbols[self.cliente.symbol]['quantity'],
                price=price,
                stopPrice=stop,
                reduceOnly=True
            )
        except Exception as e:
            print(symbols[self.cliente.symbol]['symbol'], pos, 'STOP',
                  symbols[self.cliente.symbol]['quantity'], price, stop)
            self.message.send('El error en take fue '+str(e))
        order_exe = Thread(target=self.create_order_exe,
                           args=(take['orderId'], 'take',))
        order_exe.start()
        return price

    def create_order_exe(self, order_id, intro: str):
        '''Seguimiento de todas las ordenes'''
        while True:
            sleep(0.5)
            while True:
                try:
                    '''Weight:1'''
                    order = self.cliente.client.futures_get_order(
                        orderId=order_id, symbol=symbols[self.cliente.symbol]['symbol'])
                    symbols[self.cliente.symbol]['id'] = order['orderId']
                    symbols[self.cliente.symbol]['side'] = order['side']
                    break
                except Exception as e:
                    now = dt.datetime.now(tz=dt.timezone(offset=dt.timedelta(
                        hours=-5))).replace(microsecond=0).isoformat()
                    print(str(now), 'Error '+str(e)+' con '+intro+' y ' +
                          symbols[self.cliente.symbol]['symbol'], order_id)
                    self.message.send('Error '+str(e)+' con '+intro+' y ' +
                                      symbols[self.cliente.symbol]['symbol']+' '+str(order_id))
                sleep(5)

            if (order['status'] == 'FILLED' and intro == 'create'):
                symbols[self.cliente.symbol]['price'] = float(
                    order['avgPrice'])
                symbols[self.cliente.symbol]['quote'] = float(
                    order['cumQuote'])*0.9996
                price_stop = self.stop_loss(
                    symbols[self.cliente.symbol]['side'])
                price_take = self.take_profit(
                    symbols[self.cliente.symbol]['side'])
                self.message.send(order['side']+' en '+symbols[self.cliente.symbol]['symbol']+' a ' + str(
                    symbols[self.cliente.symbol]["price"])+' con sl de '+str(price_stop)+' y tp de '+str(price_take))
                now = dt.datetime.now(tz=dt.timezone(offset=dt.timedelta(
                    hours=-5))).replace(microsecond=0).isoformat()
                print(str(now), order['side']+' en '+symbols[self.cliente.symbol]['symbol']+' a ' + str(
                    symbols[self.cliente.symbol]["price"])+' con sl de '+str(price_stop)+' y tp de '+str(price_take))
                break

            if (order['status'] == 'FILLED' and intro == 'stop'):
                '''Weight:1'''
                self.cliente.client.futures_cancel_all_open_orders(
                    symbol=symbols[self.cliente.symbol]['symbol'])
                symbols[self.cliente.symbol]['id'] = 0
                symbols[self.cliente.symbol]['quantity'] = 0.0
                self.message.send('Se tomo el sl de ' +
                                  symbols[self.cliente.symbol]['symbol'])
                now = dt.datetime.now(tz=dt.timezone(offset=dt.timedelta(
                    hours=-5))).replace(microsecond=0).isoformat()
                print(str(now), 'Se tomo el sl de ' +
                      symbols[self.cliente.symbol]['symbol'])
                break

            if (order['status'] == 'FILLED' and intro == 'take'):
                '''Weight:1'''
                self.cliente.client.futures_cancel_all_open_orders(
                    symbol=symbols[self.cliente.symbol]['symbol'])
                symbols[self.cliente.symbol]['id'] = 0
                symbols[self.cliente.symbol]['quantity'] = 0.0
                self.message.send('Se tomo el tp de ' +
                                  symbols[self.cliente.symbol]['symbol'])
                now = dt.datetime.now(tz=dt.timezone(offset=dt.timedelta(
                    hours=-5))).replace(microsecond=0).isoformat()
                print(str(now), 'Se tomo el tp de ' +
                      symbols[self.cliente.symbol]['symbol'])
                break
            if order['status'] == 'CANCELED':
                '''Weight:1'''
                self.cliente.client.futures_cancel_all_open_orders(
                    symbol=symbols[self.cliente.symbol]['symbol'])
                break

            sleep(0.5)
        sys.exit()

# -----------------------Evenetos que tienen que estar repitiendose por un largo tiempo.------------


class All_time:
    def __init__(self) -> None:
        self.hour_before = dt.datetime.now().hour
        self.message = Mensaje()
        self.balance = 0.0
        self.inicio()
        self.thread = Thread(target=self.hora)
        self.thread.start()

    def hora(self):
        '''Envío de mensaje al grupo de Telegram del saldo'''
        while True:
            hour_now = dt.datetime.now().hour
            if self.hour_before != hour_now and hour_now % 4 == 0:
                sleep(20)
                cliente = Cliente('BNBUSDT')
                '''weight:5'''
                list_balance = cliente.client.futures_account_balance()
                self.balance = float(
                    [x['balance']for x in list_balance if x['asset'] == 'USDT'][0])
                self.message.send(
                    f'Tu balance es de {round(self.balance,2)} USDT')
                self.hour_before = hour_now
                if len(list_objects) > 5:
                    list_objects.pop(0)
                with open("datos.json", "w") as write_file:
                    dump(symbols, write_file)
                del cliente

    def inicio(self):
        '''Envío de mensaje al grupo de Telegram del saldo inicial'''
        cliente = Cliente('BNBUSDT')
        '''weight:5'''
        list_balance = cliente.client.futures_account_balance()
        self.balance = float([x['balance']
                             for x in list_balance if x['asset'] == 'USDT'][0])
        self.message.send(f'Tu balance es de {round(self.balance,2)} USDT')
        del cliente


# -----------------------------------inicio de programa
if __name__ == "__main__":
    from waitress import serve
    cliente = Cliente('BNBUSDT')
    update = All_time()
    for i in list_symbols:
        try:
            '''Weight:1'''
            cliente.client.futures_change_leverage(
                symbol=i, leverage=symbols[i]['leverage'])
        except:
            pass
        '''Weight:5'''
        info_coin = cliente.client.futures_position_information(symbol=i)
        cant_pos = float(info_coin[0]['positionAmt'])
        if cant_pos != 0:
            '''Weight:1'''
            cliente.client.futures_cancel_all_open_orders(symbol=i)
            if cant_pos > 0:
                symbols[i]['price'] = float(info_coin[0]['entryPrice'])
                symbols[i]['quote'] = float(
                    info_coin[0]['isolatedWallet'])*0.9996
                symbols[i]['quantity'] = abs(cant_pos)
                symbols[i]['id'] = 100
                orders_before = Ordenes(i)
                orders_before.stop_loss('BUY')
                orders_before.take_profit('BUY')
            else:
                symbols[i]['price'] = float(info_coin[0]['entryPrice'])
                symbols[i]['quantity'] = abs(cant_pos)
                symbols[i]['id'] = 100
                orders_before = Ordenes(i)
                orders_before.stop_loss('SELL')
                orders_before.take_profit('SELL')
    now = dt.datetime.now(tz=dt.timezone(offset=dt.timedelta(
        hours=-5))).replace(microsecond=0).isoformat()
    print('Inicio', str(update.balance), str(now))
    del cliente

# -----INICIO DEL BACKEND------
    app = Flask(__name__)

    @app.route('/')
    def main():
        return render_template('index.html')

    @app.route('/webhook', methods=['POST'])
    def webhook():
        mensaje = 'nothing'

        if request.method == 'POST':
            recive = request.json
            
            if list_symbols.count(recive['ticker'].replace('PERP', '')) > 0 and recive['cod'] == "techmasters":
                ticker=recive['ticker'].replace('PERP', '')
                list_objects.append(Ordenes(ticker))
                try:
                    leverage = recive["leverage"]
                except:
                    leverage = symbols[ticker]['leverage']
                try:
                    list_objects[-1].create_order(recive['order'].upper(),recive['price'], int(leverage))
                    mensaje = 'Se realizo una orden en ' + str(recive['position']) + str(ticker)
                except Exception as e:
                    message = Mensaje()
                    now = dt.datetime.now(tz=dt.timezone(offset=dt.timedelta(
                        hours=-5))).replace(microsecond=0).isoformat()
                    print(str(now), 'Error '+str(e)+' con POST y ' +ticker)
                    message.send(str(now), 'Error '+str(e)+' con POST y ' +ticker)

            return mensaje
    #app.run(host='127.0.0.1', port=80)
    serve(app, host='0.0.0.0', port=80, url_scheme='https')
# ----------json recepción
'''
Envio del dato desde el cliente, de esta manera

{"cod":"techmasters","order":"{{strategy.order.action}}","position":"{{strategy.order.alert_message}}","ticker":"{{ticker}}","price":"{{close}}","leverage":{{strategy.order.comment}}}
'''
