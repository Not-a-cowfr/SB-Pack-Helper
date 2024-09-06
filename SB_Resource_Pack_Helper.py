import os
import shutil
import json
import zipfile
import logging as log
from tkinter import Tk, filedialog, simpledialog, Checkbutton, BooleanVar, Toplevel, Button
from github import Github

""" Change the default before committing, zip=enabled, log=disabled debug=disabled """
create_log = True
create_zip = False
enable_debug = True
logger = None

g = Github()  # if the repo ever changes to need your github token, put it here
neurepo = g.get_repo("NotEnoughUpdates/NotEnoughUpdates-REPO")

def setup_logger(log_file_path, enable_debug):
    global logger
    logger = log.getLogger()

    if enable_debug:
        logger.setLevel(log.DEBUG)
    else:
        logger.setLevel(log.INFO)

    formatter = log.Formatter('%(asctime)s.%(msecs)03d [%(levelname)s] | %(message)s', datefmt='%H:%M:%S')

    file_handler = log.FileHandler(log_file_path)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = log.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

def select_folder():
    root = Tk()
    root.withdraw()
    folder_path = filedialog.askdirectory()
    root.destroy()
    return folder_path


def prompt_for_folder_name():
    root = Tk()
    root.withdraw()
    folder_name = simpledialog.askstring("Input", "Enter the name for the new folder:")
    root.destroy()
    return folder_name


def prompt_for_options():
    root = Tk()
    root.withdraw()
    options_window = Toplevel(root)

    options_window.title("File Creation Options")

    zip_var = BooleanVar(value=create_zip)
    log_var = BooleanVar(value=create_log)
    debug_var = BooleanVar(value=enable_debug)

    zip_checkbox = Checkbutton(options_window, text="Create Zip File", variable=zip_var)
    zip_checkbox.pack()

    log_checkbox = Checkbutton(options_window, text="Create Log File", variable=log_var)
    log_checkbox.pack()

    debug_checkbox = Checkbutton(options_window, text="Enable Debug Logs", variable=debug_var)
    debug_checkbox.pack()

    def confirm_options():
        global create_zip, create_log, enable_debug
        create_zip = zip_var.get()
        create_log = log_var.get()
        enable_debug = debug_var.get()
        options_window.destroy()

    confirm_button = Button(options_window, text="Confirm", command=confirm_options)
    confirm_button.pack()

    options_window.mainloop()


def get_unique_name(base_path, name_type="file/folder"):
    if not os.path.exists(base_path):
        return base_path

    base_name, ext = os.path.splitext(base_path)
    counter = 1

    while True:
        new_path = f"{base_name}({counter}){ext}"
        if not os.path.exists(new_path):
            if logger:
                renamed = os.path.basename(new_path)
                logger.warning(f"Avoided using duplicate {name_type} name, renamed to: {renamed}")
            return new_path
        counter += 1


def convert_json_to_properties(json_content, destination_properties_path, png_file):
    try:
        data = json.loads(json_content)
        item_id = data.get("itemid", "")
        file_name_lower = os.path.basename(destination_properties_path).replace('.properties', '').lower()
        texture_file_name = os.path.basename(png_file)
        with open(destination_properties_path, 'w') as properties_file:
            properties_file.write("type=item\n")
            if item_id:
                properties_file.write(f"items={item_id}\n")
            properties_file.write(f"texture={texture_file_name}\n")
            properties_file.write(f"nbt.ExtraAttributes.id={file_name_lower}\n")
    except json.JSONDecodeError:
        if logger:
            logger.error("Error decoding JSON content.")


def extract_files(source_folder, cit_folder, ctm_folder, exclude_files=None):
    if exclude_files is None:
        exclude_files = []

    png_files = []

    for root, _, files in os.walk(source_folder):
        for file in files:
            if file.lower().endswith('.png') and file.lower() not in exclude_files:
                source_file = os.path.join(root, file)
                relative_path = os.path.relpath(root, source_folder)
                file_base_name = file.lower().replace('.png', '')
                destination_dir = os.path.join(
                    ctm_folder if "dwarven_mines" in relative_path or "crystal_hollows" in relative_path else cit_folder,
                    relative_path, file_base_name)

                os.makedirs(destination_dir, exist_ok=True)
                destination_file = os.path.join(destination_dir, file.lower())
                shutil.copy2(source_file, destination_file)
                png_files.append((file.lower(), destination_dir))

    return png_files


def copy_files_or_use_local_properties(png_files, repo, cit_folder, ctm_folder):
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    local_properties_folders = {
        'crystal_hollows': os.path.join(current_script_dir, 'crystal_hollows_properties'),
        'dwarven_mines': os.path.join(current_script_dir, 'dwarven_mines_properties')
    }

    for file, destination_dir in png_files:
        item_name = file.replace('.png', '').lower()
        properties_file_lower = item_name + '.properties'
        local_properties_folder = None

        if "dwarven_mines" in destination_dir:
            local_properties_folder = local_properties_folders['dwarven_mines']
        elif "crystal_hollows" in destination_dir:
            local_properties_folder = local_properties_folders['crystal_hollows']

        if local_properties_folder:
            local_properties_path = os.path.join(local_properties_folder, properties_file_lower)
            if os.path.exists(local_properties_path):
                shutil.copy2(local_properties_path, os.path.join(destination_dir, properties_file_lower))
                if logger:
                    logger.info(f"Used local properties for {item_name} from {local_properties_folder}")
                continue

        try:
            json_file_path = f"items/{item_name.upper()}.json"
            file_content = repo.get_contents(json_file_path)
            json_content = file_content.decoded_content.decode('utf-8')
            destination_properties_path = os.path.join(destination_dir, properties_file_lower)
            convert_json_to_properties(json_content, destination_properties_path,
                                       os.path.join(destination_dir, file.lower()))
            if logger:
                logger.info(f"Converted {json_file_path} to {properties_file_lower} and moved to {destination_dir}")
        except Exception as e:
            if logger:
                logger.error(f"Could not find or convert {json_file_path}: {e}")


def file_exists_in_folder(file_name, folder):
    return os.path.exists(os.path.join(folder, file_name))


# Folder selection + fatal errors idk how to describe them
source_folder = select_folder()  # Prompt for user to select folder, log error if no folder is selected
if not source_folder:
    if logger:
        logger.fatal("No folder selected!")
    exit()

    exit()

destination_folder_name = prompt_for_folder_name()
destination_folder_name = prompt_for_folder_name()  # Prompts user for folder name
if not destination_folder_name:
    if logger:
        logger.fatal("No folder name provided!")
       logger.fatal("No folder name provided!")
    exit()

prompt_for_options()

output_folder = os.path.join(os.getcwd(), 'output')
os.makedirs(output_folder, exist_ok=True)

if create_log:
    log_file_path = get_unique_name(os.path.join(output_folder, f'{destination_folder_name}.log'), "log file")
    setup_logger(log_file_path, enable_debug)

    if not enable_debug:
        logger.setLevel(log.INFO)

base_folder = get_unique_name(os.path.join(output_folder, destination_folder_name), "folder")
if not base_folder:
    if logger:
        logger.error("Failed to generate a unique folder name.")
    exit()

mcpatcher_cit_folder = os.path.join(base_folder, 'assets', 'minecraft', 'mcpatcher', 'cit')
mcpatcher_ctm_folder = os.path.join(base_folder, 'assets', 'minecraft', 'mcpatcher', 'ctm')
os.makedirs(mcpatcher_cit_folder, exist_ok=True)
os.makedirs(mcpatcher_ctm_folder, exist_ok=True)

shutil.copy2(os.path.join(source_folder, 'pack.png'), base_folder)
if logger:
    logger.info(f"Moved pack.png to {base_folder}")

if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pack.mcmeta')):
    shutil.copy2(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pack.mcmeta'), base_folder)
    if logger:
        logger.info(f"Moved pack.mcmeta to {base_folder}")

creditsfile = False
if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'credits.txt')):
    shutil.copy2(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'credits.txt'), base_folder)
    if logger:
        logger.info(f"Cloned credits.txt to {base_folder}")
    creditsfile = True
else:
    if logger:
        logger.warning("Didn't find credits.txt, continuing without it") # feels not important enough for a warning, but also more important than just an info log, idk

# The code gets tuah point where it makes the actual files
exclude_files = ['pack.png', 'pack.mcmeta']
png_files = extract_files(source_folder, mcpatcher_cit_folder, mcpatcher_ctm_folder, exclude_files)
copy_files_or_use_local_properties(png_files, neurepo, mcpatcher_cit_folder, mcpatcher_ctm_folder)

# file checks
# todo: delete cit folder and all children if empty
if os.path.exists(mcpatcher_ctm_folder) and not os.listdir(mcpatcher_ctm_folder):
    os.rmdir(mcpatcher_ctm_folder)
    if logger:
        logger.warning("ctm folder was empty and has been removed, if this is a mistake, report it")

if create_zip:
    zip_file_name = get_unique_name(os.path.join(output_folder, f"{destination_folder_name}.zip"), "zip file")
    with zipfile.ZipFile(zip_file_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(base_folder):
            for file in files:
                zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), os.getcwd()))
    if logger:
        logger.info(f"Folder {destination_folder_name} was zipped into {zip_file_name}")

all_files_copied = True
if not file_exists_in_folder('pack.png', base_folder):
    if logger:
        logger.error("pack.png was not moved correctly.")
    all_files_copied = False

if os.path.exists(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pack.mcmeta')) and not file_exists_in_folder(
        'pack.mcmeta', base_folder):
    if logger:
        logger.error("pack.mcmeta was not moved correctly.")
    all_files_copied = False

if creditsfile and not file_exists_in_folder('credits.txt', base_folder):
    if logger:
        logger.error("credits.txt was not moved correctly.")
    all_files_copied = False

if not all_files_copied:
    if logger:
        logger.error("Some files were not successfully copied. Please check the errors above.")
else:
    if logger:
        logger.info("All files were successfully copied and verified!")
