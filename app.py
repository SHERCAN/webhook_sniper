#-------------------------------------modules-----------------------------
import sys
from password import *
from threading import Thread
from json import load, dump
from time import sleep
from requests import post
from binance.client import Client
import datetime as dt
from flask import Flask, request, render_template
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from base64 import urlsafe_b64encode
# users----{'raul':{'key':'hsdfljqr','secret':'jifwerc'},...}

# -------------------Clase mensaje---------

class Mensaje:
    '''
    Esta clase envía los mensajes a Telegram
    '''

    def __init__(self):
        pass

    def send(self, data: str):
        post('https://api.telegram.org/bot5243749301:AAHIDCwt13NLYpmJ7WVaJLs57G0Z_IyFTLE/sendMessage',
             data={'chat_id': '-548326689', 'text': data})
    def send_user(self, data: str,user):
        post('https://api.telegram.org/bot5530592078:AAEcb0EiHsntHj2HlqDIqqY9QKkxbS4070E/sendMessage',
             data={'chat_id': user, 'text': data})

# -----------------------Eventos que tienen que estar repitiendose todo el tiempo.------------

class All_time:
    '''
    Verificación y actualizacion
    '''
    def __init__(self) -> None:
        self.hour_before = dt.datetime.now().hour
        self.list_objects = []
        self.message = Mensaje()
        self.accounts={}
        with open("coins.json") as js:
            self.symbols = load(js)
            self.list_symbols = (list(self.symbols.keys()))
        with open('users.json') as json_file:
            self.claves = load(json_file)
            self.users = (list(self.claves.keys()))
        self.thread = Thread(target=self.hora)
        self.thread.start()
        lista_balances=[]
        for i in self.users:
            cliente = self.__cliente(i)
            '''weight:5'''
            list_balance = cliente.futures_account_balance()
            lista_balances.append(float([x['balance']for x in list_balance if x['asset'] == 'USDT'][0]))
            for i in self.list_symbols:
                '''weight:1'''
                cliente.futures_change_leverage(symbol=i, leverage=self.symbols[i]['leverage'])
                '''
                -----------------------------------
                ----------------------------------
                poner el cambio de de aislado y cruzado.
                ----------------------------------
                --------------------------------
                '''
                pass
        self.balance=lista_balances.copy()
        self.message.send(f'Tu balance es de {round(self.balance[0],2)} USDT')
        del cliente
    def __cliente(self,id):
        apis = self.claves[id]
        client = Client(apis['key'], apis['secret'])
        return client

    def hora(self):
        '''Envío de mensaje al grupo de Telegram del saldo'''
        while True:
            hour_now = dt.datetime.now().hour
            if self.hour_before != hour_now and hour_now % 4 == 0:
                sleep(1000)
                lista_balances=[]
                for i in self.users:
                    cliente = self.__cliente(i)
                    '''weight:5'''
                    list_balance = cliente.futures_account_balance()
                    lista_balances.append(float([x['balance']for x in list_balance if x['asset'] == 'USDT'][0]))
                self.balance=lista_balances.copy()
                self.message.send(f'Tu balance es de {round(self.balance[0],2)} USDT')
                self.hour_before = hour_now
                if len(self.list_objects) > 15:
                    self.list_objects.pop(0)
                with open("coins.json", "w") as write_file:
                    dump(self.symbols, write_file)
                with open('users.json') as json_file:
                    self.claves = load(json_file)
                    self.users = (list(self.claves.keys()))
                del cliente

update = All_time()

# ------------------clase cliente--------------------
class Cliente:
    """
    Esta clase genera el cliente con conexión a Binance
    """
    def __init__(self, symbol: str, id: str) -> None:
        self.symbol = symbol
        self.apis = update.claves[id]
        self.client = Client(self.apis['key'], self.apis['secret'])
    
# --------------------Clase ordenes---------

class Ordenes:
    '''Esta clase es la que recibe, envía ordenes cancelaciones, etc.
    '''
    def __init__(self, symbol: str, id) -> None:
        self.cliente = Cliente(symbol, id)
        self.id=id
        self.symbol = symbol
        self.message = Mensaje()
        self.order={}
        self.order['orderId'] = 0
        try:
            update.accounts[self.id][self.symbol]['id'] != 0
            update.accounts[self.id][self.symbol]['quantity']!= 0
        except:
            update.accounts[self.id]={}
            update.accounts[self.id].update({self.symbol:{'quantity':0,'id':0,
            'side':'','leverage':1}})

    def create_order(self, position: str, close: str, leverage: int = 2):
        '''Creación de la orden que llega desde el webhook'''
        self.quan_before = 0.0
        self.close=close
        self.position=position
        self.quantity_n=''
        self.posicion=''
        self.leverage=leverage
        if update.accounts[self.id][self.symbol]['quantity'] != 0:
            self.quan_before = float(update.accounts[self.id][self.symbol]['quantity'])

        if update.accounts[self.id][self.symbol]['leverage'] != self.leverage:
            if self.quan_before != 0.0 and self.position!=update.accounts[self.id][self.symbol]['side']:
                try:
                    '''Weight:1'''
                    
                    self.order = self.cliente.client.futures_create_order(
                        symbol=update.symbols[self.cliente.symbol]['symbol'],
                        side=self.position,
                        type='MARKET',
                        quantity=str(self.quan_before)[0:update.symbols[self.cliente.symbol]["accuracy"]])
                    sleep(0.5)
                    self.quan_before = 0.0
                except Exception as e:
                    print(update.symbols[self.cliente.symbol]['symbol'], self.position, 'MARKET', str(
                        self.quantity_n)[0:update.symbols[self.cliente.symbol]["accuracy"]])
                    if self.id=="742390776":
                        self.message.send('El error en cierre '+str(e))
                '''Weight:1'''
            res=self.cliente.client.futures_change_leverage(symbol=update.symbols[self.cliente.symbol]['symbol'], leverage=self.leverage)
            #print('leverage',update.symbols[self.cliente.symbol]['symbol'],res['leverage'])
            update.accounts[self.id][self.symbol]['leverage'] = int(res['leverage'])
        '''----------------------------------------------------
        revisión saldos-----------------------------------------'''
        self.balance = update.balance[update.users.index(self.id)]
        self.quantity_n = str(((self.balance/4)*update.accounts[self.id][self.symbol]['leverage'])/float(
            self.close))[0:update.symbols[self.cliente.symbol]["accuracy"]]

        if update.accounts[self.id][self.symbol]['id'] != 0:
            self.quantity_n = str(float(self.quantity_n)+self.quan_before)
        try:
            '''Weight:1'''
            self.order = self.cliente.client.futures_create_order(
                symbol=update.symbols[self.cliente.symbol]['symbol'],
                side=self.position,
                type='MARKET',
                quantity=str(self.quantity_n)[0:update.symbols[self.cliente.symbol]["accuracy"]])
        except Exception as e:
            print(update.symbols[self.cliente.symbol]['symbol'], self.position, 'MARKET', str(
                self.quantity_n)[0:update.symbols[self.cliente.symbol]["accuracy"]])
            if self.id=="742390776":
                self.message.send('El error en compra fue '+str(e))
            self.order['orderId'] = 0

        if self.order['orderId']!=0:
            sleep(2)
            while True:
                try:
                    '''Weight:1'''
                    self.cliente.client.futures_cancel_all_open_orders(
                        symbol=update.symbols[self.cliente.symbol]['symbol'])
                    sleep(0.5)
                    '''Weight:5'''
                    self.posicion = self.cliente.client.futures_position_information(symbol=update.symbols[self.cliente.symbol]['symbol'])[0]['positionAmt']
                    break
                except:
                    print(update.symbols[self.cliente.symbol]['symbol'], self.position, 'MARKET', str(
                        self.quantity_n)[0:update.symbols[self.cliente.symbol]["accuracy"]])
                    if self.id=="742390776":
                        self.message.send('El error en compra fue '+str(e))
                    self.order['orderId'] = 0
                    break
            update.accounts[self.id][self.symbol]['quantity'] = abs(float(self.posicion))
            update.accounts[self.id][self.symbol]['id'] = self.order['orderId']
            order_exe = Thread(target=self.create_order_exe, args=(update.accounts[self.id][self.symbol]['id'], 'create',))
            order_exe.start()

    def stop_loss(self, position: str):
        '''Calculo de los stop loss de todas las ordenes'''
        self.position=position
        if self.position == 'BUY':
            self.pos = 'SELL'
            self.stop = round(
                update.accounts[self.id][self.symbol]['price']*(1.002-update.symbols[self.cliente.symbol]['stop_l']), update.symbols[self.cliente.symbol]["round"])
            self.price = round(
                update.accounts[self.id][self.symbol]['price']*(1-update.symbols[self.cliente.symbol]['stop_l']), update.symbols[self.cliente.symbol]["round"])
        elif self.position == 'SELL':
            self.pos = 'BUY'
            self.stop = round(
                update.accounts[self.id][self.symbol]['price']*(0.998+update.symbols[self.cliente.symbol]['stop_s']), update.symbols[self.cliente.symbol]["round"])
            self.price = round(
                update.accounts[self.id][self.symbol]['price']*(1+update.symbols[self.cliente.symbol]['stop_s']), update.symbols[self.cliente.symbol]["round"])
        try:
            '''Weight:1'''
            self.loss = self.cliente.client.futures_create_order(
                symbol=update.symbols[self.cliente.symbol]['symbol'],
                side=self.pos,
                type='STOP',
                quantity=update.accounts[self.id][self.symbol]['quantity'],
                price=self.price,
                stopPrice=self.stop,
                reduceOnly=True
            )
        except Exception as e:
            print(update.symbols[self.cliente.symbol]['symbol'], self.pos, 'STOP',
                  update.accounts[self.id][self.symbol]['quantity'], self.price, self.stop,)
            if self.id=="742390776":
                self.message.send('El error en stop fue '+str(e))
        order_exe = Thread(target=self.create_order_exe,
                           args=(self.loss['orderId'], 'stop',))
        order_exe.start()
        return self.price

    def take_profit(self, position: str):
        '''Calculo del take profit de todas las ordenes'''
        self.position=position
        if self.position == 'BUY':
            self.pos = 'SELL'
            self.stop = round(
                update.accounts[self.id][self.symbol]['price']*(0.998+update.symbols[self.cliente.symbol]['take_l']), update.symbols[self.cliente.symbol]["round"])
            self.price = round(
                update.accounts[self.id][self.symbol]['price']*(1+update.symbols[self.cliente.symbol]['take_l']), update.symbols[self.cliente.symbol]["round"])
        elif self.position == 'SELL':
            self.pos = 'BUY'
            self.stop = round(
                update.accounts[self.id][self.symbol]['price']*(1.002-update.symbols[self.cliente.symbol]['take_s']), update.symbols[self.cliente.symbol]["round"])
            self.price = round(
                update.accounts[self.id][self.symbol]['price']*(1-update.symbols[self.cliente.symbol]['take_s']), update.symbols[self.cliente.symbol]["round"])
        try:
            '''Weight:1'''
            self.take = self.cliente.client.futures_create_order(
                symbol=update.symbols[self.cliente.symbol]['symbol'],
                side=self.pos,
                type='TAKE_PROFIT',
                quantity=update.accounts[self.id][self.symbol]['quantity'],
                price=self.price,
                stopPrice=self.stop,
                reduceOnly=True
            )
        except Exception as e:
            print(update.symbols[self.cliente.symbol]['symbol'], self.pos, 'STOP',
                  update.accounts[self.id][self.symbol]['quantity'], self.price, self.stop)
            if self.id=="742390776":
                self.message.send('El error en take fue '+str(e))
        order_exe = Thread(target=self.create_order_exe,
                           args=(self.take['orderId'], 'take',))
        order_exe.start()
        return self.price

    def create_order_exe(self, order_id, intro: str):
        '''Seguimiento de todas las ordenes'''
        self.order_id=order_id
        self.intro=intro
        while True:
            sleep(0.5)
            while True:
                try:
                    '''Weight:1'''
                    self.order = self.cliente.client.futures_get_order(
                        orderId=self.order_id, symbol=update.symbols[self.cliente.symbol]['symbol'])
                    update.accounts[self.id][self.symbol]['id'] = self.order['orderId']
                    update.accounts[self.id][self.symbol]['side'] = self.order['side']
                    break
                except Exception as e:
                    '''Weight:5'''
                    #posicion = self.cliente.client.futures_position_information(symbol=update.symbols[self.cliente.symbol]['symbol'])[0]['positionAmt']
                    #update.accounts[self.id][self.symbol]['quantity'] = abs(float(posicion))
                    now = dt.datetime.now(tz=dt.timezone(offset=dt.timedelta(
                        hours=-5))).replace(microsecond=0).isoformat()
                    print(str(now), 'Error '+str(e)+' con '+self.intro+' y ' +
                          update.symbols[self.cliente.symbol]['symbol'], self.order_id)
                    if self.id=="742390776":
                        self.message.send('Error '+str(e)+' con '+self.intro+' y ' +
                                      update.symbols[self.cliente.symbol]['symbol']+' '+str(self.order_id))
                sleep(5)

            if (self.order['status'] == 'FILLED' and self.intro == 'create'):
                update.accounts[self.id][self.symbol]['price'] = float(self.order['avgPrice'])
                update.accounts[self.id][self.symbol]['quote'] = float(self.order['cumQuote'])*0.9996
                create_tp_sl=update.accounts[self.id][self.symbol]['side']
                sleep(10.5)
                price_take = self.take_profit(create_tp_sl)
                sleep(10.5)
                price_stop = self.stop_loss(create_tp_sl)    
                msm=create_tp_sl+' en '+update.symbols[self.cliente.symbol]['symbol']+' a ' + str(
                    update.accounts[self.id][self.symbol]["price"])+' con sl de '+str(price_stop)+' y tp de '+str(price_take)                    
                '''-----------------------------------------------------posicion envio mensaje----------
                ----------------------------------------------------------------------------------------
                ---------------------------------------------------------------------------------------'''
                if self.id=="742390776":
                    self.message.send(msm)
                now = dt.datetime.now(tz=dt.timezone(offset=dt.timedelta(
                    hours=-5))).replace(microsecond=0).isoformat()
                print(str(now), msm)
                break

            if (self.order['status'] == 'FILLED' and self.intro == 'stop'):
                '''Weight:1'''
                self.cliente.client.futures_cancel_all_open_orders(
                    symbol=update.symbols[self.cliente.symbol]['symbol'])
                update.accounts[self.id][self.symbol]['id'] = 0
                update.accounts[self.id][self.symbol]['quantity'] = 0.0
                '''----------------------------------------------------------------
                mensaje cierre del stop--------------------------------------------'''
                msm='Se tomo el sl de ' +update.symbols[self.cliente.symbol]['symbol']
                if self.id=="742390776":
                    self.message.send(msm)
                now = dt.datetime.now(tz=dt.timezone(offset=dt.timedelta(
                    hours=-5))).replace(microsecond=0).isoformat()
                print(str(now),msm)
                update.accounts[self.id][self.symbol]['side']=''
                break

            if (self.order['status'] == 'FILLED' and self.intro == 'take'):
                '''Weight:1'''
                self.cliente.client.futures_cancel_all_open_orders(
                    symbol=update.symbols[self.cliente.symbol]['symbol'])
                update.accounts[self.id][self.symbol]['id'] = 0
                update.accounts[self.id][self.symbol]['quantity'] = 0.0
                '''--------------------------------------------------------------
                -------------------take profit envio mensaje---------------------------
                -----------------------------------------------------------------------'''
                msm='Se tomo el tp de ' + update.symbols[self.cliente.symbol]['symbol']
                if self.id=="742390776":
                    self.message.send(msm)
                now = dt.datetime.now(tz=dt.timezone(offset=dt.timedelta(
                    hours=-5))).replace(microsecond=0).isoformat()
                print(str(now),msm)
                update.accounts[self.id][self.symbol]['side']=''
                break
            if self.order['status'] == 'CANCELED':
                '''Weight:1'''
                self.cliente.client.futures_cancel_all_open_orders(
                    symbol=update.symbols[self.cliente.symbol]['symbol'])
                update.accounts[self.id][self.symbol]['side']=''
                break

            sleep(0.5)
        sys.exit()

class Security:
    def __init__(self) -> None:
        self.__key1 = pass1.encode()
        self.__key2 = pass2.encode()

    def __get_fernet(self):
        kdf = PBKDF2HMAC(
            algorithm=SHA256(),
            length=32,
            salt=self.__key2,
            iterations=390000,)
        key = urlsafe_b64encode(kdf.derive(self.__key1))
        fernet = Fernet(key)
        return fernet

    def decrypt_api(self, text):
        textDecrypt = self.__get_fernet().decrypt(text.encode())
        return_text = textDecrypt.decode()
        return return_text

    def encrypt_api(self, text):
        textDecrypt = self.__get_fernet().encrypt(text.encode())
        return_text = textDecrypt.decode()
        return return_text


# -----------------------------------inicio de programa
if __name__ == "__main__":
    from waitress import serve
    now = dt.datetime.now(tz=dt.timezone(offset=dt.timedelta(
        hours=-5))).replace(microsecond=0).isoformat()
    print('Inicio', str(update.balance), str(now))
    message = Mensaje()
# -----INICIO DEL BACKEND------
    app = Flask(__name__)

    @app.route('/')
    def main():
        return render_template('main.html')

    @app.route('/webhook', methods=['POST'])
    def webhook():
        mensaje = 'nothing'

        if request.method == 'POST':
            recive = request.json
            ticker = recive['ticker'].replace('PERP', '')    
            if ((update.list_symbols.count(ticker) > 0 and recive['cod'] == "techmasters")
                    and (recive['position'] == 'short' or recive['position'] == 'long')):
                for i in update.users:
                    update.list_objects.append(Ordenes(ticker, i))
                    #print(ticker,i)
                    try:
                        leverage = recive["leverage"]
                    except:
                        leverage = update.symbols[ticker]['leverage']
                        #print(leverage, update.accounts[i][ticker]['leverage'], recive["leverage"])
                    try:
                        update.list_objects[-1].create_order(recive['order'].upper(),recive['price'], int(leverage))
                        mensaje = 'Se realizo una orden en ' + \
                            str(recive['position']) +' '+ str(ticker)
                        #message.send(mensaje+ ' '+ recive['price'])
                    except Exception as e:
                        now = dt.datetime.now(tz=dt.timezone(offset=dt.timedelta(
                            hours=-5))).replace(microsecond=0).isoformat()
                        print(str(now), 'Error '+str(e) +' con POST y ' + ticker)
                        if i=="742390776":
                            message.send(str(now)+ 'Error '+str(e) +' con POST y ' + ticker)
                sleep(60)

        return mensaje

    @app.route('/users_crud', methods=['POST'])
    def files():
        # {"crud":"crud","user":"user","key":"lajfo","secret":"iajdm"}
        if request.method == 'POST':
            mensaje = ''
            reception = request.json
            security = Security()
            key = security.decrypt_api(reception['key'])  # reception['key']
            secret = security.decrypt_api(
                reception['secret'])  # reception['secret']
            if reception['crud'] == "create" or reception['crud'] == "update":
                with open('users.json') as json_file:
                    users_post = load(json_file)
                    users_post[reception['user']] = {'key': key,'secret': secret}
                mensaje = 'create sucessfully'
            if reception['crud'] == "delete":
                with open('users.json') as json_file:
                    users_post = load(json_file)
                    users_post.pop(reception['user'])
                mensaje = 'delete sucessfully'
            with open("users.json", "w") as write_file:
                dump(users_post, write_file, indent=4, separators=(',', ': '))
            with open('users.json') as json_file:
                    users_json = load(json_file)
                    update.users = (list(users_json.keys()))
            return mensaje

    #app.run(host='localhost', port=8080)
    serve(app, host='0.0.0.0', port=80, url_scheme='https')
# ----------json recepción
'''
crud
{"crud":"crud","user":"user","key":"lajfo","secret":"iajdm"}
'''

'''
Envio del dato desde el cliente, de esta manera

"{"cod":"techmasters","order":"{{strategy.order.action}}","position":"{{strategy.order.alert_message}}","ticker":"{{ticker}}","price":"{{close}}","leverage":"{{strategy.order.comment}}"}"
'''
