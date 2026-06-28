from source_map_core import build_source_map, normalize_blocks


def test_normalize_blocks_accepts_pages_shape():
    data = {
        "pages": [
            {
                "page": 1,
                "blocks": [
                    {
                        "id": "b1",
                        "type": "paragraph",
                        "bbox": [1, 2, 3, 4],
                        "text": "Hello",
                    }
                ],
            }
        ]
    }

    blocks = normalize_blocks(data)

    assert blocks[0].block_id == "b1"
    assert blocks[0].page == 1
    assert blocks[0].bbox == [1, 2, 3, 4]


def test_normalize_blocks_accepts_page_index_from_service_pages():
    blocks = normalize_blocks(
        {
            "pages": [
                {
                    "page_index": 2,
                    "blocks": [
                        {
                            "block_id": "p002_b001",
                            "type": "paragraph",
                            "bbox": [1, 2, 3, 4],
                            "text": "Grid inverter",
                        }
                    ],
                }
            ]
        }
    )

    assert blocks[0].page == 2


def test_build_source_map_preserves_trace_data():
    blocks = normalize_blocks(
        {
            "blocks": [
                {
                    "block_id": "p001_b001",
                    "page": 1,
                    "type": "paragraph",
                    "bbox": [0, 0, 10, 10],
                    "text": "Grid inverter",
                }
            ]
        }
    )

    source_map = build_source_map(
        blocks,
        chapter_by_block={"p001_b001": ("ch_001", "chapters/001_intro.md")},
    )

    assert source_map["blocks"][0]["block_id"] == "p001_b001"
    assert source_map["blocks"][0]["chapter_id"] == "ch_001"
    assert source_map["blocks"][0]["source_text"] == "Grid inverter"
