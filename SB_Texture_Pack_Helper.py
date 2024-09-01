import os
import shutil
import json
import zipfile
from tkinter import Tk, filedialog, simpledialog
from github import Github

# Authenticate and access the repository
g = Github()  # You can pass your GitHub token here if needed, e.g., Github("your_token")
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
            properties_file.write(f"type=item\n")
            if item_id:
                properties_file.write(f"items={item_id}\n")
            properties_file.write(f"texture={texture_file_name}\n")
            properties_file.write(f"nbt.ExtraAttributes.id={file_name_lower}\n")
    except json.JSONDecodeError:
        print(f"\nERROR: Error decoding JSON content.\n")

def extract_files(source_folder, cit_folder, ctm_folder, exclude_files=None):
    png_files = []
    
    if exclude_files is None:
        exclude_files = []

    for root, _, files in os.walk(source_folder):
        for file in files:
            if file.lower().endswith('.png') and file.lower() not in exclude_files:
                source_file = os.path.join(root, file)
                relative_path = os.path.relpath(root, source_folder)
                
                # Create a directory named after the base name of the file
                file_base_name = file.lower().replace('.png', '')
                destination_dir = os.path.join(cit_folder if "dwarven_mines" not in relative_path and "crystal_hollows" not in relative_path else ctm_folder, relative_path, file_base_name)
                
                os.makedirs(destination_dir, exist_ok=True)
                destination_file = os.path.join(destination_dir, file.lower())
                shutil.copy2(source_file, destination_file)
                png_files.append((file.lower(), destination_dir))

    return png_files

def copy_files_or_use_local_properties(png_files, repo, cit_folder, ctm_folder):
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    crystal_hollows_properties_folder = os.path.join(current_script_dir, 'crystal_hollows_properties')
    dwarven_mines_properties_folder = os.path.join(current_script_dir, 'dwarven_mines_properties')

    for file, destination_dir in png_files:
        item_name = file.replace('.png', '').lower()
        json_file_upper = item_name.upper() + '.json'
        properties_file_lower = item_name + '.properties'

        local_properties_folder = None
        if "dwarven_mines" in destination_dir:
            local_properties_folder = dwarven_mines_properties_folder
        elif "crystal_hollows" in destination_dir:
            local_properties_folder = crystal_hollows_properties_folder

        if local_properties_folder:
            local_properties_path = os.path.join(local_properties_folder, properties_file_lower)
            if os.path.exists(local_properties_path):
                shutil.copy2(local_properties_path, os.path.join(destination_dir, properties_file_lower))
                print(f"SUCCESS: Used local properties for {item_name} from {local_properties_folder}")
                continue

        try:
            json_file_path = f"items/{json_file_upper}"
            file_content = repo.get_contents(json_file_path)
            json_content = file_content.decoded_content.decode('utf-8')
            destination_properties_path = os.path.join(destination_dir, properties_file_lower)
            convert_json_to_properties(json_content, destination_properties_path, os.path.join(destination_dir, file.lower()))
            print(f"SUCCESS: Converted {json_file_upper} to {properties_file_lower} and moved to {destination_dir}")
        except Exception as e:
            print(f"\nERROR: Could not find or convert {json_file_upper}: {e}\n")

# Check if a file exists in a folder
def file_exists_in_folder(file_name, folder):
    return os.path.exists(os.path.join(folder, file_name))

# For spacing
print()

# Ask the user to select the folder containing files
source_folder = select_folder()
if not source_folder:
    print("\nERROR: No folder selected!\n")
    exit()

# Set up paths for pack.png, pack.mcmeta, and credits.txt in the current script's directory
current_script_dir = os.path.dirname(os.path.abspath(__file__))
pack_png_path = os.path.join(source_folder, 'pack.png')
pack_mcmeta_path = os.path.join(current_script_dir, 'pack.mcmeta')
credits_source_path = os.path.join(current_script_dir, 'credits.txt')

if not os.path.exists(pack_png_path):
    print("\nERROR: pack.png not found!\n")
    exit()

if not os.path.exists(pack_mcmeta_path):
    print("\npack.mcmeta not found, continuing without it...\n")

# Prompt the user for the new folder name
destination_folder_name = prompt_for_folder_name()
if not destination_folder_name:
    print("\nERROR: no folder name provided!\n")
    exit()

# Create the base folder
base_folder = os.path.join(os.getcwd(), destination_folder_name)

# Define the folder paths within the base folder
assets_folder = os.path.join(base_folder, 'assets')
minecraft_folder = os.path.join(assets_folder, 'minecraft')
mcpatcher_cit_folder = os.path.join(minecraft_folder, 'mcpatcher', 'cit')
mcpatcher_ctm_folder = os.path.join(minecraft_folder, 'mcpatcher', 'ctm')

# Create the necessary directories
os.makedirs(mcpatcher_cit_folder, exist_ok=True)
os.makedirs(mcpatcher_ctm_folder, exist_ok=True)

# Copy pack.png to the base folder
shutil.copy2(pack_png_path, base_folder)
print(f"SUCCESS: Moved pack.png to {base_folder}")

# Copy pack.mcmeta to the base folder if it exists
if os.path.exists(pack_mcmeta_path):
    shutil.copy2(pack_mcmeta_path, base_folder)
    print(f"SUCCESS: Moved pack.mcmeta to {base_folder}")

# Clone credits.txt from the current script's directory
creditsfile = True
if os.path.exists(credits_source_path):
    shutil.copy2(credits_source_path, base_folder)
    print(f"SUCCESS: Cloned credits.txt to {base_folder}")
    creditsfile = True
else:
    print("\nWARNING: credits.txt not found, continuing without it...")
    creditsfile = False

# Spacing again
print()

# Extract .png files and maintain the original folder structure under 'cit' and 'ctm'
exclude_files = ['pack.png', 'pack.mcmeta']
png_files = extract_files(source_folder, mcpatcher_cit_folder, mcpatcher_ctm_folder, exclude_files)

# Copy corresponding .json files from the GitHub repo and create .properties files or use local properties files
copy_files_or_use_local_properties(png_files, neurepo, mcpatcher_cit_folder, mcpatcher_ctm_folder)

# Zip the folder into a .zip file
zip_file_name = f"{destination_folder_name}.zip"
zip_file_path = os.path.join(os.getcwd(), zip_file_name)

with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(base_folder):
        for file in files:
            file_path = os.path.join(root, file)
            zipf.write(file_path, os.path.relpath(file_path, os.getcwd()))

print(f"\nSUCCESS: Folder {destination_folder_name} was zipped into {zip_file_name}\n")

# Check if all files were copied
all_files_copied = True

# Check if pack.png was copied
if not file_exists_in_folder('pack.png', base_folder):
    print("\nERROR: pack.png was not successfully copied!\n")
    all_files_copied = False

# Check if pack.mcmeta was copied, only if it exists
if os.path.exists(pack_mcmeta_path) and not file_exists_in_folder('pack.mcmeta', base_folder):
    print("\nERROR: pack.mcmeta was not successfully copied!\n")
    all_files_copied = False

# Check if credits.txt was copied
if not file_exists_in_folder('credits.txt', base_folder) and creditsfile == True:
    print("\nERROR: credits.txt was not successfully copied!\n")
    all_files_copied = False

# Final status message
if all_files_copied:
    print("\nAll files were successfully copied and verified!\n")
else:
    print("\nSome files were not successfully copied. Please check the errors above.\n")
