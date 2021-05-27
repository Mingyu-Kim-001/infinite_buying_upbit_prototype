# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.

import sys
import time
import datetime
import utils
from slack_message import Slack_bot
from infinite_buying import Infinite_buying


if __name__ == '__main__':
    key_file = "key.txt"

    try:
        with open(key_file, "r") as f:
            lines = f.readlines()
            access_key = lines[0].rstrip()
            secret_key = lines[1].rstrip()
    except:
        error_message = "키 파일이 없습니다."
        print(error_message)
        sys.exit()

    upbit = utils.access_upbit(access_key, secret_key)

    slack_token_file = "slack_token.txt"
    try:
        with open(slack_token_file, "r") as f:
            lines = f.readlines()
            my_token = lines[0].rstrip()
            my_channel = lines[1].rstrip()
    except:
        error_message = "슬랙 토큰 파일이 없습니다."
        print(error_message)
        sys.exit()

    my_slack_bot = Slack_bot(my_token,my_channel)
    big_period = 1440 # 24시간마다
    small_period = 10  # 10분마다 체크

    infinite_buying = {}


    infinite_buying["KRW-BTC"] = Infinite_buying(buying_per_day_per_coin=10100,
                                                 coin="KRW-BTC",
                                                 upbit_api=upbit,
                                                 slack=my_slack_bot,
                                                 sell_threshold=1.15,
                                                 reset_period=50,
                                                 verbose=1)

    infinite_buying["KRW-EOS"] = Infinite_buying(buying_per_day_per_coin=10100,
                                                 coin="KRW-EOS",
                                                 upbit_api=upbit,
                                                 slack=my_slack_bot,
                                                 sell_threshold=1.15,
                                                 reset_period=50,
                                                 verbose=1)

    infinite_buying["KRW-ETH"] = Infinite_buying(buying_per_day_per_coin=10100,
                                                 coin="KRW-ETH",
                                                 upbit_api=upbit,
                                                 slack=my_slack_bot,
                                                 sell_threshold=1.15,
                                                 verbose=1)

    infinite_buying["KRW-BCH"] = Infinite_buying(buying_per_day_per_coin=10100,
                                                 coin="KRW-BCH",
                                                 upbit_api=upbit,
                                                 slack=my_slack_bot,
                                                 sell_threshold=1.15,
                                                 reset_period=50,
                                                 verbose=1)

    infinite_buying["KRW-ETC"] = Infinite_buying(buying_per_day_per_coin=10100,
                                                 coin="KRW-ETC",
                                                 upbit_api=upbit,
                                                 slack=my_slack_bot,
                                                 sell_threshold=1.15,
                                                 reset_period=50,
                                                 verbose=1)


    period_count = 91
    while True:
        my_slack_bot.post_message("-------------------------------------------------------------------------------------------")
        my_slack_bot.post_message(period_count, ":", datetime.datetime.now(),"\n")
        if period_count % (big_period // small_period) == 0:
            my_slack_bot.post_message("batch_per_day")
            for coin in infinite_buying:
                infinite_buying[coin].batch_per_day()
                my_slack_bot.post_message(infinite_buying[coin].current_data)
            tried = 0
        else:
            for coin in infinite_buying:
                infinite_buying[coin].check_periodically(big_period, small_period)
        time.sleep(small_period * 60)
        period_count += 1
