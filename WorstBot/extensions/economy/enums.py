from enum import StrEnum


class Transactions(StrEnum):
    deposit = "DEPOSIT"
    withdraw = "WITHDRAW"
    ascend = "ASCEND"
    give = "GIVE"
    receive = "RECEIVE"
    gamble = "GAMBLE"
    work = "WORK"
    conversion_rate = "CONVERSION_RATE"
