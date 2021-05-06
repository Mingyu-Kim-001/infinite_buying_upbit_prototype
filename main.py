# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.

import sys
import pyupbit
import time
import pickle
import datetime
from collections import defaultdict


class Infinite_buying:

    def __init__(self,
                 buying_per_day_per_coin,
                 coins=["KRW-BTC"],
                 reset_period=40,
                 sell_threshold=1.1,
                 check_period=5,
                 key_file="key.txt",
                 verbose=0):

        self.buying_per_day_per_coin = buying_per_day_per_coin
        # 절반씩 나눠서 구매하는 양. 하루에 최소 이 양은 구매하게 된다.
        self.minimum_buying_amount = self.buying_per_day_per_coin // 2
        self.coins = coins
        self.reset_period = reset_period
        self.sell_threshold = sell_threshold
        self.check_period = check_period
        self.upbit = None
        self.verbose = verbose
        self.data_file = "data.pickle"
        self.check_input()
        self.access_upbit(key_file)
        self.current_data = {
            "buy_order_uuid": {},
            "sell_order_uuid": {},
            "bought_first": defaultdict(bool),
            "bought_second": defaultdict(bool),
            "day_count": defaultdict(int),
            "period_count": defaultdict(int),
            "minimum_price": {},
            "balances": {}
        }

    def check_input(self):

        error_message = None

        # 최소주문량 체크
        if not self.buying_per_day_per_coin:
            error_message = "하루 예산(원)을 입력해주시기 바랍니다. 업비트의 최소 주문이 5000원이므로 무한매수법의 하루 예산은 10000원 이상입니다."
        elif type(self.buying_per_day_per_coin) != int:
            error_message = "하루 예산(원)은 숫자로 입력해 주시기 바랍니다."
        elif self.buying_per_day_per_coin < 10000:
            error_message = "하루 예산은 10000원 이상부터입니다."

        if error_message:
            self.dealing_error(error_message)

        # 코인 이름 정합성 체크
        krw_coin_list = pyupbit.get_tickers(fiat="KRW")
        for coin in self.coins:
            if not coin in krw_coin_list:
                error_message = coin + "는 목록에 없는 코인입니다. 주문 가능한 목록은 " + str(krw_coin_list) + "입니다."
                self.dealing_error(error_message)

        # 리셋 주기 정합성 체크
        if type(self.reset_period) != int:
            error_message = "리셋 주기는 숫자로 입력해 주시기 바랍니다."
        elif self.reset_period < 5:
            error_message = "리셋 주기는 5일 이상으로 입력해 주시기 바랍니다."

        if error_message:
            self.dealing_error(error_message)

        # sell_threshold 정합성 체크
        try:
            self.sell_threshold = float(self.sell_threshold)
        except:
            error_message = "sell_threshold는 숫자로 입력해 주시기 바랍니다."
            self.dealing_error(error_message)
        if self.sell_threshold <= 1.0:
            error_message = "sell_threshold는 1보다 큰 수를 입력해 주시기 바랍니다."
            self.dealing_error(error_message)

    def dealing_error(self, error_message):
        print(error_message)
        sys.exit()

    # API로 업비트 서버와 연결
    def access_upbit(self, key_file):
        try:
            with open(key_file, "r") as f:
                lines = f.readlines()
                access_key = lines[0].rstrip()
                secret_key = lines[1].rstrip()
        except:
            error_message = "키 파일이 없습니다."
            self.dealing_error(error_message)
        self.upbit = pyupbit.Upbit(access_key, secret_key)
        check_access = self.upbit.get_balances()
        if "error" in check_access:
            error_message = check_access["error"]["message"]
            self.dealing_error(error_message)

        if self.verbose:
            print("업비트와 연결되었습니다.")

    # 현재상황 데이터 읽어오기
    def get_current_data(self):
        for coin in self.coins:

            # delete old data
            if coin in self.current_data["buy_order_uuid"]:
                self.current_data["buy_order_uuid"].pop(coin)
            if coin in self.current_data["sell_order_uuid"]:
                self.current_data["sell_order_uuid"].pop(coin)

            # put latest data(if exists)
            for order in self.upbit.get_order(coin):
                if order['side'] == 'bid':
                    self.current_data["buy_order_uuid"][coin] = order["uuid"]
                if order['side'] == 'ask':
                    self.current_data["sell_order_uuid"][coin] = order["uuid"]

            # buy_order가 없으면 first를 샀다고 간주.

        # update balances
        balances = self.upbit.get_balances()
        self.current_data["balances"] = {}
        for balance in balances:
            self.current_data["balances"][balance["unit_currency"] + "-" + balance["currency"]] = balance

    #         if self.verbose:
    #             print("current_data--------------------------------------")
    #             for key in self.current_data:
    #                 print(key, self.current_data[key])

    # 호가 단위를 받아옴
    def get_price_unit(self, price):
        """
        업비트의 경우 호가단위가 아래와 같다(21년 4월 21일 기준).
        2,000,000원 이상 : 1,000원
        1,000,000원 이상~2,000,000원 미만 : 500원
        100,000원 이상~1,000,000원 미만 : 50원
        10,000원 이상~100,000원 미만 : 10원
        1,000원 이상~10,000원 : 5원
        1,000원 미만 : 1원
        100원 : 0.1원
        10원 미만 : 0.01원
        """
        if price >= 2000000: return 1000
        if price >= 1000000: return 500
        if price >= 100000: return 50
        if price >= 10000: return 10
        if price >= 1000: return 5
        if price >= 100: return 1
        if price >= 10: return 0.1
        return 0.01

    # 호가 단위에 가격을 맞춘다.
    def set_price_according_to_unit(self, price, round_off=True):
        """
        ex) 호가단위가 5원일시, 매수가격 2552원에 매수주문을 넣지 못한다. 2550원이나 2555로 단위를 맞춰서 주문을 넣어야 됨. 이를 맞춰 주는 함수
        price : 단위를 맞추려는 가격
        round_off : 내림으로 호가를 맞추는지 여부.
        """
        unit = self.get_price_unit(price)
        return int(price / unit) * unit + (0 if round_off else unit)

    # 데이터 기록
    def write_data(self):
        with open(self.data_file, "wb") as f:
            pickle.dump(self.current_data, f)

    # 걸려 있는 매도 주문 취소(남아 있다면)
    def cancel_sell_order(self, coin):
        self.get_current_data()
        if coin in self.current_data["sell_order_uuid"] and self.current_data["sell_order_uuid"][coin] in [order["uuid"]
                                                                                                           for order in
                                                                                                           self.upbit.get_order(
                                                                                                                   coin)]:
            order = self.upbit.cancel_order(self.current_data["sell_order_uuid"][coin])
            if self.verbose:
                print("매도주문취소", order)

    # 일정 비율 이상 수익일 때 전량 매도를 걸어 놓는 함수
    def sell_order_on_threshold(self, coin):

        self.cancel_sell_order(coin)
        time.sleep(1)
        self.get_current_data()
        sell_price = self.set_price_according_to_unit(
            float(self.current_data["balances"][coin]["avg_buy_price"]) * self.sell_threshold)
        sell_quantity = float(self.current_data["balances"][coin]["balance"])
        sell_order = self.upbit.sell_limit_order(coin, sell_price, sell_quantity)
        if "error" in sell_order:
            error_message = sell_order["error"]["message"]
            self.dealing_error(error_message)

        if self.verbose:
            print("전량매도주문 at", sell_price)

    # 걸려 있는 매수 주문 취소
    def cancel_buy_order(self, coin):
        self.get_current_data()
        if coin in self.current_data["buy_order_uuid"] and self.current_data["buy_order_uuid"][coin] in [order["uuid"]
                                                                                                         for order in
                                                                                                         self.upbit.get_order(
                                                                                                             coin)]:
            cancel_order = self.upbit.cancel_order(self.current_data["buy_order_uuid"][coin])
            self.current_data["buy_order_uuid"].pop(coin)
            if self.verbose:
                print("매수주문취소", cancel_order)

    def buy_if_not_concluded(self, coin):
        self.get_current_data()
        # 시장가에 무조건 구매
        if coin in self.current_data["buy_order_uuid"]:
            self.cancel_buy_order(coin)
            time.sleep(0.5)
            buy_order = self.upbit.buy_market_order(coin, self.minimum_buying_amount)
            if self.verbose:
                print("절반 구매", buy_order)

        # 다음을 위한 세팅
        self.current_data["bought_first"][coin] = False

    def batch_per_day(self):
        self.get_current_data()
        for coin in self.coins:
            if self.verbose:
                print(coin)

            # 남아 있는 매도 주문이 걸려 있다면, 취소
            self.cancel_sell_order(coin)

            time.sleep(1)
            self.get_current_data()

            # 매수한 코인이 없다면, 처음부터 시작.
            if not coin in self.current_data["balances"] or self.current_data["balances"][coin]["balance"] + \
                    self.current_data["balances"][coin]["locked"] == 0:
                self.current_data["day_count"][coin] = 0
                self.cancel_buy_order(coin)

                # 절반은 무조건 구매
                buy_order = self.upbit.buy_market_order(coin, self.minimum_buying_amount)
                if self.verbose:
                    print(coin, "첫 시작 :", self.minimum_buying_amount, "원(하루 절반) 구매")
                    print(buy_order)
                time.sleep(2)

            else:

                # 리셋 주기에 도달했을 시 시장가에 전부 매도.
                if self.current_data["day_count"][coin] == self.reset_period:
                    self.get_current_data()
                    sell_quantity = float(self.current_data["balances"][coin]["balance"])
                    sell_order = self.upbit.sell_market_order(coin, sell_quantity)
                    if self.verbose:
                        print("리셋 주기 도달, ", sell_order)
                    self.current_data["day_count"][coin] = 0
                    time.sleep(1)

                # 매수주문 취소하고 시장가에 매수
                print(coin, self.current_data["day_count"][coin], "일차")
                self.buy_if_not_concluded(coin)
                time.sleep(2)

            # 10%에 매도 주문을 걸어 놓음
            self.sell_order_on_threshold(coin)

            # 데이터 업데이트
            self.current_data["day_count"][coin] += 1
            self.current_data["bought_first"][coin] = False
            self.current_data["bought_second"][coin] = False  # 추후에 batch_per_10에서 절반을 구매하기 위해, 구매상태를 false로 변경한다.
            self.current_data["period_count"][coin] = 0

            if self.verbose:
                print("")

    # 술탄의 딸 method
    def buy_first(self, coin, big_period, small_period):
        total_check_count_per_day = big_period // small_period
        see_until = int(total_check_count_per_day / 2.71828)

        # for coin in self.coins:
        self.get_current_data()

        # 술탄의 딸 method
        if self.current_data["period_count"][coin] >= see_until and not self.current_data["bought_first"][coin]:
            self.current_data["buy_order_uuid"][coin] = self.upbit.buy_limit_order(coin,
                                                                                   self.current_data["minimum_price"][
                                                                                       coin],
                                                                                   self.minimum_buying_amount /
                                                                                   self.current_data["minimum_price"][
                                                                                       coin])
            self.current_data["bought_first"][coin] = True
            if self.verbose:
                print(coin + "을 " + str(self.current_data["minimum_price"][coin]) + "에 매수 주문을 걸었습니다.")

        else:
            if self.current_data["period_count"][coin] == 0:
                self.current_data["minimum_price"][coin] = float("inf")
            self.current_data["minimum_price"][coin] = min(self.current_data["minimum_price"][coin],
                                                           pyupbit.get_current_price(coin))
            self.current_data["period_count"][coin] += 1
            if self.verbose and not self.current_data["bought_first"][coin]:
                print(coin, "최소가격", self.current_data["minimum_price"][coin])

    # 평균단가 이하에 절반을 구입하기
    def buy_second(self, coin):

        # for coin in self.coins:

        # 평단보다 아래에 이미 구매했거나, 현재 구매되어 있는 코인이 없다면 종료.
        self.get_current_data()
        if self.current_data["bought_second"][coin] or not coin in self.current_data["balances"]:
            if self.current_data["bought_second"][coin]:
                print(coin + "은 이미 평균단가 이하에 절반치를 구매하였습니다.\n")
            else:
                print(coin, "잔고가 현재 없습니다.\n")
            # continue
            return

        # 현재가가 평단 아래일 경우 (시장가로 주문할 때 시차로 인해 평단보다 높게 구매하는 일이 발생할 수 있기 때문에, 4*호가단위의 여유분을 둔다).
        self.get_current_data()
        avg_price = round(float(self.current_data["balances"][coin]["avg_buy_price"]))
        price_unit = self.get_price_unit(avg_price)

        # 여유분을 코인 규모 따라 다르게
        yeyoo_dict = {5: 2, 10: 3, 50: 4, 500: 6, 1000: 8}
        yeyoo = yeyoo_dict[price_unit]

        current_price = pyupbit.get_current_price(coin)
        if current_price < avg_price - yeyoo * price_unit:

            buy_order = self.upbit.buy_market_order(coin, self.minimum_buying_amount)

            # 구매가 반영되기까지 잠시 기다림
            time.sleep(2)

            if self.verbose:
                print(coin + " 현재가가 평균단가", avg_price, "보다 낮기 때문에 구매하였습니다.", buy_order)

            # 10%에 매도 주문을 새로 걸어 놓음
            self.sell_order_on_threshold(coin)

            # 오늘은 더 이상 사지 않도록 표시
            self.current_data["bought_second"][coin] = True


        elif self.verbose:
            print(coin + "은 현재 가격", current_price, "이 평균단가", avg_price, "이상입니다.")

        if self.verbose:
            print(coin, "period_count", self.current_data["period_count"][coin])
            print("")

    def stop_loss(self, coin, loss_rate=0.1):
        self.get_current_data()
        if not coin in self.current_data["balances"]:
            return
        avg_price = round(float(self.current_data["balances"][coin]["avg_buy_price"]))
        current_price = pyupbit.get_current_price(coin)

        # 10%이상 하락시 손절
        if current_price < avg_price * (1 - loss_rate):
            self.cancel_sell_order(coin)
            time.sleep(1)
            self.get_current_data()
            sell_quantity = float(self.current_data["balances"][coin]["balance"])
            sell_order = self.upbit.sell_market_order(coin, sell_quantity)

            if self.verbose:
                print(coin, "손절", sell_order)

        elif self.verbose:
            print(coin, "현재가격", current_price, "가 평균단가의", round(100 * loss_rate), "% 손절라인",
                  round(avg_price * (1 - loss_rate)), "이상입니다. ")

    def check_periodically(self, big_period, small_period):
        for coin in self.coins:
            self.stop_loss(coin)
            self.buy_first(coin, big_period, small_period)
            self.buy_second(coin)

    if __name__ == '__main__':

        infinite_buying2 = Infinite_buying(buying_per_day_per_coin=20000,
                                           coins=["KRW-BTC", "KRW-XRP", "KRW-ETH", "KRW-BCH", "KRW-ETC", "KRW-BTG"],
                                           sell_threshold=1.15,
                                           verbose=1)

        big_period = 1440 // 4  # 하루에 총 4번
        small_period = 6  # 6분마다 체크
        cur_period = 0전

        while True:
            print("-------------------------------------------------------------------------------------------")
            print(cur_period, ":", datetime.datetime.now())
            print("")

            if cur_period % (big_period // small_period) == 0:
                print("batch_per_day")
                infinite_buying2.batch_per_day()
                print(infinite_buying2.current_data)
                tried = 0
            else:
                infinite_buying2.check_periodically(big_period, small_period)

            time.sleep(small_period * 60 - 12)
            cur_period += 1

