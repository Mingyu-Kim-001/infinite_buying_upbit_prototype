# API로 업비트 서버와 연결
def access_upbit(key_file):
    try:
        with open(key_file, "r") as f:
            lines = f.readlines()
            access_key = lines[0].rstrip()
            secret_key = lines[1].rstrip()
    except:
        error_message = "키 파일이 없습니다."
        print(error_message)
        sys.exit()
    upbit = pyupbit.Upbit(access_key, secret_key)
    check_access = upbit.get_balances()
    if "error" in check_access:
        error_message = check_access["error"]["message"]
        print(error_message)
        sys.exit()
    print("업비트와 연결되었습니다.")
    return upbit

