"""Office card compensation comparison and stock display restoration."""

from unittest.mock import patch

from maestro.testing import MaestroTest

from scripts.common.event_type import EventType, UIEvent
from scripts.common.finance import NET_SYMBOL, SPY_SYMBOL, FinnhubResponse
from scripts.frontend.common.entity_card import RowColor

from .. import office


def test_double_tap_shows_annual_total_comp_then_restores_stocks(mt: MaestroTest) -> None:
    """Show salary plus annual equity for each employer before restoring stock rows."""
    office.initialize_card()
    office.card.update(row_2_color=RowColor.GREEN, row_3_color=RowColor.RED)
    net_quote = FinnhubResponse(c=125.5, d=0, dp=0, h=0, l=0, o=0, pc=0, t=0)
    spy_quote = FinnhubResponse(c=600, d=0, dp=0, h=0, l=0, o=0, pc=0, t=0)
    compensation_displays: list[tuple[float, str, str, str, str]] = []

    def capture_compensation_display(seconds: float) -> None:
        compensation_displays.append(
            (
                seconds,
                office.card.row_2_value,
                office.card.row_3_value,
                office.card.row_2_color,
                office.card.row_3_color,
            )
        )

    with (
        patch.object(office, "CURRENT_SALARY", 9_000_000_001),
        patch.object(office, "CURRENT_SHARES_PER_YEAR", 4_000_000),
        patch.object(office, "SHARE_PRICE", 0.125),
        patch.object(office, "NET_SALARY", 7_000_000_003),
        patch.object(office, "NET_SHARES_PER_YEAR", 0.5),
        patch.object(
            office, "get_stock_quote", side_effect=[net_quote, spy_quote, net_quote]
        ) as get_quote,
        patch.object(office, "sleep", side_effect=capture_compensation_display),
    ):
        mt.trigger_event(
            EventType.MAESTRO_UI_EVENT, data={"trigger": UIEvent.ENTITY_CARD_4_DOUBLE_TAP}
        )

    assert compensation_displays == [
        (5, "$9,000,500,001", "$7,000,000,066", RowColor.DEFAULT, RowColor.DEFAULT)
    ]
    assert office.card.row_2_value == "$600"
    assert office.card.row_3_value == "$126"
    assert [call.args[0] for call in get_quote.call_args_list] == [
        NET_SYMBOL,
        SPY_SYMBOL,
        NET_SYMBOL,
    ]


def test_double_tap_handles_cloudflare_quote_failure(mt: MaestroTest) -> None:
    """Keep the existing failure display when the Cloudflare quote cannot be fetched."""
    office.initialize_card()

    with (
        patch.object(office, "get_stock_quote", side_effect=RuntimeError("Quote unavailable")),
        patch.object(office, "sleep") as sleep,
    ):
        mt.trigger_event(
            EventType.MAESTRO_UI_EVENT, data={"trigger": UIEvent.ENTITY_CARD_4_DOUBLE_TAP}
        )

    assert office.card.row_2_value == "Failed :("
    assert office.card.row_3_value == "Failed :("
    sleep.assert_not_called()
