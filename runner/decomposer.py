"""Decompose a monolithic .iqx script into modular include files.

Takes a single large .iqx and splits it into:
- config_inc.iqx: shared values, defaults, expressions
- {block_name}_inc.iqx: each block + its dependent elements
- main.iqx: includes + experiment definition
- test_{block_name}.iqx: standalone testers per module
"""
from __future__ import annotations

import re
from pathlib import Path
from collections import defaultdict


# Element block pattern: <type name> ... </type>
_ELEM_BLOCK = re.compile(
    r"(<(\w+)\s+(\w+)\s*>)(.*?)(</\2>)",
    re.IGNORECASE | re.DOTALL,
)

# Defaults block: <defaults> ... </defaults>
_DEFAULTS_BLOCK = re.compile(
    r"(<defaults>)(.*?)(</defaults>)",
    re.IGNORECASE | re.DOTALL,
)

# Experiment block: <expt> ... </expt> or <expt name> ... </expt>
_EXPT_BLOCK = re.compile(
    r"(<expt\b[^>]*>)(.*?)(</expt>)",
    re.IGNORECASE | re.DOTALL,
)

# References from trials: stimulustimes, stimulusframes
_STIMULUS_REFS = re.compile(
    r"/\s*(?:stimulustimes|stimulusframes)\s*=\s*\[([^\]]+)\]",
    re.IGNORECASE,
)

# References from blocks: / trials = [...]
_BLOCK_TRIALS = re.compile(
    r"/\s*trials\s*=\s*\[([^\]]+)\]",
    re.IGNORECASE,
)

# References from expt: / blocks = [...]
_EXPT_BLOCKS_ATTR = re.compile(
    r"/\s*blocks\s*=\s*\[([^\]]+)\]",
    re.IGNORECASE,
)

# Extract names from bracket lists
_BRACKET_NAMES = re.compile(r"(?:\d+[-=])?(\w+)")

# Comment lines at the top of the file
_HEADER_COMMENT = re.compile(r"^\s*//.*$", re.MULTILINE)

# Config element types (go into config module)
_CONFIG_TYPES = {"values", "expressions", "parameters", "defaults"}

# Stimulus/response element types (go with their referring trial)
_DEPENDENT_TYPES = {"text", "picture", "sound", "video", "shape", "list",
                    "radiobuttons", "textbox", "dropdown", "checkboxes",
                    "openended", "caption"}


def _extract_refs_from_body(body: str) -> set[str]:
    """Extract all element names referenced in a body via stimulus/trial/block attrs."""
    refs: set[str] = set()
    for pattern in [_STIMULUS_REFS, _BLOCK_TRIALS]:
        for m in pattern.finditer(body):
            for name_match in _BRACKET_NAMES.finditer(m.group(1)):
                name = name_match.group(1).lower()
                if not name.isdigit():
                    refs.add(name)
    # Also check ontrialbegin/ontrialend for element references like text.name.property
    dotted = re.findall(r"(?:text|picture|trial|block|list|shape|sound|video)\.(\w+)\.", body, re.IGNORECASE)
    for name in dotted:
        refs.add(name.lower())
    return refs


def _find_dependencies(
    elem_name: str,
    elem_body: str,
    all_elements: dict[str, dict],
    visited: set[str],
) -> set[str]:
    """Recursively find all elements that elem_name depends on."""
    if elem_name in visited:
        return set()
    visited.add(elem_name)

    refs = _extract_refs_from_body(elem_body)
    deps = set(refs)

    for ref in refs:
        if ref in all_elements and ref not in visited:
            sub_deps = _find_dependencies(
                ref, all_elements[ref]["body"], all_elements, visited
            )
            deps.update(sub_deps)

    return deps


def decompose_script(
    script_path: Path,
    output_dir: Path | None = None,
    experiment_name: str | None = None,
) -> dict:
    """Decompose a monolithic .iqx into modular include files.

    Args:
        script_path: Path to the monolithic .iqx script.
        output_dir: Where to write the module files. Defaults to
                     script_path.parent / "{stem}_modules".
        experiment_name: Name prefix for generated files. Defaults to script stem.

    Returns:
        Dict with created files, module breakdown, and any warnings.
    """
    if not script_path.is_file():
        return {"error": f"Script not found: {script_path}"}

    source = script_path.read_text(encoding="utf-8-sig")

    if experiment_name is None:
        experiment_name = script_path.stem.replace(" ", "_").lower()

    if output_dir is None:
        output_dir = script_path.parent / f"{script_path.stem}_modules"

    output_dir.mkdir(parents=True, exist_ok=True)

    # --- Parse all elements ---
    all_elements: dict[str, dict] = {}  # name -> {type, name, open, body, close, full}

    for m in _ELEM_BLOCK.finditer(source):
        elem_type = m.group(2).lower()
        elem_name = m.group(3).lower()
        all_elements[elem_name] = {
            "type": elem_type,
            "name": m.group(3),  # Preserve original case
            "body": m.group(4),
            "full": m.group(0),
        }

    # Parse defaults block separately
    defaults_content = ""
    defaults_match = _DEFAULTS_BLOCK.search(source)
    if defaults_match:
        defaults_content = defaults_match.group(0)

    # Parse experiment block
    expt_content = ""
    block_order = []
    expt_match = _EXPT_BLOCK.search(source)
    if expt_match:
        expt_content = expt_match.group(0)
        blocks_attr = _EXPT_BLOCKS_ATTR.search(expt_match.group(2))
        if blocks_attr:
            for name_match in _BRACKET_NAMES.finditer(blocks_attr.group(1)):
                name = name_match.group(1).lower()
                if not name.isdigit():
                    block_order.append(name)

    # --- Classify elements ---
    # Config elements (values, expressions, etc.)
    config_elements = {
        name: elem for name, elem in all_elements.items()
        if elem["type"] in _CONFIG_TYPES
    }

    # Block elements
    block_elements = {
        name: elem for name, elem in all_elements.items()
        if elem["type"] == "block"
    }

    # Trial elements
    trial_elements = {
        name: elem for name, elem in all_elements.items()
        if elem["type"] in ("trial", "surveypage")
    }

    # All other elements (text, picture, list, etc.)
    other_elements = {
        name: elem for name, elem in all_elements.items()
        if elem["type"] not in _CONFIG_TYPES
        and elem["type"] != "block"
        and elem["type"] not in ("trial", "surveypage")
        and elem["type"] != "expt"
    }

    # --- Assign elements to blocks via dependency tracing ---
    block_modules: dict[str, list[str]] = {}  # block_name -> [element_names]

    claimed: set[str] = set()  # Elements already assigned to a block

    for block_name in block_order:
        if block_name not in block_elements:
            continue

        block = block_elements[block_name]
        visited: set[str] = set()
        deps = _find_dependencies(block_name, block["body"], all_elements, visited)

        # Include the block itself
        module_elements = [block_name]

        # Add trials referenced by this block
        for dep in deps:
            if dep in trial_elements and dep not in claimed:
                module_elements.append(dep)
                claimed.add(dep)
                # Add trial's dependencies (text, pictures, lists)
                trial_deps = _find_dependencies(
                    dep, trial_elements[dep]["body"], all_elements, set()
                )
                for td in trial_deps:
                    if td in other_elements and td not in claimed:
                        module_elements.append(td)
                        claimed.add(td)

        # Add direct block dependencies that aren't trials
        for dep in deps:
            if dep in other_elements and dep not in claimed:
                module_elements.append(dep)
                claimed.add(dep)

        claimed.add(block_name)
        block_modules[block_name] = module_elements

    # Unclaimed elements go to config or a "shared" module
    unclaimed = set(other_elements.keys()) - claimed
    unclaimed_trials = set(trial_elements.keys()) - claimed

    # --- Write files ---
    created_files = []
    warnings = []

    # Config module
    config_parts = []
    if defaults_content:
        config_parts.append(defaults_content)
    for name, elem in config_elements.items():
        config_parts.append(elem["full"])
    # Add unclaimed non-trial elements to config (they're likely shared)
    for name in sorted(unclaimed):
        config_parts.append(all_elements[name]["full"])
        warnings.append(f"Element '{name}' not referenced by any block — placed in config module")

    config_path = output_dir / f"{experiment_name}_config_inc.iqx"
    config_content = f"// Configuration module for {experiment_name}\n// Shared values, defaults, and expressions.\n\n"
    config_content += "\n\n".join(config_parts) + "\n"
    config_path.write_text(config_content, encoding="utf-8")
    created_files.append(str(config_path))

    # Block modules
    include_filenames = [f"{experiment_name}_config_inc.iqx"]
    for block_name, elem_names in block_modules.items():
        module_parts = []
        for ename in elem_names:
            if ename in all_elements:
                module_parts.append(all_elements[ename]["full"])

        module_path = output_dir / f"{experiment_name}_{block_name}_inc.iqx"
        module_content = f"// {block_name} module for {experiment_name}\n\n"
        module_content += "\n\n".join(module_parts) + "\n"
        module_path.write_text(module_content, encoding="utf-8")
        created_files.append(str(module_path))
        include_filenames.append(f"{experiment_name}_{block_name}_inc.iqx")

    # Handle unclaimed trials
    if unclaimed_trials:
        orphan_parts = []
        for name in sorted(unclaimed_trials):
            orphan_parts.append(trial_elements[name]["full"])
            warnings.append(f"Trial '{name}' not referenced by any block — placed in orphaned module")
        orphan_path = output_dir / f"{experiment_name}_orphaned_inc.iqx"
        orphan_content = f"// Orphaned elements for {experiment_name}\n// These trials are not referenced by any block.\n\n"
        orphan_content += "\n\n".join(orphan_parts) + "\n"
        orphan_path.write_text(orphan_content, encoding="utf-8")
        created_files.append(str(orphan_path))

    # Main.iqx
    includes_text = "\n".join(f'<include>"{fn}"</include>' for fn in include_filenames)
    main_content = f"// Main experiment file for {experiment_name}\n// Decomposed from {script_path.name}\n\n"
    main_content += includes_text + "\n\n"
    if expt_content:
        main_content += expt_content + "\n"
    else:
        # Reconstruct expt from block order
        block_refs = "; ".join(f"{i+1}={bn}" for i, bn in enumerate(block_order))
        main_content += f"<expt>\n/ blocks = [{block_refs}]\n</expt>\n"

    main_path = output_dir / "main.iqx"
    main_path.write_text(main_content, encoding="utf-8")
    created_files.append(str(main_path))

    # Standalone testers
    tester_files = []
    for block_name in block_modules:
        tester_content = f"// Standalone tester for {block_name} module\n\n"
        tester_content += f'<include>"{experiment_name}_config_inc.iqx"</include>\n'
        tester_content += f'<include>"{experiment_name}_{block_name}_inc.iqx"</include>\n\n'
        tester_content += f"<expt>\n/ blocks = [1={block_name}]\n</expt>\n"
        tester_path = output_dir / f"test_{block_name}.iqx"
        tester_path.write_text(tester_content, encoding="utf-8")
        created_files.append(str(tester_path))
        tester_files.append(str(tester_path))

    return {
        "experiment_name": experiment_name,
        "output_dir": str(output_dir),
        "created_files": created_files,
        "tester_files": tester_files,
        "modules": {
            "config": list(config_elements.keys()) + list(unclaimed),
            **{bn: elems for bn, elems in block_modules.items()},
        },
        "block_order": block_order,
        "warnings": warnings,
        "element_count": len(all_elements),
    }
