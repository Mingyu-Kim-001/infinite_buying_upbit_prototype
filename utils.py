# API로 업비트 서버와 연결
import sys
import pyupbit
def access_upbit(access_key, secret_key):
    upbit = pyupbit.Upbit(access_key, secret_key)
    check_access = upbit.get_balances()
    if "error" in check_access:
        error_message = check_access["error"]["message"]
        print(error_message)
        sys.exit()
    print("업비트와 연결되었습니다.")
    return upbit

