import ccxt
import time
import datetime
import pandas as pd
import math
import telegram
from telegram.ext import Updater, CommandHandler


# 텔레그램 함수
def start(update, context):
    global onoff
    if onoff:
        context.bot.sendMessage(chat_id=update.effective_chat.id,
                                text='[프로그램 동작 알림]\n' +
                                     '----------------------------------------\n' +
                                     '프로그램이 이미 실행중입니다.'
                                )
    else:
        onoff = True
        context.bot.sendMessage(chat_id=update.effective_chat.id,
                                text='[프로그램 동작 알림]\n' +
                                     '----------------------------------------\n' +
                                     '프로그램을 시작합니다.'
                                )

def stop(update, context):
    global onoff
    if onoff:
        onoff = False
        context.bot.sendMessage(chat_id=update.effective_chat.id,
                                text='[프로그램 동작 알림]\n' +
                                     '----------------------------------------\n' +
                                     '프로그램을 종료합니다.'
                                )
    else:
        context.bot.sendMessage(chat_id=update.effective_chat.id,
                                text='[프로그램 동작 알림]\n' +
                                     '----------------------------------------\n' +
                                     '프로그램이 이미 종료되었습니다.'
                                )

def get_balance(update, context):
    balance = binance.fetch_balance()
    usdt = balance['total']['USDT']
    btc = balance['total']['BTC']
    context.bot.sendMessage(chat_id=update.effective_chat.id,
                            text= '[잔고 조회 알림]\n' +
                                  '----------------------------------------\n' +
                                  'USDT: ' + str(round(usdt, 4)) + '\n'
                                  'BTC: ' + str(round(btc, 4))
                            )

def get_profit(update, context):
    balance = binance.fetch_balance()
    current_balance = balance['total']['USDT']

    total_profit = current_balance - initial_balance
    total_Roi = (total_profit / initial_balance) * 100

    context.bot.sendMessage(chat_id=update.effective_chat.id,
                            text='[수익 조회 알림]\n' +
                                 '----------------------------------------\n' +
                                 'Initial Balance: ' + str(round(initial_balance, 4)) + ' USDT' + '\n' +
                                 'Current Balance: ' + str(round(current_balance, 4)) + ' USDT' + '\n' +
                                 '----------------------------------------\n' +
                                 'Total Profit: ' + str(round(total_profit, 4)) + ' USDT' + '\n' +
                                 'Total Roi: ' + str(round(total_Roi, 2)) + '%'
                            )

def enter_info(order):
    symbol = order['symbol']
    if order['info']['side'] == 'BUY':
        side = 'Long'
    else:
        side = 'Short'
    time = str(datetime.datetime.fromtimestamp(math.floor(int(order['info']['updateTime']) / 1000)))
    price = order['average']
    amount = order['amount']
    lev = int(leverage['leverage'])
    enter_cost = order['cost'] / lev

    global enter_price
    enter_price = price

    bot.sendMessage(chat_id=id,
                    text='[포지션 진입 알림]\n' +
                         '----------------------------------------\n' +
                         'Symbol: ' + symbol + '\n' +
                         'Side: ' + side + '\n' +
                         'Time: ' + time + '\n' +
                         'Price: ' + str(price) + ' USDT' + '\n' +
                         'Amount: ' + str(amount) + '\n' +
                         'Enter Cost: ' + str(enter_cost) + ' USDT' + '\n' +
                         'Leverage: ' + str(lev) + 'x'
                    )

def exit_info(order, enter_price):
    symbol = order['symbol']
    if order['info']['side'] == 'SELL':
        side = 'Long'
    else:
        side = 'Short'
    time = str(datetime.datetime.fromtimestamp(math.floor(int(order['info']['updateTime']) / 1000)))
    exit_price = order['average']
    amount = order['amount']
    lev = int(leverage['leverage'])
    enter_cost = order['cost'] / lev

    if side == 'SELL':
        profit = (exit_price - enter_price - (exit_price + enter_price) * fee) * amount
    else:
        profit = (enter_price - exit_price - (exit_price + enter_price) * fee) * amount

    Roi = profit / (enter_price * amount / lev)

    balance = binance.fetch_balance()
    usdt = balance['total']['USDT']

    bot.sendMessage(chat_id=id,
                    text='[포지션 종료 알림]\n' +
                         '----------------------------------------\n' +
                         'Symbol: ' + symbol + '\n' +
                         'Side: ' + side + '\n' +
                         'Time: ' + time + '\n' +
                         'Price: ' + str(exit_price) + ' USDT' + '\n' +
                         'Amount: ' + str(amount) + '\n' +
                         'Enter Cost: ' + str(enter_cost) + ' USDT' + '\n' +
                         'Leverage: ' + str(lev) + ' x' + '\n' +
                         '----------------------------------------\n' +
                         'Profit: ' + str(round(profit, 4)) + ' USDT' + '\n' +
                         'Roi: ' + str(round(Roi * 100, 2)) + '%' + '\n' +
                         'Balance: ' + str(round(usdt, 4)) + ' USDT'
                    )

#####

def cal_target(exchange, symbol):
    # 거래소에서 symbol에 대한 ohlcv 일봉 얻기
    symbol_ohlcv = exchange.fetch_ohlcv(
        symbol=symbol,
        timeframe='1d',
        since=None,
        limit=10
    )

    #일봉 데이터를 데이터프레임 객체로 변환
    df = pd.DataFrame(
        data=symbol_ohlcv,
        columns=['datetime', 'open', 'high', 'low', 'close', 'volume']
    )
    df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
    df.set_index('datetime', inplace=True)

    #전일 데이터와 금일 데이터로 목표가 계산
    yesterday = df.iloc[-2]
    today = df.iloc[-1]
    long_target = today['open'] + (yesterday['high'] - yesterday['low']) * 0.5
    short_target = today['open'] - (yesterday['high'] - yesterday['low']) * 0.5
    return long_target, short_target


#수량 계산
def cal_amount(usdt_balance, cur_price, portion):
    usdt_trade = usdt_balance * portion
    amount = math.floor((usdt_trade * 1000000) / cur_price) / 1000000
    return amount


def enter_position(exchange, symbol, cur_price, long_target, short_target, amount, position):
    if cur_price > long_target:
        position['type'] = 'long'
        position['amount'] = amount
        enter_order = exchange.create_market_buy_order(symbol=symbol, amount=amount)
    elif cur_price < short_target:
        position['type'] = 'short'
        position['amount'] = amount
        enter_order = exchange.create_market_sell_order(symbol=symbol, amount=amount)

    enter_info(enter_order)


def exit_position(exchange, symbol, position):
    amount = position['amount']
    if position['type'] == 'long':
        exit_order = exchange.create_market_sell_order(symbol=symbol, amount=amount)
        position['type'] = None
    elif position['type'] == 'short':
        exit_order = exchange.create_market_buy_order(symbol=symbol, amount=amount)
        position['type'] = None

    exit_info(exit_order, enter_price)





# API 키 읽기
api_key = ''
secret = ''


# 텔레그램
token = ''
id = ''

updater = Updater(token=token, use_context=True)
dispatcher = updater.dispatcher

bot = telegram.Bot(token=token)


# 텔레그램 명령어
get_balance_handler = CommandHandler('balance', get_balance)
dispatcher.add_handler(get_balance_handler)

start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)

stop_handler = CommandHandler('stop', stop)
dispatcher.add_handler(stop_handler)

get_profit_handler = CommandHandler('profit', get_profit)
dispatcher.add_handler(get_profit_handler)

updater.start_polling()


# 바이낸스 객체 생성
binance = ccxt.binance(config={
    'apiKey': api_key,
    'secret': secret,
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future'
    }
})

op_mode = False
onoff = False

fee = 0.0004
enter_price = 0


# 잔고 조회
balance = binance.fetch_balance()
usdt = balance['total']['USDT']

initial_balance = balance['total']['USDT']

leverage = binance.set_leverage(
    leverage=1,
    symbol='BTC/USDT'
)

symbol = 'BTC/USDT'
long_target, short_target = cal_target(binance, symbol)


position = {
    'type': None,
    'amount': 0
}

while True:
    if onoff:
        try:
            # time
            now = datetime.datetime.now()

            #position 종료
            if now.hour == 8 and now.minute == 50 and (0 <= now.second < 10):
                if op_mode and position['type'] is not None:
                    exit_position(binance, symbol, position)
                    op_mode = False

            # 목표가 갱신 09:00:20 ~ 09:00:30
            if now.hour == 9 and now.minute == 0 and (20 <= now.second < 30):
                long_target, short_target = cal_target(binance, symbol)

                op_mode = True
                time.sleep(10)

            # 현재가, 구매 가능 수량
            btc = binance.fetch_ticker(symbol= symbol)
            cur_price = btc['last']
            amount = cal_amount(usdt, cur_price, 0.1)

            if op_mode and position['type'] is None:
                enter_position(binance, symbol, cur_price, long_target, short_target, amount, position)

            time.sleep(1)

        except Exception as e:
            print(e)
            time.sleep(1)
