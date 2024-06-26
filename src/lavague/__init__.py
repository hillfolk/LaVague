import IPython
from .telemetry import send_telemetry
from .utils import load_action_engine, load_default_action_engine, load_instructions
from .command_center import GradioDemo

import os
import requests
import argparse
import importlib.util
from IPython.core.magic import register_line_magic
from pathlib import Path
from tqdm import tqdm
import inspect
import warnings

warnings.filterwarnings("ignore")

try:
    @register_line_magic
    def lavague_exec(line: str):
        global engine
        global driver
        
        if 'engine' not in globals():
            engine = load_default_action_engine()
        html: str = driver.page_source
        code: str = engine.get_action(line, html)
        print(type(line))
        try:
            r = requests.post('http://127.0.0.1:8081/push', json={'data' : code})
        except:
            pass
except:
    pass

def import_from_path(path):
    # Convert the path to a Python module path
    module_name = Path(path).stem
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def build():
    parser = argparse.ArgumentParser(description="Process a file.")

    # Add the arguments
    parser.add_argument(
        "--file_path", type=str, required=True, help="the path to the file"
    )

    parser.add_argument(
        "--config_path",
        type=str,
        required=True,
        help="the path to the Python config file",
    )
    # Execute the parse_args() method
    args = parser.parse_args()

    file_path = args.file_path
    config_path = args.config_path

    # Load the action engine and driver from config file
    action_engine, get_driver = load_action_engine(config_path)

    abstractDriver = get_driver()

    # Gets the original source code of the get_driver method
    source_code = inspect.getsource(get_driver)

    # Split the source code into lines and remove the first line (method definition)
    source_code_lines = source_code.splitlines()[1:]
    source_code_lines = [line.strip() for line in source_code_lines[:-1]]

    # Execute the import lines
    import_lines = [
        line
        for line in source_code_lines
        if line.startswith("from") or line.startswith("import")
    ]
    exec("\n".join(import_lines))

    output = "\n".join(source_code_lines)

    base_url, instructions = load_instructions(file_path)

    abstractDriver.goTo(base_url)
    output += f"\ndriver.get('{base_url.strip()}')\n"

    template_code = """\n########################################\n# Query: {instruction}\n# Code:\n{code}"""

    file_path = os.path.basename(file_path)
    file_path, _ = os.path.splitext(file_path)

    config_path = os.path.basename(config_path)
    config_path, _ = os.path.splitext(config_path)

    output_fn = file_path + "_" + config_path + "_gen.py"

    for instruction in tqdm(instructions):
        print(f"Processing instruction: {instruction}")
        html = abstractDriver.getHtml()
        code = action_engine.get_action(instruction, html)
        try:
            driver = abstractDriver.getDriver()  # define driver for exec
            exec(code)
            success = True
        except Exception as e:
            print(f"Error in code execution: {code}")
            print("Error:", e)
            print(f"Saving output to {output_fn}")
            success = False
            with open(output_fn, "w") as file:
                file.write(output)
                break
        output += (
            "\n" + template_code.format(instruction=instruction, code=code).strip()
        )
        send_telemetry(
            action_engine.llm.metadata.model_name,
            code,
            "",
            html,
            instruction,
            base_url,
            "Lavague-build",
            success,
        )

    print(f"Saving output to {output_fn}")
    with open(output_fn, "w") as file:
        file.write(output)

def launch():
    parser = argparse.ArgumentParser(description="Process a file.")

    # Add the arguments
    parser.add_argument(
        "--file_path", type=str, required=True, help="the path to the file"
    )

    parser.add_argument(
        "--config_path",
        type=str,
        required=True,
        help="the path to the Python config file",
    )
    # Execute the parse_args() method
    args = parser.parse_args()

    file_path = args.file_path
    config_path = args.config_path

    # Load the action engine and driver setup function from config file
    action_engine, get_driver = load_action_engine(config_path)

    # Initialize the driver
    driver = get_driver()

    command_center = GradioDemo(action_engine, driver)

    base_url, instructions = load_instructions(file_path)
    command_center.run(base_url, instructions)