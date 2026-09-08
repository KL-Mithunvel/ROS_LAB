"""
main.py — entry point for the mobile-robot mechatronics calculator.

Menu-driven, built on the klm_menu engine:

    Main menu
      -> All calculations            (pick one)
           -> View answer only
           -> View answer with full steps
           -> Edit parameters used here
           -> Run / recalculate
      -> Edit robot parameters
      -> Print all parameters
      -> Save / reload params.yaml

Run:   python main.py
"""

import string

import klm_menu
import parameters
import calculations

# Single-letter hotkeys for the calculation list. 'b' is reserved for "Back".
HOTKEYS = [c for c in string.ascii_lowercase if c != "b"]

MAIN = "main"
CALC_LIST = "calc_list"


# --------------------------------------------------------------------------- #
# Menu system (generated from calculations.CALCS)
# --------------------------------------------------------------------------- #

def build_menu_system():
    if len(calculations.CALCS) > len(HOTKEYS):
        raise RuntimeError("more calculations than available hotkeys - extend HOTKEYS")

    menu_system = {}
    calc_list_options = []

    for calc, hotkey in zip(calculations.CALCS, HOTKEYS):
        sub_name = f"calc_{calc.id}"
        calc_list_options.append([f"menu:{sub_name}", calc.title, hotkey])
        menu_system[sub_name] = {
            "menu": calc.title,
            "name": sub_name,
            "options": [
                [f"ans_{calc.id}", "View answer only", "a"],
                [f"steps_{calc.id}", "View answer with full steps", "s"],
                [f"edit_{calc.id}", "Edit parameters used here", "e"],
                [f"run_{calc.id}", "Run / recalculate", "r"],
            ],
            "back_option": True,
            "back_to": CALC_LIST,
        }

    menu_system[MAIN] = {
        "menu": "Mobile Robot Mechatronics Calculator",
        "name": MAIN,
        "options": [
            ["menu:calc_list", "All calculations", "c"],
            ["edit_all", "Edit robot parameters", "e"],
            ["print_all", "Print all parameters", "p"],
            ["save_params", "Save parameters to params.yaml", "v"],
            ["load_params", "Reload parameters from params.yaml", "l"],
            ["exit", "Exit", "x"],
        ],
        "back_option": False,
        "back_to": None,
    }
    menu_system[CALC_LIST] = {
        "menu": "All Calculations",
        "name": CALC_LIST,
        "options": calc_list_options,
        "back_option": True,
        "back_to": MAIN,
    }
    return menu_system


# --------------------------------------------------------------------------- #
# Actions
# --------------------------------------------------------------------------- #

def show_result(calc, params, steps):
    """Compute a calculation and print it (bare answer or full steps)."""
    flat = parameters.resolve(params)
    try:
        result = calc.fn(flat)
    except (ValueError, ZeroDivisionError, KeyError) as exc:
        print(f"\n  Cannot compute: {exc}")
        print("  Fix that parameter (Edit parameters used here) and try again.\n")
        return
    print()
    print(calculations.render_steps(result) if steps else calculations.render_answer(result))
    print()


def dispatch(cmd, state):
    """Handle one menu command. Return False to quit, True to keep going."""
    params = state["params"]

    if cmd == "exit":
        return False
    if cmd == "edit_all":
        parameters.edit_all(params)
        return True
    if cmd == "print_all":
        parameters.print_all(params)
        return True
    if cmd == "save_params":
        parameters.save(params)
        return True
    if cmd == "load_params":
        state["params"] = parameters.load()
        print("Reloaded params.yaml.")
        return True

    # calculation actions:  <action>_<calc id>
    action, _, calc_id = cmd.partition("_")
    calc = calculations.CALCS_BY_ID.get(calc_id)
    if calc is None:
        print(f"Unknown command: {cmd}")
        return True

    if action == "edit":
        parameters.edit_subset(params, calc.uses)
    elif action in ("ans", "run"):
        show_result(calc, params, steps=False)
    elif action == "steps":
        show_result(calc, params, steps=True)
    else:
        print(f"Unknown action: {cmd}")
    return True


# --------------------------------------------------------------------------- #
# Menu loop
# --------------------------------------------------------------------------- #

def show_menu(menu_system, state):
    menu_name = MAIN
    running = True
    while running:
        cmd, menu_name = klm_menu.present_menu(menu_name, menu_system)
        running = dispatch(cmd, state)


def main():
    state = {"params": parameters.load()}
    menu_system = build_menu_system()
    print(f"\nLoaded {len(calculations.CALCS)} calculations. "
          f"Parameters read from params.yaml.")
    show_menu(menu_system, state)
    print("Done.")


if __name__ == "__main__":
    main()
