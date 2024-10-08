import os
import shutil
import json
import zipfile
import logging as log
from tkinter import Tk, filedialog, simpledialog,  Checkbutton, IntVar, Label, Button
from github import Github

g = Github()  # if the repo ever changes to need your github token, put it here
neurepo = g.get_repo("NotEnoughUpdates/NotEnoughUpdates-REPO")

enable_zip = True
enable_log = False
enable_debug = False
logger = None

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

def show_options_popup():
    root = Tk()
    root.title("Configuration")

    zip_var = IntVar(value=1)
    log_var = IntVar(value=0)
    debug_var = IntVar(value=0)

    Label(root, text="Enable options for your task:").pack()

    Checkbutton(root, text="Create zip file", variable=zip_var).pack()
    Checkbutton(root, text="Create log file", variable=log_var).pack()
    Checkbutton(root, text="Enable debug logs", variable=debug_var).pack()

    def on_submit():
        global create_zip, create_log, enable_debug
        create_zip = zip_var.get() == 1
        create_log = log_var.get() == 1
        enable_debug = debug_var.get() == 1
        root.destroy()

    Button(root, text="Submit", command=on_submit).pack()

    root.mainloop()

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
                global destination_dir
                destination_dir = os.path.join(
                    ctm_folder if "dwarven_mines" in relative_path or "crystal_hollows" in relative_path else cit_folder,
                    relative_path, file_base_name)

                os.makedirs(destination_dir, exist_ok=True)
                destination_file = os.path.join(destination_dir, file.lower())
                shutil.copy2(source_file, destination_file)
                png_files.append((file.lower(), destination_dir))

    return png_files

def copy_files_or_use_local_properties(png_files, repo):
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




# Main script
source_folder = select_folder()
if not source_folder:
    if logger:
        logger.fatal("No folder selected!")
    exit()

destination_folder_name = prompt_for_folder_name()
if not destination_folder_name:
    if logger:
        logger.fatal("No folder name provided!")
    exit()

show_options_popup()

output_folder = os.path.join(os.getcwd(), 'output')
log_name = get_unique_name(destination_folder_name)
os.makedirs(output_folder, exist_ok=True)

if create_log:
    log_file_path = get_unique_name(os.path.join(output_folder, f'{destination_folder_name}.log'), "log file")
    setup_logger(log_file_path, enable_debug)

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
        logger.warning("Didn't find credits.txt, continuing without it")

exclude_files = ['pack.png', 'pack.mcmeta']
png_files = extract_files(source_folder, mcpatcher_cit_folder, mcpatcher_ctm_folder, exclude_files)

copy_files_or_use_local_properties(png_files, neurepo)

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
if not file_exists_in_folder('pack.png', destination_dir):
    if logger:
        logger.error(f"pack.png was not cloned into {destination_dir}.")
    all_files_copied = False

if os.path.exists(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pack.mcmeta')) and not file_exists_in_folder(
        'pack.mcmeta', destination_dir):
    if logger:
        logger.error(f"pack.mcmeta was not cloned into {destination_dir}.")
    all_files_copied = False

if creditsfile and not file_exists_in_folder('credits.txt', destination_dir):
    if logger:
        logger.error(f"credits.txt was not cloned into {destination_dir}.")
    all_files_copied = False

if not all_files_copied:
    if logger:
        logger.error("Some files were not successfully copied. Please check the errors above.")
else:
    if logger:
        logger.info("All files were successfully copied and verified!")
