from src import parser


def test_parse_space_export_fixture():
    parsed = parser.parse_file("tests/fixtures/sample_chat.txt")
    frame = parser.to_dataframe(parsed)

    assert len(frame) == 9
    assert parser.summarize(parsed)["user_count"] == 5
    assert set(frame["user"]) >= {"段 Duan", "Young", "黃偉哲"}
    assert "投影機遙控器" in frame.loc[1, "message"]
    assert "子揚&品豪" in frame.loc[2, "message"]
    assert bool(frame.loc[5, "has_url"]) is True
    assert frame.loc[6, "type"] == "sticker"
    assert frame.loc[7, "time"] == "12:30"


def test_parse_tab_export_time_and_system():
    text = "\n".join(
        [
            "[LINE] MIAT_2025聊天記錄",
            "2025/09/01 星期一",
            "上午12:30\tYoung\t半夜訊息",
            "下午12:30\t段 Duan\t中午訊息",
            "下午01:00\t\tYoung加入群組",
        ]
    )
    frame = parser.to_dataframe(parser.parse_text(text))

    assert list(frame["time"]) == ["00:30", "12:30", "13:00"]
    assert bool(frame.iloc[2]["is_system"]) is True
