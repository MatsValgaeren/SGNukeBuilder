import nuke
import os
import re
import sys
import json
import subprocess

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget, QMainWindow, QTreeView, QPushButton, QAbstractItemView, QLabel, \
    QVBoxLayout, QPushButton
from PySide6.QtGui import QStandardItem, QStandardItemModel, QFont, QColor

from shotgun_api3.shotgun import Shotgun
from .config import SERVER_PATH, LOGIN, PASSWORD, PROJECT_FOLDER_LOCATION

RETRIEVED_USER_ID = int(os.getenv("USER_ID"))
if not RETRIEVED_USER_ID:
    print("USER_ID environment variable is not set")
print('ID: ', RETRIEVED_USER_ID)

SG = Shotgun(
    SERVER_PATH,
    login=LOGIN,
    password=PASSWORD
)

my_window = None

class SGIO:
    def __init__(self, sg_api, user_id):
        self.sg = sg_api
        self.user_id = user_id
        self.can_work_on = ['rdy', 'rti', 'rvi', 'ip', 'att']

    def get_tasks(self):
        filters = [
            ['task_assignees', 'in', [{'type': 'HumanUser', 'id': self.user_id}]],
            ['sg_status_list', 'in', self.can_work_on],
            ['step.Step.code', 'is', 'comp']
        ]
        fields = [
            'id',
            'content',
            'entity.Shot.code',
            'entity.Shot.sg_sequence',
            'entity.Shot.project',
            'entity.Shot.project.Project.id',
            'entity.Shot.id'
        ]
        try:
            tasks = self.sg.find('Task', filters, fields)
            print(f"Retrieved {len(tasks)} tasks for user {self.user_id}")
            print(tasks)
            return tasks
        except Exception as e:
            print(f"Error fetching tasks: {e}")
            return []

    def video_to_images(self, input_video_path, output_image_path):
        """Convert video to image sequence"""
        print('Converting published video to image sequence for Nuke.')

        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(output_image_path)
        os.makedirs(output_dir, exist_ok=True)

        # Check if conversion already exists
        first_frame_path = output_image_path.replace('%04d', '1001')
        if os.path.exists(first_frame_path):
            print(f'Image sequence already exists: {first_frame_path}')
            return output_image_path

        if not os.path.exists(input_video_path):
            print(f'Source video not found: {input_video_path}')
            return None

        cmd = [
            "ffmpeg",
            "-i", input_video_path,
            "-vf", "fps=24",
            "-start_number", "1001",

            "-threads", "0",

            output_image_path
        ]

        try:
            print('Processing video conversion...')
            subprocess.run(cmd, check=True)
            print('Video successfully converted!')
            return output_image_path
        except subprocess.CalledProcessError as e:
            print(f'Error converting video to images: {e}')
            return None

    def images_to_video(self, input_images_path, output_video_path):
        """Convert image sequence to video"""
        print('Converting image sequence to published video for ShotGrid.')

        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_video_path), exist_ok=True)

        cmd = [
            "ffmpeg",
            "-start_number", "1001",
            "-i", input_images_path,
            "-vf", "fps=24",
            "-y",  # Overwrite output file
            output_video_path
        ]

        try:
            print('Processing image sequence to video conversion...')
            subprocess.run(cmd, check=True)
            print('Image sequence successfully converted to video!')
            return output_video_path
        except subprocess.CalledProcessError as e:
            print(f'Error converting images to video: {e}')
            return None

    def get_video_metadata(self, video_path):
        """Extracts resolution and fps from a video file using ffprobe."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate",
            "-of", "json",
            video_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        info = json.loads(result.stdout)
        stream = info['streams'][0]
        width = stream['width']
        height = stream['height']
        # r_frame_rate is a string like "24/1"
        fps_parts = stream['r_frame_rate'].split('/')
        fps = float(fps_parts[0]) / float(fps_parts[1])
        return width, height, fps

    def set_task_status(self, task_id, new_status):
        """Update task status in ShotGrid"""
        print(f'Setting task {task_id} status to {new_status}')
        try:
            self.sg.update("Task", task_id, {"sg_status_list": new_status})
            print(f"Task {task_id} status updated to {new_status}")
        except Exception as e:
            print(f"Failed to update status for Task {task_id}: {e}")

    def publish_video(self, video_file, version, proj_id, shot_id, task_id):
        """Publish video to ShotGrid"""
        if not os.path.exists(video_file):
            print(f"Video file not found: {video_file}")
            return None

        data = {
            "project": {"type": "Project", "id": int(proj_id)},
            "code": version,
            "description": f"Auto-published from script by user: {int(RETRIEVED_USER_ID)}",
            "entity": {"type": "Shot", "id": int(shot_id)},
            "sg_task": {"type": "Task", "id": int(task_id)},
            "user": {"type": "HumanUser", "id": int(RETRIEVED_USER_ID)},
        }

        try:
            version = self.sg.create("Version", data)
            print('Publishing file to ShotGrid...')
            self.sg.upload("Version", version["id"], video_file, field_name="sg_uploaded_movie")
            print('File successfully published!')
            return version
        except Exception as e:
            print(f"Error publishing video: {e}")
            return None


class PipelineFileManager:
    """Unified file path manager with consistent naming conventions"""

    def __init__(self, base_path=None, tree=None):
        self.proj_path = base_path or PROJECT_FOLDER_LOCATION
        self.tree = tree
        self.proj = None
        self.seq = None
        self.shot = None

    def get_data(self):
        """Get current selection data from tree"""
        if not self.tree:
            print('no tree')
            return

        index = self.tree.currentIndex()
        item = self.tree.model().itemFromIndex(index)
        print(index, item)
        if item:
            self.proj = item.data(Qt.UserRole)
            self.seq = item.data(Qt.UserRole + 1)
            self.shot = item.data(Qt.UserRole + 2)
            print('set all data')

    def get_shot_dir(self):
        """Get base shot directory"""
        if not all([self.proj, self.seq, self.shot]):
            self.get_data()

        print([self.proj, self.seq, self.shot])
        if not all([self.proj, self.seq, self.shot]):
            print("Missing project, sequence, or shot data")
            return None

        base = os.path.join(
            self.proj_path,
            self.proj,
            "shots",
            self.seq,
            self.shot.split('_')[-1]
        )

        return base

    def get_latest_version(self, folder_path):
        """Get latest version folder (v001, v002, etc.)"""
        if not os.path.exists(folder_path):
            print(f"Path not found: {folder_path}")
            return None

        try:
            all_dirs = [
                d for d in os.listdir(folder_path)
                if os.path.isdir(os.path.join(folder_path, d)) and re.match(r'v\d{3}', d)
            ]

            if all_dirs:
                versions = [int(re.search(r'v(\d{3})', d).group(1)) for d in all_dirs]
                max_version = max(versions)
                return f"v{max_version:03d}"
            else:
                print(f"No version folders found in: {folder_path}")
                return None
        except Exception as e:
            print(f"Error getting latest version: {e}")
            return None

    def get_next_version(self, folder_path):
        """Get next version number"""
        latest = self.get_latest_version(folder_path)
        if latest is None:
            return "v001"

        version_num = int(re.search(r'v(\d{3})', latest).group(1))
        return f"v{version_num + 1:03d}"

    def make_filename(self, task, version, extension=""):
        """Create standardized filename: proj_seq_shot_task_version.ext"""
        if not all([self.proj, self.seq, self.shot]):
            self.get_data()

        if not all([self.proj, self.seq, self.shot]):
            print("Cannot create filename - missing project data")
            return None

        base_name = f"{self.proj}_{self.seq}_{self.shot}_{task}_{version}"

        if extension:
            return f"{base_name}.{extension}"
        return base_name

    def get_source_video_path(self):
        """Get source video file path"""
        shot_dir = self.get_shot_dir()
        if not shot_dir:
            return None

        source_dir = os.path.join(shot_dir, "source", "output")
        latest_version = self.get_latest_version(source_dir)

        if not latest_version:
            print("No source video version found")
            return None

        video_filename = self.make_filename("source", latest_version, "mov")
        video_path = os.path.join(source_dir, latest_version, video_filename)

        if os.path.exists(video_path):
            return video_path
        else:
            print(f"Source video not found: {video_path}")
            return None

    def get_comp_input_path(self, for_nuke=False):
        """Get comp input image sequence path"""
        shot_dir = self.get_shot_dir()
        if not shot_dir:
            return None

        # Use same version as source
        source_dir = os.path.join(shot_dir, "source", "output")
        source_version = self.get_latest_version(source_dir)

        if not source_version:
            print("No source version found for comp input")
            return None

        comp_input_dir = os.path.join(shot_dir, "comp", "input", source_version)
        base_name = self.make_filename("source", source_version)

        if for_nuke:
            # Nuke format: filename.####.exr
            return os.path.join(comp_input_dir, f"{base_name}.####.exr")
        else:
            # Python/FFmpeg format: filename.%04d.exr
            return os.path.join(comp_input_dir, f"{base_name}.%04d.exr")

    def get_comp_output_path(self, for_nuke=False):
        """Get comp output image sequence path"""
        shot_dir = self.get_shot_dir()
        if not shot_dir:
            return None

        comp_output_dir = os.path.join(shot_dir, "comp", "output")
        comp_work_dir = os.path.join(shot_dir, "comp", "work")

        # Get next version for new output
        next_version = self.get_latest_version(comp_work_dir)

        output_dir = os.path.join(comp_output_dir, next_version)

        # Create directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        base_name = self.make_filename("comp", next_version)

        if for_nuke:
            # Nuke format: filename.####.exr
            return os.path.join(output_dir, f"{base_name}.####.exr")
        else:
            # Python/FFmpeg format: filename.%04d.exr
            return os.path.join(output_dir, f"{base_name}.%04d.exr")

    def get_nuke_script_path(self, new=False):
        """Get Nuke script path"""
        shot_dir = self.get_shot_dir()
        if not shot_dir:
            return None

        work_dir = os.path.join(shot_dir, "comp", "work")

        if new is False:
            version = self.get_latest_version(work_dir)
            if version is None:
                version = 'v001'

            print('latest v: ', version)
            if version is None:
                print("No existing version found.")
                return None  # or return a default path or raise an exception
        else:
            version = self.get_next_version(work_dir)

        script_dir = os.path.join(work_dir, version)
        if new:
            os.makedirs(script_dir, exist_ok=True)

        filename = self.make_filename("comp", version, "nknc")
        return os.path.join(script_dir, filename)

    def get_publish_script_path(self):
        """Get publish script path"""
        shot_dir = self.get_shot_dir()
        if not shot_dir:
            return None

        work_dir = os.path.join(shot_dir, "comp", "work")
        current_version = self.get_latest_version(work_dir)

        if not current_version:
            print("No work version found for publish")
            return None

        publish_dir = os.path.join(shot_dir, "comp", "publish", current_version)
        os.makedirs(publish_dir, exist_ok=True)

        filename = self.make_filename("comp", current_version, "nknc")
        return os.path.join(publish_dir, filename)

    def get_publish_video_path(self):
        """Get publish video path"""
        shot_dir = self.get_shot_dir()
        if not shot_dir:
            return None

        comp_output_dir = os.path.join(shot_dir, "comp", "output")
        latest_comp_version = self.get_latest_version(comp_output_dir)

        if not latest_comp_version:
            print("No comp output version found for publish")
            return None

        publish_dir = os.path.join(shot_dir, "comp", "publish", latest_comp_version)
        os.makedirs(publish_dir, exist_ok=True)

        filename = self.make_filename("comp", latest_comp_version, "mov")
        return os.path.join(publish_dir, filename)

    def get_all_paths(self):
        """Get all paths for current shot - useful for debugging"""
        if not all([self.proj, self.seq, self.shot]):
            self.get_data()

        paths = {
            'shot_dir': self.get_shot_dir(),
            'source_video': self.get_source_video_path(),
            'comp_input_python': self.get_comp_input_path(for_nuke=False),
            'comp_input_nuke': self.get_comp_input_path(for_nuke=True),
            'comp_output_python': self.get_comp_output_path(for_nuke=False),
            'comp_output_nuke': self.get_comp_output_path(for_nuke=True),
            'nuke_script': self.get_nuke_script_path(),
            'publish_script': self.get_publish_script_path(),
            'publish_video': self.get_publish_video_path()
        }

        return paths


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
        self.io_instance = sgio
        self.nuke_instance = NukeHandler()
        self.pfm = PipelineFileManager(tree=None)  # Will be set after tree creation

        self.setWindowTitle("ShotGrid Task Tree")
        self.resize(600, 400)
        self.tree = QTreeView()
        self.tree.header().hide()
        self.tree.setEditTriggers(QAbstractItemView.NoEditTriggers)

        # Now set the tree reference in PipelineFileManager
        self.pfm.tree = self.tree

        # self.treebleClicked.connect(self.build_comp)
        self.build_comp_button = self.add_button("Build/Open Comp", self.build_comp)
        self.upversion_button = self.add_button("Write Up Version", self.upversion_passthrough)
        self.in_progress_button = self.add_button("Put Task 'In Progress'", self.task_in_progress)
        self.publish_button = self.add_button("Publish Video", self.task_publish)

        self.main_widget = QWidget()
        layout = QVBoxLayout(self.main_widget)

        # Add widgets to the layout
        layout.addWidget(QLabel("Project Status:"))
        layout.addWidget(self.tree)
        layout.addWidget(self.build_comp_button)
        layout.addWidget(self.upversion_button)
        layout.addWidget(self.in_progress_button)
        layout.addWidget(self.publish_button)

        # Set the main widget as the central widget
        self.setCentralWidget(self.main_widget)

        # Get tasks from ShotGrid
        self.data = self.io_instance.get_tasks()

        # Build the tree model
        model = self.build_tree(self.data)
        self.tree.setModel(model)
        self.tree.expandAll()

    def upversion_passthrough(self):
        self.nuke_instance.upversion_proj(self.tree)

    def build_tree(self, tasks):
        print('Started building tree...')
        model = QStandardItemModel()
        root = model.invisibleRootItem()

        tasks_sorted = sorted(
            tasks,
            key=lambda x: (
                x["entity.Shot.project"]["name"],
                x["entity.Shot.sg_sequence"]["name"],
                x["entity.Shot.code"],
                x["id"]
            )
        )

        project_items = {}
        for task in tasks_sorted:
            proj = task["entity.Shot.project"]["name"].replace(' ', '')
            seq = task["entity.Shot.sg_sequence"]["name"]
            shot = task["entity.Shot.code"].split('_')[-1]
            task_id = task["id"]
            proj_id = task['entity.Shot.project.Project.id']
            shot_id = task['entity.Shot.id']

            # Build project level
            if proj not in project_items:
                project_item = QStandardItem(proj)
                root.appendRow([project_item])
                project_items[proj] = (project_item, {})

            project_item, seq_items = project_items[proj]

            # Build sequence level
            if seq not in seq_items:
                seq_item = QStandardItem(seq)
                project_item.appendRow([seq_item])
                seq_items[seq] = (seq_item, {})

            seq_item, shot_items = seq_items[seq]

            # Build shot level
            if shot not in shot_items:
                shot_item = QStandardItem(shot)
                shot_item.setData(proj, Qt.UserRole)  # Store project
                shot_item.setData(seq, Qt.UserRole + 1)  # Store sequence
                shot_item.setData(shot, Qt.UserRole + 2)  # Store shot
                shot_item.setData(task_id, Qt.UserRole + 3)  # Store task ID
                shot_item.setData(proj_id, Qt.UserRole + 4)
                shot_item.setData(shot_id, Qt.UserRole + 5)
                seq_item.appendRow([shot_item])
                shot_items[shot] = shot_item

        print('Tree has been built.')
        return model

    def add_button(self, label, action):
        button = QPushButton(label)
        button.clicked.connect(lambda: action())
        return button

    def task_in_progress(self):
        """Set task status to In Progress"""
        index = self.tree.currentIndex()
        item = self.tree.model().itemFromIndex(index)

        if item is None:
            print("No item selected!")
            return

        task_id = item.data(Qt.UserRole + 3)
        if not task_id:
            print("No Task ID found for selected item!")
            return

        self.io_instance.set_task_status(task_id, 'ip')
        print('Changed status of task to In Progress.')

    def task_publish(self):
        """Publish task - render images to video and upload to ShotGrid"""
        index = self.tree.currentIndex()
        item = self.tree.model().itemFromIndex(index)

        if item is None:
            print("No item selected!")
            return

        seq_id = item.data(Qt.UserRole + 1)
        shot_id = item.data(Qt.UserRole + 5)
        task_id = item.data(Qt.UserRole + 3)
        proj_id = item.data(Qt.UserRole + 4)
        print('proj id', proj_id)
        if not task_id:
            print("No Task ID found for selected item!")
            return

        # Get current comp output and convert to video
        comp_output_path = self.pfm.get_comp_output_path(False)
        publish_video_path = self.pfm.get_publish_video_path()

        if not comp_output_path or not publish_video_path:
            print("Could not determine comp output or publish video paths")
            return

        self.nuke_instance.render(self.tree)

        # Convert images to video
        video_file = self.io_instance.images_to_video(comp_output_path, publish_video_path)
        base = os.path.splitext(os.path.basename(video_file))[0]
        version = base[-4:]

        if video_file and os.path.exists(video_file):
            # def publish_video(self, video_file, version, proj_id, shot_id, task_id):
            print(video_file, version, proj_id, shot_id, task_id)
            version  = self.io_instance.publish_video(video_file, version, proj_id, shot_id, task_id)
            if version:
                version_id = version["id"]
                self.io_instance.sg.update("Version", version_id, {"sg_status_list": "rvi"})
                print("Changed status of version to Review Internal.")

            self.io_instance.set_task_status(task_id, 'rvi')
            print('Changed status of task to Review Internal.')
        else:
            print("Failed to create video for publishing")


    def build_comp(self):
        """Build composition when shot is double-clicked"""
        nuke_script_path = self.pfm.get_nuke_script_path(new=False)
        print('path is', nuke_script_path)
        if os.path.exists(nuke_script_path):
            nuke.scriptOpen(nuke_script_path)
            return
        else:
            print('making comp')
            index = self.tree.currentIndex()
            item = self.tree.model().itemFromIndex(index)
            if item is None:
                print("No item found for index!")
                return

            # Get source video and convert to images
            source_video_path = self.pfm.get_source_video_path()
            comp_input_path = self.pfm.get_comp_input_path(for_nuke=False)

            if not source_video_path:
                print("Source video not found")
                return

            if not comp_input_path:
                print("Could not determine comp input path")
                return

            # Convert video to images
            image_sequence = self.io_instance.video_to_images(source_video_path, comp_input_path)
            w, h, fps = self.io_instance.get_video_metadata(source_video_path)
            self.nuke_instance.set_nuke_project_settings(w, h, fps)

            if not image_sequence:
                print("Failed to convert video to images")
                return

            nuke_script_path = self.pfm.get_nuke_script_path(new=True)
            self.nuke_instance.create_comp(image_sequence, self.tree, nuke_script_path)


class NukeHandler():
    def __init__(self):
        self.write_name = 'RenderNode'
        self.pfm_instance = PipelineFileManager()

    def set_nuke_project_settings(self, width, height, fps):
        nuke.root()['colorManagement'].setValue('OCIO')
        format_name = f"custom_{int(width)}x{int(height)}"
        format_str = f"{int(width)} {int(height)} 0 0 {int(width)} {int(height)} 1.0 {format_name}"
        nuke.addFormat(format_str)
        nuke.root()['format'].setValue(format_name)
        nuke.root()['fps'].setValue(float(fps))

    def create_comp(self, input_images, tree, script_name):
        """Create new Nuke composition"""
        print('Creating Comp...')

        try:
            # Create Read node
            read_node = nuke.nodes.Read(file=input_images.replace('\\', '/'))
            # read_node["colorspace"].setValue('ACES - ACEScg')
            read_node["colorspace"].setValue('Output - sRGB')

            # Create Write node
            self.pfm_instance.tree = tree
            self.pfm_instance.get_data()
            output_path = self.pfm_instance.get_comp_output_path(for_nuke=True)
            if not output_path:
                print("Could not determine output path")
                return

            self.write_node = nuke.nodes.Write(file=output_path.replace('\\', '/'))
            self.write_node.setName(self.write_name)
            self.write_node["colorspace"].setValue('Output - sRGB')

            # Connect nodes
            self.write_node.setInput(0, read_node)

            dir_path = os.path.dirname(input_images)
            base_name = os.path.basename(input_images)

            if os.path.exists(dir_path):
                # Replace %04d with regex for 4 digits
                pattern = re.sub(r'%04d', r'(\\d{4})', base_name)
                regex = re.compile('^' + pattern + '$')
                frames = []
                for f in os.listdir(dir_path):
                    m = regex.match(f)
                    if m:
                        frames.append(int(m.group(1)))
                if frames:
                    first_frame = min(frames)
                    last_frame = max(frames)

                    read_node["first"].setValue(first_frame)
                    read_node["last"].setValue(last_frame)
                    nuke.root()["first_frame"].setValue(first_frame)
                    nuke.root()["last_frame"].setValue(last_frame)

                    print(f"Set frame range: {first_frame} - {last_frame}")
                else:
                    print("No matching image files found")

            nuke.scriptSaveAs(script_name)
            print('Comp created successfully.')

        except Exception as e:
            print(f"Error creating Nuke composition: {e}")

    def upversion_proj(self, tree):
        # Update pipeline manager with the new tree/context
        self.pfm_instance.tree = tree
        self.pfm_instance.get_data()

        # Get the new versioned Nuke script path
        nuke_script_name = self.pfm_instance.get_nuke_script_path(new=True)
        print('Saving name as', nuke_script_name)

        # Get the new versioned output path for the Write node
        output_path = self.pfm_instance.get_comp_output_path(for_nuke=True)
        print('New Write node output path:', output_path)

        # Find the Write node and update its file path
        write_node = nuke.toNode(self.write_name)
        if write_node is not None and output_path:
            write_node['file'].setValue(output_path.replace('\\', '/'))
            print('Updated Write node path to:', output_path)
        else:
            print('Write node not found or output path missing.')

        # Save the Nuke script with the new versioned name
        nuke.scriptSaveAs(nuke_script_name)

    def render(self, tree):
        write_node = nuke.toNode(self.write_name)

        self.pfm_instance.tree = tree
        self.pfm_instance.get_data()
        if write_node is not None:
            output_path = self.pfm_instance.get_comp_output_path(for_nuke=True)
            if not output_path:
                print("Could not determine output path")
                return

            # write_node = nuke.nodes.Write(file=output_path.replace('\\', '/'))

            output_dir = os.path.dirname(write_node["file"].value())
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            first_frame = int(nuke.root()["first_frame"].value())
            last_frame = int(nuke.root()["last_frame"].value())
            nuke.render(write_node, first_frame, last_frame)
        else:
            print("Write node not set. Cannot render.")


def run():
    """Main entry point"""
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