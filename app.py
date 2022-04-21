#modules-----------------------------
import imaplib,requests
from msilib.schema import Class
import email
from json import load, loads
from time import sleep
from binance.client import Client
from flask import Flask, request, Response, render_template
#--------------------
#clases-----------------------
class Webhook:
    app = Flask(__name__)
    def __init__(self,host:str,port:int) -> None:
        self.host=host
        self.port=port
        self.app.run(host=host,port=port)
    @app.route('/')
    def main():
        print("Llegaste")
        return render_template('main.html')

    @app.route('/webhook', methods=['POST'])
    def webhook():
        if request.method == 'POST':
            print("Data received from Webhook is: ", request.json)
            return "Webhook received!"

if __name__=="__main__":
    Webhook(host='127.0.0.1', port=8000)