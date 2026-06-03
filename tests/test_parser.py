from src import parser


def test_parse_space_export_fixture():
    parsed = parser.parse_file("tests/fixtures/sample_chat.txt")
    frame = parser.to_dataframe(parsed)

    assert len(frame) == 9
    assert parser.summarize(parsed)["user_count"] == 5
    assert any("Duan" in user for user in frame["user"])
    assert "Young" in set(frame["user"])
    assert bool(frame.loc[5, "has_url"]) is True
    assert frame.loc[6, "type"] == "sticker"
    assert frame.loc[7, "time"] == "12:30"


def test_parse_tab_export_time_and_drops_system_events():
    text = "\n".join(
        [
            "[LINE] MIAT_2025",
            "2025/09/01",
            "\u4e0a\u534812:30\tYoung\tmidnight",
            "\u4e0b\u534812:30\tDuan\tnoon",
            "\u4e0b\u534801:00\t\tYoung\u52a0\u5165\u7fa4\u7d44",
            "\u4e0b\u534801:05\tYoung\t\u5df2\u6536\u56de\u8a0a\u606f",
        ]
    )
    frame = parser.to_dataframe(parser.parse_text(text))

    assert list(frame["time"]) == ["00:30", "12:30"]
    assert set(frame["user"]) == {"Young", "Duan"}


def test_parse_space_export_drops_withdraw_and_join_events():
    text = "\n".join(
        [
            "2026.02.23",
            "16:16 Young hello",
            "16:17 Young\u5df2\u6536\u56de\u8a0a\u606f",
            "16:18 Chris join",
            "16:19 Duan normal message",
        ]
    )
    frame = parser.to_dataframe(parser.parse_text(text))

    assert list(frame["user"]) == ["Young", "Duan"]
    assert not frame["user"].str.contains("\u5df2\u6536\u56de").any()

