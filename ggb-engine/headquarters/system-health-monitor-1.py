import os
import re
import ast
import inspect
import sys
from datetime import datetime
import logging

# --- Configuration ---
PLATFORM_SCRIPTS_DIR = "/Users/darrylsmac/gullahgeecheebiz-site/ggb-engine/platforms/" # Assuming platform scripts are here
PLATFORM_FILENAMES = {
    "platform1": "platform1_app.py",
    "platform2": "platform2_app.py",
    "platform3": "platform3_app.py",
    "platform4": "platform4_app.py",
    "platform5": "platform5_app.py",
    "platform6": "platform6_app.py",
    "platform7": "platform7_app.py",
    "platform8": "platform8_app.py",
    "platform9": "platform9_app.py",
}
LOG_DIR = "/Users/darrylsmac/gullahgeecheebiz-site/ggb-engine/headquarters/logs/health-monitor/"

# --- Setup Logging ---
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "add_health_endpoints.log")),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('AddHealthEndpoints')

# --- Health Endpoint Code Template ---
HEALTH_ENDPOINT_CODE = """
@app.route('/health')
def health_check():
    \"\"\"
    Returns the health status of the application.
    \"\"\"
    # Calculate uptime
    uptime_seconds = (datetime.now() - app.start_time).total_seconds()
    days, remainder = divmod(int(uptime_seconds), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"

    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "uptime": uptime_str,
        # Add more specific checks if needed for this platform
        # e.g., "database_connected": check_db_connection(),
        # "cache_reachable": check_cache_connection()
    })
"""

# --- Helper Functions ---
def validate_python_syntax(code_string, filename="<string>"):
    """Validates Python syntax of a given code string."""
    try:
        ast.parse(code_string)
        return True, "Syntax OK"
    except SyntaxError as e:
        return False, f"Syntax Error in {filename}: {e}"
    except Exception as e:
        return False, f"Unexpected error during syntax validation for {filename}: {e}"

def find_flask_app_variable(script_content):
    """
    Attempts to find the variable name for the Flask app instance (e.g., 'app = Flask(__name__)').
    """
    match = re.search(r'(\w+)\s*=\s*Flask\s*\(\s*__name__\s*\)', script_content)
    if match:
        return match.group(1)
    return None

def add_start_time_to_app_init(script_content, app_var_name):
    """
    Adds `app.start_time = datetime.now()` right after `app = Flask(__name__)`.
    """
    if f"{app_var_name} = Flask(__name__)" not in script_content:
        return script_content, False

    lines = script_content.splitlines()
    new_lines = []
    added = False
    for line in lines:
        new_lines.append(line)
        if f"{app_var_name} = Flask(__name__)" in line and not added:
            # Check if app.start_time is already set
            next_line_index = lines.index(line) + 1
            if next_line_index < len(lines) and f"{app_var_name}.start_time =" in lines[next_line_index]:
                logger.info(f"'{app_var_name}.start_time' already present. Skipping.")
                added = True # Mark as added to prevent duplicate, even if already exists
            else:
                indent = len(line) - len(line.lstrip())
                new_lines.append(f"{' '*indent}{app_var_name}.start_time = datetime.now()")
                logger.info(f"Added '{app_var_name}.start_time = datetime.now()' to app initialization.")
                added = True
    return "\n".join(new_lines), added


def add_imports_if_missing(script_content):
    """
    Adds `from flask import Flask, jsonify` and `from datetime import datetime` if they are missing.
    Ensures `jsonify` is imported for the health endpoint.
    """
    new_content = script_content
    added_flask_import = False
    added_datetime_import = False

    # Check for Flask and jsonify
    if "from flask import Flask" not in new_content and "import Flask" not in new_content:
        # Check for from flask import Flask, jsonify
        match = re.search(r'from flask import (.*)', new_content)
        if match:
            imports = [i.strip() for i in match.group(1).split(',')]
            if 'jsonify' not in imports:
                # Add jsonify to existing import
                new_imports = ', '.join(sorted(imports + ['jsonify', 'request'])) # Added request as it's common
                new_content = re.sub(r'from flask import (.*)', f'from flask import {new_imports}', new_content, 1)
                logger.info("Added 'jsonify' to existing Flask import.")
                added_flask_import = True
            if 'Flask' not in imports: # Should not happen if `Flask` is already in the original import
                 logger.warning("Flask itself not found in import, this might be an issue.")
        else:
            # Add full import statement at the top
            new_content = "from flask import Flask, jsonify, request\n" + new_content
            logger.info("Added 'from flask import Flask, jsonify, request'.")
            added_flask_import = True

    elif "from flask import Flask, jsonify" not in new_content: # Flask is imported, but jsonify might be missing
        if "from flask import Flask" in new_content:
            new_content = new_content.replace("from flask import Flask", "from flask import Flask, jsonify, request", 1)
            logger.info("Updated 'from flask import Flask' to include 'jsonify, request'.")
            added_flask_import = True
        elif "import Flask" in new_content:
            logger.warning("Found 'import Flask', but Flask apps typically use 'from flask import Flask'. Cannot auto-add jsonify safely.")
            # This case might require manual intervention or more complex AST manipulation

    # Check for datetime import
    if "from datetime import datetime" not in new_content:
        # Find a good place to insert, e.g., after other imports or at the top
        if "import os" in new_content: # Common import, try to place after it
            new_content = new_content.replace("import os", "import os\nfrom datetime import datetime", 1)
            logger.info("Added 'from datetime import datetime' after 'import os'.")
            added_datetime_import = True
        elif "import" in new_content or "from" in new_content: # Find first import statement
             first_import_match = re.search(r'^(?:import|from).*', new_content, re.MULTILINE)
             if first_import_match:
                 insert_pos = first_import_match.start()
                 new_content = new_content[:insert_pos] + "from datetime import datetime\n" + new_content[insert_pos:]
                 logger.info("Added 'from datetime import datetime' after first import.")
                 added_datetime_import = True
             else: # No imports found, add at the top
                new_content = "from datetime import datetime\n" + new_content
                logger.info("Added 'from datetime import datetime' at the top.")
                added_datetime_import = True
        else: # No imports found, add at the top
            new_content = "from datetime import datetime\n" + new_content
            logger.info("Added 'from datetime import datetime' at the top.")
            added_datetime_import = True

    return new_content, added_flask_import or added_datetime_import

def process_platform_script(filepath):
    """
    Reads a platform script, adds the /health endpoint if not present,
    adds `app.start_time`, and necessary imports.
    """
    logger.info(f"Processing script: {filepath}")
    try:
        with open(filepath, 'r') as f:
            original_content = f.read()

        new_content = original_content
        changes_made = False

        # 1. Find Flask app variable name
        app_var_name = find_flask_app_variable(new_content)
        if not app_var_name:
            logger.warning(f"Could not find 'app = Flask(__name__)' in {filepath}. Skipping.")
            return False, "Flask app variable not found"

        # 2. Add app.start_time
        new_content, start_time_added = add_start_time_to_app_init(new_content, app_var_name)
        if start_time_added:
            changes_made = True

        # 3. Add necessary imports
        new_content, imports_added = add_imports_if_missing(new_content)
        if imports_added:
            changes_made = True

        # 4. Check for existing /health endpoint
        if "@app.route('/health')" in new_content or f"@{app_var_name}.route('/health')" in new_content:
            logger.info(f"'/health' endpoint already present in {filepath}. Skipping addition.")
        else:
            # Find a good place to insert. Often, endpoints are defined after app initialization
            # or after a few imports/configurations.
            # A simple approach: find the last '@app.route' and insert after it,
            # or insert near the end of the file before `if __name__ == '__main__':`
            insert_point = -1
            last_route_match = None
            for m in re.finditer(r'@\w+\.route\(', new_content):
                last_route_match = m
            if last_route_match:
                insert_point = last_route_match.end() # Point after the decorator line
                # Find the end of the function definition block
                try:
                    # Parse the AST to find the end of the last function with a route decorator
                    tree = ast.parse(new_content)
                    last_func_end_line = -1
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            for decorator in node.decorator_list:
                                if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                                    if decorator.func.attr == 'route':
                                        last_func_end_line = max(last_func_end_line, node.lineno + len(inspect.getsource(node)) - 1)
                                        break
                    if last_func_end_line != -1:
                        lines = new_content.splitlines()
                        # Find the actual character index for the start of the line after the function
                        current_char_count = 0
                        for i, line in enumerate(lines):
                            current_char_count += len(line) + 1 # +1 for newline character
                            if i + 1 == last_func_end_line: # After the function definition ends
                                insert_point = current_char_count
                                break
                    if insert_point == -1: # Fallback if AST parsing failed for exact insert point
                        insert_point = new_content.rfind("if __name__ == '__main__':")
                        if insert_point == -1:
                            insert_point = len(new_content) # Insert at end if no main block
                        else:
                             # Insert before `if __name__ == '__main__':` block, plus a couple newlines
                            insert_point = new_content.rfind("if __name__ == '__main__':") - 1
                            insert_point = new_content.rfind("\n", 0, insert_point) + 1 # Go to start of line before if main

                except Exception as e:
                    logger.warning(f"Error parsing AST for insert point in {filepath}: {e}. Inserting at end of file.")
                    insert_point = new_content.rfind("if __name__ == '__main__':")
                    if insert_point == -1:
                        insert_point = len(new_content)
                    else:
                        insert_point = new_content.rfind("\n", 0, insert_point) + 1


            else:
                # No routes found, try to insert before 'if __name__ == "__main__":' or at the very end
                insert_point = new_content.rfind("if __name__ == '__main__':")
                if insert_point == -1:
                    insert_point = len(new_content) # Insert at end if no main block
                else:
                    # Insert before `if __name__ == '__main__':` block, plus a couple newlines
                    insert_point = new_content.rfind("\n", 0, insert_point) # Find newline before the block
                    if insert_point == -1: insert_point = 0 # If main block is at the very beginning
                    insert_point += 1 # Position at the start of that line


            # Prepare endpoint code with correct app variable name
            endpoint_code_for_script = HEALTH_ENDPOINT_CODE.replace("@app.route", f"@{app_var_name}.route")
            
            # Insert the code
            new_content = (
                new_content[:insert_point].rstrip() +
                "\n\n" +  # Ensure separation
                endpoint_code_for_script +
                "\n" + # Ensure newline after the new code
                new_content[insert_point:].lstrip()
            )
            logger.info(f"Added '/health' endpoint to {filepath}.")
            changes_made = True

        if changes_made:
            # Validate syntax of the modified content
            is_valid, validation_msg = validate_python_syntax(new_content, filepath)
            if not is_valid:
                logger.error(f"Syntax validation FAILED for {filepath} after modification: {validation_msg}")
                logger.warning(f"Reverting changes for {filepath} due to syntax error.")
                # Optionally write the error content to a debug file
                with open(filepath + ".error", "w") as f:
                    f.write(new_content)
                return False, validation_msg # Don't write bad content
            else:
                logger.info(f"Syntax validated for {filepath} after modification: {validation_msg}")
                # Write the modified content back
                with open(filepath, 'w') as f:
                    f.write(new_content)
                logger.info(f"Successfully updated {filepath}.")
                return True, "Endpoint added and validated"
        else:
            logger.info(f"No changes needed for {filepath}.")
            return False, "No changes needed"

    except FileNotFoundError:
        logger.error(f"Script not found: {filepath}")
        return False, "File not found"
    except Exception as e:
        logger.error(f"An error occurred while processing {filepath}: {e}", exc_info=True)
        return False, f"Error processing file: {e}"

def main():
    logger.info("Starting to add /health endpoints to platform scripts.")
    processed_count = 0
    success_count = 0

    for platform_name, script_filename in PLATFORM_FILENAMES.items():
        filepath = os.path.join(PLATFORM_SCRIPTS_DIR, script_filename)
        processed_count += 1
        status, message = process_platform_script(filepath)
        if status:
            success_count += 1
            logger.info(f"[{platform_name}] SUCCESS: {message}")
        else:
            logger.error(f"[{platform_name}] FAILED: {message}")

    logger.info(f"Finished processing. {success_count}/{processed_count} scripts updated successfully.")

if __name__ == "__main__":
    # Ensure Flask and jsonify are available for testing the health endpoint locally if needed
    # This script modifies files, so ensure it's run in a controlled environment.
    main()