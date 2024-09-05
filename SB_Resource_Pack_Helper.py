import os
import shutil
import json
import zipfile
import time
import logging
from tkinter import Tk, filedialog, simpledialog
from github import Github

g = Github()
neurepo = g.get_repo("NotEnoughUpdates/NotEnoughUpdates-REPO")

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

def copy_files_or_use_local_properties(png_files, repo, cit_folder, ctm_folder, delay_between_copies=False):
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
                logger.info(f"Used local properties for {item_name} from {local_properties_folder}")
                if delay_between_copies:
                    time.sleep(2)
                continue

        try:
            json_file_path = f"items/{item_name.upper()}.json"
            file_content = repo.get_contents(json_file_path)
            json_content = file_content.decoded_content.decode('utf-8')
            destination_properties_path = os.path.join(destination_dir, properties_file_lower)
            convert_json_to_properties(json_content, destination_properties_path,
                                       os.path.join(destination_dir, file.lower()))
            logger.info(f"Converted {json_file_path} to {properties_file_lower} and moved to {destination_dir}")
        except Exception as e:
            logger.error(f"Could not find or convert {json_file_path}: {e}")

        if delay_between_copies:
            time.sleep(2)

def file_exists_in_folder(file_name, folder):
    return os.path.exists(os.path.join(folder, file_name))

def setup_logger(log_file_path):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(log_file_path, mode='a')
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

source_folder = select_folder()
if not source_folder:
    logger.error("No folder selected!")
    exit()

current_script_dir = os.path.dirname(os.path.abspath(__file__))
pack_png_path = os.path.join(source_folder, 'pack.png')
pack_mcmeta_path = os.path.join(current_script_dir, 'pack.mcmeta')
credits_source_path = os.path.join(current_script_dir, 'credits.txt')

if not os.path.exists(pack_png_path):
    logger.error("pack.png not found!")
    exit()

destination_folder_name = prompt_for_folder_name()
if not destination_folder_name:
    logger.error("No folder name provided!")
    exit()

output_folder = os.path.join(os.getcwd(), 'output')
os.makedirs(output_folder, exist_ok=True)

base_folder = os.path.join(output_folder, destination_folder_name)
mcpatcher_cit_folder = os.path.join(base_folder, 'assets', 'minecraft', 'mcpatcher', 'cit')
mcpatcher_ctm_folder = os.path.join(base_folder, 'assets', 'minecraft', 'mcpatcher', 'ctm')
os.makedirs(mcpatcher_cit_folder, exist_ok=True)
os.makedirs(mcpatcher_ctm_folder, exist_ok=True)

log_file_path = os.path.join(output_folder, f"{destination_folder_name}.log")
logger = setup_logger(log_file_path)

shutil.copy2(pack_png_path, base_folder)
logger.info(f"Moved pack.png to {base_folder}")

if os.path.exists(pack_mcmeta_path):
    shutil.copy2(pack_mcmeta_path, base_folder)
    logger.info(f"Moved pack.mcmeta to {base_folder}")

creditsfile = False
if os.path.exists(credits_source_path):
    shutil.copy2(credits_source_path, base_folder)
    logger.info(f"Cloned credits.txt to {base_folder}")
    creditsfile = True

exclude_files = ['pack.png', 'pack.mcmeta']
png_files = extract_files(source_folder, mcpatcher_cit_folder, mcpatcher_ctm_folder, exclude_files)

copy_files_or_use_local_properties(png_files, neurepo, mcpatcher_cit_folder, mcpatcher_ctm_folder, delay_between_copies=True)

if os.path.exists(mcpatcher_ctm_folder) and not os.listdir(mcpatcher_ctm_folder):
    os.rmdir(mcpatcher_ctm_folder)
    logger.warning("ctm folder was empty and has been removed, if this is a mistake, report it")

zip_file_name = f"{destination_folder_name}.zip"
zip_file_path = os.path.join(output_folder, zip_file_name)
with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, _, files in os.walk(base_folder):
        for file in files:
            zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), os.getcwd()))

logger.info(f"Folder {destination_folder_name} was zipped into {zip_file_path}")

all_files_copied = True
if not file_exists_in_folder('pack.png', output_folder):
    logger.error("pack.png was not successfully copied!")
    all_files_copied = False
if os.path.exists(pack_mcmeta_path) and not file_exists_in_folder('pack.mcmeta', output_folder):
    logger.error("pack.mcmeta was not successfully copied!")
    all_files_copied = False
if creditsfile and not file_exists_in_folder('credits.txt', output_folder):
    logger.error("credits.txt was not successfully copied!")
    all_files_copied = False

if all_files_copied:
    logger.info("All files were successfully copied and verified!")
else:
    logger.error("Some files were not successfully copied. Please check the errors above.")
