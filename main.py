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
    infinite_buying = {}
    big_period = 1440 // 2  # 8시간을 주기로
    small_period = 10  # 10분마다 체크

    infinite_buying["KRW-DOT"] = Infinite_buying(buying_per_day_per_coin=10100,
                                                 coin="KRW-DOT",
                                                 upbit_api=upbit,
                                                 slack=my_slack_bot,
                                                 sell_threshold=1.15,
                                                 verbose=1)

    tried = 2
    while True:
        print("-------------------------------------------------------------------------------------------")
        print(tried, ":", datetime.datetime.now())
        print("")
        if tried % (big_period // small_period) == 0:
            print("batch_per_day")
            for coin in infinite_buying:
                infinite_buying[coin].batch_per_day()
                print(infinite_buying[coin].current_data)
            tried = 0
        else:
            for coin in infinite_buying:
                infinite_buying[coin].check_periodically(big_period, small_period)
        time.sleep(small_period * 60)
        tried += 1
