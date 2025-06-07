SERVER_PATH = "https://dae-vfx.shotgrid.autodesk.com"
SHOTGUN_SCRIPT_NAME = "connect"
SHOTGUN_API_KEY = "sqpzhcmlsv5zvwjz_cfveHjlj"
FILE_FOLDER_LOCATION = r"C:\Users\matsv\Desktop\VfxSem2\Portfolio\CompBuilder"

# SHOTGUN_SITE = "https://dae-vfx.shotgrid.autodesk.com"
# SHOTGUN_SCRIPT_NAME = "BLG08"
# SHOTGUN_API_KEY = "bb03001ff1a4b46f9d38f7462a2d5b8dbcde11b4"

# SG = Shotgun(
#     SERVER_PATH,
#     login="mats.valgaeren",
#     password="TCaQcyP8jwj8N4!"
# )

# SG = Shotgun(
#     "https://your-site.shotgrid.autodesk.com",
#     login="your_legacy_username",        # NOT your email unless set as username
#     password="your_legacy_passphrase",   # NOT your Autodesk password; this is your legacy passphrase
#     personal_access_token="TOKEN"
# )

# SERVER_PATH = SERVER_PATH
# SCRIPT_NAME = 'TOKEN'
# SCRIPT_KEY = '950321e69a57a739d61f10d3f29dfbf733352128'
#
# SG = Shotgun(SERVER_PATH, SCRIPT_NAME, SCRIPT_KEY)

# publish_data = {
#     "project": {"type": "Project", "id": 353},
#     "code": "ts0020_0010",
#     "description": "First publish from task",
#     "path": {"local_path": xxx,
#     "entity": {"type": "Task", "id": 15265},
#     "published_file_type": {"type": "PublishedFileType", "id": 1},
#     "version_number": 2,
#     "created_by": {"type": "HumanUser", "id": RETRIEVED_USER_ID}
# }
#
# publish = SG.create("PublishedFile", publish_data)
# print("Published file ID:", publish["id"])