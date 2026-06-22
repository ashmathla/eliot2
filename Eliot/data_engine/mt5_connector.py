# data_engine/mt5_connector.py

import MetaTrader5 as mt5


def connect_mt5():

    if mt5.initialize():
        print("MT5 Connected")
        return True

    print("MT5 Connection Failed")
    return False


def shutdown_mt5():
    mt5.shutdown()