# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.
import os
import sys
import pyupbit
import time
import pickle
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
        self.balances_dict = {}
        self.verbose = verbose
        self.data_file = "data.pickle"
        self.current_data = None
        self.check_input()
        self.get_current_data()
        self.access_upbit(key_file)
        self.update_balances()


    def check_input(self):

        error_message = None

        #최소주문량 체크
        if not self.buying_per_day_per_coin:
            error_message = "하루 예산(원)을 입력해주시기 바랍니다. 업비트의 최소 주문이 5000원이므로 무한매수법의 하루 예산은 10000원 이상입니다."
        elif type(self.buying_per_day_per_coin) != int:
            error_message = "하루 예산(원)은 숫자로 입력해 주시기 바랍니다."
        elif self.buying_per_day_per_coin < 10000:
            error_message = "하루 예산은 10000원 이상부터입니다."

        if error_message:
            self.dealing_error(error_message)

        #코인 이름 정합성 체크
        krw_coin_list = pyupbit.get_tickers(fiat="KRW")
        for coin in self.coins:
            if not coin in krw_coin_list:
                error_message = coin + "는 목록에 없는 코인입니다. 주문 가능한 목록은 " + str(krw_coin_list) + "입니다."
                self.dealing_error(error_message)

        #리셋 주기 정합성 체크
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


    def dealing_error(self,error_message):
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

    # 잔고 업데이트
    def update_balances(self):
        balances = self.upbit.get_balances()
        self.balances = {}
        for balance in balances:
            self.balances_dict[balance["unit_currency"] + "-" + balance["currency"]] = balance
        if self.verbose:
            print("balance", self.balances_dict)

    # 현재상황 데이터 읽어오기
    def get_current_data(self):

        try:
            with open(self.data_file, "rb") as fr:
                self.current_data = pickle.load(fr)

        except:
            self.current_data = {
                "buy_order_uuid": {},
                "sell_order_uuid": {},
                "bought_second": defaultdict(bool),
                "day_count": defaultdict(int),
                "period_count": defaultdict(int),
                "minimum_price": {}
            }

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
        if coin in self.current_data["sell_order_uuid"] and self.current_data["sell_order_uuid"][coin] in [order["uuid"] for order in self.upbit.get_order(coin)]:
            order = self.upbit.cancel_order(self.current_data["sell_order_uuid"][coin])
            if self.verbose:
                print("매도주문취소", order)
            self.current_data["sell_order_uuid"].pop(coin)

    # 일정 비율 이상 수익일 때 전량 매도를 걸어 놓는 함수
    def sell_order_on_threshold(self, coin):
        self.update_balances()
        self.cancel_sell_order(coin)
        time.sleep(3)
        print(float(self.balances_dict[coin]["avg_buy_price"]) * self.sell_threshold)
        sell_price = self.set_price_according_to_unit(float(self.balances_dict[coin]["avg_buy_price"]) * self.sell_threshold)
        self.current_data["sell_order_uuid"][coin] = self.upbit.sell_limit_order(coin, sell_price, float(self.balances_dict[coin]["balance"]))["uuid"]
        if self.verbose:
            print("전량매도주문 at", sell_price)

    # 걸려 있는 매수 주문 취소 후
    def cancel_and_buy_if_not_concluded(self, coin):
        self.update_balances()
        if self.upbit.get_order(coin) and self.current_data["buy_order_uuid"] in [order["uuid"] for order in
                                                                                   self.upbit.get_order(coin)]:
            order = self.upbit.cancel_order(self.current_data["buy_order_uuid"])
            if self.verbose:
                print("매수주문취소", order)
            self.current_data["buy_order_uuid"].pop(coin)

            # 시장가에 무조건 구매
            buy_order = self.upbit.buy_market_order(coin,self.minimum_buying_amount)
            if self.verbose:
                print("절반 구매")
                print(buy_order)

    def batch_per_day(self):

        buy_order_uuid, sell_order_uuid, bought_under_avg_price, day_count, period_count, _ = self.current_data.values()
        self.update_balances()

        for coin in self.coins:
            if self.verbose:
                print(coin)

            # 매수한 코인이 없다면, 처음부터 시작.
            if not coin in self.balances_dict:
                day_count[coin] = 0

                # 절반은 무조건 구매
                buy_order = self.upbit.buy_market_order(coin,self.minimum_buying_amount)
                buy_order_uuid[coin] = buy_order["uuid"]
                period_count[coin] = 0
                if self.verbose:
                    print("절반 구매")
                    print(buy_order)

            # 리셋 주기에 도달했을 시 시장가에 전부 매도.
            elif day_count[coin] == self.reset_period:
                self.upbit.sell_market_order(coin, float(self.balances_dict[coin]["balance"]))
                day_count[coin] = 0

            else:
                #걸려 있는 매수주문 취소(남아 있다면)
                self.cancel_and_buy_if_not_concluded(coin)
                period_count[coin] = 0

            # 구매가 반영되기까지 잠시 기다림
            time.sleep(2)

            # 10%에 매도 주문을 걸어 놓음
            self.sell_order_on_threshold(coin)

            # 데이터 업데이트
            day_count[coin] += 1
            bought_under_avg_price[coin] = False  # 추후에 batch_per_10에서 절반을 구매하기 위해, 구매상태를 false로 변경한다.

        self.current_data = {
            "buy_order_uuid": buy_order_uuid,
            "sell_order_uuid": sell_order_uuid,
            "bought_under_avg_price": bought_under_avg_price,
            "day_count": day_count,
            "period_count": period_count,
            "minimum_price": {}
        }
        self.write_data()

    def check_price_periodically(self):

        buy_order_uuid, sell_order_uuid, bought_under_avg_price, day_count, period_count, minimum_price = self.current_data.values()
        self.update_balances()

        total_check_count_per_day = 24 * 60 // self.check_period
        see_until = int(total_check_count_per_day / 2.71828)

        for coin in self.coins:

            # 평단보다 아래에 이미 구매했거나, 현재 구매되어 있는 코인이 없다면 종료.
            if bought_under_avg_price[coin] or not coin in self.balances_dict:
                if bought_under_avg_price[coin]:
                    print(coin + "은 이미 평균단가 이하에 절반치를 구매하였습니다.")
                else:
                    print(coin + "잔고가 현재 없습니다.")
                continue

            # 현재가가 평단 아래일 경우 (시장가로 주문할 때 시차로 인해 평단보다 높게 구매하는 일이 발생할 수 있기 때문에, 4*호가단위의 여유분을 둔다).
            avg_price = round(float(self.balances_dict[coin]["avg_buy_price"]))
            price_unit = self.get_price_unit(avg_price)
            yeyoo = 4 if coin != "KRW-BTC" else 8
            if pyupbit.get_current_price(coin) < avg_price - yeyoo * price_unit:

                self.upbit.buy_market_order(coin, self.minimum_buying_amount)

                # 구매가 반영되기까지 잠시 기다림
                time.sleep(2)

                # 10%에 매도 주문을 새로 걸어 놓음
                self.sell_order_on_threshold(coin)

                # 오늘은 더 이상 사지 않도록 표시
                bought_under_avg_price[coin] = True

                if self.verbose:
                    print(coin + " 구매하였습니다.")

            elif self.verbose:
                print(coin + "은 현재 가격이 평균단가 이상입니다.")


            if period_count[coin] >= see_until and not buy_order_uuid[coin]:
                buy_order_uuid[coin] = self.upbit.buy_limit_order(coin,minimum_price[coin],self.minimum_buying_amount/minimum_price[coin])
                if self.verbose:
                    print(coin + "을 " + str(minimum_price[coin]) + "에 주문을 걸었습니다.")

            else:
                if not coin in minimum_price:
                    minimum_price[coin] = float("inf")
                minimum_price[coin] = min(minimum_price[coin],pyupbit.get_current_price(coin))
                period_count[coin] += 1
            print(coin, "period_count", period_count[coin])

        self.current_data = {
            "buy_order_uuid": buy_order_uuid,
            "sell_order_uuid": sell_order_uuid,
            "bought_under_avg_price": bought_under_avg_price,
            "day_count": day_count,
            "period_count": period_count,
            "minimum_price": minimum_price
        }
        self.write_data()



if __name__ == '__main__':

    infinite_buying = Infinite_buying(buying_per_day_per_coin = 10100,
                                      coins=["KRW-BTC","KRW-XRP"],
                                      verbose=1)


