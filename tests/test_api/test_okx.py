from app.api.okx import get_okx_option_underlyings


class TestOKXApi:
    @staticmethod
    def test_get_okx_option_underlyings():
        expected = ["BTC-USD", "ETH-USD"]
        result = get_okx_option_underlyings()
        assert result == expected
