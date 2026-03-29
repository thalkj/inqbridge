"""Generate starter experiment templates for common paradigms.

Templates are reference patterns — realistic enough to compile and run,
but designed to be freely modified. The 'custom' type generates minimal
module stubs with no paradigm assumptions.
"""
from __future__ import annotations

from pathlib import Path


# ---------------------------------------------------------------------------
# Module templates per role
# ---------------------------------------------------------------------------

_CONFIG_TEMPLATE = """\
// Configuration module for {experiment_name}
// Shared values, defaults, and expressions used across all modules.

<defaults>
/ screencolor = white
/ txcolor = black
/ txbgcolor = transparent
/ fontstyle = ("Arial", 3.5%)
/ minimumversion = "6.6"
</defaults>

<values>
/ experiment_name = "{experiment_name}"
/ debug_mode = 0
</values>
"""

_INSTRUCTIONS_TEMPLATE = """\
// Instructions module for {experiment_name}
// Displays task instructions before the main experiment begins.

<text instructions_title>
/ items = ("Welcome to the experiment")
/ fontstyle = ("Arial", 5%)
/ position = (50%, 30%)
/ txcolor = black
</text>

<text instructions_body>
/ items = ("You will be presented with a series of stimuli.~~Press the SPACEBAR to begin.")
/ fontstyle = ("Arial", 3%)
/ position = (50%, 55%)
/ txcolor = black
/ size = (80%, 30%)
</text>

<trial instructions_trial>
/ stimulustimes = [0=instructions_title, instructions_body]
/ validresponse = (" ")
/ recorddata = false
</trial>

<block instructions_block>
/ trials = [1=instructions_trial]
</block>
"""

_DEBRIEF_TEMPLATE = """\
// Debrief module for {experiment_name}
// Thank-you screen shown after the experiment completes.

<text debrief_text>
/ items = ("Thank you for participating!~~The experiment is now complete.")
/ fontstyle = ("Arial", 4%)
/ position = (50%, 50%)
/ txcolor = black
/ size = (80%, 30%)
</text>

<trial debrief_trial>
/ stimulustimes = [0=debrief_text]
/ validresponse = (" ")
/ recorddata = false
</trial>

<block debrief_block>
/ trials = [1=debrief_trial]
</block>
"""

_GENERIC_PRACTICE_TEMPLATE = """\
// Practice module for {experiment_name}
// Short practice block to familiarize participants with the task.

<text practice_fixation>
/ items = ("+")
/ fontstyle = ("Arial", 5%)
/ position = (50%, 50%)
/ txcolor = black
</text>

<text practice_stimulus>
/ items = ("SAMPLE STIMULUS")
/ fontstyle = ("Arial", 4%)
/ position = (50%, 50%)
/ txcolor = black
</text>

<text practice_feedback_correct>
/ items = ("Correct!")
/ fontstyle = ("Arial", 3.5%)
/ position = (50%, 75%)
/ txcolor = green
</text>

<text practice_feedback_incorrect>
/ items = ("Incorrect")
/ fontstyle = ("Arial", 3.5%)
/ position = (50%, 75%)
/ txcolor = red
</text>

<trial practice_trial>
/ stimulustimes = [0=practice_fixation; 500=practice_stimulus]
/ posttrialpause = 200
/ validresponse = ("e", "i")
/ correctresponse = ("e")
/ screenCapture = true
</trial>

<block practice_block>
/ trials = [1-4=practice_trial]
/ errormessage = true(practice_feedback_incorrect, 500)
/ correctmessage = true(practice_feedback_correct, 500)
</block>
"""

_GENERIC_TEST_TEMPLATE = """\
// Test module for {experiment_name}
// Main experimental block with data collection.

<text test_fixation>
/ items = ("+")
/ fontstyle = ("Arial", 5%)
/ position = (50%, 50%)
/ txcolor = black
</text>

<text test_stimulus>
/ items = ("STIMULUS 1", "STIMULUS 2", "STIMULUS 3", "STIMULUS 4")
/ fontstyle = ("Arial", 4%)
/ position = (50%, 50%)
/ txcolor = black
</text>

<trial test_trial>
/ stimulustimes = [0=test_fixation; 500=test_stimulus]
/ posttrialpause = 200
/ validresponse = ("e", "i")
/ screenCapture = true
</trial>

<block test_block>
/ trials = [1-20=test_trial]
</block>
"""

# ---------------------------------------------------------------------------
# IAT-specific templates
# ---------------------------------------------------------------------------

_IAT_CONFIG_TEMPLATE = """\
// IAT Configuration for {experiment_name}
// Shared values, defaults, and category definitions.

<defaults>
/ screencolor = black
/ txcolor = white
/ txbgcolor = transparent
/ fontstyle = ("Arial", 3.5%)
/ minimumversion = "6.6"
</defaults>

<values>
/ experiment_name = "{experiment_name}"
/ debug_mode = 0
</values>

// Category labels — change these to match your target/attribute categories
<text category_a_label>
/ items = ("Category A")
/ fontstyle = ("Arial", 4%)
/ position = (10%, 5%)
/ txcolor = green
/ erase = false
</text>

<text category_b_label>
/ items = ("Category B")
/ fontstyle = ("Arial", 4%)
/ position = (90%, 5%)
/ txcolor = green
/ erase = false
</text>

<text attribute_a_label>
/ items = ("Pleasant")
/ fontstyle = ("Arial", 4%)
/ position = (10%, 12%)
/ txcolor = white
/ erase = false
</text>

<text attribute_b_label>
/ items = ("Unpleasant")
/ fontstyle = ("Arial", 4%)
/ position = (90%, 12%)
/ txcolor = white
/ erase = false
</text>

<text error_feedback>
/ items = ("X")
/ fontstyle = ("Arial", 8%)
/ position = (50%, 70%)
/ txcolor = red
</text>

// Stimulus lists — replace with your actual stimuli
<list category_a_items>
/ items = ("Rose", "Tulip", "Daisy", "Lily")
</list>

<list category_b_items>
/ items = ("Ant", "Wasp", "Beetle", "Spider")
</list>

<list attribute_a_items>
/ items = ("Joy", "Peace", "Love", "Happy")
</list>

<list attribute_b_items>
/ items = ("Agony", "Evil", "Hatred", "Vomit")
</list>
"""

_IAT_TEST_TEMPLATE = """\
// IAT Test module for {experiment_name}
// Combined categorization block (compatible or incompatible pairing).

<text iat_stimulus>
/ items = ("<%values.current_stimulus%>")
/ fontstyle = ("Arial", 5%)
/ position = (50%, 50%)
/ txcolor = white
</text>

<values>
/ current_stimulus = ""
/ current_category = ""
</values>

// Target categorization trial
<trial iat_target_trial>
/ ontrialbegin = [
    values.current_stimulus = list.category_a_items.nextvalue;
]
/ stimulustimes = [0=category_a_label, category_b_label, attribute_a_label, attribute_b_label, iat_stimulus]
/ validresponse = ("e", "i")
/ correctresponse = ("e")
/ posttrialpause = 250
/ screenCapture = true
</trial>

// Attribute categorization trial
<trial iat_attribute_trial>
/ ontrialbegin = [
    values.current_stimulus = list.attribute_a_items.nextvalue;
]
/ stimulustimes = [0=category_a_label, category_b_label, attribute_a_label, attribute_b_label, iat_stimulus]
/ validresponse = ("e", "i")
/ correctresponse = ("e")
/ posttrialpause = 250
/ screenCapture = true
</trial>

<block iat_test_block>
/ trials = [1-10=noreplace(iat_target_trial, iat_attribute_trial)]
</block>
"""

# ---------------------------------------------------------------------------
# Stroop-specific templates
# ---------------------------------------------------------------------------

_STROOP_CONFIG_TEMPLATE = """\
// Stroop Configuration for {experiment_name}
// Color-word interference task.

<defaults>
/ screencolor = white
/ txcolor = black
/ txbgcolor = transparent
/ fontstyle = ("Arial", 3.5%)
/ minimumversion = "6.6"
</defaults>

<values>
/ experiment_name = "{experiment_name}"
/ debug_mode = 0
/ current_color = "red"
</values>

// Response key labels shown at bottom of screen
<text key_labels>
/ items = ("D = Red     F = Green     J = Blue     K = Yellow")
/ fontstyle = ("Consolas", 2.5%)
/ position = (50%, 92%)
/ txcolor = gray
/ erase = false
</text>
"""

_STROOP_TEST_TEMPLATE = """\
// Stroop Test module for {experiment_name}
// Congruent and incongruent color-word trials.

<text stroop_fixation>
/ items = ("+")
/ fontstyle = ("Arial", 5%)
/ position = (50%, 50%)
/ txcolor = black
</text>

// Congruent stimuli: word matches ink color
<text stroop_congruent>
/ items = ("RED", "GREEN", "BLUE", "YELLOW")
/ fontstyle = ("Arial", 6%)
/ position = (50%, 50%)
/ select = list.congruent_colors.currentindex
</text>

// Incongruent stimuli: word differs from ink color
<text stroop_incongruent>
/ items = ("RED", "GREEN", "BLUE", "YELLOW")
/ fontstyle = ("Arial", 6%)
/ position = (50%, 50%)
/ select = list.incongruent_colors.currentindex
</text>

// Color assignment lists
<list congruent_colors>
/ items = (red, green, blue, yellow)
/ selectionmode = random
</list>

<list incongruent_colors>
/ items = (green, yellow, red, blue)
/ selectionmode = random
</list>

<trial stroop_congruent_trial>
/ stimulustimes = [0=stroop_fixation; 500=stroop_congruent, key_labels]
/ validresponse = ("d", "f", "j", "k")
/ correctresponse = ("d")
/ posttrialpause = 200
/ screenCapture = true
</trial>

<trial stroop_incongruent_trial>
/ stimulustimes = [0=stroop_fixation; 500=stroop_incongruent, key_labels]
/ validresponse = ("d", "f", "j", "k")
/ posttrialpause = 200
/ screenCapture = true
</trial>

<block stroop_test_block>
/ trials = [1-20=noreplace(stroop_congruent_trial, stroop_incongruent_trial)]
</block>
"""

# ---------------------------------------------------------------------------
# Survey-specific templates
# ---------------------------------------------------------------------------

_SURVEY_CONFIG_TEMPLATE = """\
// Survey Configuration for {experiment_name}
// Self-report questionnaire.

<defaults>
/ screencolor = white
/ txcolor = black
/ txbgcolor = transparent
/ fontstyle = ("Arial", 3%)
/ minimumversion = "6.6"
</defaults>

<values>
/ experiment_name = "{experiment_name}"
</values>
"""

_SURVEY_TEST_TEMPLATE = """\
// Survey module for {experiment_name}
// Example Likert-scale questionnaire page.

<surveypage survey_page1>
/ caption = "Please rate how much you agree with each statement."
/ questions = [1=survey_q1; 2=survey_q2; 3=survey_q3]
/ showpagenumbers = true
/ showquestionnumbers = true
</surveypage>

<radiobuttons survey_q1>
/ caption = "I generally feel positive about the future."
/ options = ("Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree")
/ required = true
</radiobuttons>

<radiobuttons survey_q2>
/ caption = "I enjoy meeting new people."
/ options = ("Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree")
/ required = true
</radiobuttons>

<radiobuttons survey_q3>
/ caption = "I prefer routine over novelty."
/ options = ("Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree")
/ required = true
</radiobuttons>

<block survey_block>
/ trials = [1=survey_page1]
</block>
"""

# ---------------------------------------------------------------------------
# RT Task templates
# ---------------------------------------------------------------------------

_RT_CONFIG_TEMPLATE = """\
// RT Task Configuration for {experiment_name}
// Simple reaction time task.

<defaults>
/ screencolor = black
/ txcolor = white
/ txbgcolor = transparent
/ fontstyle = ("Arial", 3.5%)
/ minimumversion = "6.6"
</defaults>

<values>
/ experiment_name = "{experiment_name}"
/ debug_mode = 0
</values>
"""

_RT_TEST_TEMPLATE = """\
// RT Test module for {experiment_name}
// Target detection with variable foreperiod.

<text rt_fixation>
/ items = ("+")
/ fontstyle = ("Arial", 6%)
/ position = (50%, 50%)
/ txcolor = white
</text>

<shape rt_target>
/ shape = circle
/ size = (5%, 5%)
/ position = (50%, 50%)
/ color = green
</shape>

<list foreperiods>
/ items = (500, 750, 1000, 1250, 1500)
/ selectionmode = random
</list>

<trial rt_trial>
/ ontrialbegin = [
    trial.rt_trial.insertstimulustime(shape.rt_target, list.foreperiods.nextvalue);
]
/ stimulustimes = [0=rt_fixation]
/ validresponse = (" ")
/ beginresponsetime = 0
/ posttrialpause = 500
/ screenCapture = true
/ ontrialend = [
    trial.rt_trial.resetstimulusframes();
]
</trial>

<block rt_test_block>
/ trials = [1-20=rt_trial]
</block>
"""


# ---------------------------------------------------------------------------
# Template registry
# ---------------------------------------------------------------------------

# Maps (experiment_type, module_role) -> template string
_TEMPLATES: dict[tuple[str, str], str] = {
    # Generic / custom
    ("custom", "config"): _CONFIG_TEMPLATE,
    ("custom", "instructions"): _INSTRUCTIONS_TEMPLATE,
    ("custom", "practice"): _GENERIC_PRACTICE_TEMPLATE,
    ("custom", "test"): _GENERIC_TEST_TEMPLATE,
    ("custom", "debrief"): _DEBRIEF_TEMPLATE,
    # IAT
    ("iat", "config"): _IAT_CONFIG_TEMPLATE,
    ("iat", "instructions"): _INSTRUCTIONS_TEMPLATE,
    ("iat", "practice"): _GENERIC_PRACTICE_TEMPLATE,
    ("iat", "test"): _IAT_TEST_TEMPLATE,
    ("iat", "debrief"): _DEBRIEF_TEMPLATE,
    # Stroop
    ("stroop", "config"): _STROOP_CONFIG_TEMPLATE,
    ("stroop", "instructions"): _INSTRUCTIONS_TEMPLATE,
    ("stroop", "practice"): _GENERIC_PRACTICE_TEMPLATE,
    ("stroop", "test"): _STROOP_TEST_TEMPLATE,
    ("stroop", "debrief"): _DEBRIEF_TEMPLATE,
    # Survey
    ("survey", "config"): _SURVEY_CONFIG_TEMPLATE,
    ("survey", "instructions"): _INSTRUCTIONS_TEMPLATE,
    ("survey", "test"): _SURVEY_TEST_TEMPLATE,
    ("survey", "debrief"): _DEBRIEF_TEMPLATE,
    # RT Task
    ("rt_task", "config"): _RT_CONFIG_TEMPLATE,
    ("rt_task", "instructions"): _INSTRUCTIONS_TEMPLATE,
    ("rt_task", "practice"): _GENERIC_PRACTICE_TEMPLATE,
    ("rt_task", "test"): _RT_TEST_TEMPLATE,
    ("rt_task", "debrief"): _DEBRIEF_TEMPLATE,
}

SUPPORTED_TYPES = ["iat", "stroop", "survey", "rt_task", "custom"]

DEFAULT_MODULES = {
    "iat": ["config", "instructions", "practice", "test", "debrief"],
    "stroop": ["config", "instructions", "practice", "test", "debrief"],
    "survey": ["config", "instructions", "test", "debrief"],
    "rt_task": ["config", "instructions", "practice", "test", "debrief"],
    "custom": ["config", "instructions", "practice", "test", "debrief"],
}


# ---------------------------------------------------------------------------
# Main scaffolding function
# ---------------------------------------------------------------------------

def scaffold_experiment(
    experiment_name: str,
    experiment_type: str = "custom",
    modules: list[str] | None = None,
    output_dir: Path | None = None,
    scripts_dir: Path | None = None,
) -> dict:
    """Generate starter .iqx templates for an experiment.

    Args:
        experiment_name: Name for the experiment (used in filenames and comments).
        experiment_type: One of: iat, stroop, survey, rt_task, custom.
        modules: List of module roles to generate. Defaults per experiment type.
        output_dir: Directory to write files into (relative to scripts_dir or absolute).
        scripts_dir: Base scripts directory. Defaults to runner.config.SCRIPTS_DIR.

    Returns:
        Dict with 'created_files', 'experiment_type', 'modules',
        'main_file', and 'tester_files'.
    """
    if experiment_type not in SUPPORTED_TYPES:
        return {
            "error": f"Unknown experiment type: {experiment_type}. "
                     f"Supported: {', '.join(SUPPORTED_TYPES)}"
        }

    if modules is None:
        modules = list(DEFAULT_MODULES.get(experiment_type, DEFAULT_MODULES["custom"]))

    if scripts_dir is None:
        from .config import SCRIPTS_DIR
        scripts_dir = SCRIPTS_DIR

    if output_dir is None:
        dest = scripts_dir / experiment_name
    elif Path(output_dir).is_absolute():
        dest = Path(output_dir)
    else:
        dest = scripts_dir / output_dir

    dest.mkdir(parents=True, exist_ok=True)

    created_files = []
    include_files = []

    # Generate each module
    for role in modules:
        # Look up template: try paradigm-specific first, fall back to custom
        template = _TEMPLATES.get((experiment_type, role))
        if template is None:
            template = _TEMPLATES.get(("custom", role))
        if template is None:
            # Unknown role — generate a minimal stub
            template = _make_stub(experiment_name, role)

        content = template.format(experiment_name=experiment_name)
        filename = f"{experiment_name}_{role}_inc.iqx"
        filepath = dest / filename
        filepath.write_text(content, encoding="utf-8")
        created_files.append(str(filepath))
        include_files.append(filename)

    # Generate main.iqx
    main_content = _make_main(experiment_name, include_files, modules)
    main_path = dest / "main.iqx"
    main_path.write_text(main_content, encoding="utf-8")
    created_files.append(str(main_path))

    # Generate standalone testers for each module
    tester_files = []
    for role in modules:
        if role == "config":
            continue  # Config is included by everything, no standalone test needed
        tester_content = _make_tester(experiment_name, role)
        tester_path = dest / f"test_{role}.iqx"
        tester_path.write_text(tester_content, encoding="utf-8")
        created_files.append(str(tester_path))
        tester_files.append(str(tester_path))

    return {
        "experiment_name": experiment_name,
        "experiment_type": experiment_type,
        "modules": modules,
        "output_dir": str(dest),
        "created_files": created_files,
        "main_file": str(main_path),
        "tester_files": tester_files,
    }


def _make_main(experiment_name: str, include_files: list[str], modules: list[str]) -> str:
    """Generate the main.iqx that includes all modules."""
    includes = "\n".join(f'<include>"{f}"</include>' for f in include_files)

    # Build block list from modules that have blocks
    block_roles = [r for r in modules if r not in ("config",)]
    block_refs = "; ".join(
        f"{i+1}={experiment_name}_{role}_block"
        for i, role in enumerate(block_roles)
        if role != "config"
    )

    return f"""\
// Main experiment file for {experiment_name}
// This file includes all modules and defines the experiment flow.
// Modify the block order below to change the participant's experience.

{includes}

<expt>
/ blocks = [{block_refs}]
</expt>
"""


def _make_tester(experiment_name: str, role: str) -> str:
    """Generate a standalone tester for a single module."""
    return f"""\
// Standalone tester for the {role} module of {experiment_name}
// Run this to test the {role} module in isolation.
// Uses the config module for shared defaults.

<include>"{experiment_name}_config_inc.iqx"</include>
<include>"{experiment_name}_{role}_inc.iqx"</include>

<expt>
/ blocks = [1={experiment_name}_{role}_block]
</expt>
"""


def _make_stub(experiment_name: str, role: str) -> str:
    """Generate a minimal stub for an unknown module role."""
    return f"""\
// {role.capitalize()} module for {{experiment_name}}
// TODO: Add your {role} elements here.

<text {experiment_name}_{role}_text>
/ items = ("{role.capitalize()} placeholder — replace with actual content")
/ fontstyle = ("Arial", 4%)
/ position = (50%, 50%)
/ txcolor = black
</text>

<trial {experiment_name}_{role}_trial>
/ stimulustimes = [0={experiment_name}_{role}_text]
/ validresponse = (" ")
/ recorddata = false
</trial>

<block {experiment_name}_{role}_block>
/ trials = [1={experiment_name}_{role}_trial]
</block>
"""
