"""Private-market price feed validation without network requests."""

from unittest.mock import Mock, patch

import pytest
import requests
from maestro.testing import MaestroTest

from .. import finance


def test_private_share_price_uses_chart_metadata(mt: MaestroTest) -> None:
    response = Mock()
    response.json.return_value = {
        "chart": {"result": [{"meta": {"regularMarketPrice": 123.45}, "indicators": {}}]}
    }
    with patch.object(finance.requests, "get", return_value=response) as get:
        assert finance.get_private_share_price("EXAMPLE.PVT") == 123.45
    assert get.call_args.args[0].endswith("/EXAMPLE.PVT")
    assert get.call_args.kwargs["timeout"] == 30
    response.raise_for_status.assert_called_once()


@pytest.mark.parametrize("price", [0, -1, float("nan"), float("inf"), None, "invalid"])
def test_private_share_price_rejects_invalid_values(mt: MaestroTest, price: object) -> None:
    response = Mock()
    response.json.return_value = {"chart": {"result": [{"meta": {"regularMarketPrice": price}}]}}
    with (
        patch.object(finance.requests, "get", return_value=response),
        pytest.raises((ValueError, TypeError)),
    ):
        finance.get_private_share_price("EXAMPLE.PVT")


def test_private_share_price_rejects_http_errors(mt: MaestroTest) -> None:
    response = Mock()
    response.raise_for_status.side_effect = requests.HTTPError()
    with (
        patch.object(finance.requests, "get", return_value=response),
        pytest.raises(requests.HTTPError),
    ):
        finance.get_private_share_price("EXAMPLE.PVT")
    response.json.assert_not_called()
