# modules-----------------------------
from threading import Thread
from json import load
from time import sleep
from binance.client import Client
from flask import Flask, request, render_template
# --------------------
# clases-----------------------

#clase cliente
class Cliente:
    datos = {'side': 'BUY', 'id': 5354530132, 'symbol': 'BTCBUSD', 'quantity': 0.001,
             'price': 40542.5, 'take_l': 0.009, 'take_s': 0.017, 'stop': 0.03, 'leverage': 5}
    with open('data.json') as json_file:
        claves = load(json_file)
    client = Client(claves['shercan']['key'], claves['shercan']['secret'])
    def __init__(self) -> None:
        pass

#ordenes de compra y venta
class Ordenes:
    cliente=Cliente()
    def __init__(self) -> None:
        pass
    def create_order(self,position:str,symbol:str):
        self.cliente.datos['symbol']=symbol.replace('PERP','')
        balance=self.cliente.client.futures_account_balance()
        balance=float([x['balance'] for x in balance if x['asset']=='BUSD'][0])/2
    #print(balance)
        try:
            self.cliente.client.futures_cancel_all_open_orders(symbol=symbol)
        except:
            pass
        order=self.cliente.client.futures_create_order(
            symbol=self.cliente.datos['symbol'], 
            side=position, 
            type='MARKET', 
            quantity=str((balance*30)/float(
                self.cliente.client.futures_symbol_ticker(
                    symbol=self.cliente.datos['symbol'])['price']))[0:5]
            )
        self.cliente.datos['side']=position
        self.cliente.datos['quantity']=order['origQty']
        self.cliente.datos['id']=order['orderId']
        #print(datos)
        order_exe=Thread(target= self.create_order_exe, args=(self.cliente.datos['id'],'create',))
        order_exe.start()    
        #print(order)
    def stop_loss(self,position:str):
        #print(position)
        if position=='BUY':
            pos='SELL'
            stop=round(float(self.cliente.datos['price'])*(1.002-self.cliente.datos['stop']),1)
            price=round(float(self.cliente.datos['price'])*(1-self.cliente.datos['stop']),1)
        elif position=='SELL':
            pos='BUY'
            stop=round(float(self.cliente.datos['price'])*(0.998+self.cliente.datos['stop']),1)
            price=round(float(self.cliente.datos['price'])*(1+self.cliente.datos['stop']),1)
        #print(stop,price,pos,datos)
        stop=self.cliente.client.futures_create_order(
            symbol=self.cliente.datos['symbol'], 
            side=pos, 
            type='STOP',
            quantity=self.cliente.datos['quantity'],
            price=price,
            stopPrice=stop,
            reduceOnly=True
            )
        #print(stop)
        order_exe=Thread(target= self.create_order_exe, args=(stop['orderId'],'stop',))
        order_exe.start()    
    def take_profit(self,position:str):
        if position=='BUY':
            pos='SELL'
            stop=round(float(self.cliente.datos['price'])*(0.998+self.cliente.datos['take_l']),1)
            price=round(float(self.cliente.datos['price'])*(1+self.cliente.datos['take_l']),1)
        elif position=='SELL':
            pos='BUY'
            stop=round(float(self.cliente.datos['price'])*(1.002-self.cliente.datos['take_s']),1)
            price=round(float(self.cliente.datos['price'])*(1-self.cliente.datos['take_s']),1)
        take=self.cliente.client.futures_create_order(
            symbol=self.cliente.datos['symbol'],
            side=pos,
            type='TAKE_PROFIT',
            quantity=self.cliente.datos['quantity'],
            price=price,
            stopPrice=stop,
            reduceOnly=True
            )
        #print(take)
        order_exe=Thread(target=self.create_order_exe, args=(take['orderId'],'take',))
        order_exe.start()    
    def create_order_exe(self,order_id,intro:str):
        while True:
            order=self.cliente.client.futures_get_order(orderId=order_id,symbol=self.cliente.datos['symbol'])
            print(intro,order['status'],order['orderId'])
            if order['status']=='FILLED' and intro=='create':
                self.cliente.datos['price']=order['avgPrice']
                self.stop_loss(self.cliente.datos['side'])
                self.take_profit(self.cliente.datos['side'])
                break            
            if (order['status']=='FILLED' and intro=='stop') or order['status']=='CANCELED':
                self.cliente.client.futures_cancel_all_open_orders(symbol=self.cliente.datos['symbol'])
                break
            if (order['status']=='FILLED' and intro=='take') or order['status']=='CANCELED':
                self.cliente.client.futures_cancel_all_open_orders(self.cliente.datos['symbol'])
                break
            sleep(2)
    def prueba(self):
        print('Entro bien')

#inicio de programa
if __name__ == "__main__":
    app = Flask(__name__)
    orders=Ordenes()

    @app.route('/')
    def main():
        print("Llegaste")
        return render_template('main.html')

    @app.route('/webhook', methods=['POST'])
    def webhook():
        mensaje='nothing'
        if request.method == 'POST':
            recive = request.json
            if recive['position']=='1' and recive['order']=='buy':
                    print('long')
                    #self.orders.create_order('BUY',recive['ticker'])
                    orders.prueba()
                    mensaje='Se realizo una orden en long'
            elif recive['position']=='-1' and recive['order']=='sell':
                    print('short')
                    #self.orders.create_order('SELL',recive['ticker'])
                    orders.prueba()
                    mensaje='Se realizo una orden en short'
            return mensaje
    app.run(host='127.0.0.1', port=80)
#----------json recepción
'''
Envio del dato desde el cliente, de esta manera
{"order":"{{strategy.order.action}}","position":"{{plot_15}}","ticker":"{{ticker}}"}
'''