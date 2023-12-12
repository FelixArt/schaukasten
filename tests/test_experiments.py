import arrow



def test_arrow_construction():
    arr = arrow.get(2019,10,12)
    arr2 = arrow.get(arr)

    arr3 = arrow.get(arr2.datetime)


def test_arrow_factories():
    arr = arrow.now().floor("week")
    arr2 = arrow.now().ceil("week")
    # must fail. as ceil is end of week ie here is a difference of 1 utc unit
    assert arr.shift(weeks=1) == arr2