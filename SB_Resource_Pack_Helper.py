import os
import shutil
import json
import zipfile
import time
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
        print("ERROR: Error decoding JSON content.")

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


def copy_files_or_use_local_properties(png_files, repo, cit_folder, ctm_folder,
                                       delay_between_copies=False):
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
                print(f"SUCCESS: Used local properties for {item_name} from {local_properties_folder}")
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
            print(f"SUCCESS: Converted {json_file_path} to {properties_file_lower} and moved to {destination_dir}")
        except Exception as e:
            print(f"ERROR: Could not find or convert {json_file_path}: {e}")

        if delay_between_copies:
            time.sleep(2)

def file_exists_in_folder(file_name, folder):
    return os.path.exists(os.path.join(folder, file_name))

source_folder = select_folder()
if not source_folder:
    print("ERROR: No folder selected!")
    exit()

current_script_dir = os.path.dirname(os.path.abspath(__file__))
pack_png_path = os.path.join(source_folder, 'pack.png')
pack_mcmeta_path = os.path.join(current_script_dir, 'pack.mcmeta')
credits_source_path = os.path.join(current_script_dir, 'credits.txt')

if not os.path.exists(pack_png_path):
    print("ERROR: pack.png not found!")
    exit()

destination_folder_name = prompt_for_folder_name()
if not destination_folder_name:
    print("ERROR: no folder name provided!")
    exit()

base_folder = os.path.join(os.getcwd(), destination_folder_name)
mcpatcher_cit_folder = os.path.join(base_folder, 'assets', 'minecraft', 'mcpatcher', 'cit')
mcpatcher_ctm_folder = os.path.join(base_folder, 'assets', 'minecraft', 'mcpatcher', 'ctm')
os.makedirs(mcpatcher_cit_folder, exist_ok=True)
os.makedirs(mcpatcher_ctm_folder, exist_ok=True)

shutil.copy2(pack_png_path, base_folder)
print(f"SUCCESS: Moved pack.png to {base_folder}")

if os.path.exists(pack_mcmeta_path):
    shutil.copy2(pack_mcmeta_path, base_folder)
    print(f"SUCCESS: Moved pack.mcmeta to {base_folder}")

creditsfile = False
if os.path.exists(credits_source_path):
    shutil.copy2(credits_source_path, base_folder)
    print(f"SUCCESS: Cloned credits.txt to {base_folder}")
    creditsfile = True

exclude_files = ['pack.png', 'pack.mcmeta']
png_files = extract_files(source_folder, mcpatcher_cit_folder, mcpatcher_ctm_folder, exclude_files)

copy_files_or_use_local_properties(png_files, neurepo, mcpatcher_cit_folder, mcpatcher_ctm_folder,
                                   delay_between_copies=True)

zip_file_name = f"{destination_folder_name}.zip"
with zipfile.ZipFile(os.path.join(os.getcwd(), zip_file_name), 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, _, files in os.walk(base_folder):
        for file in files:
            zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), os.getcwd()))

print(f"SUCCESS: Folder {destination_folder_name} was zipped into {zip_file_name}")

all_files_copied = True
if not file_exists_in_folder('pack.png', base_folder):
    print("ERROR: pack.png was not successfully copied!")
    all_files_copied = False
if os.path.exists(pack_mcmeta_path) and not file_exists_in_folder('pack.mcmeta', base_folder):
    print("ERROR: pack.mcmeta was not successfully copied!")
    all_files_copied = False
if creditsfile and not file_exists_in_folder('credits.txt', base_folder):
    print("ERROR: credits.txt was not successfully copied!")
    all_files_copied = False

if all_files_copied:
    print("All files were successfully copied and verified!")
else:
    print("Some files were not successfully copied. Please check the errors above.")
