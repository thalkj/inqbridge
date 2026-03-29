"""Tests for include discovery."""
import pytest
from pathlib import Path
from runner.includes import discover_includes


@pytest.fixture
def tmp_scripts(tmp_path):
    """Create a temporary script tree with includes."""
    main = tmp_path / "main.iqx"
    inc_a = tmp_path / "inc_a.iqx"
    inc_b = tmp_path / "inc_b.iqx"

    inc_b.write_text('<text myText>\n/ items = ("hello")\n</text>', encoding="utf-8")
    inc_a.write_text('<include>"inc_b.iqx"</include>\n<block myBlock>\n</block>', encoding="utf-8")
    main.write_text('<include>"inc_a.iqx"</include>\n<expt>\n/ blocks = [1=myBlock]\n</expt>', encoding="utf-8")

    return main, inc_a, inc_b


def test_discovers_direct_include(tmp_scripts):
    main, inc_a, inc_b = tmp_scripts
    includes = discover_includes(main)
    assert inc_a.resolve() in includes


def test_discovers_transitive_include(tmp_scripts):
    main, inc_a, inc_b = tmp_scripts
    includes = discover_includes(main)
    assert inc_b.resolve() in includes


def test_correct_order(tmp_scripts):
    main, inc_a, inc_b = tmp_scripts
    includes = discover_includes(main)
    assert includes == [inc_a.resolve(), inc_b.resolve()]


def test_no_includes(tmp_path):
    script = tmp_path / "simple.iqx"
    script.write_text('<text t1>\n/ items = ("hello")\n</text>', encoding="utf-8")
    assert discover_includes(script) == []


def test_missing_include_is_skipped(tmp_path):
    script = tmp_path / "main.iqx"
    script.write_text('<include>"nonexistent.iqx"</include>', encoding="utf-8")
    assert discover_includes(script) == []


def test_circular_include(tmp_path):
    a = tmp_path / "a.iqx"
    b = tmp_path / "b.iqx"
    a.write_text('<include>"b.iqx"</include>', encoding="utf-8")
    b.write_text('<include>"a.iqx"</include>', encoding="utf-8")
    # Should not infinite loop
    includes = discover_includes(a)
    assert b.resolve() in includes


def test_search_dirs(tmp_path):
    scripts_dir = tmp_path / "scripts"
    includes_dir = tmp_path / "includes"
    scripts_dir.mkdir()
    includes_dir.mkdir()

    main = scripts_dir / "main.iqx"
    inc = includes_dir / "shared.iqx"

    inc.write_text('<text t>\n</text>', encoding="utf-8")
    main.write_text('<include>"shared.iqx"</include>', encoding="utf-8")

    includes = discover_includes(main, search_dirs=[includes_dir])
    assert inc.resolve() in includes


def test_v7_multiline_include(tmp_path):
    """Inquisit 7 uses multiline <include> with / file = "..." syntax."""
    main = tmp_path / "main.iqjs"
    inc = tmp_path / "logic_inc.iqjs"

    inc.write_text('<text t>\n/ items = ("hello")\n</text>', encoding="utf-8")
    main.write_text(
        '<include>\n/ file = "logic_inc.iqjs"\n</include>\n',
        encoding="utf-8",
    )

    includes = discover_includes(main)
    assert inc.resolve() in includes


def test_v7_multiline_include_with_comment(tmp_path):
    """v7 includes often have inline comments after the filename."""
    main = tmp_path / "main.iqjs"
    inc = tmp_path / "task_inc.iqjs"

    inc.write_text('<text t>\n</text>', encoding="utf-8")
    main.write_text(
        '<include>\n/ file = "task_inc.iqjs"//main task code\n</include>\n',
        encoding="utf-8",
    )

    includes = discover_includes(main)
    assert inc.resolve() in includes


def test_mixed_v6_v7_includes(tmp_path):
    """Script mixing v6 and v7 include styles should find both."""
    main = tmp_path / "main.iqx"
    inc_v6 = tmp_path / "old_inc.iqx"
    inc_v7 = tmp_path / "new_inc.iqx"

    inc_v6.write_text('<text t1>\n</text>', encoding="utf-8")
    inc_v7.write_text('<text t2>\n</text>', encoding="utf-8")
    main.write_text(
        '<include>"old_inc.iqx"</include>\n'
        '<include>\n/ file = "new_inc.iqx"\n</include>\n',
        encoding="utf-8",
    )

    includes = discover_includes(main)
    assert len(includes) == 2
    assert inc_v6.resolve() in includes
    assert inc_v7.resolve() in includes
