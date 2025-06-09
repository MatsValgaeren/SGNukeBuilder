# SG-NukeBuilder

[![Build Status](https://img.shields.io/github/actions/workflow/status/username/repo/ci.yml?branch=main)](https://github.com/MatsValgaeren/SG-NukeBuilder/actions)
[![Coverage](https://img.shields.io/codecov/c/github/username/repo)](https://codecov.io/gh/username/repo)
[![Latest Release](https://img.shields.io/github/v/release/username/repo)](https://github.com/MatsValgaeren/SG-NukeBuilder/releases)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Issues](https://img.shields.io/github/issues/username/repo)](https://github.com/MatsValgaeren/SG-NukeBuilder/issues)

</div>

<details>
<summary>Table of Contents</summary>

- [About](#about)
- [Features](#features)
- [Installation](#installation)
  - [Requirements](#requirements)
  - [Maya Scipt Setup](#maya-scipt-setup)
- [Usage](#usage)
- [Roadmap & Contributing](#roadmap--contributing)
- [Credits](#credits)
- [License](#license)

</details>


## About

A tool to browse, build, and publish Nuke comps with ShotGrid integration.

[//]: # (*Watch Demo Video Here: [YouTube Video]&#40;...&#41;*)


## Features

- Browse a tree of all comp tasks from ShotGrid
- Fetch and convert published files to image sequences for Nuke
- Build or open comps with correct inputs
- Version up and update ShotGrid task status
- Render comps and convert outputs to video with FFmpeg for ShotGrid review
- Publish and upload review media to ShotGrid

## Installation

#### Requirements

-   Foundry **nuke** (version 16+)

> **Note:** Or earlier versions if you manually install the required packages 
> (notably, PySide6 is bundled with Nuke 16+)

> **Note:** This tool currently works only with Nuke Non-commercial (.nknc) files. 
> Files created in Nuke NC cannot be opened in commercial Nuke, 
> and output is limited to 1920x1080 HD with certain node and codec restrictions.

-   **FFmpeg:** Ensure FFmpeg is installed and added to your system's PATH. Download it from [FFmpeg Downloads](https://www.ffmpeg.org/download.html).


#### Nuke Script Setup

1.  Download or clone this repository.
2.  Copy the `init.py`, `menu.py` and `SG_CompBuilder` Folder to your Nuke directory:
```
C:\Users\<user>\.nuke
```
3. Add a `config.py` file in the `SG_CompBuilder` folder and fill in the following variables:
```
SERVER_PATH = "https://yourshotgridsite.com"
LOGIN = "your_username"
PASSWORD = "your_password"
PROJECT_FOLDER_LOCATION = "D:/projects/my_project"
```

## Usage

1. **Run "SG_CompBuilder" -> "Load SG Tree" in Nuke** to open the UI.
2. **Select your comp task.**
3. **Click "Open/Build Comp"** to open an existing comp or build a base comp.
4. **Click "Write Up Version"** to save a new version of your project.
5. **Click "Put Task 'In Progress'"** to change the status of the ShotGrid task to 'In Progress'.
6. **Click "Publish Video"** to render and publish the current comp.

[//]: # (***Watch the Demo here: [YouTube Video]&#40;...;***)


## Roadmap & Contributing

See the [open issues](https://github.com/MatsValgaeren/SG-NukeBuilder/issues) to track planned features, known bugs, and ongoing work.

If you encounter any bugs or have feature requests, please submit them as new issues there.  Your feedback and contributions help improve RefUp!


## Credits

-   Script by Mats Valgaeren
-   Powered by:
    -   [FFmpeg](https://github.com/FFmpeg/FFmpeg)
    -   [PySide6](https://doc.qt.io/qtforpython/)


## License

[GNU General Public License v3.0](LICENSE)
