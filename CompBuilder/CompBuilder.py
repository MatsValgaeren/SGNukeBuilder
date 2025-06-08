import nuke
import os
import re
import sgtk
import sys
import requests
import subprocess

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget, QMainWindow, QTreeView, QPushButton, QAbstractItemView, QLabel, QVBoxLayout, QPushButton
from PySide6.QtGui import QStandardItem, QStandardItemModel, QFont, QColor

from shotgun_api3.shotgun import Shotgun
from .config import SERVER_PATH, LOGIN, PASSWORD, FILE_FOLDER_LOCATION


RETRIEVED_USER_ID = os.getenv("USER_ID")
if not RETRIEVED_USER_ID:
    print("USER_ID environment variable is not set")

SG = Shotgun(
    SERVER_PATH,
    login = LOGIN,
    password= PASSWORD
)

my_window = None

# nuke.knobdefault('root.colormanagement', 'ocio')
# nuke.knobdefault('root.ocio_config', 'custom')
# defaultconfig = os.environ.get('ocio', '/path/to/default_facility_config.ocio')
# nuke.knobdefault('root.customocioconfigpath', defaultconfig)

class SGIO:
    def __init__(self, sg_api, user_id):
        self.sg = sg_api
        self.output_images = ''
        self.user_id = user_id
        self.can_work_on = ['rdy', 'rti', 'ip', 'att']

    def get_tasks(self):
        filters = [
            ['task_assignees', 'in', [{'type': 'HumanUser', 'id': self.user_id}]],
            ['sg_status_list', 'in', self.can_work_on]
        ]
        fields = [
            'content',
            'entity.Shot.code',
            'entity.Shot.sg_sequence',
            'entity.Shot.project',
            'entity.Shot.id'
        ]
        try:
            tasks = self.sg.find('Task', filters, fields)
            print(f"Retrieved {len(tasks)} tasks for user {self.user_id}")
            return tasks
        except Exception as e:
            print(f"Error fetching tasks: {e}")
            return []

    def video_to_images(self, input_video_dir, output_folder):
        print('Converting published video to image sequence for Nuke.')
        parts = os.path.normpath(output_folder).split(os.sep)
        output_name = '_'.join([parts[-7], parts[-5], parts[-4], parts[-3], parts[-1]])
        output_folder = input_video_dir.replace('output', 'input')
        output_folder = output_folder.replace('source', 'comp')
        self.output_images = os.path.join(output_folder, (output_name + ".####.jpg"))
        output_folder_dir = os.path.join(output_folder, (output_name+ ".%04d.jpg"))
        output_folder_check = os.path.join(output_folder, (output_name + ".1001.jpg"))

        if not os.path.exists(output_folder_check):
            print('Processing')

            cmd = [
                "ffmpeg",
                "-i", input_video_dir + r"connect_ts0020_0010_source_v001.mov",
                "-vf", "fps=24",
                "-start_number", "1001",
                output_folder_dir
            ]

            try:
                subprocess.run(cmd, check=True)
                print('Video successfully converted!')
            except subprocess.CalledProcessError as e:
                print('Something went wrong while trying to convert the video into image sequence.')

    def images_to_video(self, input_images_dir, output_file):
        print('Converting image sequence to published video for ShotGrid.')
        input_images_dir = r"C:\Users\matsv\Desktop\VfxSem2\Portfolio\CompBuilder\Shotgrid Connect\shots\ts0020\0010\comp\output\v001\comp_out_v001.%04d.exr"
        output = r"C:\Users\matsv\Desktop\VfxSem2\Portfolio\CompBuilder\Shotgrid Connect\shots\ts0020\0010\comp\publish\v001\out_video.mov"

        cmd = [
            "ffmpeg",
            "-start_number", "1001",
            "-i", input_images_dir,
            "-vf", "fps=24",
            output
        ]

        try:
            print('Processing')
            subprocess.run(cmd, check=True)
            print('Image Sequence successfully converted!')
        except subprocess.CalledProcessError as e:
            print('Something went wrong while trying to convert the image sequence into a video.')


class StandardItem(QStandardItem):
    def __init__(self, txt='', font_size=12, set_bold=False, color=QColor(0, 0, 0)):
        super().__init__()

        fnt = QFont('Open Sans', font_size)
        fnt.setBold(set_bold)

        self.setEditable(False)
        self.setForeground(color)
        self.setFont(fnt)
        self.setText(txt)


class MainWindow(QMainWindow):
    def __init__(self, sgio):
        super().__init__()
        self.setWindowTitle("ShotGrid Task Tree")
        self.resize(600, 400)
        self.tree = QTreeView()
        self.tree.header().hide()
        self.tree.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.in_progress_button = self.add_button("In Progress", self.task_in_progress)
        self.publish_button = self.add_button("Publish", self.task_publish)

        self.main_widget = QWidget()
        layout = QVBoxLayout(self.main_widget)

        # Add widgets to the layout
        layout.addWidget(QLabel("Project Status:"))
        layout.addWidget(self.tree)
        layout.addWidget(self.in_progress_button)
        layout.addWidget(self.publish_button)

        # Set the main widget as the central widget
        self.setCentralWidget(self.main_widget)

        # Get tasks from ShotGrid
        self.io_instance = sgio
        self.data = self.io_instance.get_tasks()

        # Build the tree model
        model = self.build_tree(self.data)
        self.tree.setModel(model)
        self.tree.expandAll()


    def build_tree(self, tasks):
        print('Started building tree/')
        model = QStandardItemModel()
        root = model.invisibleRootItem()

        tasks_sorted = sorted(
            tasks,
            key=lambda x: (
                x["entity.Shot.project"]["name"],
                x["entity.Shot.sg_sequence"]["name"],
                x["entity.Shot.code"],
                x["entity.Shot.id"]
            )
        )

        project_items = {}
        for task in tasks_sorted:
            proj = task["entity.Shot.project"]["name"]
            seq = task["entity.Shot.sg_sequence"]["name"]
            shot = task["entity.Shot.code"]
            id = task["entity.Shot.id"]
            # tsk = task["task"]

            if proj not in project_items:
                project_item = QStandardItem(proj)
                root.appendRow([project_item])
                project_items[proj] = (project_item, {})
            else:
                project_item, seq_items = project_items[proj]

            seq_items = project_items[proj][1]
            if seq not in seq_items:
                seq_item = QStandardItem(seq)

                project_item.appendRow([seq_item])
                seq_items[seq] = (seq_item, {})
            else:
                seq_item, shot_items = seq_items[seq]

            shot_items = seq_items[seq][1]
            if shot not in shot_items:
                shot_item = QStandardItem(shot)

                version_file_location = os.path.join(
                    FILE_FOLDER_LOCATION, project_item.text(), "shots", seq_item.text(), shot_item.text().split('_')[-1], "source", "output"
                )

                file_location = ''
                print(version_file_location)
                # List all directories in the version_file_location
                try:
                    all_dirs = [
                        d for d in os.listdir(version_file_location)
                        if os.path.isdir(os.path.join(version_file_location, d)) and re.match(r'v\d{3}', d)
                    ]
                except FileNotFoundError:
                    print(f"Path not found: {version_file_location}")
                    all_dirs = []

                if all_dirs:
                    versions = [int(re.search(r'v(\d{3})', d).group(1)) for d in all_dirs]
                    max_version = max(versions)
                    latest_folder = f"v{max_version:03d}"
                    file_location = os.path.join(version_file_location, latest_folder, '')
                    print(file_location)
                else:
                    print("No version folders found.")

                shot_item.setData(file_location, Qt.UserRole)
                shot_item.setData(id, Qt.UserRole + 1)
                seq_item.appendRow([shot_item])
                shot_items[shot] = shot_item
            else:
                shot_item = shot_items[shot]

        self.tree.doubleClicked.connect(self.get_value)

        print('Tree has been build.')

        return model

    def add_button(self, label, action):
        button = QPushButton(label)
        button.clicked.connect(lambda: action())
        return button

    def task_in_progress(self):
        index = self.tree.currentIndex()
        item = self.tree.model().itemFromIndex(index)

        if item is None:
            print("No item selected!")
            return
        task_id = item.data(Qt.UserRole + 1)

        if not task_id:
            print("No Task ID found for selected item!")
            return
        set_task_status(task_id, 'ip')
        print('Changed status of task to In Progress.')

    def task_publish(self):
        index = self.tree.currentIndex()
        item = self.tree.model().itemFromIndex(index)
        if item is None:
            print("No item selected!")
            return
        task_id = item.data(Qt.UserRole + 1)
        if not task_id:
            print("No Task ID found for selected item!")
            return
        self.io_instance.images_to_video('wfew', 'wefs')
        self.video_file = r"C:\Users\matsv\Desktop\VfxSem2\Portfolio\CompBuilder\Shotgrid Connect\shots\ts0020\0010\comp\publish\v001\out_video.mov"
        self.publish_video(self.video_file)

        set_task_status(task_id, 'rvi')
        print('Changed status of task to Review Internal.')

    def publish_video(self, video_file):
        data = {
            "project": {"type": "Project", "id": 353},
            "code": "v001",
            "description": "Auto-published from script",
            "entity": {"type": "Task", "id": 15265},
            "user": {"type": "HumanUser", "id": RETRIEVED_USER_ID},
        }

        version = SG.create("Version", data)

        print('Publishing file.')
        SG.upload("Version", version["id"], video_file, field_name="sg_uploaded_movie")

    def get_value(self, index):
        item = self.tree.model().itemFromIndex(index)
        if item is None:
            print("No item found for index!")
            return

        file_location = item.data(Qt.UserRole)

        output_location = FILE_FOLDER_LOCATION + r"\Shotgrid Connect\shots\ts0020\0010\comp\input\v001\\"
        # output_location = file_location.replace("input", "output")
        self.io_instance.video_to_images(file_location, output_location)
        create_comp(self.io_instance.output_images)


def create_comp(input_images):
    print('Creating Comp...')
    name = FILE_FOLDER_LOCATION + r"C:\Shotgrid Connect\shots\ts0020\0010\comp\work\v001\comp_v001.nkc"
    if not os.path.exists(name):
        nuke.scriptSaveAs()

    try:
        read = nuke.nodes.Read(file=input_images.replace('\\', '/'))
        read["colorspace"].setValue("Output - sRGB")
        read['reload'].execute()
    except Exception as e:
        print("Error creating Nuke Read node:", e)

    write = nuke.nodes.Write(file="render/output.####.exr")

    dir_path = os.path.dirname(input_images)
    base_name = os.path.basename(input_images)

    # Replace frame number with a wildcard regex
    # Example: image.%04d.exr or image.0001.exr → image.\d+.exr
    pattern = re.sub(r'\d+', r'\\d+', base_name)
    regex = re.compile('^' + pattern + '$')

    # Count matching files
    file_count = len([f for f in os.listdir(dir_path) if regex.match(f)])
    print("Number of images in sequence:", file_count)
    video_length = 1000 + file_count

    read["first"].setValue("1001")
    read["last"].setValue(f"{video_length}")
    write["colorspace"].setValue(("Output - sRGB"))

    nuke.root()["first_frame"].setValue(1001)
    nuke.root()["last_frame"].setValue(video_length)

    write.setInput(0, read)

    print('Created Comp.')


def set_task_status(task_id, new_status):
    print('setting task status')
    try:
        SG.update("Task", 15265, {"sg_status_list": new_status})
        print(f"Task {task_id} status updated to {new_status}")
    except Exception as e:
        print(f"Failed to update status for Task {task_id}: {e}")


def run():
    try:
        global my_window
        app = QApplication.instance()
        sgio = SGIO(SG, RETRIEVED_USER_ID)
        my_window = MainWindow(sgio)
        my_window.show()
    except Exception as e:
        import traceback
        print("Exception in run():", e)
        traceback.print_exc()


