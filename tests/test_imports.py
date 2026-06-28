def test_python_packages_import():
    import bookmd_core
    import source_map_core
    import translator_core

    assert bookmd_core.__name__ == "bookmd_core"
    assert source_map_core.__name__ == "source_map_core"
    assert translator_core.__name__ == "translator_core"
