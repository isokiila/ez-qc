import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
import os
import shutil
from surfaceprops import SURFACE_PROPERTIES
from smd_parser import get_materials
from propdata import PROP_DATA_BASE_TYPES
from PIL import Image, ImageTk
import subprocess
from tkinter import messagebox
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo.png")

# -------------------------
# Variables
# -------------------------

selected_model = None
selected_physics = None
concave_collision = False

qc_window = None
qc_preview = None

cdmaterials_path = "models/"
model_output_path = "props_ezqc/"

selected_materials = []

skins = []

mass = "10.0"

prop_base = "None"
prop_health = "0"

settings_file = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "settings.json"
)

studiomdl_path = ""
game_folder = ""

# -------------------------
# Work folder
# -------------------------

work_folder = os.path.join(os.getcwd(), "ezqc_work")
os.makedirs(work_folder, exist_ok=True)


# -------------------------
# Generate/update QC
# -------------------------

def update_qc():

    # We need a visual model before we can make a QC
    if selected_model is None:
        return

    model_name = os.path.splitext(selected_model)[0]

    qc = f'''$modelname "{model_output_path}{model_name}.mdl"

'''

    # CDMaterials
    qc += f'''$cdmaterials "{cdmaterials_path}"

'''

    # Surface property
    qc += f'''$surfaceprop "{surfaceprop.get()}"

'''

    # Visual model
    qc += f'''$body "Body" "{selected_model}"

$staticprop

$sequence "idle" "{selected_model}" fps 30

'''

    # Alternate skins
    if skins:
        qc += '''$texturegroup "skinfamilies"
{
'''

        # Original materials
        qc += '    {'

        for material in selected_materials:
            qc += f' "{material}"'

        qc += ' }\n'

        # Alternate skins
        for skin in skins:
            qc += '    {'

            for material in selected_materials:
                entry = skin["entries"][material]
                replacement = entry.get().strip()

                if replacement:
                    qc += f' "{replacement}"'
                else:
                    qc += f' "{material}"'

            qc += ' }\n'

        qc += '''}

'''

    # Collision model
    if selected_physics is not None:
        qc += f'''$collisionmodel "{selected_physics}"
{{
'''

        if concave_var.get():
            qc += '''    $concave
'''

        if mass != "":
            qc += f'''    $mass {mass}
'''

        qc += '''}

'''

        # Prop Data
        prop_base_value = prop_base.get().strip()
        prop_health_value = prop_health.get().strip()

        # Only add prop_data if the user defined a base type or health
        if prop_base_value != "None" or prop_health_value != "":
            qc += '''$keyvalues
{
    "prop_data"
    {
        "allowstatic" "1"
'''

            if prop_base_value != "None":
                qc += f'''        "base" "{prop_base_value}"
'''

            if prop_health_value != "":
                qc += f'''        "health" "{prop_health_value}"
'''

            qc += '''    }
}

'''

    # Update the QC preview if it exists
    if qc_preview is not None:
        try:
            if qc_preview.winfo_exists():
                qc_preview.config(state="normal")
                qc_preview.delete("1.0", tk.END)
                qc_preview.insert("1.0", qc)
                qc_preview.config(state="disabled")
        except tk.TclError:
            pass

    # Save the generated QC
    qc_path = os.path.join(work_folder, "compile.qc")

    with open(qc_path, "w") as file:
        file.write(qc)


# -------------------------
# Browse for SMD
# -------------------------

def browse_smd(model_type):

    global selected_model
    global selected_physics

    smd_file = filedialog.askopenfilename(
        title=f"Select {model_type} SMD",
        filetypes=[
            ("SMD files", "*.smd"),
            ("All files", "*.*")
        ]
    )

    if not smd_file:
        return

    filename = os.path.basename(smd_file)

    destination = os.path.join(
        work_folder,
        filename
    )

    shutil.copy2(
        smd_file,
        destination
    )

    if model_type == "model":

        selected_model = filename

        selected_model_label.config(
            text=f"Visual model: {filename}",
            fg="green"
        )

        # Get material names from visual model
        global selected_materials
        selected_materials = get_materials(destination)

    elif model_type == "physics":

        selected_physics = filename

        selected_phys_label.config(
            text=f"Physics model: {filename}",
            fg="green"
        )

    # Update the QC immediately
    update_qc()

# -------------------------
# Add Skins
# -------------------------

def add_alternate_skin():

    if not selected_model:
        return

    skin_frame = tk.LabelFrame(
        skins_frame,
        text=f"Skin"
    )

    skin_frame.pack(
        fill="x",
        padx=10,
        pady=5
    )

    skin_entries = {}

    for row, material in enumerate(selected_materials):

        label = tk.Label(
            skin_frame,
            text=f"{material}:"
        )

        label.grid(
            row=row,
            column=0,
            padx=5,
            pady=2,
            sticky="w"
        )

        entry = tk.Entry(
            skin_frame,
            width=25
        )

        entry.grid(
            row=row,
            column=1,
            padx=5,
            pady=2
        )

        entry.bind(
            "<KeyRelease>",
            lambda event: update_qc()
        )

        skin_entries[material] = entry

    remove_button = tk.Button(
        skin_frame,
        text="Remove skin",
        command=lambda: remove_skin(skin_frame)
    )

    remove_button.grid(
        row=len(selected_materials),
        column=0,
        columnspan=2,
        pady=5
    )

    skin_data = {
        "frame": skin_frame,
        "entries": skin_entries
    }

    skins.append(skin_data)

    update_qc()

def remove_skin(frame):

    global skins

    frame.destroy()

    for skin in skins:
        if skin["frame"] == frame:
            skins.remove(skin)
            break

    skins_frame.update_idletasks()
    window.update_idletasks()

    update_qc()

# -------------------------
# Open QC preview
# -------------------------

def open_qc_preview():

    global qc_window
    global qc_preview

    # If the window already exists, bring it to the front
    if qc_window is not None:

        try:
            if qc_window.winfo_exists():
                qc_window.lift()
                return
        except tk.TclError:
            pass

    # Create preview window
    qc_window = tk.Toplevel(window)

    qc_window.title("QC Preview")
    qc_window.geometry("600x500")

    # Text box
    qc_preview = tk.Text(
        qc_window,
        wrap="none",
        state="disabled"
    )

    qc_preview.pack(
        fill="both",
        expand=True,
        padx=10,
        pady=10
    )

    # Generate the initial preview
    update_qc()

# -------------------------
# Compile
# -------------------------

def load_settings():
    global studiomdl_path
    global game_folder

    if not os.path.exists(settings_file):
        return

    try:
        with open(settings_file, "r") as file:
            settings = json.load(file)

        studiomdl_path = settings.get(
            "studiomdl_path",
            ""
        )

        game_folder = settings.get(
            "game_folder",
            ""
        )

    except (json.JSONDecodeError, OSError):
        pass


def save_settings():
    settings = {
        "studiomdl_path": studiomdl_path,
        "game_folder": game_folder
    }

    with open(settings_file, "w") as file:
        json.dump(
            settings,
            file,
            indent=4
        )

load_settings()

def show_compile_output(output):
    output_window = tk.Toplevel(window)
    output_window.title("Compile Output")
    output_window.geometry("700x500")

    output_text = tk.Text(
        output_window,
        wrap="none"
    )
    output_text.pack(
        side="left",
        fill="both",
        expand=True
    )

    scrollbar = tk.Scrollbar(
        output_window,
        orient="vertical",
        command=output_text.yview
    )
    scrollbar.pack(
        side="right",
        fill="y"
    )

    output_text.configure(
        yscrollcommand=scrollbar.set
    )

    output_text.insert(
        "1.0",
        output
    )

    output_text.configure(
        state="disabled"
    )

def compile_qc():

    global studiomdl_path
    global game_folder

    if selected_model is None:
        messagebox.showerror(
            "EZ-QC!",
            "Please select a visual model first."
        )
        return

    # Make sure the QC file is up to date
    update_qc()

    # Select game folder if we don't have a valid one
    if not game_folder or not os.path.isdir(game_folder):

        game_folder = filedialog.askdirectory(
            title="Select Source game folder"
        )

        if not game_folder:
            return

        save_settings()

    # Select studiomdl.exe if we don't have a valid one
    if not studiomdl_path or not os.path.isfile(studiomdl_path):

        studiomdl_path = filedialog.askopenfilename(
            title="Select studiomdl.exe",
            filetypes=[
                ("studiomdl.exe", "studiomdl.exe"),
                ("Executable files", "*.exe"),
                ("All files", "*.*")
            ]
        )

        if not studiomdl_path:
            return

        save_settings()

    qc_path = os.path.join(
        work_folder,
        "compile.qc"
    )

    try:
        result = subprocess.run(
            [
                studiomdl_path,
                "-game",
                game_folder,
                qc_path
            ],
            capture_output=True,
            text=True
        )

    except Exception as error:
        messagebox.showerror(
            "Compilation failed",
            str(error)
        )
        return

    # Combine stdout and stderr so we see all StudioMDL output
    output = result.stdout

    if result.stderr:
        output += "\n" + result.stderr

    # Show StudioMDL output
    show_compile_output(output)

    # Show compilation result
    if result.returncode == 0:
        messagebox.showinfo(
            "Compilation complete",
            "The model compiled successfully\n\n"
            "See the Compile Output window for details."
        )
    else:
        messagebox.showerror(
            "Compilation failed",
            "StudioMDL returned an error.\n\n"
            "See the Compile Output window for details."
        )

# -------------------------
# Change game
# -------------------------

def change_game():
    global game_folder
    global studiomdl_path

    new_game_folder = filedialog.askdirectory(
        title="Select Source game folder (e.g. common/Half-Life 2/hl2/)"
    )

    if not new_game_folder:
        return

    game_folder = new_game_folder

    # Ask for the compiler belonging to this game
    new_studiomdl_path = filedialog.askopenfilename(
        title="Select studiomdl.exe (Found in upper bin folder, e.g. common/Half-Life 2/bin/)",
        filetypes=[
            ("studiomdl.exe", "studiomdl.exe"),
            ("Executable files", "*.exe"),
            ("All files", "*.*")
        ]
    )

    if new_studiomdl_path:
        studiomdl_path = new_studiomdl_path

    save_settings()

# -------------------------
# Main window
# -------------------------

window = tk.Tk()

window.title("EZ-QC!")
window.geometry("550x950")

# Title Frame

top_frame = tk.Frame(window)
top_frame.pack(fill="x", padx=10, pady=(20, 10))

logo_image = Image.open(LOGO_PATH)

logo_image = logo_image.resize(
    (320, 80),
    Image.Resampling.LANCZOS
)

logo_photo = ImageTk.PhotoImage(logo_image)

logo_label = tk.Label(
    top_frame,
    image=logo_photo
)

logo_label.pack(side="left")

preview_button = tk.Button(
    top_frame,
    text="Open QC Preview",
    command=open_qc_preview
)
preview_button.pack(side="right", padx=(5, 0))

compile_button = tk.Button(
    top_frame,
    text="Compile!",
    command=compile_qc
)
compile_button.pack(side="right")

game_frame = tk.Frame(window)
game_frame.pack(fill="x", padx=10, pady=(0, 10))

change_game_button = tk.Button(
    game_frame,
    text="Change Game",
    command=change_game
)
change_game_button.pack(side="right")


# Scrollable main window
main_canvas = tk.Canvas(window)
main_scrollbar = tk.Scrollbar(
    window,
    orient="vertical",
    command=main_canvas.yview
)

main_frame = tk.Frame(main_canvas)

main_frame.bind(
    "<Configure>",
    lambda event: main_canvas.configure(
        scrollregion=main_canvas.bbox("all")
    )
)

main_frame_id = main_canvas.create_window(
    (0, 0),
    window=main_frame,
    anchor="nw"
)
def resize_main_frame(event):
    main_canvas.itemconfig(
        main_frame_id,
        width=event.width
    )

main_canvas.bind(
    "<Configure>",
    resize_main_frame
)

main_canvas.configure(
    yscrollcommand=main_scrollbar.set
)

main_canvas.pack(
    side="left",
    fill="both",
    expand=True
)

main_scrollbar.pack(
    side="right",
    fill="y"
)


# Model button

browse_button = tk.Button(
    main_frame,
    text="Select model",
    command=lambda: browse_smd("model")
)

browse_button.pack()


selected_model_label = tk.Label(
    main_frame,
    text="No model SMD selected",
    fg="red"
)

selected_model_label.pack(pady=20)

# Physics button

browse_button2 = tk.Button(
    main_frame,
    text="Select physics model",
    command=lambda: browse_smd("physics")
)

browse_button2.pack()


selected_phys_label = tk.Label(
    main_frame,
    text="No physics SMD selected",
    fg="red"
)

selected_phys_label.pack(pady=20)

# Concave check

concave_var = tk.BooleanVar(value=False)

concave_checkbox = tk.Checkbutton(
    main_frame,
    text="Concave collision?",
    variable=concave_var,
    command=update_qc
)

concave_checkbox.pack(pady=10)

# Mass

mass_label = tk.Label(
    main_frame,
    text="Mass:"
)
mass_label.pack(pady=(10, 0))

mass_entry = tk.Entry(
    main_frame,
    textvariable=mass
)
mass_entry.insert(0, "10.0")
mass_entry.pack()

mass2_label = tk.Label(
    main_frame,
    text="Tip: Max weight for player pickup is 35. For gravity gun it's 250.\nLeave blank for no mass / automatic.",
    fg="grey"
)
mass2_label.pack(pady=(5, 0))

def update_mass(event=None):
    global mass
    mass = mass_entry.get()
    update_qc()

mass_entry.bind(
    "<KeyRelease>",
    update_mass
)

# Output model

output_model_label = tk.Label(
    main_frame,
    text="Output model:"
)

output_model_label.pack(pady=(20, 5))


output_model_entry = tk.Entry(
    main_frame,
    width=40
)

output_model_entry.insert(0, "props_ezqc/")
output_model_entry.pack()

def update_model_output(event=None):
    global model_output_path

    model_output_path = output_model_entry.get()

    if model_output_path and not model_output_path.endswith("/"):
        model_output_path += "/"

    update_qc()

output_model_entry.bind(
    "<KeyRelease>",
    update_model_output
)

# CDMaterials entry

cdmaterials_label = tk.Label(
    main_frame,
    text="Material path:"
)

cdmaterials_label.pack(pady=(20, 5))


cdmaterials_entry = tk.Entry(
    main_frame,
    width=40
)

cdmaterials_entry.insert(0, "models/")
cdmaterials_entry.pack()

def update_cdmaterials(event=None):
    global cdmaterials_path

    cdmaterials_path = cdmaterials_entry.get()

    update_qc()


cdmaterials_entry.bind("<KeyRelease>", update_cdmaterials)

# Skins

skins_frame = tk.Frame(main_frame)
skins_frame.pack(pady=10)
skins_frame.pack_propagate(True)

skins_label = tk.Label(
    main_frame,
    text="Alternate skins:"
)

skins_label.pack(pady=(20, 5))

add_skin_button = tk.Button(
    main_frame,
    text="Add alternate skin",
    command=add_alternate_skin
)

add_skin_button.pack(pady=10)

# Surfaceprop

surfaceprops_label = tk.Label(
    main_frame,
    text="Surfaceprop:"
)

surfaceprops_label.pack(pady=(20, 5))

surfaceprop = tk.StringVar(value="default")

surfaceprop_box = ttk.Combobox(
    main_frame,
    textvariable=surfaceprop,
    values=SURFACE_PROPERTIES,
    state="readonly",
    width=30
)

surfaceprop_box.pack()

surfaceprop_box.bind(
    "<<ComboboxSelected>>",
    lambda event: update_qc()
)

# Prop data

prop_base = tk.StringVar(value="None")
prop_health = tk.StringVar(value="")

prop_data_label = tk.Label(
    main_frame,
    text="Prop Data"
)
prop_data_label.pack(pady=(15, 5))


base_label = tk.Label(
    main_frame,
    text="Base type:"
)
base_label.pack()

prop_base_dropdown = ttk.Combobox(
    main_frame,
    textvariable=prop_base,
    values=PROP_DATA_BASE_TYPES,
    state="readonly"
)

prop_base_dropdown.pack()

health_label = tk.Label(
    main_frame,
    text="Health"
)
health_label.pack(pady=(10, 0))

health_entry = tk.Entry(
    main_frame,
    textvariable=prop_health
)
health_entry.pack()

health2_label = tk.Label(
    main_frame,
    text="Tip: 0 means don't break. Leave blank to let base type decide health.",
    fg="grey"
)
health2_label.pack(pady=(5, 0))

health_entry.bind(
    "<KeyRelease>",
    lambda event: update_qc()
)
prop_base_dropdown.bind(
    "<<ComboboxSelected>>",
    lambda event: update_qc()
)


# -------------------------
# Cleanup
# -------------------------

def cleanup_work_folder():

    for filename in os.listdir(work_folder):

        file_path = os.path.join(
            work_folder,
            filename
        )

        if os.path.isfile(file_path):
            os.remove(file_path)

        elif os.path.isdir(file_path):
            shutil.rmtree(file_path)

    window.destroy()


window.protocol(
    "WM_DELETE_WINDOW",
    cleanup_work_folder
)


# Start program

window.mainloop()